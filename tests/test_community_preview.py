"""Public demo isolation, bounded allocation and expiry regression coverage."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from community.app import create_app
from community.preview_store import GUEST_COOKIE


ORIGIN = "https://preview.example"


@pytest.fixture
def preview(tmp_path):
    clock = [1793275200.0]
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "index.html").write_text("<!doctype html><title>ourcommunity</title>")
    (assets / "app.js").write_text("console.log('local');")
    app = create_app(preview=True, public_origin=ORIGIN, clock=lambda: clock[0],
                     preview_root=tmp_path, static_dir=assets, db_path=tmp_path / "never-created.sqlite3")
    yield app, clock
    app.state.preview_store.close()


def visitor(app):
    client = TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN})
    assert client.get("/api/session").status_code == 200
    return client


def role(client, persona="sora"):
    response = client.post("/api/auth/demo", json={"persona": persona})
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrf"]
    return response


def test_two_visitors_same_sample_ids_never_share_data(preview):
    app, _ = preview
    first, second = visitor(app), visitor(app)
    role(first)
    role(second)
    payload = {"client_id": "preview-private-id", "body": "나의 독립 체험 기록"}
    sent = first.post("/api/groups/hangang/messages", json=payload)
    assert sent.status_code == 201
    assert any(item["body"] == payload["body"] for item in first.get("/api/groups/hangang/messages").json()["items"])
    assert not any(item["body"] == payload["body"] for item in second.get("/api/groups/hangang/messages").json()["items"])
    assert second.delete(f"/api/messages/{sent.json()['id']}").status_code == 404
    original = second.cookies.get("oc_session")
    second.cookies.set("oc_session", first.cookies.get("oc_session"), domain="preview.example", path="/")
    assert second.get("/api/groups").status_code == 401
    second.cookies.set("oc_session", original, domain="preview.example", path="/")
    assert first.post("/api/auth/logout").status_code == 200
    role(first, "mira")
    assert any(item["body"] == payload["body"] for item in first.get("/api/groups/hangang/messages").json()["items"])
    assert not Path(app.state.db_path).exists()
    assert len(app.state.preview_store.guests) == 2


def test_missing_forged_expired_guest_does_not_allocate_or_merge(preview):
    app, clock = preview
    bare = TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN})
    assert bare.post("/api/auth/demo", json={"persona": "mira"}).status_code == 401
    assert len(app.state.preview_store.guests) == 0
    bare.cookies.set(GUEST_COOKIE, "not-a-valid-namespace")
    assert bare.get("/api/session").status_code == 401
    assert len(app.state.preview_store.guests) == 0
    client = visitor(app)
    role(client)
    guest = next(iter(app.state.preview_store.guests.values()))
    folder = guest.path.parent
    clock[0] += 3601
    assert client.get("/api/groups").status_code == 401
    assert not folder.exists()
    assert client.get("/api/session").json()["user"] is None
    assert len(app.state.preview_store.guests) == 1


def test_guest_cap_and_creation_races_are_atomic(tmp_path):
    app = create_app(preview=True, public_origin=ORIGIN, preview_root=tmp_path,
                     preview_limits={"max_guests": 3, "creation_limit": 3})
    try:
        clients = [TestClient(app, base_url=ORIGIN) for _ in range(8)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(lambda client: client.get("/api/session").status_code, clients))
        assert statuses.count(200) == 3 and statuses.count(429) == 5
        assert len(list(app.state.preview_store.root.iterdir())) == 3
        for client in clients:
            client.close()
    finally:
        app.state.preview_store.close()


def test_expired_database_waits_for_inflight_release(preview):
    app, clock = preview
    client = visitor(app)
    store = app.state.preview_store
    guest, _ = store.acquire(client.cookies.get(GUEST_COOKIE), False, False)
    clock[0] += 3601
    with pytest.raises(Exception) as failure:
        store.acquire(client.cookies.get(GUEST_COOKIE), False, False)
    assert failure.value.status_code == 401
    assert guest.path.exists()
    store.release(guest)
    assert not guest.path.parent.exists()


def test_mutation_and_creation_rate_limits_recover(tmp_path):
    clock = [1793275200.0]
    app = create_app(preview=True, public_origin=ORIGIN, preview_root=tmp_path, clock=lambda: clock[0],
                     preview_limits={"creation_limit": 1, "writes_per_minute": 1, "mutation_limit": 2})
    try:
        first = visitor(app)
        role(first)
        assert first.post("/api/groups/hangang/read", json={"seq": 1}).status_code == 429
        second = TestClient(app, base_url=ORIGIN)
        assert second.get("/api/session").status_code == 429
        clock[0] += 61
        assert second.get("/api/session").status_code == 200
        assert first.post("/api/groups/hangang/read", json={"seq": 1}).status_code == 200
        clock[0] += 61
        assert first.post("/api/groups/hangang/read", json={"seq": 1}).status_code == 429
    finally:
        app.state.preview_store.close()


@pytest.mark.parametrize("origin", [None, "http://public.example", "https://*.example", "https://preview.example/", "https://user:password@preview.example"])
def test_origin_configuration_fails_closed(origin):
    with pytest.raises(ValueError):
        create_app(preview=True, public_origin=origin)


def test_preview_has_no_real_auth_invitation_or_public_sharing(preview):
    app, _ = preview
    client = visitor(app)
    role(client, "mira")
    for path in ("/auth/register", "/auth/login", "/groups/hangang/invites", "/invites/unknown/join"):
        assert client.post("/api" + path, json={}).status_code == 403
    assert client.get("/api/public/groups/hangang").status_code == 403
    assert client.patch("/api/groups/hangang/settings", json={"public_space": True, "version": 1}).status_code == 403
    assert client.patch("/api/groups/hangang/settings", json={"palette": "forest", "version": 1}).status_code == 200
    assert client.get("/api/session").json()["preview"]["sharing_enabled"] is False


def test_cookie_headers_origin_host_and_static_boundaries(preview):
    app, _ = preview
    client = TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN})
    result = client.get("/api/session")
    assert all(part in result.headers["set-cookie"] for part in ("HttpOnly", "SameSite=Strict", "Secure"))
    assert "Secure" in role(client).headers["set-cookie"]
    assert client.get("/api/session", headers={"Host": "attacker.example"}).status_code == 400
    assert client.post("/api/auth/demo", json={"persona": "mira"}, headers={"Origin": "https://attacker.example"}).status_code == 403
    assert client.post("/api/auth/demo", json={"persona": "mira"}, headers={"Origin": "null"}).status_code == 403
    assert client.get("/api/session", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    navigation = {"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Dest": "document"}
    assert client.get("/groups/hangang/chat", headers=navigation).status_code == 200
    assert client.get("/api/session", headers=navigation).status_code == 403
    assert client.get("/groups/hangang/chat").headers["content-type"].startswith("text/html")
    assert client.get("/api/missing").status_code == 404
    assert client.get("/api").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/assets/missing.js").status_code == 404
    assert client.get("/app.js").status_code == 200
    assert client.get("/%2e%2e/requirements-app.txt").status_code == 404
    for path in ("/%00", "/assets/%00.js", "/" + "a" * 300):
        assert client.get(path).status_code == 404
    assert result.headers["X-Robots-Tag"] == "noindex, nofollow"
    assert "frame-ancestors 'none'" in result.headers["Content-Security-Policy"]


def test_streamed_body_limit_does_not_trust_content_length(preview):
    app, _ = preview
    client = visitor(app)
    role(client)
    response = client.post("/api/groups/hangang/messages", content=(b"x" * 10000 for _ in range(3)),
                           headers={"Content-Length": "1", "Content-Type": "application/json"})
    assert response.status_code == 413
    assert client.get("/api/groups/hangang/messages").status_code == 200
    malformed = client.post("/api/groups/hangang/read", json={"seq": 1},
                            headers=[(b"origin", ORIGIN.encode()), (b"x-csrf-token", b"\xe9")])
    assert malformed.status_code == 403
    huge_length = client.post("/api/groups/hangang/read", content=b"{}", headers={"Content-Length": "1" * 5000})
    assert huge_length.status_code == 413
    nondecimal = client.post("/api/groups/hangang/read", content=b"{}", headers=[(b"content-length", b"\xb2")])
    assert nondecimal.status_code == 413


def test_process_restart_never_restores_or_merges_old_guest(preview, tmp_path):
    first_app, _ = preview
    first = visitor(first_app)
    role(first)
    first.post("/api/groups/hangang/messages", json={"client_id": "restart-proof-123", "body": "이전 프로세스의 기록"})
    replacement = create_app(preview=True, public_origin=ORIGIN, preview_root=tmp_path)
    try:
        second = TestClient(replacement, base_url=ORIGIN, headers={"Origin": ORIGIN}, cookies=first.cookies)
        assert second.get("/api/session").status_code == 401
        assert len(replacement.state.preview_store.guests) == 0
        assert second.get("/api/session").status_code == 200
        role(second)
        messages = second.get("/api/groups/hangang/messages").json()["items"]
        assert not any(item["body"] == "이전 프로세스의 기록" for item in messages)
        assert first_app.state.preview_store.root != replacement.state.preview_store.root
    finally:
        replacement.state.preview_store.close()
