"""
FirstPatch AI — Setup Failure Doctor (Comprehensive Diagnostics Service)

Pattern-based, evidence-backed diagnostic analyzer for setup, build, and environment errors:
- Python dependency and module errors (ModuleNotFoundError, ImportError, version mismatch)
- Virtual environment mistakes (missing venv, python path mismatch)
- Node.js dependency and build errors (npm ERR!, ERESOLVE, Cannot find module, Vite/Next build failures)
- Missing environment variables (KeyError, missing .env keys)
- Configuration and port conflicts (EADDRINUSE, port bind errors)
- Filesystem and permission errors (EACCES, PermissionError)
- Test collection and import failures (pytest collection errors)

Safety guarantee:
- Zero shell command execution
- Untrusted user input treated purely as data
- Every suggested command is purely instructional
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from app.schemas import (
    DiagnosticFinding,
    DiagnosticRequest,
    DiagnosticResponse,
    RepositoryOverview,
)

logger = logging.getLogger(__name__)


class ComprehensiveDiagnosticsService:
    """
    Analyzes setup error logs against repository configuration without executing shell commands.
    """

    @classmethod
    def diagnose(
        cls,
        request: DiagnosticRequest,
        repo_overview: Optional[RepositoryOverview] = None,
    ) -> DiagnosticResponse:
        findings: list[DiagnosticFinding] = []

        err_text = request.error_description or ""
        cmd_text = request.command_output or ""
        snippets = " ".join(request.config_snippets)
        combined = f"{err_text}\n{cmd_text}\n{snippets}".lower()

        # 1. Virtual environment mistake (running global python or missing venv)
        if any(kw in combined for kw in ["externally-managed-environment", "virtualenv", "venv", "activate", "no module named pip"]):
            findings.append(
                DiagnosticFinding(
                    likely_cause="Python virtual environment is not active or environment is externally managed",
                    supporting_evidence=[
                        "Error mentions virtual environment or externally-managed-environment",
                        f"Repository config indicators: {', '.join(c for c in (repo_overview.config_files if repo_overview else []) if 'requirements' in c or 'pyproject' in c) or 'Python environment'}",
                    ],
                    safe_diagnostic_steps=[
                        "Check which python is running: which python (macOS/Linux) or where.exe python (Windows)",
                        "Create a virtual environment: python -m venv .venv",
                        "Activate it: source .venv/bin/activate (macOS/Linux) or .\\.venv\\Scripts\\Activate.ps1 (Windows)",
                    ],
                    suggested_fix="Create and activate a local virtual environment before installing packages",
                    verification_steps=[
                        "Verify python path points inside .venv: python -c \"import sys; print(sys.prefix)\"",
                        "Verify package installation succeeds inside the virtual environment",
                    ],
                    confidence="high",
                    is_verified=False,
                )
            )

        # 2. Python ModuleNotFoundError / ImportError
        m_py_mod = re.search(r"modulenotfounderror:\s*no module named ['\"]?([a-zA-Z0-9_\-\.]+)['\"]?", combined)
        if m_py_mod or any(kw in combined for kw in ["modulenotfounderror", "no module named", "importerror: cannot import name"]):
            missing_module = m_py_mod.group(1) if m_py_mod else "required package"
            config_context = []
            if repo_overview:
                for cfg in repo_overview.config_files:
                    if any(p in cfg.lower() for p in ["requirements", "pyproject.toml", "setup.py", "pipfile"]):
                        config_context.append(cfg)

            findings.append(
                DiagnosticFinding(
                    likely_cause=f"A required dependency or module '{missing_module}' is not installed",
                    supporting_evidence=[
                        f"Error output: ModuleNotFoundError for '{missing_module}'",
                        f"Repository manifest candidates: {', '.join(config_context) or 'No dependency files detected in top level'}",
                    ],
                    safe_diagnostic_steps=[
                        f"Run: pip install {missing_module} (or pip install -r requirements.txt)",
                        f"Check if package is installed: pip show {missing_module}",
                        "Check current pip list: pip list",
                        "Verify correct python interpreter is selected in IDE",
                    ],
                    suggested_fix=f"Install missing dependencies via: pip install -r requirements.txt (or pip install {missing_module})",
                    verification_steps=[
                        f"Verify module imports cleanly: python -c \"import {missing_module}\"",
                        "Re-run your previous command",
                    ],
                    confidence="high",
                    is_verified=False,
                )
            )

        # 3. Node.js dependency error (ERESOLVE, Cannot find module, npm ERR!)
        m_node_mod = re.search(r"cannot find module ['\"]?([a-zA-Z0-9_@\-\/\.]+)['\"]?", combined)
        if m_node_mod or any(kw in combined for kw in ["eresolve", "npm err!", "yarn error", "pnpm-lock.yaml", "node_modules"]):
            node_pkg = m_node_mod.group(1) if m_node_mod else "dependency"
            findings.append(
                DiagnosticFinding(
                    likely_cause=f"Node.js package resolution failed or package '{node_pkg}' is missing",
                    supporting_evidence=[
                        "Error log contains Node.js / npm package indicators",
                        f"Repository manifest: {'package.json' if repo_overview and 'package.json' in repo_overview.config_files else 'JavaScript package files'}",
                    ],
                    safe_diagnostic_steps=[
                        "Run: npm install (or npm install --legacy-peer-deps)",
                        "Check if node_modules exists in project root",
                        "Check your Node.js version: node --version",
                        "Review package.json scripts and dependencies",
                    ],
                    suggested_fix="Install dependencies cleanly: npm install (or npm install --legacy-peer-deps if peer conflict exists)",
                    verification_steps=[
                        "Check if node_modules folder is populated",
                        "Run: npm run build or npm test to verify dependencies",
                    ],
                    confidence="high",
                    is_verified=False,
                )
            )

        # 4. Missing Environment Variables
        raw_combined = f"{err_text}\n{cmd_text}\n{snippets}"
        m_env = re.search(r"keyerror:\s*['\"]?([a-zA-Z0-9_]+)['\"]?", raw_combined, re.IGNORECASE)
        if m_env or any(kw in combined for kw in ["environment variable", "missing required env", "env var"]):
            env_var = m_env.group(1) if m_env else "KEY"
            findings.append(
                DiagnosticFinding(
                    likely_cause=f"Required environment variable '{env_var}' is not set",
                    supporting_evidence=[
                        f"Log points to missing environment variable or KeyError on '{env_var}'",
                        "Application failed during configuration loading",
                    ],
                    safe_diagnostic_steps=[
                        "Check if a .env.example or template file exists in repository",
                        f"Check if {env_var} is defined in your current environment or .env file",
                    ],
                    suggested_fix=f"Copy .env.example to .env and configure '{env_var}' with appropriate development values",
                    verification_steps=[
                        f"Test that the variable is read properly without starting the full app",
                        "Start application to confirm configuration passes",
                    ],
                    confidence="high",
                    is_verified=False,
                )
            )

        # 5. Port conflict (EADDRINUSE / Address already in use)
        if any(kw in combined for kw in ["eaddrinuse", "address already in use", "port", "bind"]):
            findings.append(
                DiagnosticFinding(
                    likely_cause="The target network port is already allocated by another process",
                    supporting_evidence=["Log contains port bind or EADDRINUSE indicator"],
                    safe_diagnostic_steps=[
                        "On Linux/macOS: lsof -i :<port> or ss -tulpn | grep :<port>",
                        "On Windows PowerShell: Get-NetTCPConnection -LocalPort <port>",
                    ],
                    suggested_fix="Stop the conflicting process or change the port via environment variables or CLI flags",
                    verification_steps=["Restart the dev server and check for successful startup message"],
                    confidence="high",
                    is_verified=False,
                )
            )

        # 6. Pytest / Test Collection failure
        if any(kw in combined for kw in ["pytest: error", "collected 0 items", "error collecting", "conftest.py"]):
            findings.append(
                DiagnosticFinding(
                    likely_cause="Pytest test discovery or fixture initialization failed",
                    supporting_evidence=[
                        "Error occurs during test collection or conftest import phase",
                        f"Test locations detected in repo: {', '.join(t.path for t in repo_overview.test_locations) if repo_overview and repo_overview.test_locations else 'None'}",
                    ],
                    safe_diagnostic_steps=[
                        "Run pytest with collection only: pytest --collect-only -v",
                        "Verify PYTHONPATH or working directory is root of repository",
                    ],
                    suggested_fix="Ensure test dependencies are installed and run pytest from the workspace directory where config files reside",
                    verification_steps=["Run: pytest --collect-only and ensure test items are collected without errors"],
                    confidence="medium",
                    is_verified=False,
                )
            )

        # 7. Permission Denied (EACCES / PermissionError)
        if any(kw in combined for kw in ["permission denied", "eacces", "permissionerror", "access is denied"]):
            findings.append(
                DiagnosticFinding(
                    likely_cause="Filesystem permission restriction prevented reading or writing files",
                    supporting_evidence=["Log contains permission denied or EACCES indicators"],
                    safe_diagnostic_steps=[
                        "Check owner and permissions of target directory or file",
                        "Avoid running package managers with sudo unless strictly necessary",
                    ],
                    suggested_fix="Ensure current user owns the workspace files and has write permissions to temp directories",
                    verification_steps=["Run a simple write test or re-run command as the current user"],
                    confidence="medium",
                    is_verified=False,
                )
            )

        # Fallback if no specific pattern matched
        if not findings:
            findings.append(
                DiagnosticFinding(
                    likely_cause="Unrecognized setup error pattern",
                    supporting_evidence=["Error text provided in request"],
                    safe_diagnostic_steps=[
                        "Inspect the full traceback to identify the exact line and file raising the error",
                        "Search the project's GitHub issues for the error keywords",
                        "Review repository README.md and CONTRIBUTING.md for prerequisites",
                    ],
                    suggested_fix="Follow project setup instructions step-by-step in a fresh virtual environment",
                    verification_steps=["Re-run command with verbose/debug flags to get detailed error context"],
                    confidence="low",
                    is_verified=False,
                )
            )

        return DiagnosticResponse(
            owner=request.owner,
            repo=request.repo,
            findings=findings,
            disclaimer=(
                "These suggestions are deterministic diagnostic recommendations based on repository analysis. "
                "No commands were executed on your system. Always inspect commands before executing."
            ),
            ai_generated=False,
        )
