"""Shared, bounded visitor state. No external schema creation or credentials here."""

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import re
import secrets
import uuid
import psycopg
from fastapi import HTTPException
from community.database import iso
from community.postgres import DomainConnection, connection, privilege_violations, validate_dsn
from community.preview_store import validate_origin
from community.seed import seed_connection


def db_time(db):
    return float(db.execute("SELECT extract(epoch FROM clock_timestamp())").fetchone()[0])


@dataclass(frozen=True)
class PostgresGuest:
    id: uuid.UUID
    token_hash: str
    expires: float
    lease_id: uuid.UUID


class PostgresPreviewStore:
    def __init__(self, origin, dsn, ttl=3600, max_guests=16, creation_limit=6,
                 mutation_limit=500, writes_per_minute=60):
        self.origin = origin
        self.parsed = validate_origin(origin)
        self.secure = self.parsed.scheme == "https"
        validate_dsn(dsn)
        self._dsn = dsn
        self.ttl, self.max_guests, self.creation_limit = ttl, max_guests, creation_limit
        self.mutation_limit, self.writes_per_minute = mutation_limit, writes_per_minute
        self._validated = False

    @contextmanager
    def _connection(self):
        try:
            with connection(self._dsn) as db:
                if not self._validated:
                    if privilege_violations(db):
                        raise HTTPException(503, "체험 저장소의 전용 접근 권한을 확인해야 해요.")
                    self._validated = True
                yield db
        except psycopg.IntegrityError:
            raise HTTPException(409, "저장 상태가 바뀌었어요. 현재 상태를 다시 확인해 주세요.") from None
        except (psycopg.Error, ValueError):
            # Never return/log a DSN, SQL parameter or backend exception to the visitor.
            raise HTTPException(503, "체험 저장소에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.") from None

    def acquire(self, token, create, mutation):
        if token and not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise HTTPException(401, "체험 시간이 끝났어요. 새로고침하면 새 공간에서 시작해요.")
        if not token and not create:
            raise HTTPException(401, "체험 화면을 새로고침하고 역할을 선택해 주세요.")
        fresh = None
        with self._connection() as db:
            if not token:
                created = db.execute("SELECT created_at FROM guest_gate WHERE id=1 FOR UPDATE").fetchone()[0]
                timestamp = db_time(db)  # Recheck after lock wait, using the shared DB clock.
                db.execute("DELETE FROM leases WHERE expires_at<=%s", (timestamp,))
                db.execute("DELETE FROM guests g WHERE expires_at<=%s AND NOT EXISTS "
                           "(SELECT 1 FROM leases l WHERE l.guest_id=g.id)", (timestamp,))
                created = [value for value in created if value > timestamp - 60]
                count = db.execute("SELECT count(*) FROM guests").fetchone()[0]
                if count >= self.max_guests or len(created) >= self.creation_limit:
                    raise HTTPException(429, "체험 공간이 잠시 붐비고 있어요. 잠시 후 다시 시도해 주세요.")
                fresh = token = secrets.token_urlsafe(32)
                tenant = uuid.uuid4()
                db.execute("INSERT INTO guests(id,token_hash,expires_at) VALUES(%s,%s,%s)",
                           (tenant, hashlib.sha256(token.encode()).hexdigest(), timestamp + self.ttl))
                db.execute("UPDATE guest_gate SET created_at=%s WHERE id=1", (created + [timestamp],))
                db.execute("SELECT set_config('ourcommunity.tenant_id',%s,true)", (str(tenant),))
                seed_connection(DomainConnection(db), timestamp)
            digest = hashlib.sha256(token.encode()).hexdigest()
            row = db.execute("SELECT id,expires_at,mutations,requests,writes FROM guests WHERE token_hash=%s FOR UPDATE",
                             (digest,)).fetchone()
            timestamp = db_time(db)
            if not row or row[1] <= timestamp:
                raise HTTPException(401, "체험 시간이 끝났어요. 새로고침하면 새 공간에서 시작해요.")
            tenant, expiry, mutations, requests, writes = row
            db.execute("DELETE FROM leases WHERE guest_id=%s AND expires_at<=%s", (tenant, timestamp))
            requests = [value for value in requests if value > timestamp - 60]
            writes = [value for value in writes if value > timestamp - 60]
            inflight = db.execute("SELECT count(*) FROM leases WHERE guest_id=%s", (tenant,)).fetchone()[0]
            if inflight >= 8 or len(requests) >= 360:
                raise HTTPException(429, "요청이 너무 빨라요. 잠깐 기다려 주세요.")
            if mutation and (mutations >= self.mutation_limit or len(writes) >= self.writes_per_minute):
                raise HTTPException(429, "이번 체험의 변경 횟수를 다 썼어요. 잠시 쉬었다가 새 체험을 시작해 주세요.")
            db.execute("UPDATE guests SET requests=%s,writes=%s,mutations=%s WHERE id=%s",
                       (requests + [timestamp], writes + ([timestamp] if mutation else []), mutations + int(mutation), tenant))
            lease = uuid.uuid4()
            db.execute("INSERT INTO leases(id,guest_id,expires_at) VALUES(%s,%s,%s)", (lease, tenant, timestamp + 90))
            guest = PostgresGuest(tenant, digest, expiry, lease)
        # Admission commits separately so failed business transactions still consume budget.
        return guest, fresh

    @contextmanager
    def transaction(self, guest):
        with self._connection() as db:
            row = db.execute("SELECT expires_at FROM guests WHERE id=%s AND token_hash=%s FOR UPDATE",
                             (guest.id, guest.token_hash)).fetchone()
            timestamp = db_time(db)
            active = db.execute("SELECT 1 FROM leases WHERE id=%s AND guest_id=%s AND expires_at>%s",
                                (guest.lease_id, guest.id, timestamp)).fetchone()
            if not row or row[0] <= timestamp or not active:
                raise HTTPException(401, "체험 시간이 끝났어요. 새로고침하면 새 공간에서 시작해요.")
            db.execute("SELECT set_config('ourcommunity.tenant_id',%s,true)", (str(guest.id),))
            yield DomainConnection(db)

    def release(self, guest):
        try:
            with self._connection() as db:
                db.execute("DELETE FROM leases WHERE id=%s AND guest_id=%s", (guest.lease_id, guest.id))
        except HTTPException:
            # A terminated function or unavailable DB cannot leak an inflight count forever.
            # The 90-second shared lease expires; don't replace an already-sent response.
            pass

    def check(self):
        with self._connection() as db:
            db.execute("SELECT id FROM guest_gate WHERE id=1").fetchone()

    def metadata(self, guest=None):
        return {"enabled": True, "isolated": True, "persistent": False, "restart_resets": False,
                "storage": "postgresql", "ttl_seconds": self.ttl,
                "expires_at": iso(guest.expires) if guest else None,
                "mutation_limit": self.mutation_limit, "sharing_enabled": False}

    def close(self):
        # No process-global DB pool or cleanup thread; shared rows survive a cold start.
        pass
