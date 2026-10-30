"""Bounded, single-process visitor sandboxes. Never opens the local product DB."""

import atexit
from collections import deque
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import re
import secrets
import shutil
import tempfile
import threading
from urllib.parse import urlsplit
from fastapi import HTTPException
from community.database import initialize, iso
from community.seed import seed_demo


GUEST_COOKIE = "oc_preview_guest"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def validate_origin(value):
    parsed = urlsplit(value or "")
    if (not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query
            or parsed.fragment or parsed.scheme not in {"http", "https"} or "*" in value):
        raise ValueError("PREVIEW_MODE requires one exact PUBLIC_ORIGIN without a path")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Public preview requires HTTPS; HTTP is allowed only on loopback")
    if parsed.port == 443 and parsed.scheme == "https":
        raise ValueError("Omit the default HTTPS port from PUBLIC_ORIGIN")
    return parsed


@dataclass
class Guest:
    path: Path
    expires: float
    inflight: int = 0
    mutations: int = 0
    writes: deque = field(default_factory=deque)
    requests: deque = field(default_factory=deque)


class PreviewStore:
    def __init__(self, origin, clock, root=None, ttl=3600, max_guests=16, creation_limit=6,
                 mutation_limit=500, writes_per_minute=60):
        self.origin = origin
        self.parsed = validate_origin(origin)
        self.secure = self.parsed.scheme == "https"
        self.clock, self.ttl = clock, ttl
        self.max_guests, self.creation_limit = max_guests, creation_limit
        self.mutation_limit, self.writes_per_minute = mutation_limit, writes_per_minute
        self.directory = tempfile.TemporaryDirectory(prefix="ourcommunity-preview-", dir=root)
        self.root = Path(self.directory.name)
        self.lock = threading.RLock()
        self.guests, self.created = {}, deque()
        self.stopped = threading.Event()
        self.cleaner = threading.Thread(target=self._clean_loop, daemon=True)
        self.cleaner.start()
        atexit.register(self.close)

    def _clean_loop(self):
        while not self.stopped.wait(30):
            with self.lock:
                self._clean(self.clock())

    def _clean(self, timestamp):
        for key, guest in list(self.guests.items()):
            if guest.expires <= timestamp and not guest.inflight:
                shutil.rmtree(guest.path.parent)
                del self.guests[key]
        while self.created and self.created[0] <= timestamp - 60:
            self.created.popleft()

    def acquire(self, token, create, mutation):
        with self.lock:
            timestamp = self.clock()
            self._clean(timestamp)
            fresh = None
            key = hashlib.sha256((token or "").encode()).hexdigest()
            guest = self.guests.get(key)
            if token and (not re.fullmatch(r"[A-Za-z0-9_-]{43}", token) or not guest or guest.expires <= timestamp):
                raise HTTPException(401, "체험 시간이 끝났어요. 새로고침하면 새 공간에서 시작해요.")
            if not guest:
                if not create:
                    raise HTTPException(401, "체험 화면을 새로고침하고 역할을 선택해 주세요.")
                if len(self.guests) >= self.max_guests or len(self.created) >= self.creation_limit:
                    raise HTTPException(429, "체험 공간이 잠시 붐비고 있어요. 잠시 후 다시 시도해 주세요.")
                fresh = secrets.token_urlsafe(32)
                key = hashlib.sha256(fresh.encode()).hexdigest()
                folder = self.root / secrets.token_hex(16)
                folder.mkdir(mode=0o700)
                guest = Guest(folder / "demo.sqlite3", timestamp + self.ttl)
                try:
                    initialize(guest.path)
                    seed_demo(guest.path, timestamp)
                except Exception:
                    shutil.rmtree(folder)
                    raise
                self.guests[key] = guest
                self.created.append(timestamp)
            for queue in (guest.requests, guest.writes):
                while queue and queue[0] <= timestamp - 60:
                    queue.popleft()
            if guest.inflight >= 8 or len(guest.requests) >= 360:
                raise HTTPException(429, "요청이 너무 빨라요. 잠깐 기다려 주세요.")
            if mutation and (guest.mutations >= self.mutation_limit or len(guest.writes) >= self.writes_per_minute):
                raise HTTPException(429, "이번 체험의 변경 횟수를 다 썼어요. 잠시 쉬었다가 새 체험을 시작해 주세요.")
            guest.requests.append(timestamp)
            if mutation:
                guest.mutations += 1
                guest.writes.append(timestamp)
            guest.inflight += 1
            return guest, fresh

    def release(self, guest):
        with self.lock:
            guest.inflight -= 1
            self._clean(self.clock())

    def metadata(self, guest=None):
        return {"enabled": True, "isolated": True, "persistent": False, "restart_resets": True, "ttl_seconds": self.ttl,
                "expires_at": iso(guest.expires) if guest else None,
                "mutation_limit": self.mutation_limit, "sharing_enabled": False}

    def close(self):
        self.stopped.set()
        with self.lock:
            if not any(guest.inflight for guest in self.guests.values()):
                self.guests.clear()
                self.directory.cleanup()


def preview_metadata(request):
    store = getattr(request.app.state, "preview_store", None)
    return {"preview": store.metadata(getattr(request.state, "preview_guest", None))} if store else {}
