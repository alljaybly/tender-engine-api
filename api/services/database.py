"""
Database manager — dual backend: SQLite (local) and PostgreSQL (production).

- When DATABASE_URL env var starts with "postgresql://", PostgreSQL is used.
- Otherwise, a local SQLite file is used (backward compatible).

Async operations:   aiosqlite (SQLite) or asyncpg (PostgreSQL)
Sync operations:    sqlite3   (SQLite) or psycopg2 (PostgreSQL)

All existing function signatures are preserved exactly:
  get_db()          -> async connection
  close_db()        -> close async connection
  _get_connection() -> sync connection
  get_user_by_email_sync()
  get_user_by_id_sync()
  get_api_key_sync()
  init_db()         -> schema creation at startup
"""
import os
import sqlite3
import aiosqlite
import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

# ── Backend detection ─────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = DATABASE_URL.startswith("postgresql://")

if USE_POSTGRES:
    try:
        import asyncpg
        import psycopg2
        import psycopg2.extras
        logger.info("[DB] PostgreSQL backend selected")
    except ImportError as e:
        logger.error("[DB] PostgreSQL drivers missing: %s. Install asyncpg and psycopg2-binary.", e)
        raise
else:
    logger.info("[DB] SQLite backend selected")

# ── SQLite paths ──────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "tender_engine.db")

# ── PostgreSQL connection pool (lazy init) ────────────────────────────
_pg_pool: Any = None  # asyncpg.Pool


async def _get_pg_pool():
    """Get or create the asyncpg connection pool."""
    global _pg_pool
    if _pg_pool is None:
        _pg_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            command_timeout=30,
        )
    return _pg_pool


# ── SQL translation helpers ───────────────────────────────────────────

def _compile_placeholders(sql: str, args: tuple) -> str:
    """Convert ? placeholders to $1, $2, ... for PostgreSQL.

    Placeholders are numbered left-to-right so that args[i] maps to the
    (i+1)-th placeholder ($1 = args[0]), matching the positional binding
    used by both psycopg2 and asyncpg.
    """
    if not USE_POSTGRES:
        return sql
    result = sql
    for i, _ in enumerate(args, start=1):
        result = result.replace("?", f"${i}", 1)
    return result


def _pg_row_to_dict(row, columns):
    """Convert a psycopg2 tuple row to a dict keyed by column names."""
    return dict(zip(columns, row))


# ── Schema DDL ────────────────────────────────────────────────────────

