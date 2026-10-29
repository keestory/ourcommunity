"""Local-only ASGI entry point. Public deployment needs a separate security design."""

import os
from pathlib import Path
import time
from urllib.parse import urlsplit
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from community import auth_routes, chat_routes, event_routes, group_routes, growth, safety_routes
from community.database import initialize
from community.seed import seed_demo


ORIGINS = {f"http://{host}:{port}" for host in ("localhost", "127.0.0.1") for port in (5173, 4173, 8000)}


def create_app(db_path=None, demo=False, clock=None, allowed_origins=None):
    application = FastAPI(title="ourcommunity · local prototype", docs_url=None, redoc_url=None)
    application.state.db_path = Path(db_path or os.environ.get("COMMUNITY_DB", ".harness/community.sqlite3"))
    application.state.demo = demo
    application.state.clock = clock or time.time
    application.state.allowed_origins = set(allowed_origins or ORIGINS)
    initialize(application.state.db_path)
    if demo:
        seed_demo(application.state.db_path, application.state.clock())

    @application.middleware("http")
    async def local_boundary(request: Request, call_next):
        hostname = request.url.hostname
        allowed_hosts = {urlsplit(origin).hostname for origin in application.state.allowed_origins}
        if hostname not in allowed_hosts:
            return JSONResponse({"detail": "로컬 실행 주소에서만 사용할 수 있어요."}, status_code=400)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.headers.get("origin") not in application.state.allowed_origins:
                return JSONResponse({"detail": "허용되지 않은 요청 출처예요."}, status_code=403)
            length = request.headers.get("content-length", "0")
            if not length.isdigit() or int(length) > 16384:
                return JSONResponse({"detail": "요청이 너무 커요."}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request, exception):
        fields = [{"field": ".".join(str(part) for part in e["loc"][1:]),
                   "message": "입력 형식과 길이를 확인해 주세요."} for e in exception.errors()]
        return JSONResponse({"detail": "입력한 내용을 확인해 주세요.", "fields": fields}, status_code=422)

    @application.get("/api/health")
    def health():
        return {"status": "ok", "demo": demo, "external_auth": False, "push_connected": False}

    for router in (auth_routes.ROUTER, group_routes.ROUTER, chat_routes.ROUTER,
                   event_routes.ROUTER, growth.ROUTER, safety_routes.ROUTER):
        application.include_router(router)
    return application


app = create_app(demo=os.environ.get("DEMO_MODE") == "1")
