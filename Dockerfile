FROM node:24-bookworm-slim AS web_build
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/build_ca; fi; npm ci
COPY web/ ./
# Token output is checked by repository QA; the runtime build requires no Python tooling.
RUN npx tsc --noEmit && npx vite build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PREVIEW_MODE=1 PORT=8080 WEB_CONCURRENCY=1
WORKDIR /app
COPY requirements-app.txt ./
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; \
    pip install --no-cache-dir -r requirements-app.txt && useradd --uid 10001 --create-home preview
COPY --chown=preview:preview community/ ./community/
COPY --from=web_build --chown=preview:preview /build/web/dist ./web/dist/
USER preview
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import os,urllib.request,urllib.parse; origin=os.environ['PUBLIC_ORIGIN']; request=urllib.request.Request('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/api/health',headers={'Host':urllib.parse.urlsplit(origin).netloc}); urllib.request.urlopen(request,timeout=3)"
CMD ["sh", "-c", "exec uvicorn community.app:app --host 0.0.0.0 --port \"${PORT:-8080}\" --workers 1 --no-proxy-headers --limit-concurrency 128 --timeout-keep-alive 5"]
