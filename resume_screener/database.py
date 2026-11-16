"""Save each screening run in SQLite so you can open it again later."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS screenings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_title TEXT NOT NULL,
    job_description TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screening_id INTEGER NOT NULL REFERENCES screenings(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    data TEXT NOT NULL
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def save_screening(db_path, job_title: str, job_text: str, results: list[dict]) -> int:
    with connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO screenings (job_title, job_description, created_at) VALUES (?, ?, ?)",
            (job_title, job_text, datetime.now().isoformat(timespec="seconds")),
        )
        screening_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO candidates (screening_id, rank, data) VALUES (?, ?, ?)",
            [(screening_id, i, json.dumps(r)) for i, r in enumerate(results, start=1)],
        )
    return screening_id


def get_screening(db_path, screening_id: int) -> dict | None:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM screenings WHERE id = ?", (screening_id,)).fetchone()
        if row is None:
            return None
        candidates = conn.execute(
            "SELECT data FROM candidates WHERE screening_id = ? ORDER BY rank", (screening_id,)
        ).fetchall()
    return {**dict(row), "results": [json.loads(c["data"]) for c in candidates]}


def list_screenings(db_path) -> list[dict]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """SELECT s.id, s.job_title, s.created_at, COUNT(c.id) AS total
               FROM screenings s LEFT JOIN candidates c ON c.screening_id = s.id
               GROUP BY s.id ORDER BY s.id DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def delete_screening(db_path, screening_id: int) -> None:
    with connect(db_path) as conn:
        conn.execute("DELETE FROM screenings WHERE id = ?", (screening_id,))
