"""Fictional, explicitly marked demo content; never imported customer data."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from community.database import connect, notify
from community.event_logic import reconcile_contribution
from community.security import hash_password


PEOPLE = [
    ("mira", "서윤", "#B56D4B", "owner"),
    ("jun", "도현", "#4E718C", "organizer"),
    ("sora", "수아", "#7C7952", "member"),
    ("haneul", "하늘", "#8E6980", "member"),
    ("jiho", "지호", "#607C69", "member"),
    ("yuna", "유나", "#AA8054", "member"),
    ("min", "민", "#638584", "member"),
    ("sol", "솔", "#8E7367", "member"),
]


def seed_demo(path, timestamp):
    db = connect(path)
    try:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM groups WHERE id='hangang'").fetchone():
            db.rollback()
            return
        password = hash_password("local-demo-only-2026")
        for user_id, name, color, _ in PEOPLE:
            db.execute("INSERT INTO users VALUES(?,?,?,?,?)", (user_id, user_id, name, password, color))
        db.execute("INSERT INTO users VALUES(?,?,?,?,?)", ("outsider", "outsider", "별", password, "#847198"))
        db.execute("INSERT INTO groups(id,name,description,subtitle) VALUES(?,?,?,?)",
                   ("hangang", "한강 새벽 러너스", "각자의 속도로 달리고, 함께한 시간을 모아요.", "러닝 · 서울 마포 · 샘플 크루"))
        db.execute("INSERT INTO groups(id,name,description,subtitle) VALUES(?,?,?,?)",
                   ("seongsu", "성수 가벼운 밤", "하루를 마무리하는 가벼운 한 바퀴.", "러닝 · 서울 성수 · 샘플 크루"))
        for user_id, _, _, role in PEOPLE:
            db.execute("INSERT INTO memberships(group_id,user_id,role,joined_at) VALUES(?,?,?,?)",
                       ("hangang", user_id, role, timestamp - 86400 * 30))
        db.execute("INSERT INTO memberships(group_id,user_id,role,joined_at) VALUES(?,?,?,?)",
                   ("seongsu", "outsider", "owner", timestamp - 86400 * 30))
        local = datetime.fromtimestamp(timestamp, ZoneInfo("Asia/Seoul"))
        saturday = (local + timedelta(days=(5 - local.weekday()) % 7 or 7)).replace(hour=7, minute=0, second=0, microsecond=0)
        previous = (local - timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0)
        events = [
            ("토요일, 강바람 한 바퀴", "5km를 편안하게 달려요. 처음 오신 분도, 걷고 싶은 분도 함께해요.", "망원 한강공원 시계탑 앞", saturday.timestamp(), 8),
            ("지난 모임 · 함께 맞은 아침", "샘플 출석을 확인하고 우리 공간이 어떻게 자라는지 체험해 보세요.", "망원 한강공원", previous.timestamp(), 10),
        ]
        event_ids = []
        for title, description, location, starts, capacity in events:
            event_ids.append(db.execute("INSERT INTO events(group_id,title,description,location,starts_at,ends_at,capacity,creator_id) VALUES(?,?,?,?,?,?,?,?)",
                                       ("hangang", title, description, location, starts, starts + 3600, capacity, "mira")).lastrowid)
        for user_id in ["mira", "jun", "haneul"]:
            db.execute("INSERT INTO registrations(event_id,user_id,status,queued_at) VALUES(?,?,?,?)",
                       (event_ids[0], user_id, "confirmed", timestamp - 86400))
        for index, (user_id, _, _, _) in enumerate(PEOPLE):
            present = "present" if index < 4 else "unmarked"
            reg_id = db.execute("INSERT INTO registrations(event_id,user_id,status,queued_at,attendance) VALUES(?,?,?,?,?)",
                                (event_ids[1], user_id, "confirmed", timestamp - 86400 * 2, present)).lastrowid
            if present == "present":
                registration = db.execute("SELECT * FROM registrations WHERE id=?", (reg_id,)).fetchone()
                event = db.execute("SELECT * FROM events WHERE id=?", (event_ids[1],)).fetchone()
                reconcile_contribution(db, registration, event, timestamp - 3600)
        conversation = [
            ("mira", "이번 토요일에도 각자의 속도로 달려요. 모임에서 참가 신청을 해 주세요 🌿"),
            ("sora", "지난번에 처음 함께했는데 기다려 주셔서 고마웠어요! 이번에도 갈게요."),
            ("jun", "천천히 달리는 팀은 제가 같이 갈게요. 걷다가 합류해도 괜찮아요."),
            ("haneul", "달리고 나서 벤치에서 쉬었던 시간이 좋았어요."),
            ("mira", "우리 공간에도 벤치가 생겼네요. 함께한 날을 이렇게 기억해 봐요."),
        ]
        for index, (user_id, body) in enumerate(conversation):
            membership = db.execute("SELECT id FROM memberships WHERE group_id='hangang' AND user_id=?", (user_id,)).fetchone()[0]
            db.execute("INSERT INTO messages(group_id,membership_id,client_id,body,created_at) VALUES(?,?,?,?,?)",
                       ("hangang", membership, f"seed-message-{index}", body, timestamp - (len(conversation) - index) * 900))
        db.execute("INSERT INTO announcements(group_id,author_id,body,created_at) VALUES(?,?,?,?)",
                   ("hangang", "mira", "우리의 약속: 빠른 기록보다 함께하는 시간. 무리하지 않고, 서로의 속도를 존중해요.", timestamp - 86400))
        notify(db, "sora", "hangang", "announcement", "우리 크루의 첫 공지를 확인해 주세요", timestamp - 3600)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
