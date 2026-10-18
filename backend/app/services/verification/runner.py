"""
FirstPatch AI — Execution Drivers (Phase 3)

Provides isolated execution drivers for running allowlisted test suites.
Implements strict security boundaries:
- Network disabled by default (--network none)
- Non-root user (--user 1000:1000)
- Read-only root filesystem (--read-only)
- Read-only workspace mount (:ro)
- Memory (512MB), CPU (1.0 core), and PID limit (100) constraints
- Capability dropping (--cap-drop ALL, no-new-privileges)
- Bounded output capture (50KB max)
- Graceful cleanup and timeout enforcement

Includes:
- BaseExecutionDriver: abstract interface
- DockerExecutionDriver: production container driver with health probing
- MockExecutionDriver: deterministic driver for isolated testing
"""
from __future__ import annotations

import abc
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Optional
from uuid import UUID

from app.schemas.verification import (
    RuntimeProfile,
    VerificationInfrastructureHealth,
    VerificationRunRequest,
)

logger = logging.getLogger(__name__)

# Output ceiling in characters / bytes (50KB)
MAX_OUTPUT_BYTES = 50 * 1024

# Strictly allowlisted container images — NO USER CUSTOM IMAGES
ALLOWLISTED_IMAGES: dict[RuntimeProfile, str] = {
    RuntimeProfile.PYTHON_PYTEST: "python:3.11-slim",
    RuntimeProfile.NODE_JEST: "node:20-slim",
    RuntimeProfile.NODE_NPM_TEST: "node:20-slim",
}