# SQLite DDL (unchanged from existing)
SQLITE_USERS_DDL = """
    CREATE TABLE IF NOT EXISTS users (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        email                   TEXT UNIQUE NOT NULL,
        hashed_password         TEXT NOT NULL,
        full_name               TEXT DEFAULT '',
        company_name            TEXT DEFAULT '',
        role                    TEXT DEFAULT 'customer',
        plan                    TEXT DEFAULT 'free',
        is_active               INTEGER DEFAULT 1,
        email_verified          INTEGER DEFAULT 1,
        failed_login_attempts   INTEGER DEFAULT 0,
        locked_until            TIMESTAMP,
        last_login_at           TIMESTAMP,
        created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

SQLITE_API_KEYS_DDL = """
    CREATE TABLE IF NOT EXISTS api_keys (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL REFERENCES users(id),
        key        TEXT UNIQUE NOT NULL,
        name       TEXT DEFAULT 'Default',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

SQLITE_AUTH_SESSIONS_DDL = """
    CREATE TABLE IF NOT EXISTS auth_sessions (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        session_id          TEXT UNIQUE NOT NULL,
        refresh_token_hash  TEXT NOT NULL,
        user_agent          TEXT DEFAULT '',
        ip_address          TEXT DEFAULT '',
        remember_me         INTEGER DEFAULT 0,
        impersonated_by     INTEGER,
        expires_at          TIMESTAMP NOT NULL,
        last_active_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        revoked_at          TIMESTAMP,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

SQLITE_AUTH_AUDIT_DDL = """
    CREATE TABLE IF NOT EXISTS auth_audit_log (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id             INTEGER,
        actor_user_id       INTEGER,
        action              TEXT NOT NULL,
        session_id          TEXT,
        ip_address          TEXT DEFAULT '',
        user_agent          TEXT DEFAULT '',
        details_json        TEXT,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

SQLITE_PROCESSING_JOBS_DDL = """
    CREATE TABLE IF NOT EXISTS processing_jobs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id          TEXT UNIQUE NOT NULL,
        user_id         TEXT,
        filename        TEXT,
        original_name   TEXT,
        status          TEXT DEFAULT 'queued',
        progress        TEXT DEFAULT 'pending',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        result_json     TEXT,
        error_message   TEXT,
        retry_count     INTEGER DEFAULT 0,
        retry_data_json TEXT
    )
"""

SQLITE_MARKETING_LEADS_DDL = """
    CREATE TABLE IF NOT EXISTS marketing_leads (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        email           TEXT UNIQUE NOT NULL,
        company         TEXT DEFAULT '',
        role            TEXT DEFAULT '',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

SQLITE_TENDERS_DDL = """
    CREATE TABLE IF NOT EXISTS tenders (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id            TEXT UNIQUE NOT NULL,
        user_id           TEXT,
        filename          TEXT,
        original_filename TEXT,
        file_hash         TEXT DEFAULT '',
        mime_type         TEXT DEFAULT '',
        file_size         INTEGER DEFAULT 0,
        status            TEXT DEFAULT 'queued',
        pipeline_version  TEXT DEFAULT 'v1',
        created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at      TIMESTAMP
    )
"""

SQLITE_TENDER_RESULTS_DDL = """
    CREATE TABLE IF NOT EXISTS tender_results (
        id                         INTEGER PRIMARY KEY AUTOINCREMENT,
        tender_id                  TEXT NOT NULL,
        raw_text                   TEXT,
        sector                     TEXT,
        sector_confidence          TEXT,
        duration_months            INTEGER,
        locations_json             TEXT,
        workforce_json             TEXT,
        schedule_json              TEXT,
        boq_json                   TEXT,
        boq_confidence             TEXT,
        pricing_json               TEXT,
        pricing_mode               TEXT DEFAULT 'estimated',
        warnings_json              TEXT,
        evidence_json              TEXT,
        extraction_method          TEXT,
        pipeline_version           TEXT DEFAULT 'v1',
        created_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        win_probability_index      REAL,
        win_probability_explanation TEXT,
        critical_traps_json        TEXT,
        compliance_gaps_json       TEXT,
        detected_currency_json     TEXT,
        FOREIGN KEY (tender_id) REFERENCES tenders(job_id)
    )
"""

SQLITE_PROCESSING_EVENTS_DDL = """
    CREATE TABLE IF NOT EXISTS processing_events (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tender_id   TEXT NOT NULL,
        stage       TEXT NOT NULL,
        status      TEXT DEFAULT 'pending',
        details     TEXT,
        duration_ms INTEGER,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tender_id) REFERENCES tenders(job_id)
    )
"""

SQLITE_AUDIT_LOG_DDL = """
    CREATE TABLE IF NOT EXISTS audit_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        tender_id       TEXT NOT NULL,
        stage           TEXT NOT NULL,
        status          TEXT NOT NULL DEFAULT 'pending',
        timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        duration_ms     INTEGER,
        confidence      TEXT,
        source_module   TEXT,
        warnings        TEXT,
        errors          TEXT,
        details         TEXT,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tender_id) REFERENCES tenders(job_id)
    )
