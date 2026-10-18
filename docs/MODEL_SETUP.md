# FirstPatch AI — Local Model Setup & Management

FirstPatch AI uses **Ollama** as its default local inference provider. This enables private, offline-capable code reasoning without API fees or telemetry leaks.

---

## Supported & Recommended Models

| Model Tag | Parameters | Disk Size | Best For | Recommended RAM |
| :--- | :--- | :--- | :--- | :--- |
| **`gemma4:e2b`** | ~2B (Efficient) | ~7.5 GB GGUF | Fast reasoning & guided mentorship on laptops | $\ge 8$ GB RAM |
| **`gemma4:e4b`** | ~4B (Efficient) | ~9.5 GB GGUF | Balanced code comprehension & architectural analysis | $\ge 16$ GB RAM |
| **`gemma4`** (Default) | Standard | ~9.5 GB | Full capability Gemma 4 model | $\ge 16$ GB RAM |
| **`gemma4:26b` / `31b`**| 26B / 31B | > 18 GB | Deep multi-file reasoning & maintainer reviews | $\ge 32$ GB Unified Memory |
| **`gemma2:2b`** | 2.6B | ~1.6 GB | Ultra-lightweight fallback for low-spec machines | $\ge 8$ GB RAM |
| **`qwen2.5-coder:3b`** | 3.1B | ~1.9 GB | Code reasoning & structured diff generation | $\ge 8$ GB RAM |
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

### 3. Pull Gemma 4 & Supporting Models
```bash
# Pull primary Gemma 4 model (or specific parameter size)
ollama pull gemma4:e2b
# or: ollama pull gemma4

# Pull embedding model for hybrid semantic search
ollama pull nomic-embed-text

# (Optional) Lightweight fallbacks
ollama pull gemma2:2b
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