class BaseExecutionDriver(abc.ABC):
    """Abstract driver interface for isolated test execution."""

    @abc.abstractmethod
    def check_availability(self) -> VerificationInfrastructureHealth:
        """Inspects whether the isolated execution runtime is safely available."""
        pass

    @abc.abstractmethod
    def prepare_workspace(
        self, owner: str, repo: str, commit_sha: str, source_snapshot_path: Optional[str] = None
    ) -> str:
        """
        Creates an isolated temporary workspace from a repository snapshot.
        Never modifies the original repository on the host.
        Returns the absolute path to the isolated disposable workspace.
        """
        pass

    @abc.abstractmethod
    def execute(
        self,
        run_id: UUID,
        request: VerificationRunRequest,
        workspace_path: str,
    ) -> tuple[int, str, str, bool]:
        """
        Executes allowlisted tests in the isolated environment.
        Returns: (exit_code, stdout, stderr, timed_out)
        """
        pass

    @abc.abstractmethod
    def cancel(self, run_id: UUID) -> bool:
        """Cancels an active execution job."""
        pass

    @abc.abstractmethod
    def cleanup(self, workspace_path: str, container_name: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """Cleans up the temporary workspace and any container remnants."""
        pass


class DockerExecutionDriver(BaseExecutionDriver):
    """
    Production Docker driver implementing hardened container isolation.
    """

    def __init__(self, sandbox_root: Optional[str] = None):
        self._sandbox_root = sandbox_root or os.path.join(tempfile.gettempdir(), "firstpatch_sandboxes")
        os.makedirs(self._sandbox_root, exist_ok=True)
        self._active_containers: dict[UUID, str] = {}

    def check_availability(self) -> VerificationInfrastructureHealth:
        """Checks if Docker is installed and the daemon is reachable."""
        docker_bin = shutil.which("docker")
        if not docker_bin:
            return VerificationInfrastructureHealth(
                runtime_available=False,
                runtime_name="docker",
                isolation_level="none",
                supported_profiles=list(ALLOWLISTED_IMAGES.keys()),
                message="Docker CLI is not installed on the host. Isolated verification is unavailable.",
                host_execution_permitted=False,
            )

        try:
            res = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                return VerificationInfrastructureHealth(
                    runtime_available=True,
                    runtime_name=f"docker-daemon ({res.stdout.strip()})",
                    isolation_level="hardened_linux_container",
                    supported_profiles=list(ALLOWLISTED_IMAGES.keys()),
                    message="Hardened container runtime available.",
                    host_execution_permitted=False,
                )
            else:
                return VerificationInfrastructureHealth(
                    runtime_available=False,
                    runtime_name="docker",
                    isolation_level="none",
                    supported_profiles=list(ALLOWLISTED_IMAGES.keys()),
                    message=f"Docker CLI found, but daemon is unreachable: {res.stderr.strip()[:100]}",
                    host_execution_permitted=False,
                )
        except Exception as exc:
            return VerificationInfrastructureHealth(
                runtime_available=False,
                runtime_name="docker",
                isolation_level="none",
                supported_profiles=list(ALLOWLISTED_IMAGES.keys()),
                message=f"Docker probe failed: {str(exc)}",
                host_execution_permitted=False,
            )

    def prepare_workspace(
        self, owner: str, repo: str, commit_sha: str, source_snapshot_path: Optional[str] = None
    ) -> str:
        """
        Creates an isolated disposable directory for this run.
        Copies repository snapshot files if source_snapshot_path is provided.
        """
        prefix = f"fp_{owner}_{repo}_{commit_sha[:7]}_"
        workspace = tempfile.mkdtemp(prefix=prefix, dir=self._sandbox_root)

        if source_snapshot_path and os.path.exists(source_snapshot_path):
            # Copy snapshot contents without touching original
            for item in os.listdir(source_snapshot_path):
                s = os.path.join(source_snapshot_path, item)
                d = os.path.join(workspace, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)

        return workspace

    def execute(
        self,
        run_id: UUID,
        request: VerificationRunRequest,
        workspace_path: str,
    ) -> tuple[int, str, str, bool]:
        """
        Spawns a sandboxed Docker container with strict constraints.
        """
        image = ALLOWLISTED_IMAGES.get(request.runtime)
        if not image:
            return -1, "", f"Unsupported runtime profile: {request.runtime}", False

        container_name = f"fp_run_{str(run_id).replace('-', '')[:16]}"
        self._active_containers[run_id] = container_name

        # Construct hardened container arguments
        cmd = [
            "docker", "run",
            "--name", container_name,
            "--rm",
            "--network", "none",
            "--user", "1000:1000",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--cpus", "1.0",
            "--memory", "512m",
            "--pids-limit", "100",
            "--security-opt", "no-new-privileges:true",
            "--cap-drop", "ALL",
            "-v", f"{os.path.abspath(workspace_path)}:/workspace:ro",
            "-w", "/workspace",
            image,
        ]

        # Template test command based on allowlisted profile
        if request.runtime == RuntimeProfile.PYTHON_PYTEST:
            cmd.extend(["pytest", "-q", "--tb=short", request.test_target])
        elif request.runtime == RuntimeProfile.NODE_JEST:
            cmd.extend(["npx", "--no-install", "jest", request.test_target])
        elif request.runtime == RuntimeProfile.NODE_NPM_TEST:
            cmd.extend(["npm", "test", "--", request.test_target])

        timed_out = False
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
            )
            exit_code = proc.returncode
            stdout = self._bound_output(proc.stdout)
            stderr = self._bound_output(proc.stderr)
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = -1
            stdout = self._bound_output(exc.stdout or "")
            stderr = self._bound_output(f"Execution timed out after {request.timeout_seconds} seconds.")
            # Force kill running container
            self._kill_container(container_name)
        except Exception as exc:
            exit_code = -1
            stdout = ""
            stderr = self._bound_output(f"Failed to execute container: {str(exc)}")
        finally:
            self._active_containers.pop(run_id, None)

        return exit_code, stdout, stderr, timed_out

    def cancel(self, run_id: UUID) -> bool:
        """Cancels a container run by ID."""
        container_name = self._active_containers.get(run_id)
        if not container_name:
            return False
        return self._kill_container(container_name)

    def cleanup(self, workspace_path: str, container_name: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """Deletes disposable workspace and ensures container termination."""
        error = None
        if container_name:
            self._kill_container(container_name)

        if os.path.exists(workspace_path):
            try:
                shutil.rmtree(workspace_path, ignore_errors=True)
            except Exception as exc:
                error = f"Failed to delete workspace: {str(exc)}"
                logger.error("Cleanup error for workspace %s: %s", workspace_path, exc)
                return False, error

        return True, None

    def _kill_container(self, container_name: str) -> bool:
        try:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    @staticmethod
    def _bound_output(text: str) -> str:
        if len(text) > MAX_OUTPUT_BYTES:
            truncated_marker = "\n[... FIRSTPATCH OUTPUT TRUNCATED AT 50KB MAXIMUM LIMIT ...]\n"
            return text[:MAX_OUTPUT_BYTES - len(truncated_marker)] + truncated_marker
        return text


class MockExecutionDriver(BaseExecutionDriver):
    """
    Deterministic mock driver for unit and regression testing.
    Validates state machine transitions, timeout enforcement, output bounding,
    and cleanup behavior without requiring Docker.
    """

    def __init__(
        self,
        is_available: bool = True,
        default_scenario: str = "pass",
    ):
        self.is_available = is_available
        self.scenario = default_scenario
        self.cancelled_runs: set[UUID] = set()
        self.cleaned_workspaces: list[str] = []
        self.executed_requests: list[VerificationRunRequest] = []

    def check_availability(self) -> VerificationInfrastructureHealth:
        if not self.is_available:
            return VerificationInfrastructureHealth(
                runtime_available=False,
                runtime_name="mock-driver",
                isolation_level="none",
                supported_profiles=list(ALLOWLISTED_IMAGES.keys()),
                message="Execution runtime is unavailable.",
                host_execution_permitted=False,
            )
        return VerificationInfrastructureHealth(
            runtime_available=True,
            runtime_name="mock-sandbox",
            isolation_level="simulated_isolated_sandbox",
            supported_profiles=list(ALLOWLISTED_IMAGES.keys()),
            message="Mock isolated execution driver ready.",
            host_execution_permitted=False,
        )

    def prepare_workspace(
        self, owner: str, repo: str, commit_sha: str, source_snapshot_path: Optional[str] = None
    ) -> str:
        return f"/mock/sandboxes/{owner}_{repo}_{commit_sha[:7]}"

    def execute(
        self,
        run_id: UUID,
        request: VerificationRunRequest,
        workspace_path: str,
    ) -> tuple[int, str, str, bool]:
        self.executed_requests.append(request)

        if self.scenario == "pass":
            stdout = (
                "============================= test session starts ==============================\n"
                "rootdir: /workspace\n"
                "collected 3 items\n\n"
                "tests/test_mod.py ...                                                    [100%]\n\n"
                "============================== 3 passed in 0.14s ==============================="
            )
            return 0, stdout, "", False

        elif self.scenario == "fail":
            stdout = (
                "============================= test session starts ==============================\n"
                "collected 3 items\n\n"
                "tests/test_mod.py ..F                                                    [100%]\n\n"
                "=================================== FAILURES ===================================\n"
                "__________________________________ test_fail ___________________________________\n"
                "    def test_fail():\n"
                ">       assert 1 == 2\n"
                "E       assert 1 == 2\n"
                "=========================== 1 failed, 2 passed in 0.20s ========================="
            )
            return 1, stdout, "", False

        elif self.scenario == "collection_error":
            stdout = (
                "============================= test session starts ==============================\n"
                "collected 0 items / 1 error\n\n"
                "==================================== ERRORS ====================================\n"
                "___________________ ERROR collecting tests/test_invalid.py _____________________\n"
                "ModuleNotFoundError: No module named 'nonexistent_dependency'\n"
                "============================== 1 error in 0.05s ================================="
            )
            return 2, stdout, "ModuleNotFoundError: No module named 'nonexistent_dependency'", False

        elif self.scenario == "timeout":
            return -1, "", f"Execution timed out after {request.timeout_seconds} seconds.", True

        elif self.scenario == "oversized_output":
            # Generate 120KB of output
            huge_stdout = "All tests running...\n" + ("x" * 120_000) + "\n============================== 1 passed in 0.10s ==============================="
            return 0, huge_stdout, "", False

        return 0, "=== 1 passed in 0.01s ===", "", False

    def cancel(self, run_id: UUID) -> bool:
        self.cancelled_runs.add(run_id)
        return True

    def cleanup(self, workspace_path: str, container_name: Optional[str] = None) -> tuple[bool, Optional[str]]:
        self.cleaned_workspaces.append(workspace_path)
        return True, None
