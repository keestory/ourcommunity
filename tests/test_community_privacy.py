"""Public aggregates expose only delayed coarse collective states."""

from datetime import datetime
from zoneinfo import ZoneInfo
from community.growth import activity_window
from test_community_helpers import arena


def seed_activity(arena, count=5, days=3, consent=True, current=False):
    start, _ = activity_window(arena.timestamp)
    with arena.database() as db:
        members = db.execute("SELECT id,user_id FROM memberships WHERE group_id='hangang' ORDER BY id LIMIT ?", (count,)).fetchall()
        for member in members:
            db.execute("UPDATE memberships SET activity_consent=? WHERE id=?", (int(consent), member["id"]))
            for day in range(days):
                timestamp = arena.timestamp - 60 if current else start + day * 86400 + 3600
                db.execute("INSERT INTO messages(group_id,membership_id,client_id,body,created_at) VALUES(?,?,?,?,?)",
                           ("hangang", member["id"], f"activity-{day}-{timestamp}", "비공개 원문 절대 노출 금지", timestamp))


def publish(owner):
    return owner.patch("/api/groups/hangang/settings", json={"public_space": True, "version": 1})


def test_public_setting_is_separate_from_member_consent(arena):
    public, owner = arena.client(), arena.client("mira")
    assert public.get("/api/public/groups/hangang").status_code == 404
    assert publish(owner).status_code == 200
    seed_activity(arena, consent=False)
    result = public.get("/api/public/groups/hangang").json()
    assert result["recent"]["visible"] is False
    assert set(result) == {"id", "name", "description", "palette", "assets", "recent"}
    assert all(set(asset) == {"id", "name", "description"} for asset in result["assets"])
    assert "비공개 원문" not in str(result) and "서윤" not in str(result)


def test_k_threshold_and_revocation_immediately_suppress(arena):
    owner, sora, public = arena.client("mira"), arena.client("sora"), arena.client()
    publish(owner)
    seed_activity(arena)
    result = public.get("/api/public/groups/hangang").json()
    assert result["recent"]["visible"] is True and result["recent"]["stage"] == "warm"
    assert set(result["recent"]) == {"visible", "stage", "label", "period"}
    assert sora.patch("/api/groups/hangang/preferences", json={"activity_consent": False}).status_code == 200
    assert public.get("/api/public/groups/hangang").json()["recent"]["visible"] is False
    sora.patch("/api/groups/hangang/preferences", json={"activity_consent": True})
    assert public.get("/api/public/groups/hangang").json()["recent"]["visible"] is True
    assert sora.post("/api/groups/hangang/leave").status_code == 200
    assert public.get("/api/public/groups/hangang").json()["recent"]["visible"] is False
    assert owner.get("/api/groups/hangang/growth").json()["recent"]["visible"] is False


def test_current_week_and_single_day_activity_remain_hidden(arena):
    owner = arena.client("mira")
    seed_activity(arena, current=True)
    assert owner.get("/api/groups/hangang/growth").json()["recent"]["visible"] is False
    with arena.database() as db:
        db.execute("DELETE FROM messages WHERE client_id LIKE 'activity-%'")
    seed_activity(arena, days=1)
    assert owner.get("/api/groups/hangang/growth").json()["recent"]["visible"] is False


def test_activity_uses_fixed_completed_week_with_at_least_day_delay():
    timezone = ZoneInfo("Asia/Seoul")
    monday = datetime(2026, 10, 26, 12, tzinfo=timezone).timestamp()
    tuesday = datetime(2026, 10, 27, 0, tzinfo=timezone).timestamp()
    for timestamp in (monday, tuesday):
        start, end = activity_window(timestamp)
        assert timestamp - end >= 86400
        assert end - start == 7 * 86400
        assert datetime.fromtimestamp(end, timezone).weekday() == 0
    assert activity_window(tuesday)[1] > activity_window(monday)[1]


def test_asset_memories_survive_inactivity_and_public_version_guard(arena):
    owner, member, organizer = arena.client("mira"), arena.client("sora"), arena.client("jun")
    before = owner.get("/api/groups/hangang/growth").json()["assets"]
    assert [asset["unlocked"] for asset in before] == [True, True, False]
    assert member.patch("/api/groups/hangang/settings", json={"version": 1, "public_space": True}).status_code == 403
    assert organizer.patch("/api/groups/hangang/settings", json={"version": 1, "public_space": True}).status_code == 403
    assert publish(owner).status_code == 200
    assert publish(owner).status_code == 409
    arena.timestamp += 86400 * 5
    assert owner.get("/api/groups/hangang/growth").json()["assets"] == before
