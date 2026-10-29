"""Group membership, invitations and explicit privacy preferences."""

import secrets
from fastapi import APIRouter, HTTPException, Request
from community.database import iso, now, record_audit, transaction
from community.schemas import InviteInput, PreferenceInput, SettingsInput
from community.security import current_user, digest, member


ROUTER = APIRouter(prefix="/api")


def group_view(db, group_id, user_id):
    membership = member(db, group_id, user_id)
    group = dict(db.execute("SELECT * FROM groups WHERE id=?", (group_id,)).fetchone())
    count = db.execute("SELECT count(*) FROM memberships WHERE group_id=? AND state='active'", (group_id,)).fetchone()[0]
    group.update(role=membership["role"], member_count=count, public_space=bool(group["public_space"]),
                 preferences={"muted": bool(membership["muted"]), "activity_consent": bool(membership["activity_consent"])})
    return group


@ROUTER.get("/groups")
def list_groups(request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        rows = db.execute("SELECT group_id FROM memberships WHERE user_id=? AND state='active' ORDER BY id", (user["id"],))
        return {"items": [group_view(db, r["group_id"], user["id"]) for r in rows.fetchall()]}


@ROUTER.get("/groups/{group_id}")
def get_group(group_id: str, request: Request):
    with transaction(request) as db:
        return group_view(db, group_id, current_user(request, db)["id"])


@ROUTER.get("/groups/{group_id}/members")
def members(group_id: str, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        member(db, group_id, user["id"])
        rows = db.execute("SELECT u.id,u.display_name,u.color,m.role FROM memberships m "
                          "JOIN users u ON u.id=m.user_id WHERE group_id=? AND state='active' ORDER BY m.id", (group_id,))
        return {"items": [dict(row) for row in rows]}


@ROUTER.patch("/groups/{group_id}/preferences")
def preferences(group_id: str, data: PreferenceInput, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        membership = member(db, group_id, user["id"])
        for key, value in data.model_dump(exclude_none=True).items():
            db.execute(f"UPDATE memberships SET {key}=? WHERE id=?", (int(value), membership["id"]))
        return group_view(db, group_id, user["id"])


@ROUTER.patch("/groups/{group_id}/settings")
def settings(group_id: str, data: SettingsInput, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        membership = member(db, group_id, user["id"], staff=True)
        if membership["role"] != "owner":
            raise HTTPException(403, "공개 범위와 공간 설정은 소유자만 바꿀 수 있어요.")
        group = db.execute("SELECT * FROM groups WHERE id=?", (group_id,)).fetchone()
        if group["version"] != data.version:
            raise HTTPException(409, "설정이 바뀌었어요. 새로고침 후 다시 확인해 주세요.")
        for key, value in data.model_dump(exclude_none=True, exclude={"version"}).items():
            db.execute(f"UPDATE groups SET {key}=? WHERE id=?", (value, group_id))
        db.execute("UPDATE groups SET version=version+1 WHERE id=?", (group_id,))
        record_audit(db, group_id, user["id"], "group_settings", group_id, "공개/공간 설정 변경", now(request))
        return group_view(db, group_id, user["id"])


@ROUTER.post("/groups/{group_id}/invites", status_code=201)
def create_invite(group_id: str, data: InviteInput, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        member(db, group_id, user["id"], staff=True)
        token = secrets.token_urlsafe(24)
        expiry = now(request) + 86400 * 7
        db.execute("INSERT INTO invites(token_hash,group_id,expires_at,max_uses) VALUES(?,?,?,?)",
                   (digest(token), group_id, expiry, data.max_uses))
        return {"token": token, "path": f"/invite/{token}", "expires_at": iso(expiry)}


def valid_invite(db, token, timestamp, user_id=None):
    row = db.execute("SELECT i.*,g.name,g.description FROM invites i JOIN groups g ON g.id=i.group_id "
                     "WHERE token_hash=?", (digest(token),)).fetchone()
    # A lost join response can be retried after the final invitation use. This
    # grants no new access: the same account must already be an active member.
    if row and user_id and db.execute(
        "SELECT 1 FROM memberships WHERE user_id=? AND group_id=? AND state='active'",
        (user_id, row["group_id"]),
    ).fetchone():
        return row
    if not row or row["expires_at"] <= timestamp or row["uses"] >= row["max_uses"]:
        raise HTTPException(404, "초대가 만료되었거나 사용할 수 없어요. 새 초대를 요청해 주세요.")
    return row


@ROUTER.get("/invites/{token}")
def invite_preview(token: str, request: Request):
    with transaction(request) as db:
        row = valid_invite(db, token, now(request))
        return {"group_id": row["group_id"], "name": row["name"], "description": row["description"],
                "history_policy": "가입 이후의 대화와 현재 공지·모임을 볼 수 있어요."}


@ROUTER.post("/invites/{token}/join")
def join(token: str, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        invitation = valid_invite(db, token, now(request), user["id"])
        group_id = invitation["group_id"]
        active = db.execute("SELECT 1 FROM memberships WHERE user_id=? AND group_id=? AND state='active'",
                            (user["id"], group_id)).fetchone()
        if not active:
            removed = db.execute("SELECT 1 FROM memberships WHERE user_id=? AND group_id=? AND state='removed'",
                                 (user["id"], group_id)).fetchone()
            if removed:
                raise HTTPException(403, "가입이 제한되어 있어요. 운영자에게 문의해 주세요.")
            seq = db.execute("SELECT coalesce(max(id),0) FROM messages WHERE group_id=?", (group_id,)).fetchone()[0]
            db.execute("INSERT INTO memberships(group_id,user_id,role,joined_at,history_from_seq,read_seq) VALUES(?,?,?,?,?,?)",
                       (group_id, user["id"], "member", now(request), seq, seq))
            db.execute("UPDATE invites SET uses=uses+1 WHERE token_hash=?", (digest(token),))
        return group_view(db, group_id, user["id"])


def end_membership(db, group_id, user_id, actor_id, state, timestamp):
    membership = member(db, group_id, user_id)
    if membership["role"] == "owner":
        raise HTTPException(409, "소유자는 그룹을 떠나거나 내보낼 수 없어요. 소유권 이전 기능은 준비 중이에요.")
    db.execute("UPDATE memberships SET state=?,activity_consent=0 WHERE id=?", (state, membership["id"]))
    db.execute("UPDATE registrations SET status='cancelled',offer_expires_at=NULL WHERE user_id=? "
               "AND event_id IN(SELECT id FROM events WHERE group_id=? AND starts_at>?)",
               (user_id, group_id, timestamp))
    db.execute("DELETE FROM notifications WHERE group_id=? AND user_id=?", (group_id, user_id))
    record_audit(db, group_id, actor_id, state, user_id, "멤버 접근 종료", timestamp)


@ROUTER.post("/groups/{group_id}/leave")
def leave(group_id: str, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        end_membership(db, group_id, user["id"], user["id"], "left", now(request))
        return {"ok": True}


@ROUTER.delete("/groups/{group_id}/members/{user_id}")
def remove_member(group_id: str, user_id: str, request: Request):
    with transaction(request) as db:
        actor = current_user(request, db)
        member(db, group_id, actor["id"], staff=True)
        end_membership(db, group_id, user_id, actor["id"], "removed", now(request))
        return {"ok": True}