"""

SQLITE_PLATFORM_ANALYTICS_DDL = """
    CREATE TABLE IF NOT EXISTS platform_analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        processing_duration_ms INTEGER,
        upload_size_bytes INTEGER,
        page_count INTEGER,
        ocr_used INTEGER,
        ocr_page_count INTEGER,
        document_language TEXT,
        detected_jurisdiction TEXT,
        tender_type TEXT,
        procurement_method TEXT,
        detected_currency TEXT,
        currencies_detected_json TEXT,
        employer_detected INTEGER,
        tender_number_detected INTEGER,
        closing_date_detected INTEGER,
        boq_detected INTEGER,
        boq_item_count INTEGER,
        work_categories_detected_json TEXT,
        pricing_executed INTEGER,
        readiness_score REAL,
        submission_package_generated INTEGER,
        completion_guide_generated INTEGER,
        processing_status TEXT,
        warnings_count INTEGER,
        errors_count INTEGER,
        upload_time_ms INTEGER,
        validation_time_ms INTEGER,
        ocr_duration_ms INTEGER,
        text_extraction_duration_ms INTEGER,
        entity_extraction_duration_ms INTEGER,
        boq_duration_ms INTEGER,
        pricing_duration_ms INTEGER,
        report_generation_duration_ms INTEGER,
        zip_package_generation_duration_ms INTEGER,
        total_processing_time_ms INTEGER,
        average_page_processing_time_ms REAL,
        is_scanned INTEGER,
        is_digital INTEGER,
        contains_boq INTEGER,
        contains_drawings INTEGER,
        contains_tables INTEGER,
        contains_appendices INTEGER,
        contains_pricing_schedules INTEGER,
        contains_forms INTEGER,
        contains_signatures INTEGER,
        contains_evaluation_criteria INTEGER,
        contains_mandatory_documentation INTEGER,
        extraction_quality_json TEXT,
        document_characteristics_json TEXT,
        raw_metrics_json TEXT,
        FOREIGN KEY (job_id) REFERENCES tenders(job_id)
    )
