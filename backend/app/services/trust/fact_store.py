"""Fact Store for Proof-Carrying Contributions.

Stores immutable repository snapshots, files, symbols, imports, policy facts,
issue facts, and verification execution records bound to specific commit SHAs.
Uses SQLite with parameterized queries, strict path normalization, and idempotent insertion.
"""

import hashlib
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional
import urllib.parse

RESERVED_DEVICE_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def normalize_repo_path(raw_path: str) -> str:
    """Normalize a repository path and strictly reject unsafe or absolute paths."""
    if not raw_path or not isinstance(raw_path, str):
        raise ValueError("Repository path must be a non-empty string.")
    
    # Reject raw null bytes
    if "\0" in raw_path:
        raise ValueError(f"Null byte detected in path: {raw_path!r}")

    # Check for URL-encoded null bytes or control sequences
    decoded = urllib.parse.unquote(raw_path)
    if "\0" in decoded:
        raise ValueError(f"Decoded null byte detected in path: {raw_path!r}")

    # Reject non-printable control characters
    for ch in decoded:
        if ord(ch) < 32 or ord(ch) == 127:
            raise ValueError(f"Control character detected in path: {raw_path!r}")
        
    # Standardize backslashes on the decoded path
    p = decoded.replace("\\", "/").strip()
    
    # Reject drive-letters (e.g. C:, D:)
    if re.match(r"^[a-zA-Z]:", p):
        raise ValueError(f"Absolute drive-letter path is forbidden: {raw_path}")
        
    # Reject leading slashes or UNC paths
    if p.startswith("/"):
        raise ValueError(f"Absolute path is forbidden: {raw_path}")
        
    # Strip leading ./
    while p.startswith("./"):
        p = p[2:]
        
    # Check directory traversal segments
    parts = p.split("/")
    if any(segment == ".." for segment in parts):
        raise ValueError(f"Path traversal ('..') is strictly forbidden: {raw_path}")

    # Check reserved device names and invalid trailing dots/spaces
    for seg in parts:
        base_name = seg.split(".")[0].upper()
        if base_name in RESERVED_DEVICE_NAMES:
            raise ValueError(f"Reserved device name is forbidden: {raw_path}")
        if seg.endswith(".") or seg.endswith(" "):
            raise ValueError(f"Path segment has forbidden trailing dot or space: {raw_path}")
        
    # Remove empty or current directory dot segments
    clean_parts = [seg for seg in parts if seg and seg != "."]
    if not clean_parts:
        raise ValueError(f"Path resolves to empty root: {raw_path}")
        
    return "/".join(clean_parts)



