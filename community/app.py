"""Local product and isolated previews, with explicit storage and host boundaries."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
import time
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from community import auth_routes, chat_routes, event_routes, group_routes, growth, safety_routes
from community.database import initialize
from community.seed import seed_demo
from community.preview_boundary import PreviewBoundary
from community.preview_store import PreviewStore, preview_metadata


ORIGINS = {f"http://{host}:{port}" for host in ("localhost", "127.0.0.1") for port in (5173, 4173, 8000)}


def create_app(db_path=None, demo=False, clock=None, allowed_origins=None, preview=False,
               public_origin=None, preview_root=None, preview_limits=None, static_dir=None, postgres_dsn=None):
    if os.environ.get("VERCEL") == "1" and (not preview or not postgres_dsn):
        raise ValueError("Vercel preview requires PREVIEW_MODE=1 and shared PREVIEW_DATABASE_URL")
    if not public_origin and os.environ.get("VERCEL") == "1" and os.environ.get("VERCEL_URL"):
        public_origin = "https://" + os.environ["VERCEL_URL"]
    @asynccontextmanager
    async def lifespan(instance):
        yield
        if instance.state.preview_store:
            instance.state.preview_store.close()

    application = FastAPI(title="ourcommunity · prototype", docs_url=None, redoc_url=None, lifespan=lifespan,
                          openapi_url=None if preview else "/openapi.json")
    application.state.db_path = Path(db_path or os.environ.get("COMMUNITY_DB", ".harness/community.sqlite3"))
    application.state.demo = demo or preview
    application.state.clock = clock or time.time
    application.state.allowed_origins = set(allowed_origins or ORIGINS)
    application.state.preview_store = None
    if postgres_dsn and not preview:
        raise ValueError("Shared PostgreSQL is available only for isolated preview")
    if preview and postgres_dsn:
        from community.postgres_preview import PostgresPreviewStore
        application.state.preview_store = PostgresPreviewStore(public_origin, postgres_dsn, **(preview_limits or {}))
    elif preview:
        if os.environ.get("WEB_CONCURRENCY", "1") != "1":
            raise ValueError("Preview requires exactly one worker")
        application.state.preview_store = PreviewStore(public_origin, application.state.clock,
                                                       root=preview_root, **(preview_limits or {}))
    else:
        initialize(application.state.db_path)
        if demo:
            seed_demo(application.state.db_path, application.state.clock())

    @application.middleware("http")
    async def local_boundary(request: Request, call_next):
        if preview:
            return await call_next(request)
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
    def health(request: Request):
        store = application.state.preview_store
        if store and hasattr(store, "check"):
            store.check()
        return {"status": "ok", "demo": demo or preview, "external_auth": False,
                "push_connected": False, **preview_metadata(request)}

    for router in (auth_routes.ROUTER, group_routes.ROUTER, chat_routes.ROUTER,
                   event_routes.ROUTER, growth.ROUTER, safety_routes.ROUTER):
        application.include_router(router)
    if preview:
        application.add_middleware(PreviewBoundary, store=application.state.preview_store)
        assets = Path(static_dir or Path(__file__).resolve().parent.parent / "web" / "dist").resolve()

        @application.get("/{path:path}")
        def preview_frontend(path: str):
            if path == "api" or path.startswith("api/") or any(ord(char) < 32 or ord(char) == 127 for char in path):
                raise HTTPException(404, "찾을 수 없는 주소예요.")
            try:
                target = (assets / path).resolve()
                if not target.is_relative_to(assets):
                    raise HTTPException(404, "찾을 수 없는 주소예요.")
                if target.is_file():
                    return FileResponse(target)
            except (ValueError, OSError):
                raise HTTPException(404, "찾을 수 없는 주소예요.") from None
            if path.startswith("assets/") or Path(path).suffix:
                raise HTTPException(404, "파일을 찾을 수 없어요.")
            if not (assets / "index.html").is_file():
                raise HTTPException(503, "체험 화면을 준비하고 있어요.")
            return FileResponse(assets / "index.html")
    return application


app = create_app(demo=os.environ.get("DEMO_MODE") == "1", preview=os.environ.get("PREVIEW_MODE") == "1",
                 public_origin=os.environ.get("PUBLIC_ORIGIN"), postgres_dsn=os.environ.get("PREVIEW_DATABASE_URL"))
