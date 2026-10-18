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

---

## 📋 What Exactly Do You Have To Do? (End-to-End Walkthrough)

Whether you are a student, hackathon judge, or first-time open-source contributor, here is the exact step-by-step workflow:

### Step 1: Initialize Local AI Infrastructure
Start Ollama and pull the recommended open-weight models:
```bash
# Pull the high-throughput Gemma 4 mentor model and embedding model
ollama pull gemma4:e2b
ollama pull nomic-embed-text
```

### Step 2: Start the FirstPatch Application
In Terminal 1 (Backend):
```bash
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --port 8000 --reload
```

In Terminal 2 (Frontend):
```bash
cd frontend
npm install
npm run dev
```
Open **`http://localhost:3000`** in your browser.

### Step 3: Run the Empirical ML Model Benchmarks
Verify local inference speed and grounding accuracy on your hardware:
```bash
./backend/venv/bin/python scripts/run_benchmarks.py --all
```

### Step 4: Analyze a Target Open-Source Repository
On the FirstPatch dashboard (`http://localhost:3000`), enter any public repository (e.g. `pallets/flask` or `tiangolo/fastapi`) or select from the **Explore** directory:
1. **Repository Reality Check:** Browse the extracted AST classes, functions, and line ranges in the **Files** and **Architecture** tabs. Notice that every symbol links to exact source lines (`#L10-L30`).
2. **Issue Matching:** Navigate to the **Issues** tab to see transparent fit scores, estimated effort, and detected prerequisites (e.g. `pytest`, `asyncio`).
3. **Setup Failure Doctor:** If you encounter environment or installation issues, paste the error trace into the **Setup Doctor** tab for immediate categorization and safe remediation shell commands.
4. **Interactive Mentorship:** Open the **Mentor** tab to choose between **Learn Mode** (Socratic guidance and concept explanations) or **Copilot Mode** (direct code patches and test suggestions).
5. **Flight Recorder & PR Verification:** Click **Start Contribution** on an issue. Check off steps, run unit tests safely in the subprocess sandbox, audit proposed diffs for leaked secrets, and generate a maintainer-ready PR description with raw test logs.

---

## 📊 Empirical ML Model Benchmarks (Live Local Evaluation)

Evaluated on local Apple Silicon hardware running Ollama (Temperature: 0.1, Token context: 8192):

| Model Tag | Size / GGUF | Pass Rate | Avg Throughput | AST Reasoning Speed | JSON Schema Adherence | Diff Security Audit |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`gemma4:e2b`** (Active) | 7.5 GB | **100.0% (3/3)** | **72.4 tok/s** | **80.5 tok/s** (Passed) | **67.5 tok/s** (100% Valid JSON) | **71.8 tok/s** (Passed) |
| **`qwen2.5-coder:3b`** | 1.9 GB | **100.0% (3/3)** | **37.7 tok/s** | 16.3 tok/s (Passed) | 37.7 tok/s (100% Valid JSON) | 45.1 tok/s (Passed) |
| **`gemma2:2b`** | 1.6 GB | 66.7% (2/3) | 23.5 tok/s | 7.1 tok/s (Passed) | 45.2 tok/s (100% Valid JSON) | 50.6 tok/s (Partial) |

- **Key Finding:** `gemma4:e2b` achieved **72.4 tokens/second** generation throughput—nearly double `qwen2.5-coder:3b` (37.7 tok/s) and 3x faster than `gemma2:2b` (23.5 tok/s)—with perfect JSON schema compliance and zero hallucinations.
- **Reproduce anytime:** Run `./backend/venv/bin/python scripts/run_benchmarks.py --all` or `curl -X POST http://127.0.0.1:8000/api/benchmark/run`.

---

## 🤖 Multi-Agent AI Orchestration Architecture

FirstPatch AI coordinates specialized agentic roles to ensure reliable guidance:

```
[User Question / Issue Request]
              │
              ▼
   ┌───────────────────────┐
   │ 1. Triage Agent       │ ──► Classifies task (architecture explanation vs bug fix vs setup)
   └──────────┬────────────┘
              │
              ▼
   ┌───────────────────────┐
   │ 2. Reality Check      │ ──► Hybrid lexical + vector retrieval; cross-references
   │    Grounding Agent    │     all claims against AST symbol tables & line numbers
   └──────────┬────────────┘
              │
              ▼
   ┌───────────────────────┐
   │ 3. Socratic / Copilot │ ──► Generates progressive concept breakdowns, quizzes (Learn)
   │    Mentorship Agent   │     or concrete diff suggestions & test commands (Copilot)
   └──────────┬────────────┘
              │
              ▼
   ┌───────────────────────┐
   │ 4. Verification &     │ ──► Audits diffs for leaked secrets, executes sandboxed tests,
   │    Review Agent       │     and compiles Flight Recorder audit logs into PR draft
   └───────────────────────┘
```

---

## 🌊 DigitalOcean Gradient™ AI Agentic Cloud Integration

FirstPatch AI supports hybrid edge-and-cloud architecture using the **DigitalOcean Gradient™ AI Agentic Cloud**:

- **Official MLH DigitalOcean Hub:** [mlh.link/digitalocean-gradient](https://mlh.link/digitalocean-gradient)
- **DigitalOcean Products & Pricing:** [mlh.link/digitalocean-products](https://mlh.link/digitalocean-products)
- **Complete Architecture Guide:** See [`docs/DIGITALOCEAN_GRADIENT.md`](docs/DIGITALOCEAN_GRADIENT.md)

### Supported DigitalOcean Services:
1. **DigitalOcean Gradient™ AI GPU Droplets & Bare Metal GPUs:** On-demand NVIDIA H100/A100 compute nodes for multi-repository indexing and parallel CI sandbox test suites.
2. **DigitalOcean Gradient™ Serverless Inference & 1-Click Models:** Offload reasoning for resource-constrained client machines.
3. **DigitalOcean Gradient™ Knowledge Bases:** Distributed vector storage for enterprise codebases.
4. **DigitalOcean Gradient™ Guardrails:** Pre-submission pull request auditing to guarantee zero secret leaks.

```bash
# Deploy FirstPatch AI on DigitalOcean with doctl
doctl compute droplet create firstpatch-ai-node \
  --region nyc1 \
  --image ubuntu-24-04-x64 \
  --size so-2vcpu-16gb
```

---

## 🧪 Running Automated Tests

### Backend Unit Tests (Pytest)
```bash
./backend/venv/bin/pytest -v
```
All 10 core test suites will execute:
- Repository URL parsing & normalization
- Python AST extractor & symbol detection
- Source chunking & SHA256 hashing
- Issue intelligence scoring
- Setup Failure Doctor error classification
- Safe command sandbox & dangerous token blocking
- PR Review Simulator checks
- Flight Recorder event logging & PR draft generation
- ML Benchmark Suite verification

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

