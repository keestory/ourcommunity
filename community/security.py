"""Authentication and authorization shared by every API resource."""

import hashlib
import hmac
import secrets
from fastapi import HTTPException
from community.database import now


COOKIE = "oc_session"
STAFF = {"owner", "organizer"}
DEMO_USER_IDS = frozenset({"mira", "jun", "sora", "haneul", "jiho", "yuna", "min", "sol", "outsider"})


def identity_enabled(request, user_id):
    """A reused demo database must not grant sample identities in ordinary mode."""
    return request.app.state.demo or user_id not in DEMO_USER_IDS


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password):
    salt = secrets.token_hex(16)
    key = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1)
    return salt + ":" + key.hex()


def verify_password(password, stored):
    try:
        salt, expected = stored.split(":")
        actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1)
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def user_view(user):
    return {key: user[key] for key in ("id", "username", "display_name", "color")}


def session_row(request, db):
    token = request.cookies.get(COOKIE, "")
    row = db.execute(
        "SELECT s.*,u.username,u.display_name,u.color FROM sessions s "
        "JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?",
        (digest(token), now(request)),
    ).fetchone()
    return row if row and identity_enabled(request, row["user_id"]) else None


def current_user(request, db):
    session = session_row(request, db)
    if not session:
        raise HTTPException(401, "로그인이 필요해요. 다시 로그인해 주세요.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        supplied = request.headers.get("x-csrf-token", "")
        if not hmac.compare_digest(supplied, session["csrf"]):
            raise HTTPException(403, "요청을 확인할 수 없어요. 새로고침 후 다시 시도해 주세요.")
    return {"id": session["user_id"], **{k: session[k] for k in ("username", "display_name", "color")}}


def member(db, group_id, user_id, staff=False):
    if not db.execute("SELECT 1 FROM groups WHERE id=?", (group_id,)).fetchone():
        raise HTTPException(404, "그룹을 찾을 수 없어요.")
    row = db.execute(
        "SELECT * FROM memberships WHERE group_id=? AND user_id=? AND state='active'",
        (group_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(403, "이 그룹의 멤버만 볼 수 있어요. 초대를 통해 가입해 주세요.")
    if staff and row["role"] not in STAFF:
        raise HTTPException(403, "그룹 운영자만 할 수 있는 작업이에요.")
    return row


def event_for(db, event_id, user_id, staff=False):
    event = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    if not event:
        raise HTTPException(404, "모임을 찾을 수 없어요.")
    membership = member(db, event["group_id"], user_id, staff)
    if event["starts_at"] < membership["joined_at"]:
        raise HTTPException(403, "가입 이전에 진행된 모임에는 접근할 수 없어요.")
    return event, membership


def create_session(request, response, db, user):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.execute("DELETE FROM sessions WHERE expires_at<=?", (now(request),))
    old = request.cookies.get(COOKIE)
    if old:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (digest(old),))
    db.execute("INSERT INTO sessions VALUES(?,?,?,?)", (digest(token), user["id"], csrf, now(request) + 86400 * 7))
    response.set_cookie(COOKIE, token, max_age=86400 * 7, httponly=True, samesite="strict", secure=False)
    return {"user": user_view(user), "csrf": csrf, "demo": request.app.state.demo}