class FactStore:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self.conn:
            self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
                repo_id TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (repo_id, commit_sha)
            );

            CREATE TABLE IF NOT EXISTS files (
                repo_id TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                path TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                PRIMARY KEY (repo_id, commit_sha, path)
            );

            CREATE TABLE IF NOT EXISTS symbols (
                repo_id TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                path TEXT NOT NULL,
                symbol_name TEXT NOT NULL,
                symbol_type TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                confidence TEXT DEFAULT 'high',
                PRIMARY KEY (repo_id, commit_sha, path, symbol_name)
            );

            CREATE TABLE IF NOT EXISTS imports (
                repo_id TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                source_path TEXT NOT NULL,
                imported_module TEXT NOT NULL,
                imported_name TEXT,
                confidence TEXT DEFAULT 'high',
                PRIMARY KEY (repo_id, commit_sha, source_path, imported_module, imported_name)
            );

            CREATE TABLE IF NOT EXISTS test_mappings (
                repo_id TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                test_path TEXT NOT NULL,
                target_module TEXT NOT NULL,
                confidence TEXT DEFAULT 'high',
                PRIMARY KEY (repo_id, commit_sha, test_path, target_module)
            );

            CREATE TABLE IF NOT EXISTS policy_facts (
                repo_id TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                policy_type TEXT NOT NULL,
                value TEXT NOT NULL,
                source_file TEXT,
                line_range TEXT,
                raw_text TEXT,
                PRIMARY KEY (repo_id, commit_sha, policy_type)
            );

            CREATE TABLE IF NOT EXISTS issue_facts (
                repo_id TEXT NOT NULL,
                issue_number INTEGER NOT NULL,
                state TEXT NOT NULL,
                is_assigned INTEGER NOT NULL,
                assignees TEXT,
                has_open_pr INTEGER NOT NULL,
                claim_comment TEXT,
                timestamp TEXT NOT NULL,
                PRIMARY KEY (repo_id, issue_number)
            );

            CREATE TABLE IF NOT EXISTS verification_runs (
                run_id TEXT PRIMARY KEY,
                repo_id TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                driver TEXT NOT NULL,
                status TEXT NOT NULL,
                exit_code INTEGER,
                output_hash TEXT NOT NULL,
                passed_tests INTEGER DEFAULT 0,
                failed_tests INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL
            );
            """)

    def register_snapshot(self, repo_id: str, commit_sha: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO snapshots (repo_id, commit_sha) VALUES (?, ?)",
                (repo_id, commit_sha),
            )

    def store_file(self, repo_id: str, commit_sha: str, path: str, content: str) -> str:
        clean_path = normalize_repo_path(path)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self.register_snapshot(repo_id, commit_sha)
        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO files (repo_id, commit_sha, path, content, content_hash)
                   VALUES (?, ?, ?, ?, ?)""",
                (repo_id, commit_sha, clean_path, content, content_hash),
            )
        return clean_path

    def get_file(self, repo_id: str, commit_sha: str, path: str) -> Optional[Dict[str, Any]]:
        clean_path = normalize_repo_path(path)
        cursor = self.conn.execute(
            "SELECT path, content, content_hash FROM files WHERE repo_id = ? AND commit_sha = ? AND path = ?",
            (repo_id, commit_sha, clean_path),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def store_symbol(
        self,
        repo_id: str,
        commit_sha: str,
        path: str,
        symbol_name: str,
        symbol_type: str,
        start_line: int,
        end_line: int,
        confidence: str = "high",
    ) -> None:
        clean_path = normalize_repo_path(path)
        self.register_snapshot(repo_id, commit_sha)
        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO symbols
                   (repo_id, commit_sha, path, symbol_name, symbol_type, start_line, end_line, confidence)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (repo_id, commit_sha, clean_path, symbol_name, symbol_type, start_line, end_line, confidence),
            )

    def get_symbol(self, repo_id: str, commit_sha: str, path: str, symbol_name: str) -> Optional[Dict[str, Any]]:
        clean_path = normalize_repo_path(path)
        cursor = self.conn.execute(
            """SELECT path, symbol_name, symbol_type, start_line, end_line, confidence
               FROM symbols WHERE repo_id = ? AND commit_sha = ? AND path = ? AND symbol_name = ?""",
            (repo_id, commit_sha, clean_path, symbol_name),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def store_import(
        self,
        repo_id: str,
        commit_sha: str,
        source_path: str,
        imported_module: str,
        imported_name: Optional[str] = None,
        confidence: str = "high",
    ) -> None:
        clean_path = normalize_repo_path(source_path)
        self.register_snapshot(repo_id, commit_sha)
        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO imports
                   (repo_id, commit_sha, source_path, imported_module, imported_name, confidence)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (repo_id, commit_sha, clean_path, imported_module, imported_name or "", confidence),
            )

    def get_imports(self, repo_id: str, commit_sha: str, source_path: str) -> List[Dict[str, Any]]:
        clean_path = normalize_repo_path(source_path)
        cursor = self.conn.execute(
            """SELECT source_path, imported_module, imported_name, confidence
               FROM imports WHERE repo_id = ? AND commit_sha = ? AND source_path = ?""",
            (repo_id, commit_sha, clean_path),
        )
        return [dict(r) for r in cursor.fetchall()]

    def store_policy_fact(
        self,
        repo_id: str,
        commit_sha: str,
        policy_type: str,
        value: str,
        source_file: Optional[str] = None,
        line_range: Optional[str] = None,
        raw_text: Optional[str] = None,
    ) -> None:
        self.register_snapshot(repo_id, commit_sha)
        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO policy_facts
                   (repo_id, commit_sha, policy_type, value, source_file, line_range, raw_text)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (repo_id, commit_sha, policy_type, value, source_file, line_range, raw_text),
            )

    def get_policy_fact(self, repo_id: str, commit_sha: str, policy_type: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute(
            """SELECT policy_type, value, source_file, line_range, raw_text
               FROM policy_facts WHERE repo_id = ? AND commit_sha = ? AND policy_type = ?""",
            (repo_id, commit_sha, policy_type),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def store_issue_fact(
        self,
        repo_id: str,
        issue_number: int,
        state: str,
        is_assigned: bool,
        assignees: List[str],
        has_open_pr: bool,
        claim_comment: Optional[str],
        timestamp: str,
    ) -> None:
        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO issue_facts
                   (repo_id, issue_number, state, is_assigned, assignees, has_open_pr, claim_comment, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    repo_id,
                    issue_number,
                    state,
                    1 if is_assigned else 0,
                    ",".join(assignees),
                    1 if has_open_pr else 0,
                    claim_comment,
                    timestamp,
                ),
            )

    def get_issue_fact(self, repo_id: str, issue_number: int) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute(
            """SELECT repo_id, issue_number, state, is_assigned, assignees, has_open_pr, claim_comment, timestamp
               FROM issue_facts WHERE repo_id = ? AND issue_number = ?""",
            (repo_id, issue_number),
        )
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["is_assigned"] = bool(d["is_assigned"])
        d["has_open_pr"] = bool(d["has_open_pr"])
        d["assignees"] = [a for a in d["assignees"].split(",") if a] if d["assignees"] else []
        return d

    def store_verification_run(
        self,
        run_id: str,
        repo_id: str,
        commit_sha: str,
        driver: str,
        status: str,
        exit_code: Optional[int],
        output_hash: str,
        passed_tests: int,
        failed_tests: int,
        timestamp: str,
    ) -> None:
        self.register_snapshot(repo_id, commit_sha)
        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO verification_runs
                   (run_id, repo_id, commit_sha, driver, status, exit_code, output_hash, passed_tests, failed_tests, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    repo_id,
                    commit_sha,
                    driver,
                    status,
                    exit_code,
                    output_hash,
                    passed_tests,
                    failed_tests,
                    timestamp,
                ),
            )

    def get_verification_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute(
            """SELECT run_id, repo_id, commit_sha, driver, status, exit_code, output_hash, passed_tests, failed_tests, timestamp
               FROM verification_runs WHERE run_id = ?""",
            (run_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
