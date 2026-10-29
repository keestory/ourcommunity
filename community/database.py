"""SQLite boundaries; every business transition is one serialized transaction."""

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL,
 password_hash TEXT NOT NULL, color TEXT NOT NULL DEFAULT '#52786B'
);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
 csrf TEXT NOT NULL, expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS groups (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
 subtitle TEXT NOT NULL, public_space INTEGER NOT NULL DEFAULT 0,
 palette TEXT NOT NULL DEFAULT 'dawn', version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS memberships (
 id INTEGER PRIMARY KEY AUTOINCREMENT, group_id TEXT NOT NULL REFERENCES groups(id),
 user_id TEXT NOT NULL REFERENCES users(id), role TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'active', joined_at REAL NOT NULL,
 history_from_seq INTEGER NOT NULL DEFAULT 0, read_seq INTEGER NOT NULL DEFAULT 0,
 activity_consent INTEGER NOT NULL DEFAULT 0, muted INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_membership
 ON memberships(group_id,user_id) WHERE state='active';
CREATE TABLE IF NOT EXISTS messages (
 id INTEGER PRIMARY KEY AUTOINCREMENT, group_id TEXT NOT NULL REFERENCES groups(id),
 membership_id INTEGER NOT NULL REFERENCES memberships(id),
 client_id TEXT NOT NULL, body TEXT NOT NULL, created_at REAL NOT NULL,
 deleted INTEGER NOT NULL DEFAULT 0, UNIQUE(membership_id,client_id)
);
CREATE INDEX IF NOT EXISTS messages_group ON messages(group_id,id);
CREATE TABLE IF NOT EXISTS announcements (
 id INTEGER PRIMARY KEY AUTOINCREMENT, group_id TEXT NOT NULL REFERENCES groups(id),
 author_id TEXT NOT NULL REFERENCES users(id), body TEXT NOT NULL, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, group_id TEXT NOT NULL REFERENCES groups(id),
 title TEXT NOT NULL, description TEXT NOT NULL, location TEXT NOT NULL,
 starts_at REAL NOT NULL, ends_at REAL NOT NULL, capacity INTEGER NOT NULL,
 status TEXT NOT NULL DEFAULT 'published', version INTEGER NOT NULL DEFAULT 1,
 creator_id TEXT NOT NULL REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS registrations (
 id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL REFERENCES events(id),
 user_id TEXT NOT NULL REFERENCES users(id), status TEXT NOT NULL,
 queued_at REAL NOT NULL, offer_expires_at REAL,
 attendance TEXT NOT NULL DEFAULT 'unmarked', UNIQUE(event_id,user_id)
);
CREATE TABLE IF NOT EXISTS idempotency (
 user_id TEXT NOT NULL, scope TEXT NOT NULL, request_id TEXT NOT NULL,
 action TEXT NOT NULL, PRIMARY KEY(user_id,scope,request_id)
);
CREATE TABLE IF NOT EXISTS contributions (
 registration_id INTEGER PRIMARY KEY REFERENCES registrations(id),
 group_id TEXT NOT NULL REFERENCES groups(id), user_id TEXT NOT NULL REFERENCES users(id),
 event_day TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY AUTOINCREMENT, group_id TEXT NOT NULL,
 actor_id TEXT NOT NULL, action TEXT NOT NULL, object_id TEXT NOT NULL,
 detail TEXT NOT NULL, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS invites (
 token_hash TEXT PRIMARY KEY, group_id TEXT NOT NULL REFERENCES groups(id),
 expires_at REAL NOT NULL, max_uses INTEGER NOT NULL, uses INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS blocks (
 actor_id TEXT NOT NULL REFERENCES users(id), target_id TEXT NOT NULL REFERENCES users(id),
 PRIMARY KEY(actor_id,target_id)
);
CREATE TABLE IF NOT EXISTS reports (
 id INTEGER PRIMARY KEY AUTOINCREMENT, group_id TEXT NOT NULL REFERENCES groups(id),
 reporter_id TEXT NOT NULL REFERENCES users(id), target_id TEXT NOT NULL REFERENCES users(id),
 message_id INTEGER NOT NULL REFERENCES messages(id), reason TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'open', created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL REFERENCES users(id),
 group_id TEXT NOT NULL REFERENCES groups(id), kind TEXT NOT NULL,
 title TEXT NOT NULL, event_id INTEGER, read INTEGER NOT NULL DEFAULT 0,
 created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS login_attempts (
 key TEXT NOT NULL, created_at REAL NOT NULL
);
"""


def connect(path):
    db = sqlite3.connect(str(path), timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=10000")
    return db


def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript(SCHEMA)


@contextmanager
def transaction(request):
    db = connect(request.app.state.db_path)
    try:
        db.execute("BEGIN IMMEDIATE")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def now(request):
    return float(request.app.state.clock())


def iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def record_audit(db, group_id, actor_id, action, object_id, detail, timestamp):
    db.execute(
        "INSERT INTO audit(group_id,actor_id,action,object_id,detail,created_at) VALUES(?,?,?,?,?,?)",
        (group_id, actor_id, action, str(object_id), detail, timestamp),
    )


def notify(db, user_id, group_id, kind, title, timestamp, event_id=None):
    db.execute(
        "INSERT INTO notifications(user_id,group_id,kind,title,created_at,event_id) VALUES(?,?,?,?,?,?)",
        (user_id, group_id, kind, title, timestamp, event_id),
    )
