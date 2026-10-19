import os
import re
import httpx
import json
from typing import Dict, Any, List, Optional
from backend.app.config import settings

class CloudLLMService:
    """
    Cloud LLM service supporting custom user-supplied API keys for repository Q&A and deep analysis.
    Supports:
      - Google AI Studio / Gemini API (Gemma 4: gemma-4-31b-it, gemma-4-26b, etc.)
      - OpenRouter (google/gemma-4-...)
      - OpenAI (sk-...)
      - DigitalOcean Gradient™ AI Agentic Cloud
      - Groq (gsk_...)
      - Anthropic (sk-ant-...)
      - OpenAI-compatible endpoints
    """

    def resolve_provider(self, api_key: Optional[str], provider: Optional[str] = None) -> str:
        if provider:
            p = provider.lower().strip()
            if "google" in p or "studio" in p or "gemma" in p:
                return "google_ai_studio"
            if "openrouter" in p:
                return "openrouter"
            if "gradient" in p or "digitalocean" in p:
                return "gradient"
            if "anthropic" in p or "claude" in p:
                return "anthropic"
            if "groq" in p:
                return "groq"
            return "openai"

        if not api_key:
            if getattr(settings, "GEMMA_API_KEY", None) or getattr(settings, "GOOGLE_AI_API_KEY", None):
                return "google_ai_studio"
            if getattr(settings, "DO_GRADIENT_API_KEY", None):
                return "gradient"
            return "openai"

        key = api_key.strip()
        if key.startswith("AIza"):
            return "google_ai_studio"
        if key.startswith("sk-or-"):
            return "openrouter"
        if key.startswith("sk-ant-"):
            return "anthropic"
        if key.startswith("gsk_"):
            return "groq"
        if key.startswith("grad_"):
            return "gradient"
        return "openai"

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Generate answer via cloud API key with repository grounded evidence.
        """
        key = (
            api_key or
            getattr(settings, "GEMMA_API_KEY", None) or
            getattr(settings, "GOOGLE_AI_API_KEY", None) or
            getattr(settings, "DO_GRADIENT_API_KEY", None) or
            os.getenv("OPENAI_API_KEY", "")
        )
        if not key:
            raise ValueError(
                "No API key provided. Supply a Gemma/Google AI/OpenAI API key in request or configure GEMMA_API_KEY / DO_GRADIENT_API_KEY."
            )

        detected_provider = self.resolve_provider(key, provider)

        if detected_provider == "google_ai_studio":
            return await self._call_google_ai_studio(prompt, system_prompt, key, model, temperature)
        elif detected_provider == "openrouter":
            return await self._call_openai_compatible(
                endpoint="https://openrouter.ai/api/v1/chat/completions",
                prompt=prompt,
                system_prompt=system_prompt,
                api_key=key,
                model=model or "google/gemma-4-31b-it",
                provider_name="OpenRouter (Gemma 4)",
                temperature=temperature
            )
        elif detected_provider == "anthropic":
            return await self._call_anthropic(prompt, system_prompt, key, model, temperature)
        elif detected_provider == "gradient":
            return await self._call_gradient(prompt, system_prompt, key, model, temperature)
        elif detected_provider == "groq":
            return await self._call_groq(prompt, system_prompt, key, model, temperature)
        else:
            return await self._call_openai_compatible(
                endpoint="https://api.openai.com/v1/chat/completions",
                prompt=prompt,
                system_prompt=system_prompt,
                api_key=key,
                model=model or "gpt-4o-mini",
                provider_name="OpenAI",
                temperature=temperature
            )

    async def _call_google_ai_studio(
        self,
        prompt: str,
        system_prompt: Optional[str],
        api_key: str,
        model: Optional[str],
        temperature: float
    ) -> Dict[str, Any]:
        target_model = model or getattr(settings, "GEMMA_MODEL", "gemma-4-31b-it")
        clean_model = target_model.replace("models/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key.strip()
        }

        full_prompt = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER QUERY / REPO CONTEXT:\n{prompt}" if system_prompt else prompt
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": full_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2048
            }
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Google AI Studio (Gemma) API returned status {resp.status_code}: {resp.text[:250]}")
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("No candidates returned from Google AI Studio")
            content_parts = candidates[0].get("content", {}).get("parts", [{}])
            text = content_parts[0].get("text", "") if content_parts else ""
            usage = data.get("usageMetadata", {})
            return {
                "response": text,
                "provider": "Google AI Studio (Gemma 4)",
                "model": clean_model,
                "usage": usage,
                "success": True
            }

    async def _call_openai_compatible(
        self,
        endpoint: str,
        prompt: str,
        system_prompt: Optional[str],
        api_key: str,
        model: str,
        provider_name: str,
        temperature: float = 0.1,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        if extra_headers:
            headers.update(extra_headers)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1500
        }

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"{provider_name} API returned status {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return {
                "response": content,
                "provider": provider_name,
                "model": model,
                "usage": usage,
                "success": True
            }

    async def _call_gradient(
        self,
        prompt: str,
        system_prompt: Optional[str],
        api_key: str,
        model: Optional[str],
        temperature: float
    ) -> Dict[str, Any]:
        workspace_id = getattr(settings, "DO_GRADIENT_WORKSPACE_ID", "") or os.getenv("DO_GRADIENT_WORKSPACE_ID", "")
        headers = {}
        if workspace_id:
            headers["x-gradient-workspace-id"] = workspace_id
        return await self._call_openai_compatible(
            endpoint="https://api.gradient.ai/v1/chat/completions",
            prompt=prompt,
            system_prompt=system_prompt,
            api_key=api_key,
            model=model or "gemma2-9b",
            provider_name="DigitalOcean Gradient™ AI Agentic Cloud",
            temperature=temperature,
            extra_headers=headers
        )

    async def _call_groq(
        self,
        prompt: str,
        system_prompt: Optional[str],
        api_key: str,
        model: Optional[str],
        temperature: float
    ) -> Dict[str, Any]:
        return await self._call_openai_compatible(
            endpoint="https://api.groq.com/openai/v1/chat/completions",
            prompt=prompt,
            system_prompt=system_prompt,
            api_key=api_key,
            model=model or "llama-3.1-8b-instant",
            provider_name="Groq Fast Inference",
            temperature=temperature
        )

    async def _call_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        api_key: str,
        model: Optional[str],
        temperature: float
    ) -> Dict[str, Any]:
        headers = {
            "x-api-key": api_key.strip(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": model or "claude-3-5-sonnet-20241022",
            "max_tokens": 1500,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Anthropic API returned status {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            content = data["content"][0]["text"]
            return {
                "response": content,
                "provider": "Anthropic Claude",
                "model": model or "claude-3-5-sonnet-20241022",
                "usage": data.get("usage", {}),
                "success": True
            }

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract and safely parse JSON from raw model generation."""
        cleaned = text.strip()
        # Check fenced blocks
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except Exception:
                pass
        # Check direct parse
        try:
            return json.loads(cleaned)
        except Exception:
            pass
        # Check substring { ... }
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start:end+1])
            except Exception:
                pass
        return None

    def _generate_deterministic_analysis(
        self,
        repo_metadata: Dict[str, Any],
        file_tree: List[Dict[str, Any]],
        ast_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Provides high-quality deterministic fallback analysis if all AI providers are offline."""
        lang = repo_metadata.get("language") or "Python"
        name = repo_metadata.get("name", "Repository")
        files = [f.get("path", "") for f in file_tree]

        entrypoints = [f for f in files if any(e in f.lower() for e in ["main.py", "app.py", "index.ts", "index.js", "cli.py"])]
        if not entrypoints:
            entrypoints = [files[0]] if files else ["src/main.py"]

        test_files = [f for f in files if "test" in f.lower()]
        doc_files = [f for f in files if any(d in f.lower() for d in ["readme", "contributing", "docs", "license"])]

        return {
            "executive_summary": f"{name} is an open-source {lang} project structured for modular extensibility with {len(files)} discovered files.",
            "architecture_pattern": "Modular Package / Service Architecture",
            "primary_language": lang,
            "entrypoints": [{"path": ep, "role": "Primary execution and router initialization"} for ep in entrypoints[:3]],
            "key_components": [
                {"name": "Core Service Layer", "path": entrypoints[0], "role": "Coordinates domain logic and application workflows", "importance": "high"},
                {"name": "Test Suite", "path": test_files[0] if test_files else "tests/", "role": "Regression safety and behavior validation", "importance": "high"}
            ],
            "beginner_friendly_areas": [
                {
                    "area": "Documentation & Typings",
                    "why": "Clear scope, zero execution side-effects, fast pull request review.",
                    "recommended_files": doc_files[:3] if doc_files else ["README.md"]
                },
                {
                    "area": "Unit Test Coverage",
                    "why": "Existing tests provide clear patterns to reproduce; low risk of breaking core runtime.",
                    "recommended_files": test_files[:3] if test_files else ["tests/"]
                }
            ],
            "high_risk_areas": [
                {
                    "area": "Core Engine & State Machine",
                    "reason": "Direct impact on all downstream callers; strict review standards.",
                    "files": entrypoints[:2]
                }
            ],
            "contribution_quickstart": {
                "prerequisites": [f"{lang} runtime environment", "git"],
                "setup_command": "pip install -r requirements.txt" if lang == "Python" else "npm install",
                "test_command": "pytest tests/ -v" if lang == "Python" else "npm test",
                "lint_command": "flake8" if lang == "Python" else "npm run lint"
            },
            "architectural_pitfalls": [
                "Modifying global state across module boundaries.",
                "Submitting changes without corresponding unit test coverage."
            ],
            "suggested_first_issues": [
                "Add type annotations to utility helpers.",
                "Expand edge case test coverage in the test suite.",
                "Improve error messaging in entrypoint argument parsing."
            ],
            "model_used": "Deterministic Grounded Fallback",
            "provider_used": "Grounded Reality Checker"
        }

    async def gemma_analyze_repository(
        self,
        repo_metadata: Dict[str, Any],
        file_tree: List[Dict[str, Any]],
        key_files: Dict[str, str],
        ast_summary: Dict[str, Any],
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a comprehensive Gemma 4 deep architectural analysis over a repository.
        Falls back to local Ollama (gemma4:e2b) or deterministic grounded synthesis.
        """
        from backend.app.services.ollama_service import ollama_service

        system_prompt = (
            "You are Gemma 4, a world-class AI open-source mentor and principal software architect. "
            "Analyze the provided repository manifest, file tree, key files, and AST symbol tables. "
            "Your output must be a single, strict, valid JSON object with these keys:\n"
            "{\n"
            '  "executive_summary": "Thorough 2-3 sentence overview explaining what this software does and its architectural philosophy.",\n'
            '  "architecture_pattern": "Specific architectural pattern (e.g., Layered Hexagonal, Asynchronous Event-Driven, Modular Plugin Pipeline)",\n'
            '  "primary_language": "Main programming language and runtime ecosystem",\n'
            '  "entrypoints": [{"path": "file_path", "role": "What starts or routes execution here"}],\n'
            '  "key_components": [{"name": "component_name", "path": "file_path", "role": "Brief responsibility", "importance": "high|medium|low"}],\n'
            '  "beginner_friendly_areas": [{"area": "Module/directory name", "why": "Why it is approachable for first-timers", "recommended_files": ["file1", "file2"]}],\n'
            '  "high_risk_areas": [{"area": "Critical subsystem", "reason": "Why caution is needed", "files": ["file1"]}],\n'
            '  "contribution_quickstart": {\n'
            '    "prerequisites": ["Required tools/runtimes"],\n'
            '    "setup_command": "Command to install dependencies",\n'
            '    "test_command": "Command to run local test suite",\n'
            '    "lint_command": "Command to run linters/formatters"\n'
            '  },\n'
            '  "architectural_pitfalls": ["Common mistake 1", "Common mistake 2"],\n'
            '  "suggested_first_issues": ["Idea for a good first patch 1", "Idea for a good first patch 2"]\n'
            "}\n"
            "CRITICAL: Output ONLY valid JSON. No conversational wrapper or markdown backticks outside the JSON."
        )

        file_tree_snippet = [f.get("path", "") for f in file_tree[:40]]
        key_files_snippets = {}
        for fpath, content in list(key_files.items())[:6]:
            key_files_snippets[fpath] = content[:1500]

        user_prompt = (
            f"REPOSITORY: {repo_metadata.get('full_name', repo_metadata.get('name', 'Repository'))}\n"
            f"DESCRIPTION: {repo_metadata.get('description', '')}\n"
            f"PRIMARY LANGUAGE: {repo_metadata.get('language', 'Unknown')}\n"
            f"TOTAL FILES: {len(file_tree)}\n\n"
            f"FILE MANIFEST (first 40 files):\n{json.dumps(file_tree_snippet, indent=2)}\n\n"
            f"KEY FILES SNIPPETS:\n{json.dumps(key_files_snippets, indent=2)}\n\n"
            f"AST SYMBOL SUMMARY:\n{json.dumps(ast_summary, indent=2)}\n\n"
            "Now produce the complete Gemma 4 architectural analysis JSON."
        )

        chosen_key = (
            api_key or
            getattr(settings, "GEMMA_API_KEY", None) or
            getattr(settings, "GOOGLE_AI_API_KEY", None) or
            getattr(settings, "DO_GRADIENT_API_KEY", None)
        )

        # 1. Try Cloud Gemma 4 if key provided
        if chosen_key:
            try:
                res = await self.generate_response(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    api_key=chosen_key,
                    provider=provider or getattr(settings, "GEMMA_PROVIDER", "google_ai_studio"),
                    model=model or getattr(settings, "GEMMA_MODEL", "gemma-4-31b-it"),
                    temperature=0.2
                )
                parsed = self._extract_json(res["response"])
                if parsed:
                    parsed["model_used"] = res.get("model", "gemma-4-31b-it")
                    parsed["provider_used"] = res.get("provider", "Google AI Studio (Gemma 4)")
                    return parsed
            except Exception:
                pass

        # 2. Try Local Ollama Gemma 4
        ollama_status = await ollama_service.get_status()
        if ollama_status.get("online"):
            try:
                ollama_res = await ollama_service.generate_response(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    model=model or getattr(settings, "OLLAMA_MODEL", "gemma4:e2b"),
                    temperature=0.2
                )
                parsed = self._extract_json(ollama_res["response"])
                if parsed:
                    parsed["model_used"] = ollama_res.get("model", "gemma4:e2b (local)")
                    parsed["provider_used"] = "Ollama Local Inference"
                    return parsed
            except Exception:
                pass

        # 3. Deterministic Grounded Synthesis Fallback
        return self._generate_deterministic_analysis(repo_metadata, file_tree, ast_summary)

cloud_llm_service = CloudLLMService()
