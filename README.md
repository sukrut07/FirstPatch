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

### Setup Local Models on Ollama (Gemma 4 & Embeddings)

FirstPatch AI supports local inference using Google's **Gemma 4** family via Ollama. Quantized GGUF models allow full repository reasoning on laptops without high-end GPUs.

#### 1. Download & Configure Gemma 4 in Ollama

```bash
# Pull the default Gemma 4 model
ollama pull gemma4

# Or select specific Gemma 4 parameter variants based on your hardware:
# - E2B Parameters (Efficient 2B):
ollama pull gemma4:e2b

# - E4B Parameters (Efficient 4B):
ollama pull gemma4:e4b

# - 26B / 31B Parameters (High capacity):
ollama pull gemma4:26b
ollama pull gemma4:31b

# Pull embedding model for semantic code retrieval
ollama pull nomic-embed-text

# Optional lightweight alternatives:
ollama pull gemma2:2b
ollama pull qwen2.5-coder:3b
```

#### 2. Verify Available Models in Ollama

```bash
ollama list
```

#### 3. Test Response Generation Directly

**Command Line:**
```bash
ollama run gemma4 "Explain the role of pytest fixtures in open-source testing"
```

**Local Web Service API:**
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "gemma4:e2b",
  "prompt": "How do I structure a good pull request?"
}'
```

#### 4. Official Google Gemma & Hackathon Resources
- [Google Gemma Ollama Integration Guide](https://ai.google.dev/gemma/docs/integrations/ollama)
- [MLH Hack Days Gemma Hub](https://hack-days-gemma-mlh.pages.dev/)
- [Gemma on Gemini API](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api)
- [Official Google Gemma Cookbook](https://github.com/google-gemma/cookbook)
- [MLH Gemma Documentation](https://mlh.link/gemma-docs)

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
