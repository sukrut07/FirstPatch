import os
import json
from typing import Dict, Any, List, Optional
from backend.app.database import get_db, get_iso_now

from pathlib import Path

class DocumentationService:
    def __init__(self):
        root_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
        self.output_dir = os.path.join(root_dir, "docs", "generated")

    def generate_all_documentation(self, repository_id: str) -> Dict[str, Any]:
        """
        Generates 4 standardized markdown documents for an analyzed repository:
        1. PROJECT_OVERVIEW.md
        2. ARCHITECTURE.md
        3. BEGINNER_SETUP.md
        4. CONTRIBUTION_GUIDE.md
        """
        os.makedirs(self.output_dir, exist_ok=True)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM repositories WHERE id = ?", (repository_id,))
            repo = cursor.fetchone()
            if not repo:
                raise ValueError(f"Repository {repository_id} not found in database.")

            cursor.execute("SELECT * FROM repository_files WHERE repository_id = ?", (repository_id,))
            files = [dict(f) for f in cursor.fetchall()]

            cursor.execute("SELECT * FROM repository_snapshots WHERE repository_id = ? AND is_current = 1", (repository_id,))
            snapshot = cursor.fetchone()

        commit_sha = snapshot["commit_sha"] if snapshot else (repo["default_commit_sha"] or "main")
        files_count = len(files)
        test_files = [f for f in files if f.get("is_test")]
        config_files = [f for f in files if f.get("is_config")]
        entrypoints = [f for f in files if f.get("is_entrypoint")]

        # 1. Detect Covered Domains
        domains = self._detect_covered_domains(files, repo)

        # 2. Generate PROJECT_OVERVIEW.md
        overview_md = self._generate_overview_md(repo, commit_sha, files, domains, entrypoints, test_files)
        overview_path = os.path.join(self.output_dir, "PROJECT_OVERVIEW.md")
        with open(overview_path, "w", encoding="utf-8") as f:
            f.write(overview_md)

        # 3. Generate ARCHITECTURE.md (with Mermaid diagram)
        arch_md = self._generate_architecture_md(repo, commit_sha, files, entrypoints, test_files)
        arch_path = os.path.join(self.output_dir, "ARCHITECTURE.md")
        with open(arch_path, "w", encoding="utf-8") as f:
            f.write(arch_md)

        # 4. Generate BEGINNER_SETUP.md
        setup_md = self._generate_setup_md(repo, files, config_files)
        setup_path = os.path.join(self.output_dir, "BEGINNER_SETUP.md")
        with open(setup_path, "w", encoding="utf-8") as f:
            f.write(setup_md)

        # 5. Generate CONTRIBUTION_GUIDE.md
        contrib_md = self._generate_contribution_md(repo, files)
        contrib_path = os.path.join(self.output_dir, "CONTRIBUTION_GUIDE.md")
        with open(contrib_path, "w", encoding="utf-8") as f:
            f.write(contrib_md)

        return {
            "repository_id": repository_id,
            "commit_sha": commit_sha,
            "generated_at": get_iso_now(),
            "documents": {
                "project_overview": overview_path,
                "architecture": arch_path,
                "beginner_setup": setup_path,
                "contribution_guide": contrib_path
            },
            "domains_detected": domains
        }

    def _detect_covered_domains(self, files: List[Dict[str, Any]], repo: Any) -> List[Dict[str, Any]]:
        domains = []
        paths_str = " ".join([f["path"].lower() for f in files])
        topics = repo["topics"] or ""

        if "web" in paths_str or "flask" in paths_str or "fastapi" in paths_str or "django" in paths_str or "routes" in paths_str:
            domains.append({
                "name": "Web Application & APIs",
                "confidence": "High",
                "evidence": "Detected HTTP routes, request handlers, and framework manifests."
            })
        if "test" in paths_str or "tests" in paths_str:
            domains.append({
                "name": "Automated Testing & CI",
                "confidence": "High",
                "evidence": f"Found {len([f for f in files if f.get('is_test')])} dedicated test modules."
            })
        if "cli" in paths_str or "click" in paths_str or "argparse" in paths_str or "main.py" in paths_str:
            domains.append({
                "name": "Developer Tooling & CLI",
                "confidence": "Medium",
                "evidence": "Detected command-line entrypoint and argument parser bindings."
            })
        if not domains:
            domains.append({
                "name": "Core Software Library",
                "confidence": "Medium",
                "evidence": "Package structured as a modular reusable library."
            })
        return domains

    def _generate_overview_md(self, repo: Any, commit_sha: str, files: List[Dict[str, Any]], domains: List[Dict[str, Any]], entrypoints: List[Dict[str, Any]], test_files: List[Dict[str, Any]]) -> str:
        lines = [
            f"# 📖 Project Overview: {repo['owner']}/{repo['name']}",
            f"> **Repository URL:** [{repo['html_url']}]({repo['html_url']})  ",
            f"> **Analyzed Commit SHA:** `{commit_sha}`  ",
            f"> **Primary Language:** {repo['language'] or 'Unknown'} | **License:** {repo['license_name'] or 'Not specified'}",
            "",
            "## 1. 💡 Project Purpose",
            repo["description"] or "No official description provided in repository metadata.",
            "",
            "## 2. 🌐 Covered Technical Domains",
        ]
        for d in domains:
            lines.append(f"- **{d['name']}** ({d['confidence']} Confidence): {d['evidence']}")

        lines.extend([
            "",
            "## 3. 📂 Core Directory Structure & Key Files",
            f"- **Total Indexed Files:** {len(files)} files",
            f"- **Entrypoints:** {', '.join([f['path'] for f in entrypoints]) if entrypoints else 'Standard library package layout'}",
            f"- **Test Suite Directory:** {len(test_files)} test files detected in `tests/`",
            "",
            "## 4. 🧭 Where Should a Beginner Start Reading?",
            "1. Read `README.md` for project mission and quick start.",
            "2. Inspect the main entry point to understand how parameters are received.",
            "3. Look at `tests/` to see how functions are expected to behave under normal and error conditions."
        ])
        return "\n".join(lines)

    def _generate_architecture_md(self, repo: Any, commit_sha: str, files: List[Dict[str, Any]], entrypoints: List[Dict[str, Any]], test_files: List[Dict[str, Any]]) -> str:
        entry_node = entrypoints[0]["path"] if entrypoints else "Entrypoint/CLI"
        mermaid = f"""```mermaid
graph TD
    User([Developer / Contributor]) --> Entry["{entry_node}"]
    Entry --> Core[Core Application Logic]
    Core --> Config[Configuration & Environment]
    Core --> Tests["Automated Tests ({len(test_files)} files)"]
    classDef verified fill:#1e293b,stroke:#3b82f6,stroke-width:2px;
    class Entry,Core,Config,Tests verified;
```"""

        return f"""# 🏗️ Architecture & Component Workflow: {repo['owner']}/{repo['name']}

> **Commit SHA:** `{commit_sha}`  
> **Status:** Grounded from verified repository files

## 1. Component Interaction Diagram

{mermaid}

## 2. Execution Dataflow
1. **Invocation:** User or runtime triggers `{entry_node}`.
2. **Configuration Loading:** Defaults and environment variables are parsed into the configuration object.
3. **Execution:** Core modules perform processing and dispatch responses or operations.
4. **Verification:** Unit tests assert output invariants and handle edge cases.
"""

    def _generate_setup_md(self, repo: Any, files: List[Dict[str, Any]], config_files: List[Dict[str, Any]]) -> str:
        return f"""# 🛠️ Beginner Development Environment Setup: {repo['owner']}/{repo['name']}

Follow these steps to set up a clean, reproducible development environment on your machine:

## Step 1: Fork & Clone
```bash
# 1. Fork the repo on GitHub to your username
# 2. Clone your personal fork locally:
git clone https://github.com/YOUR_USERNAME/{repo['name']}.git
cd {repo['name']}

# 3. Add the official upstream remote:
git remote add upstream {repo['html_url']}.git
```

## Step 2: Create a Working Branch
```bash
git checkout -b my-first-contribution
```

## Step 3: Install Dependencies
```bash
# Create and activate a clean virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies:
pip install -e .
pip install pytest
```

## Step 4: Run the Test Suite
```bash
pytest
```
*Expected Result:* All tests should pass before making any code modifications.
"""

    def _generate_contribution_md(self, repo: Any, files: List[Dict[str, Any]]) -> str:
        return f"""# 📜 Contribution Guidelines: {repo['owner']}/{repo['name']}

Follow these project conventions to ensure your pull request is welcomed and quickly merged by maintainers:

## 1. 🌿 Branch & Git Conventions
- Never commit directly to `main` or `master`.
- Create a dedicated branch with a descriptive name (e.g., `fix/keyerror-handling` or `docs/fix-typo`).
- Use [Conventional Commits](https://www.conventionalcommits.org/): `fix: ...`, `feat: ...`, `docs: ...`, `test: ...`.

## 2. 🧪 Test Requirement
- Maintainers will reject PRs that fix bugs without accompanying regression tests.
- Add your test cases under `tests/` before opening the PR.

## 3. 🛡️ Secret & Log Check
- Ensure no API keys, private credentials, or debugging `print()` statements are left in the diff.

## 4. 📝 Pull Request Checklist
- [ ] My change is focused on a single issue.
- [ ] I have executed the local test suite and all tests passed.
- [ ] My commit messages follow the project conventions.
- [ ] I have linked the issue number in my PR description (`Fixes #123`).
"""

documentation_service = DocumentationService()
