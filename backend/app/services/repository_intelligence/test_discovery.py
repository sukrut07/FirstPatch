"""
FirstPatch AI — Phase 2 Static Test Discovery & Verification Boundaries

Discovers testing frameworks, test files, and test cases using static analysis.
CRITICAL SECURITY BOUNDARY:
- Inspects configuration files and ASTs statically.
- Never executes arbitrary repository code, npm scripts, or build commands.
- Never labels static discovery as a passed test run.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from app.services.repository_intelligence.schemas import (
    CodeStructureReport,
    FileType,
    RepositorySnapshot,
    SymbolType,
    TestDiscoveryReport,
)
from app.services.repository_intelligence.snapshot import RepositorySnapshotService

logger = logging.getLogger(__name__)


class TestDiscoveryService:
    """
    Safely discovers test setups and files across Python and JS/TS repositories.
    Only uses static inspection. Never executes commands.
    """

    def __init__(self, snapshot_service: RepositorySnapshotService):
        self.snapshot_service = snapshot_service

    async def discover_tests(
        self,
        snapshot: RepositorySnapshot,
        code_report: Optional[CodeStructureReport] = None,
    ) -> TestDiscoveryReport:
        """
        Statically discover test configurations, directories, test files,
        and test cases without executing any code.
        """
        test_frameworks: list[str] = []
        test_directories: set[str] = set()
        test_config_files: list[str] = []
        discovered_test_files: list[str] = []
        discovered_test_cases: list[str] = []
        command_suggestions: list[str] = []

        # Step 1: Discover test files from snapshot file entries
        for file_entry in snapshot.files:
            path = file_entry.path
            if file_entry.file_type == FileType.TEST:
                discovered_test_files.append(path)
                # Find test directory
                parts = path.split("/")
                if len(parts) > 1:
                    test_directories.add(parts[0])

            # Test config files
            base = path.split("/")[-1].lower()
            if base in {
                "pytest.ini", ".pytest.ini", "tox.ini", "jest.config.js",
                "jest.config.ts", "vitest.config.js", "vitest.config.ts",
                ".mocharc.json", ".mocharc.js",
            }:
                test_config_files.append(path)

        # Step 2: Inspect Python configurations (pytest.ini, pyproject.toml)
        if any("pytest" in f.lower() for f in test_config_files) or any(f.endswith(".py") for f in discovered_test_files):
            test_frameworks.append("pytest")
            command_suggestions.append("pytest")

        # Check pyproject.toml for tool.pytest
        if "pyproject.toml" in snapshot.dependency_manifests:
            pyproject_content = await self.snapshot_service.get_file_content(snapshot, "pyproject.toml")
            if pyproject_content and "tool.pytest" in pyproject_content:
                if "pytest" not in test_frameworks:
                    test_frameworks.append("pytest")
                if "pytest" not in command_suggestions:
                    command_suggestions.append("pytest")

        # Step 3: Inspect Node / JS configurations (package.json)
        if "package.json" in snapshot.dependency_manifests:
            pkg_content = await self.snapshot_service.get_file_content(snapshot, "package.json")
            if pkg_content:
                try:
                    pkg_data = json.loads(pkg_content)
                    scripts = pkg_data.get("scripts", {})
                    if "test" in scripts:
                        test_script = scripts["test"]
                        if "jest" in test_script and "Jest" not in test_frameworks:
                            test_frameworks.append("Jest")
                        elif "vitest" in test_script and "Vitest" not in test_frameworks:
                            test_frameworks.append("Vitest")
                        elif "mocha" in test_script and "Mocha" not in test_frameworks:
                            test_frameworks.append("Mocha")
                        else:
                            test_frameworks.append(f"npm test ({test_script[:30]})")

                        command_suggestions.append("npm test")
                except json.JSONDecodeError:
                    pass

        # Step 4: Extract discovered test cases from code_report if available
        if code_report:
            for file_path, file_struct in code_report.files.items():
                for sym in file_struct.symbols:
                    if sym.symbol_type == SymbolType.TEST_CASE:
                        discovered_test_cases.append(f"{file_path}::{sym.name}")

        return TestDiscoveryReport(
            test_frameworks=sorted(list(set(test_frameworks))),
            test_directories=sorted(list(test_directories)),
            test_config_files=sorted(test_config_files),
            discovered_test_files=sorted(discovered_test_files)[:50],
            discovered_test_cases=discovered_test_cases[:50],
            execution_command_suggestions=command_suggestions,
            is_statically_discovered=True,
            execution_performed=False,
        )
