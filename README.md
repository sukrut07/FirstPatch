# FirstPatch AI

**Your Open-Source Mentor** — evidence-backed AI guidance for making your first meaningful contribution to an unfamiliar GitHub repository.

---

## What Is FirstPatch AI?

FirstPatch AI helps beginner developers:

1. Understand an unfamiliar repository's structure and technology stack
2. Discover candidate open issues ranked by beginner-friendliness
3. Receive a step-by-step contribution plan backed by real repository evidence
4. Diagnose development setup problems
5. Know exactly what has and hasn't been verified before submitting a PR

It is **not** a generic chatbot. Every displayed fact is traced to a verifiable source. Uncertainties and missing information are shown explicitly, never fabricated.

---

## Features & Capabilities

| Feature | Status | Notes |
|---|---|---|
| Public GitHub repository analysis | ✅ Implemented | Metadata, commit SHA, languages, tree, README |
| Evidence-backed repository overview | ✅ Implemented | Every fact tied to a verifiable EvidenceRef |
| Python AST Code Extraction | ✅ Implemented | Classes, methods, functions, imports, decorators, line ranges |
| Multi-language Structure Heuristics | ✅ Implemented | JS/TS, Go, Rust with explicit limitation disclosures |
| 7-Criterion Issue Matching Engine | ✅ Implemented | Deterministic, transparent scoring |
| Controlled Agent Orchestrator | ✅ Implemented | 8-stage pipeline coordinating Tools A through H |
| Repository Reality Checker | ✅ Implemented | Fact-checks plans, eliminates hallucinated files & false claims |
| Setup Failure Doctor | ✅ Implemented | Python, Node, venv, missing env, port conflict, pytest collection |
| Gemma 4 AI Provider Adapter | ✅ Implemented | `gemma-4-31b-it` via Google AI Studio API & local Ollama |
| Deterministic AI Fallback | ✅ Implemented | Full functionality preserved without AI credentials |
| Comprehensive Test Suite | ✅ 67/67 Passing | Unit, integration, AST, AI provider, and reality checker tests |
| Production Frontend Build | ✅ Verified | Next.js 14, TypeScript strict, 0 errors, 0 warnings |


---

## Architecture

```
firstpatch-ai/
  frontend/          Next.js 14 + TypeScript + Tailwind CSS
  backend/           Python 3.11+ + FastAPI + Pydantic v2
  docs/              Architecture, API contracts, security, implementation plan
  .env.example       All required environment variable placeholders
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full component diagram and data flow.

---

## Prerequisites

| Tool | Version | Required For |
|---|---|---|
| Python | 3.11+ | Backend |
| Node.js | 18+ | Frontend |
| npm | 9+ | Frontend dependencies |
| Git | Any | Repository analysis |

Optional:
- A [GitHub Personal Access Token](https://github.com/settings/tokens) (increases API rate limit from 60 to 5000 requests/hour)
- A [Google AI Studio API key](https://aistudio.google.com) (enables Gemma AI enrichment)
- [Ollama](https://ollama.ai) (enables local Gemma inference)

---

## Installation

### 1. Clone and configure environment

```bash
git clone https://github.com/YOUR_HANDLE/HacktoberDYP
cd HacktoberDYP
cp .env.example .env
# Edit .env and fill in at minimum: GITHUB_TOKEN (optional but recommended)
```

### 2. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (macOS/Linux)
source .venv/bin/activate

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`  
API docs at: `http://localhost:8000/api/docs`

### 3. Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Frontend will be available at: `http://localhost:3000`

---

## Environment Variables

Copy `.env.example` to `.env` in the project root. Key variables:

| Variable | Default | Description |
|---|---|---|
| `GITHUB_TOKEN` | (empty) | GitHub PAT for higher rate limits |
| `AI_PROVIDER` | `none` | `none`, `google_ai_studio`, or `local_ollama` |
| `GOOGLE_AI_API_KEY` | (empty) | Required if `AI_PROVIDER=google_ai_studio` |
| `GOOGLE_AI_MODEL` | `gemma-4-31b-it` | Gemma model to use (`gemma-4-31b-it`, `gemma-4-26b-a4b-it`, `gemma-3-27b-it`) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Required if `AI_PROVIDER=local_ollama` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./firstpatch.db` | SQLite DB path |

⚠️ **Never commit your actual `.env` file.** It is in `.gitignore`.

---

## Running Tests

### Backend tests

```bash
cd backend
.\.venv\Scripts\Activate.ps1    # Windows
# OR
source .venv/bin/activate       # macOS/Linux

pytest tests/ -v
```

### Frontend type checks

```bash
cd frontend
npx tsc --noEmit
npm run lint
```

---

## Using the Application

1. Open `http://localhost:3000`
2. Enter a public GitHub repository URL (e.g. `https://github.com/tiangolo/fastapi`)
3. Click **Analyze** — the backend fetches real repository metadata
4. Navigate to **Issues** to see ranked open issues with transparent scores
5. Click **Generate Plan** on any issue to get a step-by-step contribution guide
6. Check **Settings** to see service health and AI provider status

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Backend won't start | Check Python 3.11+ is installed; activate venv first |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` in the backend directory |
| GitHub rate limit (429) | Set `GITHUB_TOKEN` in `.env` |
| Repository not found (404) | Confirm the repo exists and is public |
| AI features show "not configured" | Set `AI_PROVIDER` and corresponding credentials in `.env` |
| Frontend can't reach backend | Ensure backend is running on port 8000; check `NEXT_PUBLIC_API_URL` in `frontend/.env.local` |

---

## Security

- Repository content is treated as **untrusted data** — it is never executed or used as instructions to the AI.
- URL validation prevents Server-Side Request Forgery (SSRF).
- No code is executed automatically — test execution requires explicit user initiation and an isolated environment (not implemented in Phase 0).
- Credentials are never logged or returned in API responses.

See [docs/SECURITY.md](docs/SECURITY.md) for the full security model.

---

## Current Implementation Status

**Working:** Repository analysis, issue discovery, issue matching, contribution plan generation, setup diagnostics, health endpoint, AI provider adapter with deterministic fallback.

**Not yet implemented:** Test execution (requires sandboxed environment), PR preparation workflow, authenticated GitHub session management.

See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for the full roadmap.

---

## License

MIT