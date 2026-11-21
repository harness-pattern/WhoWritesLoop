"""SQLite schema and helpers for evolution2watch."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(
    os.environ.get(
        "E2W_DB",
        Path(__file__).resolve().parent.parent / "data" / "evolution2watch.sqlite",
    )
)

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS repos (
    repo_id      INTEGER PRIMARY KEY,
    slug         TEXT UNIQUE NOT NULL,
    category     TEXT NOT NULL,
    language     TEXT,
    archived_at  TEXT,
    pr_count     INTEGER DEFAULT 0,
    fetched_at   TEXT
);

CREATE TABLE IF NOT EXISTS prs (
    repo_id            INTEGER NOT NULL,
    number             INTEGER NOT NULL,
    node_id            TEXT,
    title              TEXT,
    body               TEXT,
    author_login       TEXT,
    author_type        TEXT,
    author_association TEXT,
    created_at         TEXT,
    closed_at          TEXT,
    merged_at          TEXT,
    state              TEXT,
    is_draft           INTEGER DEFAULT 0,
    base_ref           TEXT,
    head_ref           TEXT,
    comments_count     INTEGER DEFAULT 0,
    review_comments    INTEGER DEFAULT 0,
    commits_count      INTEGER DEFAULT 0,
    additions          INTEGER,
    deletions          INTEGER,
    changed_files      INTEGER,
    merge_commit_sha   TEXT,
    labels             TEXT,
    detail_status      INTEGER DEFAULT 0,   -- 0=pending 1=ok 2=error 3=skipped
    detail_error       TEXT,
    tier               TEXT,
    agent_family       TEXT,
    tier_evidence      TEXT,
    layers             TEXT,                -- JSON {layer: loc}
    layers_by_files    TEXT,                -- JSON {layer: n_files}
    layers_touched     INTEGER,
    touches_core       INTEGER,
    core_share         REAL,
    test_share         REAL,
    unclassified_loc   INTEGER DEFAULT 0,
    change_type        TEXT,
    abstraction_label  TEXT,
    judge_status       INTEGER DEFAULT 0,
    judge_json         TEXT,
    PRIMARY KEY (repo_id, number)
);

CREATE TABLE IF NOT EXISTS pr_files (
    repo_id       INTEGER NOT NULL,
    number        INTEGER NOT NULL,
    path          TEXT NOT NULL,
    previous_path TEXT,
    status        TEXT,
    additions     INTEGER,
    deletions     INTEGER,
    layer         TEXT,
    is_test       INTEGER DEFAULT 0,
    PRIMARY KEY (repo_id, number, path)
);

CREATE TABLE IF NOT EXISTS pr_commits (
    repo_id      INTEGER NOT NULL,
    number       INTEGER NOT NULL,
    sha          TEXT NOT NULL,
    author_login TEXT,
    author_name  TEXT,
    author_email TEXT,
    message      TEXT,
    committed_at TEXT,
    PRIMARY KEY (repo_id, number, sha)
);

CREATE TABLE IF NOT EXISTS pr_reviews (
    repo_id      INTEGER NOT NULL,
    number       INTEGER NOT NULL,
    review_id    TEXT,
    reviewer     TEXT,
    state        TEXT,
    submitted_at TEXT,
    PRIMARY KEY (repo_id, number, review_id)
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_prs_repo_created ON prs(repo_id, created_at);
CREATE INDEX IF NOT EXISTS idx_prs_detail ON prs(detail_status);
CREATE INDEX IF NOT EXISTS idx_files_pr ON pr_files(repo_id, number);
"""


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(path) if path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=60)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def get_meta(con: sqlite3.Connection, key: str, default=None):
    row = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(con: sqlite3.Connection, key: str, value):
    con.execute(
        "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
    con.commit()
