# FirstPatch AI — Phase 3: Isolated Test Execution & Contribution Verification

## 1. Overview & Objective

Phase 3 implements an isolated, reproducible test verification service for FirstPatch AI. It allows contributors and mentors to execute allowlisted repository test suites safely and receive authentic, structured test records bound to exact repository snapshot commit SHAs.

Core tenet: **Zero unverified claims.**
- Tests discovered in repository metadata are never reported as "passed".
- Tests are marked `PASSED` only when executed inside a disposable isolated container runtime, the exit code is 0, and no failures or collection crashes occurred.
- If the host environment lacks container infrastructure (e.g. Docker daemon is unavailable), the system explicitly reports status `UNAVAILABLE` rather than falling back to dangerous host execution.

---

## 2. Execution Architecture

```
                                  [ Contributor Client / UI ]
                                               │
                                               │ POST /api/verification/run
                                               ▼
                                 [ FastAPI Verification Router ]
                                               │
                                 ┌─────────────┴─────────────┐
                                 │ VerificationService       │
                                 │ (Concurrency Semaphore 3) │
                                 └─────────────┬─────────────┘
                                               │
                 ┌─────────────────────────────┼─────────────────────────────┐
                 │                             │                             │
                 ▼                             ▼                             ▼
       [ Infrastructure Probe ]     [ Workspace Isolation ]       [ Strict Container Driver ]
       - Checks Docker / daemon     - Disposable temp directory    - Non-root (1000:1000)
       - Prohibits host fallback    - Cloned from snapshot         - Read-only root & source
       - Returns UNAVAILABLE if     - Host original untouched      - --network none
         no safe container runtime  - Auto-cleanup guaranteed      - 512MB RAM, 1.0 CPU, 100 PIDs
                                                                   - Bounded output (50KB max)
                                                                   - Strict image allowlist
                                                                   - Pytest / Jest templates
                                               │
                                               ▼
                                  [ Test Output Parsers ]
                                  - PytestOutputParser
                                  - JestNpmOutputParser
                                  - Accurate counts & summaries
                                               │
                                               ▼
                               [ VerificationRecordStore ]
                                  - Indexed by run_id
                                  - Indexed by (owner, repo, commit_sha)
                                  - Indexed by session_id
                                               │
                                               ▼
                              [ Reality Checker Adapter ]
                                  - Binds plan claims to commit SHA
                                  - Rejects stale commit records
                                  - Neutralizes unverified claims
```

---

## 3. Security Boundaries & Hardening Controls

| Security Boundary | Control Implementation |
|---|---|
| **No Host Execution** | Untrusted repository code is NEVER executed on the host OS under any circumstances. If container runtime is absent, status is `UNAVAILABLE`. |
| **No Arbitrary Commands** | Test commands are constructed solely from trusted server templates (`pytest -q --tb=short <target>` or `npx --no-install jest <target>`). LLMs or client HTTP requests cannot supply shell strings. |
| **Strict Image Allowlist** | Only preconfigured, audited images (`python:3.11-slim`, `node:20-slim`) are permitted. User-supplied images are rejected. |
| **Network Isolation** | Containers are run with `--network none` by default, preventing unauthorized outbound connections, credential exfiltration, or reverse shells. |
| **Privilege Elimination** | Containers run as unprivileged user (`--user 1000:1000`), with `--security-opt no-new-privileges:true`, and `--cap-drop ALL`. Privileged mode is strictly forbidden. |
| **Filesystem Hardening** | Root filesystem is `--read-only`. Workspace source is mounted read-only (`:ro`). Writable scratch space is limited to a bounded temporary in-memory tmpfs (`/tmp:rw,noexec,nosuid,size=64m`). |
| **Resource & Denial of Service Limits** | Bounded CPU (`--cpus 1.0`), RAM (`--memory 512m`), process table (`--pids-limit 100`), wall-clock timeouts (default 45s, max 120s), and log limits (max 50KB stdout/stderr). |
| **Credential Protection** | Neither host filesystem roots, Docker sockets (`/var/run/docker.sock`), application environment variables, nor secrets are ever mounted into execution containers. |
| **Disposable Lifecycle & Cleanup** | Workspace directories and container instances are cleaned up unconditionally in `finally` blocks upon completion, failure, timeout, or cancellation. |

---

## 4. Supported Project Types

