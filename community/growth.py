"""Nonmonetary shared memories and delayed, suppressed activity summaries."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, Request
from community.database import now, transaction
from community.security import current_user, member


ROUTER = APIRouter(prefix="/api")
ASSETS = [
    {"id": "trail-sign", "name": "우리의 첫 이정표", "description": "함께 시작한 발걸음을 기억해요.", "goal": 2},
    {"id": "bench", "name": "잠깐 쉬어 가는 벤치", "description": "빠르지 않아도, 함께 쉬어 갈 자리가 있어요.", "goal": 4},
    {"id": "memory-tree", "name": "함께 자라는 나무", "description": "함께한 날들이 우리 공간에 뿌리를 내려요.", "goal": 6},
]


def contribution_count(db, group_id):
    # One verified contribution per person per Korea calendar day. Chat never awards assets.
    return db.execute("SELECT count(*) FROM (SELECT user_id,event_day FROM contributions "
                      "WHERE group_id=? AND active=1 GROUP BY user_id,event_day)", (group_id,)).fetchone()[0]


def activity_window(timestamp):
    local = datetime.fromtimestamp(timestamp, ZoneInfo("Asia/Seoul")) - timedelta(days=1)
    end = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return (end - timedelta(days=7)).timestamp(), end.timestamp()


def activity_view(db, group_id, timestamp):
    start, end = activity_window(timestamp)
    rows = db.execute("SELECT m.user_id,msg.created_at FROM messages msg JOIN memberships m ON m.id=msg.membership_id "
                      "WHERE msg.group_id=? AND msg.created_at>=? AND msg.created_at<? AND msg.deleted=0 "
                      "AND m.state='active' AND m.activity_consent=1", (group_id, start, end)).fetchall()
    per_user = {}
    for row in rows:
        day = datetime.fromtimestamp(row["created_at"], ZoneInfo("Asia/Seoul")).date().isoformat()
        per_user.setdefault(row["user_id"], set()).add(day)
    hidden = {"visible": False, "stage": "private", "label": "우리만의 편안한 시간", "period": "보호된 대화 분위기"}
    if len(per_user) < 5:
        return hidden
    total = sum(len(days) for days in per_user.values())
    if max(len(days) for days in per_user.values()) / total > 0.5:
        return hidden
    shared_days = set().union(*per_user.values())
    if len(shared_days) < 2:
        return hidden
    warm = len(shared_days) >= 3
    return {"visible": True, "stage": "warm" if warm else "gentle",
            "label": "함께 이어지는 이야기" if warm else "차분히 오가는 이야기", "period": "지난 완결 주의 분위기"}


def growth_view(db, group_id, timestamp):
    count = contribution_count(db, group_id)
    return {"assets": [{**asset, "unlocked": count >= asset["goal"], "progress": min(count, asset["goal"])} for asset in ASSETS],
            "total_contributions": count, "recent": activity_view(db, group_id, timestamp),
            "rule": "다른 운영자가 확인한 출석을 하루 한 번씩 기억해요. 대화량과 휴식은 기념물에 영향을 주지 않아요."}


@ROUTER.get("/groups/{group_id}/growth")
def growth(group_id: str, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        member(db, group_id, user["id"])
        return growth_view(db, group_id, now(request))


@ROUTER.get("/public/groups/{group_id}")
def public_group(group_id: str, request: Request):
    with transaction(request) as db:
        group = db.execute("SELECT * FROM groups WHERE id=? AND public_space=1", (group_id,)).fetchone()
        if not group:
            raise HTTPException(404, "공개된 공간을 찾을 수 없어요.")
        count = contribution_count(db, group_id)
        # Deliberate allowlist: no member, event, message, raw count, exact timestamp or progress data.
        return {"id": group["id"], "name": group["name"], "description": group["description"], "palette": group["palette"],
                "assets": [{"id": a["id"], "name": a["name"], "description": a["description"]} for a in ASSETS if count >= a["goal"]],
                "recent": activity_view(db, group_id, now(request))}
