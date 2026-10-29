"""Scoped reporting, mutual content blocking, and in-app notifications."""

from fastapi import APIRouter, HTTPException, Request
from community.chat_routes import lookup_message
from community.database import iso, now, record_audit, transaction
from community.schemas import ReportInput, ResolveInput
from community.security import current_user, member


ROUTER = APIRouter(prefix="/api")


@ROUTER.post("/groups/{group_id}/blocks/{target_id}")
def block(group_id: str, target_id: str, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        member(db, group_id, user["id"])
        member(db, group_id, target_id)
        if target_id == user["id"]:
            raise HTTPException(422, "자신을 차단할 수 없어요.")
        db.execute("INSERT OR IGNORE INTO blocks VALUES(?,?)", (user["id"], target_id))
        return {"ok": True}


@ROUTER.delete("/blocks/{target_id}")
def unblock(target_id: str, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        db.execute("DELETE FROM blocks WHERE actor_id=? AND target_id=?", (user["id"], target_id))
        return {"ok": True}


@ROUTER.get("/blocks")
def blocks(request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        rows = db.execute("SELECT u.id,u.display_name FROM blocks b JOIN users u ON u.id=b.target_id WHERE actor_id=?", (user["id"],))
        return {"items": [dict(row) for row in rows]}


@ROUTER.post("/groups/{group_id}/reports", status_code=201)
def report(group_id: str, data: ReportInput, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        member(db, group_id, user["id"])
        message, _ = lookup_message(db, data.message_id, user["id"])
        if message["group_id"] != group_id:
            raise HTTPException(403, "이 그룹의 메시지만 신고할 수 있어요.")
        if message["user_id"] == user["id"]:
            raise HTTPException(422, "본인의 메시지는 직접 삭제할 수 있어요.")
        report_id = db.execute("INSERT INTO reports(group_id,reporter_id,target_id,message_id,reason,created_at) VALUES(?,?,?,?,?,?)",
                               (group_id, user["id"], message["user_id"], data.message_id, data.reason, now(request))).lastrowid
        return {"id": report_id, "status": "open"}


@ROUTER.get("/groups/{group_id}/reports")
def reports(group_id: str, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        member(db, group_id, user["id"], staff=True)
        rows = db.execute("SELECT id,message_id,reason,status,created_at FROM reports WHERE group_id=? AND target_id!=? ORDER BY id DESC LIMIT 100",
                          (group_id, user["id"]))
        return {"items": [{**dict(row), "created_at": iso(row["created_at"])} for row in rows]}


@ROUTER.patch("/reports/{report_id}")
def resolve_report(report_id: int, data: ResolveInput, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        case = db.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
        if not case:
            raise HTTPException(404, "신고를 찾을 수 없어요.")
        member(db, case["group_id"], user["id"], staff=True)
        if case["target_id"] == user["id"]:
            raise HTTPException(403, "본인에 관한 신고는 다른 운영자가 검토해야 해요.")
        db.execute("UPDATE reports SET status=? WHERE id=?", (data.status, report_id))
        record_audit(db, case["group_id"], user["id"], "report_reviewed", report_id, "독립 운영자 검토", now(request))
        return {"ok": True}


@ROUTER.get("/notifications")
def notifications(request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        rows = db.execute("SELECT n.* FROM notifications n JOIN memberships m ON m.group_id=n.group_id "
                          "AND m.user_id=n.user_id AND m.state='active' WHERE n.user_id=? ORDER BY n.id DESC LIMIT 50", (user["id"],))
        return {"items": [{"id": r["id"], "group_id": r["group_id"], "kind": r["kind"], "title": r["title"],
                           "event_id": r["event_id"], "read": bool(r["read"]), "created_at": iso(r["created_at"])} for r in rows]}


@ROUTER.post("/notifications/read")
def read_notifications(request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        db.execute("UPDATE notifications SET read=1 WHERE user_id=?", (user["id"],))
        return {"ok": True}


@ROUTER.get("/groups/{group_id}/audit")
def audit(group_id: str, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        member(db, group_id, user["id"], staff=True)
        rows = db.execute("SELECT a.action,a.object_id,a.detail,a.created_at,u.display_name actor_name "
                          "FROM audit a JOIN users u ON u.id=a.actor_id WHERE group_id=? ORDER BY a.id DESC LIMIT 50", (group_id,))
        return {"items": [{**dict(r), "created_at": iso(r["created_at"])} for r in rows]}
