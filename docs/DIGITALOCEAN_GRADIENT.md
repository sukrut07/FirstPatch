# 🌊 FirstPatch AI — DigitalOcean Gradient™ AI Agentic Cloud Integration

FirstPatch AI features a hybrid architecture combining local-first edge inference (via Ollama) with the **DigitalOcean Gradient™ AI Agentic Cloud** for scalable, enterprise-grade open-source mentorship, multi-agent routing, and distributed test sandboxes.

Official Resources:
- [DigitalOcean Gradient™ AI Agentic Cloud Hub](https://mlh.link/digitalocean-gradient)
- [DigitalOcean Product Listing & Documentation](https://mlh.link/digitalocean-products)
- [DigitalOcean CLI (`doctl`) Documentation](https://docs.digitalocean.com/reference/doctl/)

---

## 1. DigitalOcean Gradient™ Architecture Overview

```
                      ┌─────────────────────────────────────────┐
                      │           Developer Client              │
                      │  Next.js 16 UI / Local Terminal CLI     │
                      └────────────────────┬────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    │                                             │
      Offline / Edge│                                Cloud Route  │ (High concurrency /
             Mode   ▼                                             ▼  large-scale PR audit)
       ┌────────────────────────┐                   ┌───────────────────────────────┐
       │   Local Ollama Engine  │                   │ DigitalOcean Gradient™ AI     │
       │   - gemma4:e2b         │                   │ Agentic Cloud                 │
       │   - nomic-embed-text   │                   │ - Gradient GPU Droplets       │
       │   - Local AST Sandbox  │                   │ - Serverless Inference        │
       └────────────────────────┘                   │ - Managed Knowledge Bases     │
                                                    │ - Agentic Routing Guardrails  │
                                                    └───────────────────────────────┘
```

---

## 2. Gradient Services Utilized

### A. DigitalOcean Gradient™ AI GPU Droplets & Bare Metal GPUs
- **Use Case:** Heavy multi-repository indexing, multi-language Tree-sitter parsing, and parallel regression test sandboxes.
- **Hardware:** On-demand NVIDIA H100, A100, and L40S GPU droplets configured with pre-installed PyTorch, CUDA, and container runtimes.

### B. DigitalOcean Gradient™ Serverless Inference & 1-Click Models
- **Use Case:** Serverless execution for developers running on low-resource machines (e.g. Chromebooks or 8GB laptops).
- Provides immediate API access to open foundation models without maintaining local GPU infrastructure.

### C. DigitalOcean Gradient™ Knowledge Bases
- **Use Case:** Centralized, vector-indexed repository chunk storage.
- FirstPatch AI automatically syncs AST-grounded code chunks, line coordinates, and symbol tables to DigitalOcean Gradient Knowledge Bases for sub-second semantic retrieval across massive mono-repos.

### D. Multi-Agent Routing & Safety Guardrails
- **Use Case:** Pre-submission pull request auditing.
- Scans proposed diffs through Gradient Guardrails to ensure zero leaked secrets, no dangerous subprocess injections, and strict compliance with repository contribution standards.

---

## 3. Deployment with `doctl` (DigitalOcean CLI)

### 1. Authenticate `doctl`
```bash
# Initialize DigitalOcean CLI with your API token
doctl auth init
```

### 2. Create a DigitalOcean Gradient™ GPU Droplet
```bash
# Create an AI GPU Droplet for FirstPatch AI backend
doctl compute droplet create firstpatch-ai-node \
  --region nyc1 \
  --image ubuntu-24-04-x64 \
  --size so-2vcpu-16gb \
  --ssh-keys <YOUR_SSH_KEY_FINGERPRINT>
```

### 3. Deploy via DigitalOcean App Platform
FirstPatch AI is configured for 1-click deployment on DigitalOcean App Platform using Docker or the native Python/Node buildpacks:
```bash
# Deploy using app specification
doctl apps create --spec .do/app.yaml
```

---

## 4. Configuration

To enable DigitalOcean Gradient™ AI Agentic Cloud in FirstPatch AI, update your `.env` or system environment variables:

```ini
# FirstPatch AI - DigitalOcean Gradient Configuration
DO_GRADIENT_API_KEY=your_digitalocean_gradient_api_key_here
DO_GRADIENT_WORKSPACE_ID=your_gradient_workspace_id_here
AI_INFERENCE_PROVIDER=ollama   # options: 'ollama' (default) or 'digitalocean_gradient'
```
