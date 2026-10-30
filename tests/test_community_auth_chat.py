"""Authentication, durable sessions, private chat and membership boundaries."""

from fastapi.testclient import TestClient
from community.app import create_app
from community.security import digest, verify_password
from test_community_helpers import arena


def test_register_persists_hashed_password_and_session(arena):
    client = arena.client()
    credentials = {"username": "new_runner", "display_name": "새 러너", "password": "test-password-123"}
    result = client.post("/api/auth/register", json=credentials)
    assert result.status_code == 201
    assert "HttpOnly" in result.headers["set-cookie"] and "SameSite=strict" in result.headers["set-cookie"]
    token = client.cookies.get("oc_session")
    with arena.database() as db:
        stored = db.execute("SELECT password_hash FROM users WHERE username='new_runner'").fetchone()[0]
        assert stored != credentials["password"] and verify_password(credentials["password"], stored)
        assert db.execute("SELECT token_hash FROM sessions").fetchone()[0] == digest(token)
    reopened = TestClient(create_app(arena.path, clock=lambda: arena.timestamp,
                                     allowed_origins={"http://testserver"}), cookies={"oc_session": token})
    assert reopened.get("/api/session").json()["user"]["username"] == "new_runner"
    client.headers["X-CSRF-Token"] = result.json()["csrf"]
    assert client.post("/api/auth/logout").status_code == 200
    assert reopened.get("/api/session").json()["user"] is None
    reopened.close()
    assert client.post("/api/auth/login", json={k: credentials[k] for k in ("username", "password")}).status_code == 200


