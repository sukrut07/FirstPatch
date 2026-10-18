# 🚀 FirstPatch AI — Your Open-Source Mentor

> **"Contribute like you understand it, because you will."**  
> *The Contribution Trust Layer for Open Source.*

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

1. **Proof-Carrying Contributions:** Distinguishes model-generated recommendations from independently checked facts with a four-verdict Reality Checker: `VERIFIED`, `REFUTED`, `STALE`, and `UNKNOWN`.
2. **Deterministic Code Intelligence:** Uses native Python AST extraction and symbol table parsing. It never asks an LLM to hallucinate file paths or line bounds.
3. **Multi-Dimensional Issue Fit:** Renders an interactive 5-dimensional radar geometry across Technical Fit, Interest Alignment, Evidence Depth, Solvability, and Learning Opportunities.
4. **Setup Failure Doctor:** Diagnostic engine classifying build errors (`ModuleNotFoundError`, `ERESOLVE`, port collisions, missing `.env`) with safe, copyable fixes.
5. **Human-in-the-Loop Triage:** Enforces a 6-step contributor triage and hypothesis log before code generation.
6. **Contribution Flight Recorder:** Immutable append-only audit ledger recording every step, test execution, and finding into a truthful PR draft.

---

## 🏗️ Technical Architecture

```
                  ┌─────────────────────────────────────────┐
                  │      Next.js 16 + React 19 Frontend     │
                  │   - Recharts Diagrammatic AST Analysis  │
                  │   - Custom API Key & Model Drawer       │
                  │   - Socratic Learn vs. Copilot Modes    │
                  └────────────────────┬────────────────────┘
                                       │ HTTP / JSON
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │          FastAPI Backend Engine         │
                  │         (Python 3.11+, Pydantic)        │
                  │  - Routers: repositories, issues, mentor│
                  │    contributions, verification, trust,  │
                  │    compliance, learning, benchmark      │
                  └─────────┬─────────────────────┬─────────┘
                            │                     │
              Deterministic │                     │ Grounded Context
                 Extraction │                     ▼
                            │        ┌─────────────────────────┐
                            │        │   Local Ollama Engine   │
                            │        │   (gemma4:e2b / gemma2) │
                            │        │   (nomic-embed-text)    │
                            │        │   + Cloud API Key router│
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

FirstPatch AI supports local zero-cost inference using Google's **Gemma 4** family via Ollama. Quantized GGUF models allow full repository reasoning on laptops without high-end GPUs:

```bash
# Pull the recommended default Gemma 4 model
ollama pull gemma4:e2b

# Pull embedding model for semantic code retrieval
ollama pull nomic-embed-text

# Optional high-capacity variants:
ollama pull gemma4:26b
ollama pull gemma4:31b
```

#### Official Google Gemma & Hackathon Resources
- [Google Gemma Ollama Integration Guide](https://ai.google.dev/gemma/docs/integrations/ollama)
- [MLH Hack Days Gemma Hub](https://hack-days-gemma-mlh.pages.dev/)
- [Gemma on Gemini API](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api)
- [Official Google Gemma Cookbook](https://github.com/google-gemma/cookbook)
- [MLH Gemma Documentation](https://mlh.link/gemma-docs)

---

## 🚀 Quickstart Guide

### 1. Configure Environment
```bash
cp .env.example .env
```

### 2. Start the Backend
```bash
# Activate virtual environment
source backend/venv/bin/activate  # or: ./backend/venv/bin/python

# Install dependencies
pip install -r backend/requirements.txt

# Start backend server
uvicorn backend.app.main:app --port 8000 --reload
```
Backend API will be running at **`http://127.0.0.1:8000`** (Swagger docs at `/docs`).

### 3. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```
Open your browser at **`http://localhost:3000`**.

---

## 📊 Diagrammatic Analysis of Codebases (Recharts)

On any repository workspace (`/repo/[owner]/[repo]`), switch to the **Diagrammatic Analysis** tab to interact with visual telemetry:
- **Language & File Type Composition (Donut / Pie Chart):** File count, Kilobytes, and source percentages.
- **AST Symbol Density by Module (Bar Chart):** Compares function and class distribution to locate architectural cores.
- **Issue Multi-Dimensional Fit Profile (Radar Chart):** Evaluates beginner issues across 5 dimensions.
- **Architecture Composition & Test Ratio (Horizontal Bar Chart):** Compares implementation code, test suites, and configuration files.

---

## ⚡ Optional Cloud LLM API Key Acceleration

In the **AI Mentor** tab, click **Configure API Key** to provide a custom API key (stored securely in your local browser `localStorage`):
- **OpenAI:** `sk-...` (`gpt-4o-mini` / `gpt-4o`)
- **DigitalOcean Gradient™ AI Agentic Cloud:** `grad_...` ([mlh.link/digitalocean-gradient](https://mlh.link/digitalocean-gradient))
- **Groq:** `gsk_...` (`llama-3.1-8b-instant`)
- **Anthropic Claude:** `sk-ant-...`

*If left blank, FirstPatch AI runs 100% locally on Ollama Gemma 4 with zero cloud dependencies or costs.*

---

## 🧪 Automated Testing & Compliance Verification

### Run 10-Problem Compliance Suite
```bash
./backend/venv/bin/pytest backend/tests/test_compliance.py -v
```
Verifies all 10 problems from the problem analysis (AST navigation, issue matching, stacktrace line bounding, onboarding guide, setup doctor, contributor triage, contribution policy, reality checker, flight recorder, maintainer drafts).

### Run Full Test Suite
```bash
./backend/venv/bin/pytest -v
```

### Build Frontend
```bash
cd frontend
npm run build
```

---

## 🛡️ Security & Privacy Principles

1. **Local Model Execution:** Default inference runs locally via Ollama. No private repository source code is transmitted to cloud LLM providers.
2. **Network Transparency:** Network requests are limited strictly to public GitHub APIs for repository metadata and file fetching.
3. **Safe Subprocess Execution:** Command verification rejects destructive shell commands (`rm -rf`, `sudo`, piping to `/dev/sd*`, chained shell injections) and enforces timeouts.
4. **Zero-Secret Storage:** Sensitive tokens and keys are never embedded in database records or prompt context.

---

## 📄 License

MIT License. Open-source contribution mentorship platform.
