"""Read-only deployment preflight; never creates roles, grants, tables or keys."""

import os
import sys
from community.postgres import connection, privilege_violations, validate_dsn


def main():
    dsn = os.environ.get('PREVIEW_DATABASE_URL', '')
    try:
        validate_dsn(dsn)
        with connection(dsn) as db:
            failures = privilege_violations(db)
            if not failures:
                ready = db.execute('SELECT id FROM ourcommunity_preview.guest_gate WHERE id=1').fetchone()
                if not ready:
                    failures.append('preview migration marker is missing')
            # No writes in this check, regardless of outcome.
            db.rollback()
        for failure in failures:
            print(f'BLOCKED: {failure}')
        print('BLOCKED' if failures else 'PASS: dedicated role and schema boundary')
        return int(bool(failures))
    except Exception:
        print('BLOCKED: connection, TLS, role or schema check failed. No credentials are printed.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