def test_csrf_origin_host_and_auth_boundaries(arena):
    anonymous = arena.client()
    assert anonymous.get("/api/groups").status_code == 401
    client = arena.client("sora")
    client.headers.pop("X-CSRF-Token")
    payload = {"client_id": "csrf-check-123", "body": "안녕하세요"}
    assert client.post("/api/groups/hangang/messages", json=payload).status_code == 403
    assert client.post("/api/auth/demo", json={"persona": "mira"}, headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.get("/api/session", headers={"Host": "evil.example"}).status_code == 400
    response = client.post("/api/auth/register", json={"username": "x", "display_name": "x", "password": "secret"})
    assert response.status_code == 422 and "secret" not in response.text
    assert client.post("/api/auth/demo", json={"persona": "mira", "role": "owner"}).status_code == 422


def test_demo_explicit_and_login_throttle(arena, tmp_path):
    disabled = TestClient(create_app(tmp_path / "off.sqlite3", allowed_origins={"http://testserver"}),
                          headers={"Origin": "http://testserver"})
    assert disabled.get("/api/session").json()["demo"] is False
    assert disabled.post("/api/auth/demo", json={"persona": "mira"}).status_code == 404
    disabled.close()
    client = arena.client()
    for _ in range(10):
        assert client.post("/api/auth/login", json={"username": "sora", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "sora", "password": "wrong"}).status_code == 429


def test_group_and_direct_id_isolation(arena):
    outsider = arena.client("outsider")
    for suffix in ("", "/messages", "/events", "/growth", "/members", "/announcements", "/audit", "/reports"):
        assert outsider.get("/api/groups/hangang" + suffix).status_code == 403
    assert outsider.get("/api/events/1").status_code == 403
    assert outsider.delete("/api/messages/1").status_code == 403
    assert outsider.get("/api/groups/unknown").status_code == 404
    assert outsider.get("/api/events/987654").status_code == 404
    sora = arena.client("sora")
    assert "attendees" not in sora.get("/api/events/1").json()
    assert sora.patch("/api/groups/hangang/preferences", json={"role": "owner"}).status_code == 422
    assert sora.post("/api/groups/hangang/announcements", json={"body": "관리자 흉내", "request_id": "forged-123"}).status_code == 403


def test_messages_idempotency_tombstone_rate_limit_and_read_cursor(arena):
    client = arena.client("sora")
    payload = {"client_id": "message-idempotent", "body": "함께 달려요"}
    first = client.post("/api/groups/hangang/messages", json=payload)
    duplicate = client.post("/api/groups/hangang/messages", json=payload)
    assert first.status_code == duplicate.status_code == 201 and first.json() == duplicate.json()
    assert client.post("/api/groups/hangang/messages", json={**payload, "body": "변경"}).status_code == 409
    assert client.delete(f"/api/messages/{first.json()['id']}").status_code == 200
    retry = client.post("/api/groups/hangang/messages", json=payload).json()
    assert retry["deleted"] and retry["body"] == ""
    assert client.delete("/api/messages/1").status_code == 403
    for number in range(5):
        assert client.post("/api/groups/hangang/messages", json={"client_id": f"rate-limit-{number}", "body": "안녕"}).status_code == 201
    assert client.post("/api/groups/hangang/messages", json={"client_id": "rate-limit-excess", "body": "안녕"}).status_code == 429
    read = client.post("/api/groups/hangang/read", json={"seq": 10000}).json()["read_seq"]
    assert client.post("/api/groups/hangang/read", json={"seq": 1}).json()["read_seq"] == read
    assert client.get("/api/groups/hangang/messages").json()["unread_count"] == 0


def test_chat_pages_latest_older_and_updates(arena):
    with arena.database() as db:
        membership = db.execute("SELECT id FROM memberships WHERE user_id='jun'").fetchone()[0]
        for index in range(70):
            db.execute("INSERT INTO messages(group_id,membership_id,client_id,body,created_at) VALUES(?,?,?,?,?)",
                       ("hangang", membership, f"page-{index}", f"기록 {index}", arena.timestamp - 400 + index))
    client = arena.client("sora")
    latest = client.get("/api/groups/hangang/messages").json()
    assert len(latest["items"]) == 50 and latest["has_more"]
    assert latest["items"][-1]["body"] == "기록 69"
    assert latest["next_cursor"] == latest["items"][0]["seq"]
    earlier = client.get(f"/api/groups/hangang/messages?before={latest['next_cursor']}").json()
    assert len(earlier["items"]) == 25 and not earlier["has_more"]
    assert earlier["items"][-1]["seq"] < latest["items"][0]["seq"]
    owner = arena.client("mira")
    assert owner.delete("/api/messages/2").status_code == 200
    refresh = client.get("/api/groups/hangang/messages?after=1&limit=200").json()
    assert refresh["items"][0]["deleted"] and refresh["items"][0]["body"] == ""


def test_leave_rejoin_has_new_history_epoch_and_removal_is_immediate(arena):
    owner, member = arena.client("mira"), arena.client("sora")
    invitation = owner.post("/api/groups/hangang/invites", json={}).json()
    with arena.database() as db:
        assert db.execute("SELECT token_hash FROM invites").fetchone()[0] == digest(invitation["token"])
    assert member.post("/api/groups/hangang/leave").status_code == 200
    assert member.get("/api/groups/hangang/messages").status_code == 403
    assert member.get("/api/events/1").status_code == 403
    assert member.get("/api/notifications").json()["items"] == []
    assert member.post(f"/api/invites/{invitation['token']}/join").status_code == 200
    assert member.get("/api/groups/hangang/messages").json()["items"] == []
    assert member.delete("/api/messages/2").status_code == 403
    assert member.get("/api/events/2").status_code == 403
    assert member.get("/api/groups/hangang/announcements").status_code == 200
    assert owner.delete("/api/groups/hangang/members/sora").status_code == 200
    assert member.post(f"/api/invites/{invitation['token']}/join").status_code == 403
    assert owner.post("/api/groups/hangang/leave").status_code == 409


def test_block_report_and_notification_permissions(arena):
    sora, mira, jun = arena.client("sora"), arena.client("mira"), arena.client("jun")
    assert sora.post("/api/groups/hangang/blocks/mira").status_code == 200
    assert all(item["author"]["id"] != "mira" for item in sora.get("/api/groups/hangang/messages").json()["items"])
    assert all(item["author"]["id"] != "sora" for item in mira.get("/api/groups/hangang/messages").json()["items"])
    assert sora.delete("/api/blocks/mira").status_code == 200
    report = sora.post("/api/groups/hangang/reports", json={"message_id": 1, "reason": "불편한 메시지"})
    assert report.status_code == 201
    assert mira.get("/api/groups/hangang/reports").json()["items"] == []
    path = f"/api/reports/{report.json()['id']}"
    assert mira.patch(path, json={"status": "reviewed"}).status_code == 403
    assert jun.patch(path, json={"status": "reviewed"}).status_code == 200
    assert sora.get("/api/groups/hangang/reports").status_code == 403
    assert sora.patch("/api/groups/hangang/preferences", json={"muted": True}).status_code == 200
    before = len(sora.get("/api/notifications").json()["items"])
    payload = {"body": "새 공지", "request_id": "announcement-123"}
    first, second = mira.post("/api/groups/hangang/announcements", json=payload), mira.post("/api/groups/hangang/announcements", json=payload)
    assert first.json()["id"] == second.json()["id"]
    assert len(sora.get("/api/notifications").json()["items"]) == before
    assert sora.post("/api/notifications/read").status_code == 200
    assert all(item["read"] for item in sora.get("/api/notifications").json()["items"])
