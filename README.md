# 🚀 FirstPatch AI — Your Local Open-Source Mentor

> **"Don't just help developers write code. Help them understand, contribute, and grow as developers."**

FirstPatch AI is a local-first, privacy-focused open-source contribution mentor. It guides beginners and students through exploring unfamiliar repositories, understanding complex architectures, identifying beginner-friendly issues, diagnosing environment setup errors, and verifying changes through real, sandboxed test runs before submitting maintainer-ready pull requests.

---

## 🌟 Why FirstPatch AI is Different

Traditional developer tools either provide static issue lists (FirstIssue, Good First Issue) or blindly generate code without explanation (Copilot, Cursor). FirstPatch AI bridges the gap between **wanting to contribute** and **making a verified, educational contribution**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FIRSTPATCH AI PIPELINE                            │
├───────────────┬────────────────┬───────────────┬──────────────┬─────────────┤
│ 1. REALITY    │ 2. DISCOVERY   │ 3. ENVIRONMENT│ 4. MENTORSHIP│ 5. FLIGHT   │
│    CHECKER    │    & MATCHING  │    DOCTOR     │    & LEARNING│    RECORDER │
└───────────────┴────────────────┴───────────────┴──────────────┴─────────────┘
```

1. **Repository Reality Checker (Deterministic Grounding)**
   - Uses real AST parsing (`ast` visitor in Python, regex symbol extractors for other languages) to extract exact function signatures, classes, imports, and line ranges.
   - **Zero Code Hallucinations:** Every claim links directly to a verifiable file and line coordinates (`https://github.com/owner/repo/blob/SHA/file#L10-L30`).
2. **Contextual Issue Discovery & Transparent Scoring**
   - Ranks open GitHub issues with transparent heuristics: label signals (`good-first-issue`, `beginner`), description clarity, prerequisite skills, and codebase touch-points.
3. **Setup Failure Doctor**
   - Parses installation and build failures (`pip`, `npm`, `poetry`, `docker`), categorizes runtime errors, and suggests safe shell commands.
4. **Dual Mentorship Modes**
   - **Learn Mode (Socratic Mentorship):** Explains architectural concepts progressively, provides micro-drills, and teaches missing skills (e.g., pytest fixtures, async loops) before coding.
   - **Copilot Mode (Implementation Guidance):** Generates structured contribution plans, suggests minimal file diffs, and isolates unit tests.
5. **Contribution Flight Recorder & Truthful Verification**
   - Records the journey timeline (`Understand` → `Plan` → `Attempt` → `Verify` → `PR Draft`).
   - Runs tests in a restricted local sandbox and captures real exit codes and `stdout`/`stderr`. **Never fakes `PASSED` status**.
   - Generates maintainer-ready PR descriptions with verified test evidence and simulated maintainer review audit findings.

---

## 🏗️ Technical Architecture

```
                  ┌─────────────────────────────────────────┐
                  │      Next.js 16 + React 19 Frontend     │
                  │   (TypeScript, Tailwind CSS, Lucide)    │
                  └────────────────────┬────────────────────┘
                                       │ HTTP / JSON
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │          FastAPI Backend Engine         │
                  │         (Python 3.11+, Pydantic)        │
                  └─────────┬─────────────────────┬─────────┘
                            │                     │
              Deterministic │                     │ Evidence-Backed Prompt
                 Extraction │                     ▼
                            │        ┌─────────────────────────┐
                            │        │   Local Ollama Engine   │
                            │        │   (gemma2:2b / qwen2.5) │
                            │        │   (nomic-embed-text)    │
                            ▼        └─────────────────────────┘
        ┌───────────────────────────────────────┐
        │        Local SQLite Database          │
        │ - FTS5 Lexical Chunk Index            │
        │ - AST Symbols & Evidence Ledger       │
        │ - Flight Recorder Audit Trail         │
        └───────────────────────────────────────┘
```

---

## 📦 Prerequisites

1. **Python 3.11+**
2. **Node.js 18+** & npm
3. **Ollama** running locally on `http://127.0.0.1:11434`

### Setup Local Models on Ollama

Pull the recommended local models:

```bash
# 1. Primary mentor model (lightweight, runs smoothly on laptops)
ollama pull gemma2:2b

# 2. Embedding model for semantic code retrieval
ollama pull nomic-embed-text

# 3. Optional coding model alternative
ollama pull qwen2.5-coder:3b
```

Verify that Ollama is active:
```bash
curl http://127.0.0.1:11434/api/tags
```

---

## 🚀 Quickstart Guide

### 1. Start the Backend

```bash
# Navigate to the project root
cd /path/to/FirstPatch

# Create and activate virtual environment
python3 -m venv backend/venv
source backend/venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run the FastAPI server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend API will be live at:
- **API Root:** `http://127.0.0.1:8000`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **Health Check:** `http://127.0.0.1:8000/api/health`

### 2. Start the Frontend

In a separate terminal:

```bash
cd /path/to/FirstPatch/frontend

# Install dependencies
npm install

# Run Next.js in development mode
npm run dev
```

Open your browser at **`http://localhost:3000`**.

---

## 🧪 Running Automated Tests

### Backend Unit Tests (Pytest)
```bash
./backend/venv/bin/pytest -v
```
All 9 core test suites will execute:
- Repository URL parsing & normalization
- Python AST extractor & symbol detection
- Source chunking & SHA256 hashing
- Issue intelligence scoring
- Setup Failure Doctor error classification
- Safe command sandbox & dangerous token blocking
- PR Review Simulator checks
- Flight Recorder event logging & PR draft generation

### Frontend Production Build
```bash
cd frontend
npm run build
```

---

## 🛡️ Security & Privacy Principles

1. **Local Model Execution:** Model inference runs 100% locally on your machine via Ollama. No private repository source code is transmitted to cloud LLM providers.
2. **Network Transparency:** Network requests are limited strictly to public GitHub APIs for repository metadata and file fetching.
3. **Safe Subprocess Execution:** Command verification rejects destructive shell commands (`rm -rf`, `sudo`, piping to `/dev/sd*`, chained shell injections) and enforces timeouts.
4. **Zero-Secret Storage:** Sensitive tokens and keys are never embedded in database records or prompt context.

---

## 📄 License

MIT License. Open-source contribution mentorship platform.
