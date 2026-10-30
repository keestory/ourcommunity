"""Small SQL dialect adapter; tenant choice belongs to the verified guest store."""

from contextlib import contextmanager
import re
import psycopg
from psycopg.conninfo import conninfo_to_dict


SCHEMA = "ourcommunity_preview"
RUNTIME_ROLE = "ourcommunity_preview_runtime"
IDENTITY_TABLES = {"memberships", "messages", "announcements", "events", "registrations",
                   "audit", "reports", "notifications"}


def validate_dsn(dsn):
    try:
        config = conninfo_to_dict(dsn)
        host = config.get("host", "")
        if not host or config.get("hostaddr") or "," in host or config.get("service"):
            raise ValueError()
        if config.get("user", "").split(".")[0] != RUNTIME_ROLE:
            raise ValueError()
        if host not in {"localhost", "127.0.0.1", "::1"} and config.get("sslmode") != "verify-full":
            raise ValueError()
        if config.get("options"):
            raise ValueError()
    except (ValueError, psycopg.Error):
        raise ValueError("Preview PostgreSQL requires the dedicated runtime role, explicit host and verified TLS") from None


@contextmanager
def connection(dsn):
    # No prepared statements or process-global pool: compatible with transaction pooling.
    with psycopg.connect(dsn, prepare_threshold=None, connect_timeout=5) as db:
        db.execute("SET LOCAL search_path = pg_catalog, ourcommunity_preview, pg_temp")
        db.execute("SET LOCAL statement_timeout = '5s'")
        db.execute("SET LOCAL lock_timeout = '3s'")
        db.execute("SET LOCAL idle_in_transaction_session_timeout = '10s'")
        role = db.execute("SELECT current_user, session_user, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
                          "FROM pg_roles WHERE rolname=current_user").fetchone()
        if role != (RUNTIME_ROLE, RUNTIME_ROLE, False, False, False, False, False):
            raise ValueError("Refusing a privileged PostgreSQL runtime role")
        yield db


def privilege_violations(db):
    """Read-only preflight; PUBLIC grants cannot be denied for one login role."""
    failures = []
    if db.execute("SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user)").fetchone():
        failures.append("runtime has role memberships")
    if db.execute("SELECT has_database_privilege(current_user,current_database(),'CREATE')").fetchone()[0]:
        failures.append("runtime can create database schemas")
    for schema, table in db.execute("SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname NOT IN ('pg_catalog','information_schema',%s) AND n.nspname !~ '^pg_' "
            "AND c.relkind IN ('r','p','v','m','f') AND has_schema_privilege(current_user,n.oid,'USAGE') "
            "AND (has_table_privilege(current_user,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') "
            "OR has_any_column_privilege(current_user,c.oid,'SELECT,INSERT,UPDATE,REFERENCES'))", (SCHEMA,)):
        failures.append(f"external relation privilege: {schema}.{table}")
    for (schema,) in db.execute("SELECT nspname FROM pg_namespace WHERE nspname !~ '^pg_' "
            "AND has_schema_privilege(current_user,oid,'CREATE')"):
        failures.append(f"schema creation privilege: {schema}")
    for schema, name in db.execute("SELECT n.nspname,p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
            "WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname !~ '^pg_' "
            "AND has_schema_privilege(current_user,n.oid,'USAGE') AND has_function_privilege(current_user,p.oid,'EXECUTE')"):
        failures.append(f"non-catalog executable function: {schema}.{name}")
    for schema, name in db.execute("SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname NOT IN ('pg_catalog','information_schema',%s) AND n.nspname !~ '^pg_' "
            "AND c.relkind='S' AND has_schema_privilege(current_user,n.oid,'USAGE') "
            "AND has_sequence_privilege(current_user,c.oid,'SELECT,USAGE,UPDATE')", (SCHEMA,)):
        failures.append(f"external sequence privilege: {schema}.{name}")
    if db.execute("SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                  "WHERE n.nspname=%s AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)", (SCHEMA,)).fetchone():
        failures.append("runtime owns application objects")
    if db.execute("SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                  "WHERE n.nspname=%s AND c.relkind='r' AND c.relname NOT IN ('guests','guest_gate','leases') "
                  "AND (NOT c.relrowsecurity OR NOT c.relforcerowsecurity)", (SCHEMA,)).fetchone():
        failures.append("domain RLS is not enabled and forced")
    return failures


class Row(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


class Cursor:
    def __init__(self, cursor, returning=False):
        self.cursor = cursor
        self.lastrowid = cursor.fetchone()[0] if returning else None

    def _row(self, values):
        if values is None:
            return None
        return Row((column.name, value) for column, value in zip(self.cursor.description, values)
                   if column.name != "tenant_id")

    def fetchone(self):
        return self._row(self.cursor.fetchone())

    def fetchall(self):
        return [self._row(row) for row in self.cursor.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())


class DomainConnection:
    def __init__(self, raw):
        self.raw = raw

    def execute(self, statement, params=()):
        # Only repository-owned SQL enters this adapter. Values stay bound parameters.
        statement = statement.replace("?", "%s")
        statement = re.sub(r"ON CONFLICT\(([^)]+)\)", r"ON CONFLICT(tenant_id,\1)", statement)
        if statement.startswith("INSERT OR IGNORE INTO"):
            statement = statement.replace("INSERT OR IGNORE INTO", "INSERT INTO", 1) + " ON CONFLICT DO NOTHING"
        match = re.match(r"INSERT INTO (\w+)", statement)
        returning = bool(match and match[1] in IDENTITY_TABLES)
        if returning:
            statement += " RETURNING id"
        return Cursor(self.raw.execute(statement, params), returning)
