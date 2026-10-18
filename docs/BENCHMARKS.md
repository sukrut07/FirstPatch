# 📊 FirstPatch AI — ML Model Benchmarking Report

This document reports empirical benchmarks conducted on local machine inference (via Ollama) evaluating models across core open-source contribution mentorship tasks.

---

## 1. Benchmark Suite Methodology

The FirstPatch benchmark suite tests models across three real-world developer tasks:

1. **AST Code Understanding & Citation:** Tests whether the model identifies exact function parameters, default values, exceptions, and lines from parsed AST blocks without hallucinating missing arguments.
2. **Contribution Plan Generation (Strict JSON):** Evaluates whether the model outputs valid, uncorrupted JSON adhering to the target schema (`root_cause`, `files_to_modify`, `learning_gap`, `recommended_test`).
3. **PR Review Security & Diff Audit:** Tests detection of committed credentials, debug statements (`print()`, `console.log`), and missing unit tests.

---

## 2. Empirical Benchmark Results (Live Ollama Evaluation)

Hardware: Apple Silicon (Local Ollama Engine, Temperature: 0.1)

| Model Tag | Parameters / Size | Pass Rate | Avg Throughput | AST Reasoning Speed | JSON Schema Adherence | Diff Security Audit |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`gemma4:e2b`** | ~2B (7.5 GB) | **100.0% (3/3)** | **72.4 tok/s** | **80.5 tok/s** (Passed) | **67.5 tok/s** (100% Valid JSON) | **71.8 tok/s** (Passed) |
| **`qwen2.5-coder:3b`** | 3.1B (1.9 GB) | **100.0% (3/3)** | **37.7 tok/s** | 16.3 tok/s (Passed) | 37.7 tok/s (100% Valid JSON) | 45.1 tok/s (Passed) |
| **`gemma2:2b`** | 2.6B (1.6 GB) | 66.7% (2/3) | 23.5 tok/s | 7.1 tok/s (Passed) | 45.2 tok/s (100% Valid JSON) | 50.6 tok/s (Partial) |

---

## 3. Analysis & Key Insights

1. **Throughput Superiority:** `gemma4:e2b` achieved an average generation speed of **72.4 tokens/second**, nearly double that of `qwen2.5-coder:3b` (37.7 tok/s) and over 3x faster than `gemma2:2b` (23.5 tok/s).
2. **Zero JSON Schema Failure:** Both `gemma4:e2b` and `qwen2.5-coder:3b` generated 100% parseable, valid JSON without malformed keys or markdown wrapping bugs.
3. **Security Diff Precision:** `gemma4:e2b` detected the hardcoded credential risk and debug output with rich explanation and actionable remediation commands.

---

## 4. How to Reproduce Benchmarks

### Via CLI:
```bash
# Run benchmark on active model (default: gemma4:e2b)
./backend/venv/bin/python scripts/run_benchmarks.py

# Benchmark all installed Ollama chat models
./backend/venv/bin/python scripts/run_benchmarks.py --all

# Benchmark a specific model
./backend/venv/bin/python scripts/run_benchmarks.py --model gemma4:e2b
```

### Via REST API:
```bash
# Trigger benchmark for active model
curl -X POST http://127.0.0.1:8000/api/benchmark/run

# Compare all installed models
curl http://127.0.0.1:8000/api/benchmark/compare
```