### 1. Python (`python_pytest`)
- Preconfigured runtime: `python:3.11-slim`
- Discovers pytest targets from repository snapshot metadata
- Sanitized test target argument (path traversal and metacharacters rejected)
- Accurately parses collected, passed, failed, skipped, and collection errors

### 2. Node.js & TypeScript (`node_jest` / `node_npm_test`)
- Preconfigured runtime: `node:20-slim`
- Discovers package manifests and test scripts
- Executes allowlisted runner with `--no-install` flag
- Accurately parses suite and test totals, failures, and diagnostic traces

---

## 5. Verification Status Lifecycle Machine

The state machine strictly governs the 10 execution states:
```
QUEUED ──> PREPARING ──> RUNNING ──> PASSED
  │           │             │    ──> FAILED
  │           │             │    ──> TIMED_OUT
  │           │             │    ──> CANCELLED
  │           ▼             │
  │     BLOCKED             │
  ▼                         │
UNSUPPORTED / UNAVAILABLE ──┘
```

- **QUEUED**: Request accepted and assigned a UUID `run_id`.
- **PREPARING**: Disposable sandbox workspace is provisioned.
- **RUNNING**: Container spawned and test process actively executing.
- **PASSED**: Process exited with code 0 and runner output confirmed 0 failed/0 errors.
- **FAILED**: Process exited non-zero or failures were reported in runner summary.
- **TIMED_OUT**: Process exceeded configured wall-clock timeout limit.
- **BLOCKED**: Workspace preparation or dependency requirements could not be safely satisfied.
- **UNSUPPORTED**: Repository runtime or runner is outside the server allowlist.
- **UNAVAILABLE**: Host lacks required container infrastructure (e.g. Docker daemon unreachable).
- **CANCELLED**: Job was terminated by explicit contributor/admin cancellation.

---

## 6. Repository Reality Checker Integration

The `VerificationRealityAdapter` integrates isolated test results into the `RepositoryRealityChecker`:
- Evaluates contribution plans to check if implementation steps make claims like "verified tests pass" or "all tests passed".
- Looks up the latest `VerificationRunRecord` matching `(owner, repo, commit_sha)`.
- **Commit SHA Binding**: If a verification record exists for commit `A`, but the plan snapshot is at commit `B`, the adapter flags the record as `TESTS_STALE_RECORD` and neutralizes false claims.
- **Evidence Backing**: Only when a genuine `PASSED` record with identical `commit_sha` is verified does the adapter mark steps as `is_verified=True` and append verified citations.
- **Discovered vs Executed**: If tests exist in the repository metadata but no verification run was triggered, the adapter flags `TESTS_DISCOVERED_NOT_EXECUTED` and instructs the user to run the sandbox.

---

## 7. API Contracts

### `GET /api/verification/health`
Returns sandboxing container infrastructure capability:
```json
{
  "runtime_available": false,
  "runtime_name": "docker",
  "isolation_level": "none",
  "supported_profiles": ["python_pytest", "node_jest", "node_npm_test"],
  "message": "Docker CLI is not installed on the host. Isolated verification is unavailable.",
  "host_execution_permitted": false
}
```

### `POST /api/verification/run`
Submits an isolated verification request (returns HTTP 202 Accepted):
```json
{
  "owner": "pallets",
  "repo": "flask",
  "commit_sha": "a1b2c3d4e5f67890",
  "runtime": "python_pytest",
  "test_target": "tests",
  "timeout_seconds": 45
}
```

### `GET /api/verification/runs/{run_id}`
Retrieves a verification execution record with bounded output logs.

### `POST /api/verification/runs/{run_id}/cancel`
Cancels an ongoing verification run.

### `GET /api/verification/{session_id}`
Returns contribution session verification status and checks.

---

## 8. Residual Security Risks & Production Isolation Note

> [!WARNING]
> **Container Isolation vs Multi-Tenant Sandboxing**:
> Standard Docker containers share the host Linux kernel. While FirstPatch AI applies comprehensive container hardening (`--network none`, `--user 1000:1000`, `--read-only`, tmpfs, PID/CPU/memory limits, `--cap-drop ALL`), containerization reduces risk but does not eliminate all theoretical kernel vulnerabilities, zero-day container escape exploits, or microarchitectural side-channels.
>
> In multi-tenant enterprise deployments, FirstPatch AI should be run atop hardware-virtualized microVM runtimes (such as AWS Firecracker, Kata Containers, or Google gVisor) on dedicated ephemeral worker nodes.
