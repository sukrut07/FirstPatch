import subprocess
import shlex
import time
import uuid
import os
from typing import Dict, Any, List, Optional
from backend.app.database import get_db, get_iso_now

class VerificationService:
    def __init__(self):
        pass

    def discover_tests(self, file_paths: List[str]) -> List[Dict[str, str]]:
        """Detects available test commands based on repository files."""
        discovered = []
        lower_files = [f.lower() for f in file_paths]

        # Python testing
        has_pytest = any("pytest" in f or "test_" in f or "_test.py" in f for f in lower_files)
        has_pyproject = any("pyproject.toml" in f or "setup.py" in f for f in lower_files)

        if has_pytest:
            discovered.append({
                "framework": "pytest",
                "command": "pytest",
                "args": "-v tests/",
                "description": "Standard pytest runner for unit and regression tests"
            })
            discovered.append({
                "framework": "python unittest",
                "command": "python -m unittest",
                "args": "discover -s tests",
                "description": "Built-in Python unittest discovery"
            })

        # Node / JS testing
        if any("package.json" in f for f in lower_files):
            discovered.append({
                "framework": "npm",
                "command": "npm test",
                "args": "",
                "description": "NPM package test script defined in package.json"
            })

        # Rust testing
        if any("cargo.toml" in f for f in lower_files):
            discovered.append({
                "framework": "cargo",
                "command": "cargo test",
                "args": "",
                "description": "Rust built-in test suite"
            })

        # Go testing
        if any(f.endswith(".go") for f in lower_files):
            discovered.append({
                "framework": "go test",
                "command": "go test",
                "args": "./...",
                "description": "Go package test suite"
            })

        if not discovered:
            discovered.append({
                "framework": "generic",
                "command": "echo 'No automated test runner detected in file manifest.'",
                "args": "",
                "description": "Manual verification required"
            })

        return discovered

    def run_safe_command(
        self,
        command_str: str,
        workspace_id: Optional[str] = None,
        repository_id: str = "local",
        cwd: Optional[str] = None,
        timeout_seconds: int = 40
    ) -> Dict[str, Any]:
        """Safely executes a verification command and logs actual exit code, stdout, and stderr."""
        # Sanitize command string to avoid chained destructive commands
        blocked_tokens = ["rm -rf /", ":(){ :|:& };:", "dd if=", "mkfs", "chmod -R 777 /"]
        for b in blocked_tokens:
            if b in command_str:
                return {
                    "id": str(uuid.uuid4()),
                    "status": "BLOCKED",
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Security restriction: command contains prohibited pattern '{b}'.",
                    "duration_ms": 0
                }

        # Build clean environment without sensitive host secrets
        safe_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin"),
            "HOME": os.environ.get("HOME", "/tmp"),
            "LANG": "en_US.UTF-8",
            "PYTHONUNBUFFERED": "1"
        }
        if os.name == "nt":
            safe_env["SystemRoot"] = os.environ.get("SystemRoot", r"C:\Windows")
            safe_env["COMSPEC"] = os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")
            safe_env["PATHEXT"] = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD")

        start_time = time.time()
        run_id = str(uuid.uuid4())

        try:
            # Execute with shlex split for safety
            args = shlex.split(command_str)
            if os.name == "nt":
                import sys
                if args and args[0].lower() in ("python3", "python3.exe"):
                    args[0] = sys.executable
                if args and args[0].lower() in ("echo", "dir", "type", "cls", "copy", "del", "mkdir", "rmdir"):
                    args = ["cmd.exe", "/c"] + args

            process = subprocess.run(
                args,
                cwd=cwd or None,
                env=safe_env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            duration_ms = int((time.time() - start_time) * 1000)
            status = "PASSED" if process.returncode == 0 else "FAILED"
            stdout = process.stdout[:15000]
            stderr = process.stderr[:15000]
            exit_code = process.returncode

        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            status = "TIMED_OUT"
            stdout = ""
            stderr = f"Execution timed out after {timeout_seconds} seconds."
            exit_code = -124

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            status = "FAILED"
            stdout = ""
            stderr = f"Execution error: {str(e)}"
            exit_code = -1

        # Persist to database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO verification_runs (
                id, workspace_id, repository_id, command, working_directory,
                exit_code, stdout, stderr, status, duration_ms, run_by_user,
                sandbox_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, workspace_id, repository_id, command_str, cwd or "workspace",
                exit_code, stdout, stderr, status, duration_ms, 1,
                "restricted_process", get_iso_now()
            ))

        return {
            "id": run_id,
            "command": command_str,
            "status": status,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": duration_ms
        }

verification_service = VerificationService()
