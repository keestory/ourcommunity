"""Concurrent last-seat transactions, explicit offers and verified attendance."""

from concurrent.futures import ThreadPoolExecutor
from community.database import iso
from test_community_helpers import arena, rsvp


def test_concurrent_last_seats_and_duplicate_retries(arena):
    owner = arena.client("mira")
    event = arena.event(owner)
    clients = [arena.client(user) for user in ("mira", "jun", "sora", "haneul", "jiho", "yuna")]
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda client: rsvp(client, event["id"]), clients))
    assert all(response.status_code == 200 for response in results)
    assert sorted(response.json()["my_status"] for response in results) == ["confirmed"] * 2 + ["waitlisted"] * 4
    with ThreadPoolExecutor(max_workers=6) as pool:
        assert all(response.status_code == 200 for response in pool.map(lambda client: rsvp(client, event["id"]), clients))
    result = owner.get(f"/api/events/{event['id']}").json()
    assert result["confirmed_count"] == 2 and result["waiting_count"] == 4
    with arena.database() as db:
        assert db.execute("SELECT count(*) FROM registrations WHERE event_id=?", (event["id"],)).fetchone()[0] == 6


def test_waitlist_offer_requires_acceptance_and_expires_in_order(arena):
    owner, jun, sora, haneul = [arena.client(user) for user in ("mira", "jun", "sora", "haneul")]
    event_id = arena.event(owner)["id"]
    for client in (owner, jun, sora, haneul):
        assert rsvp(client, event_id).status_code == 200
    assert rsvp(owner, event_id, "cancel").status_code == 200
    offered = sora.get(f"/api/events/{event_id}").json()
    assert offered["my_status"] == "offered" and offered["offer_expires_at"]
    assert offered["confirmed_count"] == 1 and offered["offered_count"] == 1
    assert rsvp(sora, event_id, "accept").json()["my_status"] == "confirmed"
    assert rsvp(sora, event_id, "cancel").status_code == 200
    assert haneul.get(f"/api/events/{event_id}").json()["my_status"] == "offered"
    assert rsvp(owner, event_id, request_id="join-again-123").json()["my_status"] == "waitlisted"
    arena.timestamp += 1801
    assert haneul.get(f"/api/events/{event_id}").json()["my_status"] == "expired"
    assert owner.get(f"/api/events/{event_id}").json()["my_status"] == "offered"
    assert rsvp(haneul, event_id, "accept").status_code == 409
    result = owner.get(f"/api/events/{event_id}").json()
    assert result["confirmed_count"] + result["offered_count"] <= result["capacity"]


def test_event_creation_retry_and_cancel_version_guard(arena):
    owner, sora = arena.client("mira"), arena.client("sora")
    event = arena.event(owner)
    assert arena.event(owner)["id"] == event["id"]
    altered = {"request_id": "event-2-86400", "title": "바뀐 제목", "location": "한강공원",
               "starts_at": iso(arena.timestamp + 86400), "ends_at": iso(arena.timestamp + 90000), "capacity": 2}
    assert owner.post("/api/groups/hangang/events", json=altered).status_code == 409
    assert sora.post("/api/groups/hangang/events", json=altered).status_code == 403
    assert rsvp(sora, event["id"]).status_code == 200
    path = f"/api/events/{event['id']}/cancel"
    assert sora.post(path, json={"version": 1}).status_code == 403
    assert owner.post(path, json={"version": 8}).status_code == 409
    assert owner.post(path, json={"version": 1}).json()["status"] == "cancelled"
    assert rsvp(sora, event["id"], request_id="new-after-cancel").status_code == 409
    assert any(item["kind"] == "event_cancelled" for item in sora.get("/api/notifications").json()["items"])


def test_removal_releases_seat_and_blocks_old_session(arena):
    owner, sora, jun, haneul = [arena.client(user) for user in ("mira", "sora", "jun", "haneul")]
    event_id = arena.event(owner)["id"]
    for client in (sora, jun, haneul):
        rsvp(client, event_id)
    assert owner.delete("/api/groups/hangang/members/sora").status_code == 200
    assert rsvp(sora, event_id).status_code == 403
    assert haneul.get(f"/api/events/{event_id}").json()["my_status"] == "offered"


def test_attendance_requires_independent_staff_and_is_reversible(arena):
    owner, sora, jun = arena.client("mira"), arena.client("sora"), arena.client("jun")
    past_id = 2
    count = owner.get("/api/groups/hangang/growth").json()["total_contributions"]
    assert count == 4
    assert owner.post("/api/events/1/attendance", json={"user_id": "sora", "present": True}).status_code == 409
    assert owner.post(f"/api/events/{past_id}/attendance", json={"user_id": "mira", "present": True}).status_code == 403
    assert sora.post(f"/api/events/{past_id}/attendance", json={"user_id": "jiho", "present": True}).status_code == 403
    for _ in range(2):
        assert owner.post(f"/api/events/{past_id}/attendance", json={"user_id": "jiho", "present": True}).status_code == 200
    assert owner.get("/api/groups/hangang/growth").json()["total_contributions"] == count + 1
    assert owner.post(f"/api/events/{past_id}/attendance", json={"user_id": "jiho", "present": False}).status_code == 200
    assert owner.get("/api/groups/hangang/growth").json()["total_contributions"] == count
    assert jun.post(f"/api/events/{past_id}/attendance", json={"user_id": "mira", "present": False}).status_code == 200
    assert owner.get("/api/groups/hangang/growth").json()["total_contributions"] == count - 1
    revisions = [entry for entry in owner.get("/api/groups/hangang/audit").json()["items"] if entry["action"] == "attendance_revised"]
    assert len(revisions) == 3


def test_same_korea_day_cap_and_chat_do_not_award_assets(arena):
    owner, sora = arena.client("mira"), arena.client("sora")
    event_id = arena.event(owner)["id"]
    second_id = arena.event(owner, offset=88200)["id"]
    rsvp(sora, event_id)
    rsvp(sora, second_id)
    before = owner.get("/api/groups/hangang/growth").json()["total_contributions"]
    for number in range(5):
        sora.post("/api/groups/hangang/messages", json={"client_id": f"no-reward-{number}", "body": "함께해요"})
    assert owner.get("/api/groups/hangang/growth").json()["total_contributions"] == before
    arena.timestamp += 90000
    for value in (event_id, second_id):
        assert owner.post(f"/api/events/{value}/attendance", json={"user_id": "sora", "present": True}).status_code == 200
    assert owner.get("/api/groups/hangang/growth").json()["total_contributions"] == before + 1
    assert owner.post(f"/api/events/{event_id}/attendance", json={"user_id": "sora", "present": False}).status_code == 200
    assert owner.get("/api/groups/hangang/growth").json()["total_contributions"] == before + 1
    assert owner.post(f"/api/events/{second_id}/attendance", json={"user_id": "sora", "present": False}).status_code == 200
    assert owner.get("/api/groups/hangang/growth").json()["total_contributions"] == before
