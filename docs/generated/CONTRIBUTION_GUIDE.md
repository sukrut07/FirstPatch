# 📜 Contribution Guidelines: pallets/flask

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
