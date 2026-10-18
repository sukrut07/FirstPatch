import sqlite3
import os
import json
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Generator, Any, Optional
from backend.app.config import settings

def get_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db() -> None:
    os.makedirs(os.path.dirname(settings.DATABASE_PATH), exist_ok=True)
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Repositories table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS repositories (
            id TEXT PRIMARY KEY,
            owner TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            default_branch TEXT DEFAULT 'main',
            stars INTEGER DEFAULT 0,
            forks INTEGER DEFAULT 0,
            open_issues_count INTEGER DEFAULT 0,
            language TEXT,
            topics TEXT,
            license_name TEXT,
            html_url TEXT,
            default_commit_sha TEXT,
            status TEXT DEFAULT 'ready',
            analysis_summary TEXT,
            analysis_limitations TEXT,
            ai_analysis TEXT,
            ai_analysis_model TEXT,
            last_analyzed_at TEXT,
            created_at TEXT NOT NULL
        )
        """)
        
        try:
            cursor.execute("ALTER TABLE repositories ADD COLUMN ai_analysis TEXT")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE repositories ADD COLUMN ai_analysis_model TEXT")
        except Exception:
            pass
        
        # 2. Repository Snapshots
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS repository_snapshots (
            id TEXT PRIMARY KEY,
            repository_id TEXT NOT NULL,
            commit_sha TEXT NOT NULL,
            file_count INTEGER DEFAULT 0,
            total_symbols INTEGER DEFAULT 0,
            is_current INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
        )
        """)
        
        # 3. Repository Files
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS repository_files (
            id TEXT PRIMARY KEY,
            repository_id TEXT NOT NULL,
            commit_sha TEXT,
            path TEXT NOT NULL,
            file_type TEXT,
            size_bytes INTEGER DEFAULT 0,
            is_test INTEGER DEFAULT 0,
            is_config INTEGER DEFAULT 0,
            is_entrypoint INTEGER DEFAULT 0,
            content TEXT,
            parsed_metadata TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
        )
        """)
        
        # 4. Code Chunks
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS code_chunks (
            id TEXT PRIMARY KEY,
            repository_id TEXT NOT NULL,
            commit_sha TEXT,
            file_path TEXT NOT NULL,
            symbol_name TEXT,
            chunk_type TEXT,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            content TEXT NOT NULL,
            content_hash TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
        )
        """)
        
        # Check if FTS5 table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='code_chunks_fts'")
        if not cursor.fetchone():
            try:
                cursor.execute("""
                CREATE VIRTUAL TABLE code_chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    repository_id UNINDEXED,
                    file_path,
                    symbol_name,
                    content
                )
                """)
            except Exception as e:
                # Fallback if FTS5 not compiled in
                print(f"[Warning] FTS5 table creation error: {e}")

        # 5. Evidence Records
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidence_records (
            id TEXT PRIMARY KEY,
            repository_id TEXT NOT NULL,
            commit_sha TEXT,
            file_path TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            symbol_name TEXT,
            chunk_type TEXT,
            content_hash TEXT,
            source_url TEXT NOT NULL,
            snippet TEXT,
            claim TEXT,
            status TEXT DEFAULT 'verified',
            created_at TEXT NOT NULL,
            FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
        )
        """)
        
        # 6. Issues Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id TEXT PRIMARY KEY,
            repository_id TEXT NOT NULL,
            github_issue_id INTEGER,
            number INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT,
            state TEXT DEFAULT 'open',
            author TEXT,
            comments_count INTEGER DEFAULT 0,
            labels TEXT,
            html_url TEXT,
            is_pull_request INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
        )
        """)
        
        # 7. Issue Recommendations
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS issue_recommendations (
            id TEXT PRIMARY KEY,
            issue_id TEXT NOT NULL,
            repository_id TEXT NOT NULL,
            fit_score REAL DEFAULT 0.0,
            technical_fit_score REAL DEFAULT 0.0,
            interest_fit_score REAL DEFAULT 0.0,
            evidence_confidence_score REAL DEFAULT 0.0,
            viability_score REAL DEFAULT 0.0,
            learning_value_score REAL DEFAULT 0.0,
            skill_match TEXT,
            estimated_complexity TEXT,
            estimated_effort TEXT,
            reasons TEXT,
            potential_blockers TEXT,
            relevant_files TEXT,
            prerequisite_skills TEXT,
            confidence TEXT,
            missing_info TEXT,
            why_this_project TEXT,
            why_this_issue TEXT,
            what_to_verify_first TEXT,
            grounded_investigation TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE
        )
        """)
        
        # Idempotently add any new columns to existing issue_recommendations table
        cursor.execute("PRAGMA table_info(issue_recommendations)")
        rec_cols = {row["name"] for row in cursor.fetchall()}
        migration_cols = [
            ("technical_fit_score", "REAL DEFAULT 0.0"),
            ("interest_fit_score", "REAL DEFAULT 0.0"),
            ("evidence_confidence_score", "REAL DEFAULT 0.0"),
            ("viability_score", "REAL DEFAULT 0.0"),
            ("learning_value_score", "REAL DEFAULT 0.0"),
            ("why_this_project", "TEXT"),
            ("why_this_issue", "TEXT"),
            ("what_to_verify_first", "TEXT"),
            ("grounded_investigation", "TEXT")
        ]
        for col_name, col_def in migration_cols:
            if col_name not in rec_cols:
                try:
                    cursor.execute(f"ALTER TABLE issue_recommendations ADD COLUMN {col_name} {col_def}")
                except Exception:
                    pass

        # 7b. Hypothesis Logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hypothesis_logs (
            id TEXT PRIMARY KEY,
            issue_id TEXT NOT NULL,
            workspace_id TEXT,
            hypothesis TEXT NOT NULL,
            supporting_evidence TEXT,
            contradicting_evidence TEXT,
            verification_method TEXT,
            status TEXT DEFAULT 'untested',
            remaining_uncertainty TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE
        )
        """)

        # 7c. Issue Triages
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS issue_triages (
            id TEXT PRIMARY KEY,
            issue_id TEXT NOT NULL UNIQUE,
            user_summary TEXT,
            expected_behavior TEXT,
            actual_behavior TEXT,
            suspected_code_path TEXT,
            reproduction_notes TEXT,
            decision TEXT DEFAULT 'undecided',
            decision_rationale TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE
        )
        """)

        # 7d. Maintainer Communication Drafts
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintainer_drafts (
            id TEXT PRIMARY KEY,
            issue_id TEXT NOT NULL,
            draft_type TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE
        )
        """)
        
        # 8. Saved Repositories and Issues
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_repositories (
            repository_id TEXT PRIMARY KEY,
            saved_at TEXT NOT NULL,
            FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_issues (
            issue_id TEXT PRIMARY KEY,
            saved_at TEXT NOT NULL,
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE
        )
        """)
        
        # 9. Conversations and Messages
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            repository_id TEXT NOT NULL,
            mode TEXT DEFAULT 'learn',
            title TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            citations TEXT,
            evidence_ids TEXT,
            mode TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
        """)
        
        # 10. Contribution Workspaces
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS contribution_workspaces (
            id TEXT PRIMARY KEY,
            repository_id TEXT NOT NULL,
            issue_id TEXT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            definition_of_done TEXT,
            draft_pr_title TEXT,
            draft_pr_body TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS contribution_steps (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            step_index INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            expected_result TEXT,
            verification_method TEXT,
            user_notes TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (workspace_id) REFERENCES contribution_workspaces(id) ON DELETE CASCADE
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS contribution_events (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            repository_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            summary TEXT NOT NULL,
            details TEXT,
            evidence_refs TEXT,
            verification_status TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (workspace_id) REFERENCES contribution_workspaces(id) ON DELETE CASCADE
        )
        """)
        
        # 11. Verification Runs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_runs (
            id TEXT PRIMARY KEY,
            workspace_id TEXT,
            repository_id TEXT NOT NULL,
            command TEXT NOT NULL,
            working_directory TEXT,
            exit_code INTEGER,
            stdout TEXT,
            stderr TEXT,
            status TEXT DEFAULT 'NOT_RUN',
            duration_ms INTEGER DEFAULT 0,
            run_by_user INTEGER DEFAULT 1,
            sandbox_type TEXT DEFAULT 'restricted_process',
            created_at TEXT NOT NULL
        )
        """)
        
        # 12. Review Findings
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_findings (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            severity TEXT DEFAULT 'warning',
            confidence TEXT DEFAULT 'high',
            file_path TEXT,
            line_number INTEGER,
            title TEXT NOT NULL,
            explanation TEXT NOT NULL,
            suggested_fix TEXT,
            is_verified INTEGER DEFAULT 0,
            dismissed INTEGER DEFAULT 0,
            dismiss_reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (workspace_id) REFERENCES contribution_workspaces(id) ON DELETE CASCADE
        )
        """)
        
        # 13. Learning Profile & Progress
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_profiles (
            id TEXT PRIMARY KEY,
            preferred_languages TEXT,
            skill_level TEXT DEFAULT 'Beginner',
            interests TEXT,
            learning_goals TEXT,
            completed_drills_count INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL
        )
        """)
        
        # 14. Model Configs & User Preferences
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_configs (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        
        # Default learning profile if empty
        cursor.execute("SELECT id FROM learning_profiles WHERE id='default'")
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO learning_profiles (id, preferred_languages, skill_level, interests, learning_goals, completed_drills_count, updated_at)
            VALUES ('default', '["Python", "JavaScript", "TypeScript"]', 'Beginner', '["Web Development", "AI/ML", "DevTools"]', 'Make my first verified open-source contribution', 0, ?)
            """, (get_iso_now(),))

print("Database initialized successfully.")
