"""Atomic RSVP, cancellation and independently verified attendance."""

from fastapi import APIRouter, HTTPException, Request
from community.commands import creation_receipt, save_receipt
from community.database import notify, now, record_audit, transaction
from community.event_logic import apply_rsvp, event_view, reconcile_contribution
from community.schemas import AttendanceInput, EventInput, RsvpInput, VersionInput
from community.security import current_user, event_for, member


ROUTER = APIRouter(prefix="/api")


@ROUTER.get("/groups/{group_id}/events")
def list_events(group_id: str, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        membership = member(db, group_id, user["id"])
        rows = db.execute("SELECT * FROM events WHERE group_id=? AND starts_at>=? ORDER BY starts_at DESC LIMIT 100",
                          (group_id, membership["joined_at"])).fetchall()
        return {"items": [event_view(db, row, user["id"], membership["role"], now(request)) for row in rows]}


@ROUTER.post("/groups/{group_id}/events", status_code=201)
def create_event(group_id: str, data: EventInput, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        membership = member(db, group_id, user["id"], staff=True)
        scope = f"event_create:{membership['id']}"
        fingerprint, existing = creation_receipt(db, user["id"], scope, data)
        if existing:
            event = db.execute("SELECT * FROM events WHERE id=?", (existing,)).fetchone()
            return event_view(db, event, user["id"], membership["role"], now(request))
        starts, ends = data.starts_at.timestamp(), data.ends_at.timestamp()
        if starts <= now(request) or ends <= starts or ends - starts > 86400:
            raise HTTPException(422, "앞으로 시작하는 모임을 만들고, 종료 시간을 시작 이후 24시간 안으로 정해 주세요.")
        event_id = db.execute("INSERT INTO events(group_id,title,description,location,starts_at,ends_at,capacity,creator_id) VALUES(?,?,?,?,?,?,?,?)",
                              (group_id, data.title, data.description, data.location, starts, ends, data.capacity, user["id"])).lastrowid
        event = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        save_receipt(db, user["id"], scope, data.request_id, fingerprint, event_id)
        record_audit(db, group_id, user["id"], "event_created", event_id, "모임 생성", now(request))
        return event_view(db, event, user["id"], membership["role"], now(request))


@ROUTER.get("/events/{event_id}")
def get_event(event_id: int, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        event, membership = event_for(db, event_id, user["id"])
        return event_view(db, event, user["id"], membership["role"], now(request))


@ROUTER.post("/events/{event_id}/rsvp")
def rsvp(event_id: int, data: RsvpInput, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        event, membership = event_for(db, event_id, user["id"])
        scope = f"event:{event_id}"
        prior = db.execute("SELECT action FROM idempotency WHERE user_id=? AND scope=? AND request_id=?",
                           (user["id"], scope, data.request_id)).fetchone()
        if prior and prior["action"] != data.action:
            raise HTTPException(409, "같은 요청 번호로 다른 작업을 할 수 없어요.")
        if not prior:
            apply_rsvp(db, event, user["id"], data.action, now(request))
            db.execute("INSERT INTO idempotency(user_id,scope,request_id,action) VALUES(?,?,?,?)", (user["id"], scope, data.request_id, data.action))
            record_audit(db, event["group_id"], user["id"], "rsvp_" + data.action, event_id, "참가 상태 변경", now(request))
        return event_view(db, event, user["id"], membership["role"], now(request))


@ROUTER.post("/events/{event_id}/cancel")
def cancel_event(event_id: int, data: VersionInput, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        event, membership = event_for(db, event_id, user["id"], staff=True)
        if event["status"] == "cancelled":
            return event_view(db, event, user["id"], membership["role"], now(request))
        if event["version"] != data.version:
            raise HTTPException(409, "모임 정보가 바뀌었어요. 새로고침 후 다시 확인해 주세요.")
        if event["starts_at"] <= now(request):
            raise HTTPException(409, "이미 시작한 모임은 취소할 수 없어요.")
        db.execute("UPDATE events SET status='cancelled',version=version+1 WHERE id=?", (event_id,))
        recipients = db.execute("SELECT r.user_id FROM registrations r JOIN memberships m ON m.user_id=r.user_id "
                                "AND m.group_id=? AND m.state='active' WHERE r.event_id=? AND m.muted=0 "
                                "AND r.status IN ('confirmed','offered','waitlisted')", (event["group_id"], event_id)).fetchall()
        for recipient in recipients:
            notify(db, recipient["user_id"], event["group_id"], "event_cancelled", "참가한 모임이 취소되었어요", now(request), event_id)
        db.execute("UPDATE registrations SET status='cancelled',offer_expires_at=NULL WHERE event_id=?", (event_id,))
        record_audit(db, event["group_id"], user["id"], "event_cancelled", event_id, "모임 전체 취소", now(request))
        event = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        return event_view(db, event, user["id"], membership["role"], now(request))


@ROUTER.post("/events/{event_id}/attendance")
def attendance(event_id: int, data: AttendanceInput, request: Request):
    with transaction(request) as db:
        user = current_user(request, db)
        event, membership = event_for(db, event_id, user["id"], staff=True)
        if data.user_id == user["id"]:
            raise HTTPException(403, "본인의 출석은 다른 운영자가 확인해야 해요.")
        if event["starts_at"] > now(request) or event["status"] == "cancelled":
            raise HTTPException(409, "시작한 모임의 출석만 확인할 수 있어요.")
        # Departure must not freeze a mistaken past contribution forever.
        # Positive approval still requires current membership; negative
        # correction requires the same authorized staff and historical record.
        if data.present:
            member(db, event["group_id"], data.user_id)
        registration = db.execute("SELECT * FROM registrations WHERE event_id=? AND user_id=? AND status='confirmed'",
                                  (event_id, data.user_id)).fetchone()
        if not registration:
            raise HTTPException(409, "참가가 확정된 멤버만 출석을 확인할 수 있어요.")
        value = "present" if data.present else "absent"
        if registration["attendance"] != value:
            db.execute("UPDATE registrations SET attendance=? WHERE id=?", (value, registration["id"]))
            revised = db.execute("SELECT * FROM registrations WHERE id=?", (registration["id"],)).fetchone()
            reconcile_contribution(db, revised, event, now(request))
            record_audit(db, event["group_id"], user["id"], "attendance_revised", registration["id"],
                         registration["attendance"] + " → " + value, now(request))
        return event_view(db, event, user["id"], membership["role"], now(request))
