"""Regression scenarios independently discovered in the local product review."""

import pytest
from fastapi.testclient import TestClient
from community.app import create_app
from test_community_helpers import arena, rsvp


def test_spent_invite_retry_does_not_consume_or_regrant_membership(arena):
    owner, newcomer = arena.client("mira"), arena.client("outsider")
    token = owner.post("/api/groups/hangang/invites", json={"max_uses": 1}).json()["token"]
    path = f"/api/invites/{token}/join"
    assert newcomer.post(path).status_code == 200
    assert newcomer.post(path).status_code == 200
    with arena.database() as db:
        assert db.execute("SELECT uses FROM invites").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM memberships WHERE group_id='hangang' AND user_id='outsider'").fetchone()[0] == 1
    assert newcomer.post("/api/groups/hangang/leave").status_code == 200
    assert newcomer.post(path).status_code == 404
    assert newcomer.get("/api/groups/hangang/messages").status_code == 403


def test_muted_waiter_receives_seat_without_notification(arena):
    owner, organizer, waiter = [arena.client(user) for user in ("mira", "jun", "sora")]
    assert waiter.patch("/api/groups/hangang/preferences", json={"muted": True}).status_code == 200
    event_id = arena.event(owner)["id"]
    for client in (owner, organizer, waiter):
        assert rsvp(client, event_id).status_code == 200
    assert rsvp(owner, event_id, "cancel").status_code == 200
    assert waiter.get(f"/api/events/{event_id}").json()["my_status"] == "offered"
    assert not any(item["kind"] == "seat_offer" for item in waiter.get("/api/notifications").json()["items"])
    assert rsvp(waiter, event_id, "accept").json()["my_status"] == "confirmed"


@pytest.mark.parametrize("departure", ["leave", "remove"])
def test_former_member_negative_correction_retains_permission_boundary(arena, departure):
    owner, former, outsider = [arena.client(user) for user in ("mira", "sora", "outsider")]
    if departure == "leave":
        assert former.post("/api/groups/hangang/leave").status_code == 200
    else:
        assert owner.delete("/api/groups/hangang/members/sora").status_code == 200
    path = "/api/events/2/attendance"
    negative = {"user_id": "sora", "present": False}
    assert outsider.post(path, json=negative).status_code == 403
    assert former.post(path, json=negative).status_code == 403
    assert owner.post(path, json={**negative, "present": True}).status_code == 403
    assert owner.post(path, json=negative).status_code == 200
    assert owner.post(path, json=negative).status_code == 200
    assert owner.get("/api/groups/hangang/growth").json()["total_contributions"] == 3
    assert len([item for item in owner.get("/api/groups/hangang/audit").json()["items"]
                if item["action"] == "attendance_revised"]) == 1


@pytest.mark.parametrize("persona", ["mira", "jun", "sora", "haneul", "jiho", "yuna", "min", "sol", "outsider"])
def test_disabling_demo_blocks_all_seeded_logins_and_existing_sessions(arena, persona):
    seeded = arena.client(persona)
    closed_app = create_app(arena.path, demo=False, clock=lambda: arena.timestamp,
                            allowed_origins={"http://testserver"})
    with TestClient(closed_app, headers={"Origin": "http://testserver"},
                    cookies={"oc_session": seeded.cookies.get("oc_session")}) as client:
        assert client.get("/api/session").json() == {"user": None, "csrf": None, "demo": False}
        assert client.get("/api/groups").status_code == 401
        assert client.post("/api/auth/login", json={"username": persona, "password": "local-demo-only-2026"}).status_code == 401


def test_ordinary_account_with_seed_username_is_not_a_demo_identity(tmp_path):
    app = create_app(tmp_path / "ordinary.sqlite3", demo=False, allowed_origins={"http://testserver"})
    with TestClient(app, headers={"Origin": "http://testserver"}) as client:
        response = client.post("/api/auth/register", json={"username": "mira", "display_name": "테스트", "password": "ordinary-test-password"})
        assert response.status_code == 201
        assert response.json()["user"]["id"].startswith("u_")
        assert client.get("/api/session").json()["user"]["username"] == "mira"
        assert client.post("/api/auth/login", json={"username": "mira", "password": "ordinary-test-password"}).status_code == 200
