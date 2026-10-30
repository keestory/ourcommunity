"""ASGI boundary validates authority and caps streamed bodies before parsing."""

import asyncio
from http.cookies import SimpleCookie
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from community.preview_store import GUEST_COOKIE, SAFE_METHODS


BODY_LIMIT = 16384
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; "
       "base-uri 'none'; frame-ancestors 'none'; form-action 'self'")


class PreviewBoundary:
    def __init__(self, app, store):
        self.app, self.store = app, store

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        guest, fresh = None, None

        async def secure_send(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for key, value in {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                                   "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
                                   "Content-Security-Policy": CSP, "X-Robots-Tag": "noindex, nofollow"}.items():
                    headers[key] = value
                if self.store.secure:
                    headers["Strict-Transport-Security"] = "max-age=86400"
                if fresh:
                    cookie = SimpleCookie()
                    cookie[GUEST_COOKIE] = fresh
                    morsel = cookie[GUEST_COOKIE]
                    morsel["path"], morsel["httponly"], morsel["samesite"] = "/", True, "Strict"
                    morsel["max-age"] = str(self.store.ttl)
                    if self.store.secure:
                        morsel["secure"] = True
                    headers.append("set-cookie", morsel.OutputString())
            await send(message)

        try:
            headers = Headers(scope=scope)
            self._validate(scope, headers)
            payload = await self._body(scope, receive)
            consumed = False

            async def bounded_receive():
                nonlocal consumed
                if consumed:
                    return await receive()
                consumed = True
                return {"type": "http.request", "body": payload, "more_body": False}

            path = scope["path"]
            if path.startswith("/api/") and path != "/api/health":
                if path.startswith(("/api/invites/", "/api/public/")) or path.endswith("/invites"):
                    raise HTTPException(403, "개별 체험에서는 다른 사람 초대와 공개 공유를 지원하지 않아요.")
                if path in {"/api/auth/login", "/api/auth/register"}:
                    raise HTTPException(403, "체험 전용 화면이에요. 가상 역할을 선택해 주세요.")
                cookie = SimpleCookie()
                cookie.load(headers.get("cookie", ""))
                token = cookie[GUEST_COOKIE].value if GUEST_COOKIE in cookie else None
                guest, fresh = await run_in_threadpool(self.store.acquire, token,
                    path == "/api/session" and scope["method"] == "GET", scope["method"] not in SAFE_METHODS)
                scope.setdefault("state", {}).update(db_path=guest.path, preview_guest=guest)
            await self.app(scope, bounded_receive, secure_send)
        except HTTPException as error:
            response = JSONResponse({"detail": error.detail}, status_code=error.status_code)
            if error.status_code == 401:
                response.delete_cookie(GUEST_COOKIE, secure=self.store.secure, httponly=True, samesite="strict")
                response.delete_cookie("oc_session", secure=self.store.secure, httponly=True, samesite="strict")
            if error.status_code == 429:
                response.headers["Retry-After"] = "60"
            await response(scope, receive, secure_send)
        finally:
            if guest:
                self.store.release(guest)

    def _validate(self, scope, headers):
        for name in ("host", "origin", "content-length", "cookie"):
            if len(headers.getlist(name)) > 1:
                raise HTTPException(400, "중복된 요청 헤더예요.")
        if headers.get("host", "").lower() != self.store.parsed.netloc.lower():
            raise HTTPException(400, "체험 주소를 확인해 주세요.")
        if scope["method"] not in SAFE_METHODS and headers.get("origin") != self.store.origin:
            raise HTTPException(403, "허용되지 않은 요청 출처예요.")
        external_navigation = (scope["method"] in {"GET", "HEAD"}
                               and not scope["path"].startswith("/api")
                               and headers.get("sec-fetch-mode") == "navigate"
                               and headers.get("sec-fetch-dest") == "document")
        if headers.get("sec-fetch-site") == "cross-site" and not external_navigation:
            raise HTTPException(403, "체험 주소에서 직접 열어 주세요.")
        length = headers.get("content-length", "0")
        if not length.isascii() or not length.isdigit() or len(length) > 8 or int(length) > BODY_LIMIT:
            raise HTTPException(413, "요청이 너무 커요.")

    async def _body(self, scope, receive):
        chunks, size = [], 0
        try:
            async with asyncio.timeout(10):
                while True:
                    message = await receive()
                    if message["type"] != "http.request":
                        raise HTTPException(400, "요청이 중단되었어요.")
                    chunk = message.get("body", b"")
                    size += len(chunk)
                    if size > BODY_LIMIT:
                        raise HTTPException(413, "요청이 너무 커요.")
                    chunks.append(chunk)
                    if not message.get("more_body"):
                        return b"".join(chunks)
        except TimeoutError:
            raise HTTPException(408, "요청 시간이 초과됐어요.") from None
