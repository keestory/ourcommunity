"""Opt-in PostgreSQL17 integration, strictly on the disposable loopback database."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import time
import pytest
import psycopg
from psycopg.conninfo import make_conninfo
from fastapi.testclient import TestClient
from community.app import create_app
from community.database import iso
from community.postgres import privilege_violations, validate_dsn
from community.preview_store import GUEST_COOKIE

ORIGIN = 'https://preview.example'


@pytest.fixture
def pg():
    if os.environ.get('OURCOMMUNITY_TEST_POSTGRES') != '1':
        pytest.skip('Opt in after scripts/local_postgres_preview.py; never an external DSN')
    config = json.loads(Path('.harness/postgres-local.json').read_text())
    base = dict(host='127.0.0.1', port=config['port'], dbname='ourcommunity_preview_test')
    dsn = make_conninfo(**base, user='ourcommunity_preview_runtime', password=config['runtime_password'])

    @contextmanager
    def admin():
        with psycopg.connect(**base, user='postgres', password=config['admin_password']) as db:
            yield db

    with admin() as db:
        assert db.execute('SELECT current_database()').fetchone()[0] == 'ourcommunity_preview_test'
        assert db.execute("SELECT payload FROM public.other_product_private WHERE id='existing'").fetchone()[0] == 'untouched'
        db.execute('DELETE FROM ourcommunity_preview.guests')
        db.execute("UPDATE ourcommunity_preview.guest_gate SET created_at='{}'")
    apps = []

    def app(**limits):
        instance = create_app(preview=True, public_origin=ORIGIN, postgres_dsn=dsn, preview_limits=limits)
        apps.append(instance)
        return instance

    yield dsn, admin, app
    for instance in apps:
        instance.state.preview_store.close()
    with admin() as db:
        assert db.execute("SELECT payload FROM public.other_product_private WHERE id='existing'").fetchone()[0] == 'untouched'


def client(app, cookies=None, persona='sora'):
    instance = TestClient(app, base_url=ORIGIN, headers={'Origin': ORIGIN}, cookies=cookies)
    response = instance.get('/api/session')
    assert response.status_code == 200, response.text
    if persona:
        response = instance.post('/api/auth/demo', json={'persona': persona})
        assert response.status_code == 200, response.text
        instance.headers['X-CSRF-Token'] = response.json()['csrf']
    return instance


def tenant(admin, visitor):
    digest = hashlib.sha256(visitor.cookies.get(GUEST_COOKIE).encode()).hexdigest()
    with admin() as db:
        return db.execute('SELECT id FROM ourcommunity_preview.guests WHERE token_hash=%s', (digest,)).fetchone()[0]


def test_shared_session_restart_retry_and_separate_visitors(pg):
    _, admin, app = pg
    first = client(app())
    payload = {'client_id': 'cold-start-retry', 'body': '프로세스가 바뀌어도 같은 공간'}
    sent = first.post('/api/groups/hangang/messages', json=payload)
    assert sent.status_code == 201
    replacement = TestClient(app(), base_url=ORIGIN, headers={'Origin': ORIGIN}, cookies=first.cookies)
    session = replacement.get('/api/session').json()
    assert session['user']['id'] == 'sora'
    assert session['preview']['restart_resets'] is False
    replacement.headers['X-CSRF-Token'] = session['csrf']
    assert replacement.post('/api/groups/hangang/messages', json=payload).json()['id'] == sent.json()['id']
    other = client(app())
    assert tenant(admin, first) != tenant(admin, other)
    assert not any(row['body'] == payload['body'] for row in other.get('/api/groups/hangang/messages').json()['items'])
    assert other.delete(f"/api/messages/{sent.json()['id']}").status_code == 404
    other.cookies.set('oc_session', first.cookies.get('oc_session'), domain='preview.example', path='/')
    assert other.get('/api/groups').status_code == 401
    assert first.get('/api/groups/seongsu').status_code == 403


def test_shared_creation_cap_is_atomic_between_app_instances(pg):
    _, admin, app = pg
    apps = [app(max_guests=3, creation_limit=3), app(max_guests=3, creation_limit=3)]
    clients = [TestClient(apps[i % 2], base_url=ORIGIN) for i in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(lambda visitor: visitor.get('/api/session').status_code, clients))
    assert sorted(codes) == [200] * 3 + [429] * 5
    with admin() as db:
        assert db.execute('SELECT count(*) FROM ourcommunity_preview.guests').fetchone()[0] == 3
        assert db.execute('SELECT count(*) FROM ourcommunity_preview.users').fetchone()[0] == 27


def test_concurrent_seats_retries_cancel_and_waitlist_across_workers(pg):
    _, _, app = pg
    first, second = app(), app()
    owner = client(first, persona='mira')
    guest_cookie = {GUEST_COOKIE: owner.cookies.get(GUEST_COOKIE)}
    visitors = [owner, client(second, guest_cookie, 'jun'), client(first, guest_cookie)]
    timestamp = time.time()
    created = owner.post('/api/groups/hangang/events', json={'request_id': 'pg-event-create', 'title': '같이 달리기',
        'location': '한강공원', 'starts_at': iso(timestamp + 86400), 'ends_at': iso(timestamp + 90000), 'capacity': 2})
    assert created.status_code == 201, created.text
    event = created.json()['id']
    def rsvp(visitor, action='join'):
        return visitor.post(f'/api/events/{event}/rsvp', json={'action': action, 'request_id': 'pg-seat-' + action})
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(rsvp, visitors))
    assert sorted(r.json()['my_status'] for r in responses) == ['confirmed', 'confirmed', 'waitlisted']
    with ThreadPoolExecutor(max_workers=3) as pool:
        assert all(r.status_code == 200 for r in pool.map(rsvp, visitors))
    confirmed = visitors[next(i for i, r in enumerate(responses) if r.json()['my_status'] == 'confirmed')]
    waiting = visitors[next(i for i, r in enumerate(responses) if r.json()['my_status'] == 'waitlisted')]
    assert rsvp(confirmed, 'cancel').status_code == 200
    assert waiting.get(f'/api/events/{event}').json()['my_status'] == 'offered'
    assert rsvp(waiting, 'accept').json()['my_status'] == 'confirmed'
    assert owner.get(f'/api/events/{event}').json()['confirmed_count'] == 2


def test_growth_corrections_blocks_and_removed_member(pg):
    _, _, app = pg
    owner = client(app(), persona='mira')
    member = client(app(), {GUEST_COOKIE: owner.cookies.get(GUEST_COOKIE)})
    past = next(row for row in owner.get('/api/groups/hangang/events').json()['items'] if row['can_mark_attendance'])
    path = f"/api/events/{past['id']}/attendance"
    assert member.post(path, json={'user_id': 'jiho', 'present': True}).status_code == 403
    assert owner.post(path, json={'user_id': 'mira', 'present': True}).status_code == 403
    for _ in range(2):
        assert owner.post(path, json={'user_id': 'jiho', 'present': True}).status_code == 200
    assert owner.get('/api/groups/hangang/growth').json()['total_contributions'] == 5
    assert owner.post(path, json={'user_id': 'jiho', 'present': False}).status_code == 200
    assert owner.get('/api/groups/hangang/growth').json()['total_contributions'] == 4
    for _ in range(2):
        assert member.post('/api/groups/hangang/blocks/jun').status_code == 200
    assert member.delete('/api/blocks/jun').status_code == 200
    assert owner.delete('/api/groups/hangang/members/sora').status_code == 200
    assert member.get('/api/groups/hangang/messages').status_code == 403
    assert member.get('/api/groups/hangang/growth').status_code == 403


def test_runtime_rls_foreign_keys_and_transaction_context_reset(pg):
    dsn, admin, app = pg
    first, other = client(app()), client(app())
    a, b = tenant(admin, first), tenant(admin, other)
    with admin() as db:
        foreign_member = db.execute('SELECT id FROM ourcommunity_preview.memberships WHERE tenant_id=%s LIMIT 1', (b,)).fetchone()[0]
    with psycopg.connect(dsn, prepare_threshold=None) as db:
        assert privilege_violations(db) == []
        assert db.execute('SELECT count(*) FROM ourcommunity_preview.users').fetchone()[0] == 0
        db.commit()
        db.execute("SELECT set_config('ourcommunity.tenant_id',%s,true)", (str(a),))
        assert db.execute('SELECT count(*) FROM ourcommunity_preview.users').fetchone()[0] == 9
        assert db.execute('UPDATE ourcommunity_preview.users SET display_name=%s WHERE tenant_id=%s', ('no', b)).rowcount == 0
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute('INSERT INTO ourcommunity_preview.users(id,username,display_name,password_hash,tenant_id) VALUES(%s,%s,%s,%s,%s)', ('bad', 'bad', 'bad', 'bad', b))
        db.rollback()
        assert db.execute('SELECT count(*) FROM ourcommunity_preview.users').fetchone()[0] == 0
        db.commit()
        db.execute("SELECT set_config('ourcommunity.tenant_id',%s,true)", (str(a),))
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            db.execute('INSERT INTO ourcommunity_preview.messages(group_id,membership_id,client_id,body,created_at) VALUES(%s,%s,%s,%s,%s)', ('hangang', foreign_member, 'bad-fk-123', 'invalid', time.time()))
        db.rollback()
        db.execute("SELECT set_config('ourcommunity.tenant_id',%s,true)", (str(b),))
        assert db.execute('SELECT count(*) FROM ourcommunity_preview.users').fetchone()[0] == 9
        db.commit()
        assert db.execute('SELECT count(*) FROM ourcommunity_preview.users').fetchone()[0] == 0
        db.commit()
        for statement in ('SELECT * FROM public.other_product_private', 'CREATE TABLE ourcommunity_preview.forbidden(id int)',
                          'TRUNCATE ourcommunity_preview.messages', 'SET ROLE ourcommunity_preview_owner'):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                db.execute(statement)
            db.rollback()


def test_expiry_cleanup_and_abandoned_lease_recovery(pg):
    _, admin, app = pg
    instance = app(); visitor = client(instance); store = instance.state.preview_store
    token = visitor.cookies.get(GUEST_COOKIE)
    guests = [store.acquire(token, False, False)[0] for _ in range(8)]
    with pytest.raises(Exception) as error:
        app().state.preview_store.acquire(token, False, False)
    assert error.value.status_code == 429
    with admin() as db:
        db.execute('UPDATE ourcommunity_preview.leases SET expires_at=0')
    recovered, _ = app().state.preview_store.acquire(token, False, False)
    store.release(recovered)
    with admin() as db:
        db.execute('UPDATE ourcommunity_preview.guests SET expires_at=0')
    assert visitor.get('/api/groups').status_code == 401
    assert visitor.get('/api/session').status_code == 200
    with admin() as db:
        assert db.execute('SELECT count(*) FROM ourcommunity_preview.guests').fetchone()[0] == 1
        assert db.execute('SELECT 1 FROM ourcommunity_preview.users WHERE tenant_id=%s', (guests[0].id,)).fetchone() is None


def test_failed_mutation_consumes_shared_quota(pg):
    _, _, app = pg
    visitor = client(app(mutation_limit=2))
    assert visitor.post('/api/groups/hangang/read', json={'seq': 1}, headers={'X-CSRF-Token': 'wrong'}).status_code == 403
    replacement = TestClient(app(mutation_limit=2), base_url=ORIGIN, cookies=visitor.cookies,
                             headers={'Origin': ORIGIN, 'X-CSRF-Token': visitor.headers['X-CSRF-Token']})
    assert replacement.post('/api/groups/hangang/read', json={'seq': 1}).status_code == 429


def test_existing_public_grant_detected_without_changing_external_schema(pg):
    _, admin, app = pg
    # Only this disposable fixture's sentinel, never the real project's public schema.
    with admin() as db:
        db.execute('GRANT SELECT ON public.other_product_private TO PUBLIC')
    try:
        response = TestClient(app(), base_url=ORIGIN).get('/api/session')
        assert response.status_code == 503
        assert 'untouched' not in response.text
    finally:
        with admin() as db:
            db.execute('REVOKE SELECT ON public.other_product_private FROM PUBLIC')


@pytest.mark.parametrize('dsn', ['postgresql://postgres:secret@localhost/test',
    'postgresql://ourcommunity_preview_runtime:secret@external.example/test?sslmode=require',
    'postgresql://ourcommunity_preview_runtime:secret@external.example/test?sslmode=disable',
    'user=ourcommunity_preview_runtime service=unapproved',
    'host=localhost user=ourcommunity_preview_runtime options=-csearch_path=public'])
def test_postgres_configuration_rejects_privileged_or_unverified_connections(dsn):
    with pytest.raises(ValueError) as failure:
        validate_dsn(dsn)
    assert 'secret' not in str(failure.value)


def test_vercel_never_falls_back_to_process_local_sqlite(monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    with pytest.raises(ValueError, match='shared PREVIEW_DATABASE_URL'):
        create_app(preview=True, public_origin=ORIGIN)


def test_non_system_pg_prefix_and_external_sequence_privileges_are_rejected(pg):
    dsn, admin, app = pg
    # pgsodium-like names are not the reserved literal pg_ system prefix.
    with admin() as db:
        db.execute('CREATE SCHEMA pgsodium_probe')
        db.execute('GRANT USAGE ON SCHEMA pgsodium_probe TO PUBLIC')
        db.execute('CREATE FUNCTION pgsodium_probe.unsafe_for_preview() RETURNS int LANGUAGE sql AS $$ SELECT 1 $$')
        db.execute('CREATE SEQUENCE public.other_product_sequence')
        db.execute('GRANT USAGE ON SEQUENCE public.other_product_sequence TO ourcommunity_preview_runtime')
    try:
        with psycopg.connect(dsn) as db:
            failures = privilege_violations(db)
            assert 'non-catalog executable function: pgsodium_probe.unsafe_for_preview' in failures
            assert 'external sequence privilege: public.other_product_sequence' in failures
        assert TestClient(app(), base_url=ORIGIN).get('/api/health').status_code == 503
    finally:
        with admin() as db:
            db.execute('DROP FUNCTION pgsodium_probe.unsafe_for_preview()')
            db.execute('DROP SCHEMA pgsodium_probe')
            db.execute('DROP SEQUENCE public.other_product_sequence')


def test_vercel_origin_uses_only_explicit_platform_environment(monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.setenv('VERCEL_URL', 'ourcommunity-build.example.vercel.app')
    # No connection is made at app construction.
    instance = create_app(preview=True, postgres_dsn='host=127.0.0.1 user=ourcommunity_preview_runtime dbname=local_only')
    assert instance.state.preview_store.origin == 'https://ourcommunity-build.example.vercel.app'


def test_notification_cannot_reference_another_tenant_event(pg):
    dsn, admin, app = pg
    first, other = client(app()), client(app())
    a, b = tenant(admin, first), tenant(admin, other)
    with admin() as db:
        event = db.execute('SELECT id FROM ourcommunity_preview.events WHERE tenant_id=%s LIMIT 1', (b,)).fetchone()[0]
    with psycopg.connect(dsn) as db:
        db.execute("SELECT set_config('ourcommunity.tenant_id',%s,true)", (str(a),))
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            db.execute('INSERT INTO ourcommunity_preview.notifications(user_id,group_id,kind,title,event_id,created_at) VALUES(%s,%s,%s,%s,%s,%s)',
                       ('sora', 'hangang', 'test', 'invalid cross-tenant event', event, time.time()))
        db.rollback()


def test_column_only_public_grant_is_detected(pg):
    dsn, admin, app = pg
    with admin() as db:
        db.execute('GRANT SELECT(payload) ON public.other_product_private TO PUBLIC')
    try:
        with psycopg.connect(dsn) as db:
            assert not db.execute("SELECT has_table_privilege(current_user,'public.other_product_private','SELECT')").fetchone()[0]
            assert 'external relation privilege: public.other_product_private' in privilege_violations(db)
        assert TestClient(app(), base_url=ORIGIN).get('/api/health').status_code == 503
    finally:
        with admin() as db:
            db.execute('REVOKE SELECT(payload) ON public.other_product_private FROM PUBLIC')
