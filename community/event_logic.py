"""Seat accounting and group growth are independent from chat volume."""

from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from community.database import iso, notify


def refresh_offers(db, event, timestamp):
    event_id = event["id"]
    db.execute("UPDATE registrations SET status='expired',offer_expires_at=NULL "
               "WHERE event_id=? AND status='offered' AND offer_expires_at<=?", (event_id, timestamp))
    if event["status"] != "published" or event["starts_at"] <= timestamp:
        db.execute("UPDATE registrations SET status='expired',offer_expires_at=NULL "
                   "WHERE event_id=? AND status IN('waitlisted','offered')", (event_id,))
        return
    occupied = db.execute("SELECT count(*) FROM registrations WHERE event_id=? AND status IN('confirmed','offered')",
                          (event_id,)).fetchone()[0]
    available = event["capacity"] - occupied
    waiting = db.execute("SELECT r.*,m.muted FROM registrations r JOIN memberships m "
                         "ON m.user_id=r.user_id AND m.group_id=? AND m.state='active' "
                         "WHERE r.event_id=? AND r.status='waitlisted' ORDER BY r.queued_at,r.id LIMIT ?",
                         (event["group_id"], event_id, max(0, available))).fetchall()
    for registration in waiting:
        expiry = min(timestamp + 1800, event["starts_at"])
        db.execute("UPDATE registrations SET status='offered',offer_expires_at=? WHERE id=?", (expiry, registration["id"]))
        if not registration["muted"]:
            notify(db, registration["user_id"], event["group_id"], "seat_offer", "참가할 자리가 생겼어요. 기한 안에 확정해 주세요.", timestamp, event_id)


def event_view(db, event, user_id, role, timestamp):
    refresh_offers(db, event, timestamp)
    mine = db.execute("SELECT * FROM registrations WHERE event_id=? AND user_id=?", (event["id"], user_id)).fetchone()
    counts = {r["status"]: r["n"] for r in db.execute("SELECT status,count(*) n FROM registrations WHERE event_id=? GROUP BY status", (event["id"],))}
    result = {key: event[key] for key in ("id", "group_id", "title", "description", "location", "capacity", "status", "version")}
    result.update(starts_at=iso(event["starts_at"]), ends_at=iso(event["ends_at"]),
                  confirmed_count=counts.get("confirmed", 0), offered_count=counts.get("offered", 0),
                  waiting_count=counts.get("waitlisted", 0), my_status=mine["status"] if mine else None,
                  my_attendance=mine["attendance"] if mine else None,
                  offer_expires_at=iso(mine["offer_expires_at"]) if mine and mine["offer_expires_at"] else None,
                  can_mark_attendance=role in {"owner", "organizer"} and event["starts_at"] <= timestamp and event["status"] != "cancelled")
    if role in {"owner", "organizer"}:
        attendees = db.execute("SELECT r.user_id,u.display_name,u.color,r.status,r.attendance FROM registrations r "
                               "JOIN users u ON u.id=r.user_id WHERE event_id=? AND status IN('confirmed','offered','waitlisted') ORDER BY r.id", (event["id"],))
        result["attendees"] = [dict(r) for r in attendees]
    return result


def apply_rsvp(db, event, user_id, action, timestamp):
    refresh_offers(db, event, timestamp)
    registration = db.execute("SELECT * FROM registrations WHERE event_id=? AND user_id=?", (event["id"], user_id)).fetchone()
    if event["status"] != "published" or event["starts_at"] <= timestamp:
        raise HTTPException(409, "시작했거나 취소된 모임은 신청을 바꿀 수 없어요.")
    if action == "cancel":
        if registration:
            db.execute("UPDATE registrations SET status='cancelled',offer_expires_at=NULL WHERE id=?", (registration["id"],))
        refresh_offers(db, event, timestamp)
        return
    if action == "accept":
        if registration and registration["status"] == "confirmed":
            return
        if not registration or registration["status"] != "offered":
            raise HTTPException(409, "참가 제안이 만료됐어요. 현재 신청 상태를 확인해 주세요.")
        db.execute("UPDATE registrations SET status='confirmed',offer_expires_at=NULL WHERE id=?", (registration["id"],))
        return
    if registration and registration["status"] in {"confirmed", "waitlisted", "offered"}:
        return
    occupied = db.execute("SELECT count(*) FROM registrations WHERE event_id=? AND status IN('confirmed','offered')", (event["id"],)).fetchone()[0]
    status = "confirmed" if occupied < event["capacity"] else "waitlisted"
    db.execute("INSERT INTO registrations(event_id,user_id,status,queued_at) VALUES(?,?,?,?) "
               "ON CONFLICT(event_id,user_id) DO UPDATE SET status=excluded.status,queued_at=excluded.queued_at,offer_expires_at=NULL",
               (event["id"], user_id, status, timestamp))


def reconcile_contribution(db, registration, event, timestamp):
    day = datetime.fromtimestamp(event["starts_at"], ZoneInfo("Asia/Seoul")).date().isoformat()
    db.execute("INSERT INTO contributions(registration_id,group_id,user_id,event_day,active,created_at) VALUES(?,?,?,?,?,?) "
               "ON CONFLICT(registration_id) DO UPDATE SET active=excluded.active",
               (registration["id"], event["group_id"], registration["user_id"], day,
                int(registration["attendance"] == "present"), timestamp))
