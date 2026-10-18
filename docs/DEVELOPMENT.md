# FirstPatch AI — Developer Guide

This guide covers contributing to FirstPatch AI, running tests, and managing local workflows.

---

## Directory Structure

```
FirstPatch/
├── backend/
│   ├── app/
│   │   ├── routers/       # FastAPI route endpoints
│   │   ├── services/      # Core business logic (AST, RAG, GitHub, Sandbox)
│   │   ├── config.py      # App configuration via pydantic-settings
│   │   ├── database.py    # SQLite schema & FTS5 virtual tables
│   │   └── main.py        # FastAPI entrypoint
│   ├── tests/             # Pytest test suite
│   ├── requirements.txt   # Python dependencies
│   └── venv/              # Python virtual environment (ignored)
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js App Router pages
│   │   ├── components/    # Reusable UI components (Navbar, etc.)
│   │   └── lib/           # Typed API client
│   ├── package.json       # Node dependencies
│   └── next.config.ts     # Next.js configuration
├── docs/                  # Architecture & engineering documentation
├── pytest.ini             # Pytest configuration with pythonpath=.
├── .env.example           # Example environment variables
└── README.md              # Project overview
```

---

## Running Backend Tests

Backend tests are written with `pytest` and do not require live network or external APIs (network calls are mocked or use local fixtures):

```bash
# From the project root
./backend/venv/bin/pytest -v
```

---

## Building Frontend for Production

```bash
cd frontend
npm run build
```

---

## Adding New Language Parsers

To extend AST parsing beyond Python:
1. Open `backend/app/services/ast_service.py`.
2. Implement an AST visitor or tree-sitter grammar binding for the target language.
3. Return symbol objects matching:
   ```python
   {
       "name": "function_or_class_name",
       "kind": "function" | "class" | "method",
       "start_line": int,
       "end_line": int,
       "signature": str,
       "docstring": str
   }
   ```
4. Add a unit test in `backend/tests/test_backend.py`.
