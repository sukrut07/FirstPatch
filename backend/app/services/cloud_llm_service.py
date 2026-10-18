import os
import httpx
import json
from typing import Dict, Any, List, Optional
from backend.app.config import settings

class CloudLLMService:
    """
    Cloud LLM service supporting custom user-supplied API keys for repository Q&A.
    Supports:
      - OpenAI (sk-...)
      - DigitalOcean Gradient™ AI Agentic Cloud
      - Groq (gsk_...)
      - Anthropic (sk-ant-...)
      - OpenAI-compatible endpoints
    """

    def resolve_provider(self, api_key: Optional[str], provider: Optional[str] = None) -> str:
        if provider:
            p = provider.lower().strip()
            if "gradient" in p or "digitalocean" in p:
                return "gradient"
            if "anthropic" in p or "claude" in p:
                return "anthropic"
            if "groq" in p:
                return "groq"
            return "openai"

        if not api_key:
            if getattr(settings, "DO_GRADIENT_API_KEY", None):
                return "gradient"
            return "openai"

        key = api_key.strip()
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
        key = api_key or getattr(settings, "DO_GRADIENT_API_KEY", None) or os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise ValueError("No API key provided. Supply an API key in request or configure DO_GRADIENT_API_KEY/OPENAI_API_KEY.")

        detected_provider = self.resolve_provider(key, provider)

        if detected_provider == "anthropic":
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

cloud_llm_service = CloudLLMService()
