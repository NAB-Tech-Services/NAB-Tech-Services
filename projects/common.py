"""Shared local database, validation, and CLI helpers."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


def nonempty(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('A nonempty string is required')
    return value.strip()


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp must include a UTC offset, e.g. +00:00')
    return parsed.astimezone(timezone.utc)


@contextmanager
def database(path, schema):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA foreign_keys = ON')
        db.executescript(schema)
        # Serializes read/check/write transactions across independent processes.
        db.execute('BEGIN IMMEDIATE')
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def rows(cursor):
    return [dict(row) for row in cursor.fetchall()]


def run(action):
    try:
        print(json.dumps(action(), indent=2))
    except (ValueError, OSError, sqlite3.Error) as error:
        raise SystemExit(f'Error: {error}') from error
