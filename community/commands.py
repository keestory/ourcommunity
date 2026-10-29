"""Persist creation receipts so a lost response can be retried safely."""

import json
from fastapi import HTTPException
from community.security import digest


def creation_receipt(db, user_id, scope, data):
    fingerprint = digest(data.model_dump_json(exclude={"request_id"}))
    row = db.execute("SELECT action FROM idempotency WHERE user_id=? AND scope=? AND request_id=?",
                     (user_id, scope, data.request_id)).fetchone()
    if not row:
        return fingerprint, None
    receipt = json.loads(row["action"])
    if receipt["fingerprint"] != fingerprint:
        raise HTTPException(409, "같은 요청 번호로 다른 내용을 저장할 수 없어요.")
    return fingerprint, receipt["id"]


def save_receipt(db, user_id, scope, request_id, fingerprint, object_id):
    db.execute("INSERT INTO idempotency VALUES(?,?,?,?)",
               (user_id, scope, request_id, json.dumps({"fingerprint": fingerprint, "id": object_id})))
