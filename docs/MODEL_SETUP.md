# FirstPatch AI — Local Model Setup & Management

FirstPatch AI uses **Ollama** as its default local inference provider. This enables private, offline-capable code reasoning without API fees or telemetry leaks.

---

## Supported & Recommended Models

| Model Tag | Parameters | Disk Size | Best For | Recommended RAM |
| :--- | :--- | :--- | :--- | :--- |
| **`gemma2:2b`** | 2.6B | ~1.6 GB | Fast, responsive mentoring & explanations | $\ge 8$ GB RAM |
| **`qwen2.5-coder:3b`** | 3.1B | ~1.9 GB | Code reasoning & structured diff generation | $\ge 8$ GB RAM |
| **`qwen2.5-coder:7b`** | 7.6B | ~4.7 GB | Deep architectural analysis & complex PRs | $\ge 16$ GB RAM |
| **`nomic-embed-text`** | 137M | ~274 MB | Semantic code chunk & issue embeddings | Any hardware |

---

## Installation & Setup Instructions

### 1. Install Ollama
Download and install Ollama from [ollama.com](https://ollama.com/download) or on macOS:
```bash
brew install ollama
```

### 2. Start the Ollama Service
Launch Ollama on your system. It listens on `http://127.0.0.1:11434`.

### 3. Pull Required Models
```bash
# Pull primary mentor model
ollama pull gemma2:2b

# Pull embedding model
ollama pull nomic-embed-text

# (Optional) Pull coder model
ollama pull qwen2.5-coder:3b
```

### 4. Verify Installed Models
```bash
ollama list
```
You should see:
```text
NAME                     ID              SIZE      MODIFIED
gemma2:2b                8ccf12a048a0    1.6 GB    ...
nomic-embed-text:latest  0a109f422b47    274 MB    ...
qwen2.5-coder:3b         2b04965d24e3    1.9 GB    ...
```

---

## Configuration

In `.env` or via the FirstPatch Settings UI (`/settings/models`):
```ini
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma2:2b
OLLAMA_EMBED_MODEL=nomic-embed-text
MODEL_CONTEXT_TOKENS=8192
MODEL_OUTPUT_TOKENS=1536
```

FirstPatch AI automatically checks Ollama health on every request. If Ollama is offline or a model is missing, the UI gracefully displays an offline indicator and allows you to test model health with 1 click.
