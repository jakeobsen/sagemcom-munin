"""SQLite storage for modem channel statistics."""

import re
import sqlite3
from datetime import datetime, timezone


def connect(db_path: str) -> sqlite3.Connection:
    """Open (and initialize if needed) the stats database."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS downstream_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            channel_id INTEGER,
            frequency_hz INTEGER,
            power_dbmv REAL,
            snr_db REAL,
            modulation TEXT,
            locked INTEGER,
            channel_type TEXT
        );

        CREATE TABLE IF NOT EXISTS upstream_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            channel_id INTEGER,
            frequency_hz INTEGER,
            power_dbmv REAL,
            modulation TEXT,
            locked INTEGER,
            channel_type TEXT
        );

        CREATE TABLE IF NOT EXISTS modem_log_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_timestamp TEXT NOT NULL,
            level TEXT,
            category TEXT,
            message TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            UNIQUE(log_timestamp, message)
        );

        CREATE INDEX IF NOT EXISTS idx_ds_timestamp
            ON downstream_channels(timestamp);
        CREATE INDEX IF NOT EXISTS idx_us_timestamp
            ON upstream_channels(timestamp);
        CREATE INDEX IF NOT EXISTS idx_log_lines_timestamp
            ON modem_log_lines(log_timestamp);
        """
    )


def insert_downstream(conn: sqlite3.Connection, timestamp: str, channels: list[dict]):
    """Insert a batch of downstream channel readings."""
    conn.executemany(
        """
        INSERT INTO downstream_channels
            (timestamp, channel_id, frequency_hz, power_dbmv, snr_db, modulation, locked, channel_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                timestamp,
                ch.get("channel_id"),
                ch.get("frequency_hz"),
                ch.get("power_dbmv"),
                ch.get("snr_db"),
                ch.get("modulation"),
                ch.get("locked"),
                ch.get("channel_type"),
            )
            for ch in channels
        ],
    )
    conn.commit()


def insert_upstream(conn: sqlite3.Connection, timestamp: str, channels: list[dict]):
    """Insert a batch of upstream channel readings."""
    conn.executemany(
        """
        INSERT INTO upstream_channels
            (timestamp, channel_id, frequency_hz, power_dbmv, modulation, locked, channel_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                timestamp,
                ch.get("channel_id"),
                ch.get("frequency_hz"),
                ch.get("power_dbmv"),
                ch.get("modulation"),
                ch.get("locked"),
                ch.get("channel_type"),
            )
            for ch in channels
        ],
    )
    conn.commit()


_LOG_LINE_RE = re.compile(
    r"^(\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+)\s+"
)


def _parse_log_line(line: str, fallback_timestamp: str) -> tuple[str, str | None, str | None, str]:
    """Parse a log line into (log_timestamp, level, category, message)."""
    m = _LOG_LINE_RE.match(line)
    if m:
        return m.group(1), m.group(2), m.group(3), line
    return fallback_timestamp, None, None, line


def insert_log_lines(conn: sqlite3.Connection, fetched_at: str, log_text: str) -> int:
    """Parse log_text into lines and insert only new ones.

    Returns the number of newly inserted lines.
    """
    lines = [line for line in log_text.splitlines() if line.strip()]
    if not lines:
        return 0

    rows = [_parse_log_line(line, fetched_at) for line in lines]
    cursor = conn.executemany(
        """
        INSERT OR IGNORE INTO modem_log_lines
            (log_timestamp, level, category, message, fetched_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [(ts, lvl, cat, msg, fetched_at) for ts, lvl, cat, msg in rows],
    )
    conn.commit()
    return cursor.rowcount


def now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()