"""

# PostgreSQL DDL — SERIAL instead of AUTOINCREMENT, no inline FK in CREATE
PG_USERS_DDL = """
    CREATE TABLE IF NOT EXISTS users (
        id                      SERIAL PRIMARY KEY,
        email                   TEXT UNIQUE NOT NULL,
        hashed_password         TEXT NOT NULL,
        full_name               TEXT DEFAULT '',
        company_name            TEXT DEFAULT '',
        role                    TEXT DEFAULT 'customer',
        plan                    TEXT DEFAULT 'free',
        is_active               INTEGER DEFAULT 1,
        email_verified          INTEGER DEFAULT 1,
        failed_login_attempts   INTEGER DEFAULT 0,
        locked_until            TIMESTAMP,
        last_login_at           TIMESTAMP,
        created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

PG_API_KEYS_DDL = """
    CREATE TABLE IF NOT EXISTS api_keys (
        id         SERIAL PRIMARY KEY,
        user_id    INTEGER NOT NULL REFERENCES users(id),
        key        TEXT UNIQUE NOT NULL,
        name       TEXT DEFAULT 'Default',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

PG_AUTH_SESSIONS_DDL = """
    CREATE TABLE IF NOT EXISTS auth_sessions (
        id                  SERIAL PRIMARY KEY,
        user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        session_id          TEXT UNIQUE NOT NULL,
        refresh_token_hash  TEXT NOT NULL,
        user_agent          TEXT DEFAULT '',
        ip_address          TEXT DEFAULT '',
        remember_me         INTEGER DEFAULT 0,
        impersonated_by     INTEGER,
        expires_at          TIMESTAMP NOT NULL,
        last_active_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        revoked_at          TIMESTAMP,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

PG_AUTH_AUDIT_DDL = """
    CREATE TABLE IF NOT EXISTS auth_audit_log (
        id                  SERIAL PRIMARY KEY,
        user_id             INTEGER,
        actor_user_id       INTEGER,
        action              TEXT NOT NULL,
        session_id          TEXT,
        ip_address          TEXT DEFAULT '',
        user_agent          TEXT DEFAULT '',
        details_json        TEXT,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

PG_PROCESSING_JOBS_DDL = """
    CREATE TABLE IF NOT EXISTS processing_jobs (
        id              SERIAL PRIMARY KEY,
        job_id          TEXT UNIQUE NOT NULL,
        user_id         TEXT,
        filename        TEXT,
        original_name   TEXT,
        status          TEXT DEFAULT 'queued',
        progress        TEXT DEFAULT 'pending',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        result_json     TEXT,
        error_message   TEXT,
        retry_count     INTEGER DEFAULT 0,
        retry_data_json TEXT
    )
"""

PG_MARKETING_LEADS_DDL = """
    CREATE TABLE IF NOT EXISTS marketing_leads (
        id              SERIAL PRIMARY KEY,
        name            TEXT NOT NULL,
        email           TEXT UNIQUE NOT NULL,
        company         TEXT DEFAULT '',
        role            TEXT DEFAULT '',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

PG_TENDERS_DDL = """
    CREATE TABLE IF NOT EXISTS tenders (
        id                SERIAL PRIMARY KEY,
        job_id            TEXT UNIQUE NOT NULL,
        user_id           TEXT,
        filename          TEXT,
        original_filename TEXT,
        file_hash         TEXT DEFAULT '',
        mime_type         TEXT DEFAULT '',
        file_size         INTEGER DEFAULT 0,
        status            TEXT DEFAULT 'queued',
        pipeline_version  TEXT DEFAULT 'v1',
        created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at      TIMESTAMP
    )
"""

PG_TENDER_RESULTS_DDL = """
    CREATE TABLE IF NOT EXISTS tender_results (
        id                         SERIAL PRIMARY KEY,
        tender_id                  TEXT NOT NULL REFERENCES tenders(job_id),
        raw_text                   TEXT,
        sector                     TEXT,
        sector_confidence          TEXT,
        duration_months            INTEGER,
        locations_json             TEXT,
        workforce_json             TEXT,
        schedule_json              TEXT,
        boq_json                   TEXT,
        boq_confidence             TEXT,
        pricing_json               TEXT,
        pricing_mode               TEXT DEFAULT 'estimated',
        warnings_json              TEXT,
        evidence_json              TEXT,
        extraction_method          TEXT,
        pipeline_version           TEXT DEFAULT 'v1',
        created_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        win_probability_index      REAL,
        win_probability_explanation TEXT,
        critical_traps_json        TEXT,
        compliance_gaps_json       TEXT,
        detected_currency_json     TEXT
    )
"""

PG_PROCESSING_EVENTS_DDL = """
    CREATE TABLE IF NOT EXISTS processing_events (
        id          SERIAL PRIMARY KEY,
        tender_id   TEXT NOT NULL REFERENCES tenders(job_id),
        stage       TEXT NOT NULL,
        status      TEXT DEFAULT 'pending',
        details     TEXT,
        duration_ms INTEGER,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

PG_AUDIT_LOG_DDL = """
    CREATE TABLE IF NOT EXISTS audit_log (
        id              SERIAL PRIMARY KEY,
        tender_id       TEXT NOT NULL REFERENCES tenders(job_id),
        stage           TEXT NOT NULL,
        status          TEXT NOT NULL DEFAULT 'pending',
        timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        duration_ms     INTEGER,
        confidence      TEXT,
        source_module   TEXT,
        warnings        TEXT,
        errors          TEXT,
        details         TEXT,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

PG_PLATFORM_ANALYTICS_DDL = """
    CREATE TABLE IF NOT EXISTS platform_analytics (
        id SERIAL PRIMARY KEY,
        job_id TEXT UNIQUE NOT NULL REFERENCES tenders(job_id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        processing_duration_ms INTEGER,
        upload_size_bytes INTEGER,
        page_count INTEGER,
        ocr_used INTEGER,
        ocr_page_count INTEGER,
        document_language TEXT,
        detected_jurisdiction TEXT,
        tender_type TEXT,
        procurement_method TEXT,
        detected_currency TEXT,
        currencies_detected_json TEXT,
        employer_detected INTEGER,
        tender_number_detected INTEGER,
        closing_date_detected INTEGER,
        boq_detected INTEGER,
        boq_item_count INTEGER,
        work_categories_detected_json TEXT,
        pricing_executed INTEGER,
        readiness_score REAL,
        submission_package_generated INTEGER,
        completion_guide_generated INTEGER,
        processing_status TEXT,
        warnings_count INTEGER,
        errors_count INTEGER,
        upload_time_ms INTEGER,
        validation_time_ms INTEGER,
        ocr_duration_ms INTEGER,
        text_extraction_duration_ms INTEGER,
        entity_extraction_duration_ms INTEGER,
        boq_duration_ms INTEGER,
        pricing_duration_ms INTEGER,
        report_generation_duration_ms INTEGER,
        zip_package_generation_duration_ms INTEGER,
        total_processing_time_ms INTEGER,
        average_page_processing_time_ms REAL,
        is_scanned INTEGER,
        is_digital INTEGER,
        contains_boq INTEGER,
        contains_drawings INTEGER,
        contains_tables INTEGER,
        contains_appendices INTEGER,
        contains_pricing_schedules INTEGER,
        contains_forms INTEGER,
        contains_signatures INTEGER,
        contains_evaluation_criteria INTEGER,
        contains_mandatory_documentation INTEGER,
        extraction_quality_json TEXT,
        document_characteristics_json TEXT,
        raw_metrics_json TEXT
    )
"""


# ── Synchronous connection (for middleware and sync helpers) ──────────

class _SyncPgConnection:
    """Wrapper around psycopg2 connection that provides a sqlite3-like cursor/commit interface."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return _SyncPgCursor(self._conn)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executescript(self, sql):
        """Execute multiple statements separated by semicolons."""
        cur = self.cursor()
        # Split on semicolons but not inside strings
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        for stmt in statements:
            cur.execute(stmt)
        return cur


class _SyncPgCursor:
    """Wrapper around psycopg2 cursor that provides sqlite3-like fetch methods."""

    def __init__(self, conn):
        self._conn = conn
        self._cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        self.lastrowid = None
        self._description = None

    def execute(self, sql, params=None):
        if params:
            compiled = _compile_placeholders(sql, params)
            self._cur.execute(compiled, params)
        else:
            self._cur.execute(sql)

        # Try to get lastrowid for INSERT with RETURNING
        if sql.strip().upper().startswith("INSERT"):
            try:
                # Check if there's a RETURNING clause
                result = self._cur.fetchone() if self._cur.description else None
                if result and "id" in result:
                    self.lastrowid = result["id"]
            except Exception:
                pass

        self._description = self._cur.description
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        return row

    def fetchall(self):
        return self._cur.fetchall()

    def close(self):
        self._cur.close()


def _get_connection():
    """Get a synchronous database connection.

    For SQLite: returns sqlite3.Connection with row_factory set.
    For PostgreSQL: returns _SyncPgConnection wrapper around psycopg2.
    """
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return _SyncPgConnection(conn)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── PostgreSQL ALTER TABLE migration helpers ──────────────────────────

def _pg_add_column_if_not_exists(table: str, column: str, col_type: str, cursor) -> None:
    """Add a column if it doesn't exist in PostgreSQL."""
    try:
        check_sql = (
            f"SELECT 1 FROM information_schema.columns "
            f"WHERE table_name='{table}' AND column_name='{column}'"
        )
        cursor.execute(check_sql)
        if cursor.fetchone() is None:
            cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}')
    except Exception:
        pass


# ── Synchronous schema initialization ─────────────────────────────────

def init_db():
    """Create tables if they don't exist. Called once at startup."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        if USE_POSTGRES:
            # ── PostgreSQL schema ────────────────────────────────────
            cursor.execute(PG_USERS_DDL)
            cursor.execute(PG_API_KEYS_DDL)
            cursor.execute(PG_AUTH_SESSIONS_DDL)
            cursor.execute(PG_AUTH_AUDIT_DDL)
            cursor.execute(PG_PROCESSING_JOBS_DDL)
            cursor.execute(PG_MARKETING_LEADS_DDL)
            cursor.execute(PG_TENDERS_DDL)
            cursor.execute(PG_TENDER_RESULTS_DDL)
            cursor.execute(PG_PROCESSING_EVENTS_DDL)
            cursor.execute(PG_AUDIT_LOG_DDL)
            cursor.execute(PG_PLATFORM_ANALYTICS_DDL)

            # ── Indexes ──────────────────────────────────────────────
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_session_id ON auth_sessions(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_audit_user_id ON auth_audit_log(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_audit_actor_user_id ON auth_audit_log(actor_user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_job_id ON tenders(job_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_user_id ON tenders(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_status ON tenders(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_file_hash ON tenders(file_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tender_results_tender_id ON tender_results(tender_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_processing_events_tender_id ON processing_events(tender_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_processing_events_stage ON processing_events(stage)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_tender_id ON audit_log(tender_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_stage ON audit_log(stage)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_status ON audit_log(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_platform_analytics_job_id ON platform_analytics(job_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_platform_analytics_completed_at ON platform_analytics(completed_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_platform_analytics_status ON platform_analytics(processing_status)")

            # ── ALTER TABLE migrations (PostgreSQL-safe) ─────────────
            _pg_add_column_if_not_exists("users", "company_name", "TEXT DEFAULT ''", cursor)
            _pg_add_column_if_not_exists("users", "role", "TEXT DEFAULT 'customer'", cursor)
            _pg_add_column_if_not_exists("users", "email_verified", "INTEGER DEFAULT 1", cursor)
            _pg_add_column_if_not_exists("users", "failed_login_attempts", "INTEGER DEFAULT 0", cursor)
            _pg_add_column_if_not_exists("users", "locked_until", "TIMESTAMP", cursor)
            _pg_add_column_if_not_exists("users", "last_login_at", "TIMESTAMP", cursor)
            _pg_add_column_if_not_exists("processing_jobs", "retry_count", "INTEGER DEFAULT 0", cursor)
            _pg_add_column_if_not_exists("processing_jobs", "retry_data_json", "TEXT", cursor)
            _pg_add_column_if_not_exists("tender_results", "win_probability_index", "REAL", cursor)
            _pg_add_column_if_not_exists("tender_results", "win_probability_explanation", "TEXT", cursor)
            _pg_add_column_if_not_exists("tender_results", "critical_traps_json", "TEXT", cursor)
            _pg_add_column_if_not_exists("tender_results", "compliance_gaps_json", "TEXT", cursor)
            _pg_add_column_if_not_exists("tender_results", "detected_currency_json", "TEXT", cursor)
            _pg_add_column_if_not_exists("tender_results", "evidence_json", "TEXT", cursor)

            conn.commit()
            logger.info("[DB] PostgreSQL schema initialized")

        else:
            # ── SQLite schema (unchanged from original) ──────────────
            cursor.execute(SQLITE_USERS_DDL)
            cursor.execute(SQLITE_API_KEYS_DDL)

            # ALTER TABLE migrations (SQLite)
            for statement in [
                "ALTER TABLE users ADD COLUMN company_name TEXT DEFAULT ''",
                "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'customer'",
                "ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 1",
                "ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN locked_until TIMESTAMP",
                "ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP",
            ]:
                try:
                    cursor.execute(statement)
                except sqlite3.OperationalError:
                    pass

            cursor.execute(SQLITE_AUTH_SESSIONS_DDL)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_session_id ON auth_sessions(session_id)")

            cursor.execute(SQLITE_AUTH_AUDIT_DDL)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_audit_user_id ON auth_audit_log(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_audit_actor_user_id ON auth_audit_log(actor_user_id)")

            cursor.execute(SQLITE_PROCESSING_JOBS_DDL)

            # Add retry tracking columns
            try:
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN retry_count INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE processing_jobs ADD COLUMN retry_data_json TEXT")
            except sqlite3.OperationalError:
                pass

            cursor.execute(SQLITE_MARKETING_LEADS_DDL)

            # Tenders + results + events
            cursor.executescript(SQLITE_TENDERS_DDL + "\n" + SQLITE_TENDER_RESULTS_DDL + "\n" + SQLITE_PROCESSING_EVENTS_DDL)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_job_id ON tenders(job_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_user_id ON tenders(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_status ON tenders(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_file_hash ON tenders(file_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tender_results_tender_id ON tender_results(tender_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_processing_events_tender_id ON processing_events(tender_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_processing_events_stage ON processing_events(stage)")

            # ALTER TABLE for forensic compliance columns
            for col_sql in [
                "ALTER TABLE tender_results ADD COLUMN win_probability_index REAL",
                "ALTER TABLE tender_results ADD COLUMN win_probability_explanation TEXT",
                "ALTER TABLE tender_results ADD COLUMN critical_traps_json TEXT",
                "ALTER TABLE tender_results ADD COLUMN compliance_gaps_json TEXT",
                "ALTER TABLE tender_results ADD COLUMN detected_currency_json TEXT",
                "ALTER TABLE tender_results ADD COLUMN evidence_json TEXT",
            ]:
                try:
                    cursor.execute(col_sql)
                except sqlite3.OperationalError:
                    pass

            # Audit log
            cursor.execute(SQLITE_AUDIT_LOG_DDL)
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_tender_id ON audit_log(tender_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_stage ON audit_log(stage)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_status ON audit_log(status)")
            except sqlite3.OperationalError:
                pass

            conn.commit()

            # Platform analytics schema (separate, uses direct sqlite3)
            from .analytics_service import init_analytics_schema_sync
            init_analytics_schema_sync()

            logger.info("[DB] SQLite database initialized at %s", DB_PATH)

    except Exception as e:
        logger.error("[DB] Failed to initialize database: %s", e)
        raise
    finally:
        conn.close()


# ── Async SQLite wrapper that mimics aiosqlite.Row ────────────────────

class _AsyncPgRow:
    """Wrapper around asyncpg.Record that provides aiosqlite.Row-like dict access."""

    def __init__(self, record):
        self._record = record

    def __getitem__(self, key):
        return self._record[key]

    def keys(self):
        return self._record.keys()

    def __iter__(self):
        return iter(dict(self._record))


class _AsyncPgConnection:
    """Wrapper around asyncpg connection that mimics aiosqlite.Connection interface."""

    def __init__(self, pool):
        self._pool = pool
        self._conn = None

    async def _ensure_conn(self):
        if self._conn is None:
            self._conn = await self._pool.acquire()

    async def execute(self, sql, params=None):
        await self._ensure_conn()
        if params:
            compiled = _compile_placeholders(sql, params)
            result = await self._conn.execute(compiled, *params)
        else:
            result = await self._conn.execute(sql)
        return _AsyncPgCursor(result, self._conn, sql)

    async def commit(self):
        # asyncpg auto-commits — no explicit commit needed in pool mode
        pass

    async def close(self):
        if self._conn:
            await self._pool.release(self._conn)
            self._conn = None


class _AsyncPgCursor:
    """Wrapper around asyncpg result that mimics aiosqlite cursor."""

    def __init__(self, result, conn, sql):
        self._result = result
        self._conn = conn
        self._sql = sql
        self.lastrowid = None

        # If this was an INSERT, try to extract lastrowid via RETURNING
        if sql.strip().upper().startswith("INSERT"):
            # The result from execute() for INSERT is the status string
            # We need to get lastrowid differently — the caller will use it from conn
            pass

    async def fetchone(self):
        # asyncpg execute returns the result string for INSERT/UPDATE,
        # but returns rows for SELECT. We need to handle both.
        if isinstance(self._result, str):
            return None
        # For asyncpg, the result of execute(SELECT) is the records directly
        try:
            # If the result is iterable of records
            records = await self._result  # type: ignore
            return None  # handled below
        except Exception:
            return None

    async def fetchall(self):
        return []


class _AsyncPgPoolConnection:
    """Full asyncpg pool-based connection wrapper that matches aiosqlite.Connection interface.

    This is the primary async connection for PostgreSQL. It:
    - Acquires a connection from the pool on execute
    - Returns _AsyncPgCursor objects that support fetchone()/fetchall()
    - Properly handles ? → $N placeholder conversion
    - Supports dict-like row access via asyncpg.Record
    """

    def __init__(self, pool):
        self._pool = pool

    async def execute(self, sql, params=None):
        """Execute SQL and return a cursor-like object."""
        conn = await self._pool.acquire()
        try:
            if params:
                # Convert ? to $1, $2, ... left-to-right so params[i] maps
                # to the (i+1)-th placeholder in the SQL, matching how
                # asyncpg binds positional arguments ($1 = args[0]).
                converted = sql
                for i, _ in enumerate(params, start=1):
                    converted = converted.replace("?", f"${i}", 1)
                stmt = await conn.prepare(converted)
                result = await stmt.fetch(*params)
            else:
                result = await conn.fetch(sql)

            class _Cursor:
                def __init__(self, rows):
                    self._rows = rows

                async def fetchone(self):
                    return self._rows[0] if self._rows else None

                async def fetchall(self):
                    return self._rows

            return _Cursor(result)
        finally:
            await self._pool.release(conn)

    async def commit(self):
        # asyncpg auto-commits in pool mode
        pass

    async def close(self):
        # Pool-level close is handled at shutdown
        pass


# ── Public async interface ────────────────────────────────────────────

async def get_db():
    """Return an async database connection.

    For SQLite: returns aiosqlite.Connection
    For PostgreSQL: returns _AsyncPgPoolConnection wrapping the asyncpg pool
    """
    if USE_POSTGRES:
        pool = await _get_pg_pool()
        return _AsyncPgPoolConnection(pool)

    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def close_db(db):
    """Safely close an async database connection."""
    if USE_POSTGRES:
        await db.close()
    else:
        await db.close()


async def close_pool():
    """Close the PostgreSQL connection pool at shutdown."""
    global _pg_pool
    if _pg_pool:
        await _pg_pool.close()
        _pg_pool = None


# ── Synchronous helpers for middleware compatibility ──────────────────

def get_user_by_email_sync(email: str) -> Optional[dict]:
    """Lookup user by email (synchronous, used in middleware)."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        if USE_POSTGRES:
            cursor.execute("SELECT * FROM users WHERE email = $1", (email,))
        else:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def get_user_by_id_sync(user_id: int) -> Optional[dict]:
    """Lookup user by ID (synchronous)."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        if USE_POSTGRES:
            cursor.execute("SELECT * FROM users WHERE id = $1", (user_id,))
        else:
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def get_api_key_sync(api_key: str) -> Optional[dict]:
    """Lookup an API key and return associated user data."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        if USE_POSTGRES:
            cursor.execute(
                """SELECT u.*, ak.key as api_key
                   FROM api_keys ak
                   JOIN users u ON u.id = ak.user_id
                   WHERE ak.key = $1""",
                (api_key,),
            )
        else:
            cursor.execute(
                """SELECT u.*, ak.key as api_key
                   FROM api_keys ak
                   JOIN users u ON u.id = ak.user_id
                   WHERE ak.key = ?""",
                (api_key,),
            )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()
