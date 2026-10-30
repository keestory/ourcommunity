"""Shared local fixtures with a controllable Korea-calendar clock."""

from contextlib import contextmanager
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from community.app import create_app
from community.database import connect, iso


class Arena:
    def __init__(self, path):
        self.path = path
        self.timestamp = datetime(2026, 10, 29, 12, tzinfo=timezone.utc).timestamp()
        self.app = create_app(path, demo=True, clock=lambda: self.timestamp,
                              allowed_origins={"http://testserver"})
        self.clients = []

    def client(self, user=None):
        client = TestClient(self.app, headers={"Origin": "http://testserver"})
        self.clients.append(client)
        if user:
            if user in {"mira", "jun", "sora", "outsider"}:
                response = client.post("/api/auth/demo", json={"persona": user})
            else:
                response = client.post("/api/auth/login", json={"username": user, "password": "local-demo-only-2026"})
            assert response.status_code == 200
            client.headers["X-CSRF-Token"] = response.json()["csrf"]
        return client

    @contextmanager
    def database(self):
        db = connect(self.path)
        try:
            yield db
        finally:
            db.close()

    def event(self, owner, capacity=2, offset=86400):
        response = owner.post("/api/groups/hangang/events", json={
            "request_id": f"event-{capacity}-{offset}", "title": "다 같이 달리기", "description": "테스트 모임",
            "location": "한강공원", "starts_at": iso(self.timestamp + offset),
            "ends_at": iso(self.timestamp + offset + 3600), "capacity": capacity,
        })
        assert response.status_code == 201, response.text
        return response.json()


@pytest.fixture
def arena(tmp_path):
    instance = Arena(tmp_path / "community.sqlite3")
    yield instance
    for client in instance.clients:
        client.close()


def rsvp(client, event_id, action="join", request_id=None):
    return client.post(f"/api/events/{event_id}/rsvp", json={
        "action": action, "request_id": request_id or f"request-{event_id}-{action}",
    })
