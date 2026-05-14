"""
SQLite database manager for user persistence.

Uses aiosqlite for async-safe access and sqlite3 for synchronous init.
Stores users with hashed passwords and API keys for backward compatibility.
"""
import os
import sqlite3
import aiosqlite
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "tender_engine.db")


def _get_connection() -> sqlite3.Connection:
    """Get a synchronous SQLite connection for schema setup."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """
    Create tables if they don't exist.
    Called once at startup.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                email           TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                full_name       TEXT DEFAULT '',
                plan            TEXT DEFAULT 'free',
                is_active       INTEGER DEFAULT 1,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                key        TEXT UNIQUE NOT NULL,
                name       TEXT DEFAULT 'Default',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
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
                error_message   TEXT
            )
        """)

        # New hardened schema
        cursor.executescript("""
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
            );
            CREATE INDEX IF NOT EXISTS idx_tenders_job_id ON tenders(job_id);
            CREATE INDEX IF NOT EXISTS idx_tenders_user_id ON tenders(user_id);
            CREATE INDEX IF NOT EXISTS idx_tenders_status ON tenders(status);
            CREATE INDEX IF NOT EXISTS idx_tenders_file_hash ON tenders(file_hash);

            CREATE TABLE IF NOT EXISTS tender_results (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id         TEXT NOT NULL,
                raw_text          TEXT,
                sector            TEXT,
                sector_confidence TEXT,
                duration_months   INTEGER,
                locations_json    TEXT,
                workforce_json    TEXT,
                schedule_json     TEXT,
                boq_json          TEXT,
                boq_confidence    TEXT,
                pricing_json      TEXT,
                pricing_mode      TEXT DEFAULT 'estimated',
                warnings_json     TEXT,
                extraction_method TEXT,
                pipeline_version  TEXT DEFAULT 'v1',
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tender_id) REFERENCES tenders(job_id)
            );
            CREATE INDEX IF NOT EXISTS idx_tender_results_tender_id ON tender_results(tender_id);

            CREATE TABLE IF NOT EXISTS processing_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id   TEXT NOT NULL,
                stage       TEXT NOT NULL,
                status      TEXT DEFAULT 'pending',
                details     TEXT,
                duration_ms INTEGER,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tender_id) REFERENCES tenders(job_id)
            );
            CREATE INDEX IF NOT EXISTS idx_processing_events_tender_id ON processing_events(tender_id);
            CREATE INDEX IF NOT EXISTS idx_processing_events_stage ON processing_events(stage);
        """)

        conn.commit()
        logger.info("[DB] SQLite database initialized at %s", DB_PATH)
    except Exception as e:
        logger.error("[DB] Failed to initialize database: %s", e)
        raise
    finally:
        conn.close()


async def get_db() -> aiosqlite.Connection:
    """Return an async SQLite connection for use in route handlers."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def close_db(db: aiosqlite.Connection):
    """Safely close an async database connection."""
    await db.close()


# -- Synchronous helpers for middleware compatibility --

def get_user_by_email_sync(email: str) -> Optional[dict]:
    """Lookup user by email (synchronous, used in middleware)."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
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
        cursor.execute("""
            SELECT u.*, ak.key as api_key
            FROM api_keys ak
            JOIN users u ON u.id = ak.user_id
            WHERE ak.key = ?
        """, (api_key,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()