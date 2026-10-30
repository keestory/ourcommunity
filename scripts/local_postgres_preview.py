"""Start a disposable localhost-only PostgreSQL17 fixture. No cloud credentials."""

import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import psycopg
from psycopg import sql


def main():
    root = Path(__file__).resolve().parent.parent
    target = root / '.harness' / 'postgres-local.json'
    if target.exists():
        raise SystemExit('Local fixture config already exists; refusing to replace it.')
    config = {'port': 55432, 'admin_password': secrets.token_urlsafe(32), 'runtime_password': secrets.token_urlsafe(32)}
    env = dict(os.environ, POSTGRES_PASSWORD=config['admin_password'])
    subprocess.run(['docker', 'run', '-d', '--name', 'ourcommunity-postgres-qa',
        '--tmpfs', '/var/lib/postgresql/data:rw,size=512m', '--memory', '512m', '--cpus', '1',
        '-p', '127.0.0.1:55432:5432', '-e', 'POSTGRES_PASSWORD', 'postgres:17-bookworm'], env=env, check=True, capture_output=True)
    target.parent.mkdir(exist_ok=True)
    with open(target, 'x', opener=lambda path, flags: os.open(path, flags, 0o600)) as output:
        json.dump(config, output)
    base = dict(host='127.0.0.1', port=55432, user='postgres', password=config['admin_password'])
    for attempt in range(40):
        try:
            with psycopg.connect(**base, dbname='postgres', connect_timeout=1, autocommit=True) as db:
                db.execute('CREATE DATABASE ourcommunity_preview_test')
            break
        except psycopg.OperationalError:
            if attempt == 39:
                raise SystemExit('Local PostgreSQL did not become ready; inspect the named test container.') from None
            time.sleep(0.25)
    with psycopg.connect(**base, dbname='ourcommunity_preview_test') as db:
        db.execute((root / 'migrations/001_preview_postgres.sql').read_text(), prepare=False)
        db.execute(sql.SQL('ALTER ROLE ourcommunity_preview_runtime LOGIN PASSWORD {}').format(sql.Literal(config['runtime_password'])))
        db.execute('CREATE TABLE public.other_product_private(id text PRIMARY KEY, payload text)')
        db.execute("INSERT INTO public.other_product_private VALUES('existing','untouched')")
    print('Local PostgreSQL17 ready on 127.0.0.1:55432; credentials only in ignored mode-0600 fixture file.')
    print('Run OURCOMMUNITY_TEST_POSTGRES=1 .venv/bin/python -m pytest -q')


if __name__ == '__main__':
    main()
