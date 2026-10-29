"""Local account and explicitly enabled synthetic demo sessions."""

import secrets
import sqlite3
from fastapi import APIRouter, HTTPException, Request, Response
from community.database import now, transaction
from community.schemas import DemoInput, LoginInput, RegisterInput
from community.security import (
    COOKIE, create_session, current_user, digest, hash_password,
    identity_enabled, session_row, verify_password,
)


ROUTER = APIRouter(prefix="/api")


@ROUTER.get("/session")
def session(request: Request):
    with transaction(request) as db:
        row = session_row(request, db)
        user = None
        if row:
            user = {"id": row["user_id"], **{k: row[k] for k in ("username", "display_name", "color")}}
        return {"user": user, "csrf": row["csrf"] if row else None, "demo": request.app.state.demo}


@ROUTER.post("/auth/demo")
def demo_login(data: DemoInput, request: Request, response: Response):
    if not request.app.state.demo:
        raise HTTPException(404, "체험 로그인이 꺼져 있어요.")
    with transaction(request) as db:
        user = db.execute("SELECT * FROM users WHERE id=?", (data.persona,)).fetchone()
        if not user:
            raise HTTPException(404, "체험 계정을 찾을 수 없어요.")
        return create_session(request, response, db, user)


@ROUTER.post("/auth/register", status_code=201)
def register(data: RegisterInput, request: Request, response: Response):
    with transaction(request) as db:
        user_id = "u_" + secrets.token_hex(8)
        try:
            db.execute("INSERT INTO users(id,username,display_name,password_hash) VALUES(?,?,?,?)",
                       (user_id, data.username.lower(), data.display_name, hash_password(data.password)))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "이미 사용하는 아이디예요. 다른 아이디를 입력해 주세요.") from None
        user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return create_session(request, response, db, user)


@ROUTER.post("/auth/login")
def login(data: LoginInput, request: Request, response: Response):
    with transaction(request) as db:
        timestamp = now(request)
        key = digest((request.client.host if request.client else "local") + data.username.lower())
        db.execute("DELETE FROM login_attempts WHERE created_at<?", (timestamp - 900,))
        count = db.execute("SELECT count(*) FROM login_attempts WHERE key=?", (key,)).fetchone()[0]
        if count >= 10:
            raise HTTPException(429, "잠시 후 다시 로그인해 주세요.")
        user = db.execute("SELECT * FROM users WHERE username=?", (data.username.lower(),)).fetchone()
        if not user or not identity_enabled(request, user["id"]) or not verify_password(data.password, user["password_hash"]):
            db.execute("INSERT INTO login_attempts VALUES(?,?)", (key, timestamp))
            db.commit()
            raise HTTPException(401, "아이디 또는 비밀번호를 확인해 주세요.")
        db.execute("DELETE FROM login_attempts WHERE key=?", (key,))
        return create_session(request, response, db, user)


@ROUTER.post("/auth/logout")
def logout(request: Request, response: Response):
    with transaction(request) as db:
        current_user(request, db)
        db.execute("DELETE FROM sessions WHERE token_hash=?", (digest(request.cookies.get(COOKIE, "")),))
        response.delete_cookie(COOKIE, httponly=True, samesite="strict")
        return {"ok": True}
