"""Bounded private chat, tombstones, read cursors and official announcements."""

from fastapi import APIRouter, HTTPException, Query, Request
from community.commands import creation_receipt, save_receipt
from community.database import iso, notify, now, record_audit, transaction
from community.schemas import BodyInput, MessageInput, ReadInput
from community.security import STAFF, current_user, member


ROUTER = APIRouter(prefix="/api")
VISIBLE_SQL = """SELECT msg.*,m.user_id,u.display_name,u.color FROM messages msg
 JOIN memberships m ON m.id=msg.membership_id JOIN users u ON u.id=m.user_id
 WHERE msg.group_id=? AND msg.id>? AND NOT EXISTS(
 SELECT 1 FROM blocks b WHERE (b.actor_id=? AND b.target_id=m.user_id)
 OR (b.target_id=? AND b.actor_id=m.user_id))"""


def message_view(row, user_id):
    return {"id": row["id"], "seq": row["id"], "client_id": row["client_id"], "body": "" if row["deleted"] else row["body"],
            "author": {"id": row["user_id"], "display_name": row["display_name"], "color": row["color"]},
            "created_at": iso(row["created_at"]), "deleted": bool(row["deleted"]), "mine": row["user_id"] == user_id}


def lookup_message(db, message_id, user_id):
    row = db.execute("SELECT msg.*,m.user_id,u.display_name,u.color FROM messages msg "
                     "JOIN memberships m ON m.id=msg.membership_id JOIN users u ON u.id=m.user_id "
                     "WHERE msg.id=?", (message_id,)).fetchone()
    if not row:
        raise HTTPException(404, "메시지를 찾을 수 없어요.")
    membership = member(db, row["group_id"], user_id)
    if row["id"] <= membership["history_from_seq"]:
        raise HTTPException(403, "가입 이전의 대화에는 접근할 수 없어요.")
    return row, membership


@ROUTER.get("/groups/{group_id}/messages")
def messages(group_id: str, request: Request, after: int = Query(0, ge=0),
             before: int | None = Query(None, ge=1), limit: int = Query(50, ge=1, le=200)):
    with transaction(request) as db:
        user = current_user(request, db)
        membership = member(db, group_id, user["id"])
        lower = max(after, membership["history_from_seq"])
        if after and before:
            raise HTTPException(422, "이전 기록과 새 기록은 따로 조회해 주세요.")
        params = [group_id, lower, user["id"], user["id"]]
        sql = VISIBLE_SQL
        if before:
            sql += " AND msg.id<?"
            params.append(before)
        sql += " ORDER BY msg.id " + ("ASC" if after else "DESC") + " LIMIT ?"
        rows = db.execute(sql, (*params, limit + 1)).fetchall()
        items = rows[:limit] if after else list(reversed(rows[:limit]))
        unread = db.execute("SELECT count(*) FROM (" + VISIBLE_SQL + ") WHERE deleted=0 AND user_id!=?",
                            (group_id, max(membership["read_seq"], membership["history_from_seq"]),
                             user["id"], user["id"], user["id"])).fetchone()[0]
        return {"items": [message_view(r, user["id"]) for r in items],
                "next_cursor": (items[-1 if after else 0]["id"] if items else lower), "has_more": len(rows) > limit,
                "read_seq": membership["read_seq"], "unread_count": unread}


@ROUTER.post("/groups/{group_id}/messages", status_code=201)
def send_message(group_id: str, data: MessageInput, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        membership = member(db, group_id, user["id"])
        existing = db.execute("SELECT id,body,deleted FROM messages WHERE membership_id=? AND client_id=?",
                              (membership["id"], data.client_id)).fetchone()
        if existing:
            if not existing["deleted"] and existing["body"] != data.body:
                raise HTTPException(409, "같은 요청 번호에 다른 메시지를 보낼 수 없어요.")
            row, _ = lookup_message(db, existing["id"], user["id"])
            return message_view(row, user["id"])
        recent = db.execute("SELECT count(*) FROM messages WHERE membership_id=? AND created_at>?",
                            (membership["id"], now(request) - 10)).fetchone()[0]
        if recent >= 6:
            raise HTTPException(429, "대화가 너무 빨라요. 잠깐 기다렸다가 보내 주세요.")
        message_id = db.execute("INSERT INTO messages(group_id,membership_id,client_id,body,created_at) VALUES(?,?,?,?,?)",
                                (group_id, membership["id"], data.client_id, data.body, now(request))).lastrowid
        row, _ = lookup_message(db, message_id, user["id"])
        return message_view(row, user["id"])


@ROUTER.delete("/messages/{message_id}")
def delete_message(message_id: int, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        row, membership = lookup_message(db, message_id, user["id"])
        if row["user_id"] != user["id"] and membership["role"] not in STAFF:
            raise HTTPException(403, "작성자 또는 운영자만 삭제할 수 있어요.")
        db.execute("UPDATE messages SET body='',deleted=1 WHERE id=?", (message_id,))
        record_audit(db, row["group_id"], user["id"], "message_deleted", message_id, "본문 삭제", now(request))
        return {"ok": True}


@ROUTER.post("/groups/{group_id}/read")
def mark_read(group_id: str, data: ReadInput, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        membership = member(db, group_id, user["id"])
        maximum = db.execute("SELECT coalesce(max(id),0) FROM messages WHERE group_id=?", (group_id,)).fetchone()[0]
        cursor = max(membership["read_seq"], min(data.seq, maximum))
        db.execute("UPDATE memberships SET read_seq=? WHERE id=?", (cursor, membership["id"]))
        return {"read_seq": cursor}


@ROUTER.get("/groups/{group_id}/announcements")
def announcements(group_id: str, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        member(db, group_id, user["id"])
        rows = db.execute("SELECT a.*,u.display_name FROM announcements a JOIN users u ON u.id=a.author_id "
                          "WHERE group_id=? ORDER BY a.id DESC LIMIT 10", (group_id,))
        return {"items": [{"id": r["id"], "body": r["body"], "author_name": r["display_name"],
                           "created_at": iso(r["created_at"])} for r in rows]}


@ROUTER.post("/groups/{group_id}/announcements", status_code=201)
def create_announcement(group_id: str, data: BodyInput, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        membership = member(db, group_id, user["id"], staff=True)
        scope = f"announcement:{membership['id']}"
        fingerprint, existing = creation_receipt(db, user["id"], scope, data)
        if existing:
            row = db.execute("SELECT * FROM announcements WHERE id=?", (existing,)).fetchone()
            return {"id": existing, "body": row["body"], "author_name": user["display_name"], "created_at": iso(row["created_at"])}
        timestamp = now(request)
        announcement_id = db.execute("INSERT INTO announcements(group_id,author_id,body,created_at) VALUES(?,?,?,?)",
                                      (group_id, user["id"], data.body, timestamp)).lastrowid
        save_receipt(db, user["id"], scope, data.request_id, fingerprint, announcement_id)
        members = db.execute("SELECT user_id FROM memberships WHERE group_id=? AND state='active' AND muted=0", (group_id,)).fetchall()
        for row in members:
            if row["user_id"] != user["id"]:
                notify(db, row["user_id"], group_id, "announcement", "새 공지가 올라왔어요", timestamp)
        return {"id": announcement_id, "body": data.body, "author_name": user["display_name"], "created_at": iso(timestamp)}
