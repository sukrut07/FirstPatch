import httpx
import json
from typing import Dict, Any, List, Optional
from backend.app.config import settings

class OllamaService:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip('/')

    async def get_status(self) -> Dict[str, Any]:
        """Check if Ollama is reachable and list installed models."""
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    
                    # Choose active model
                    active_model = settings.OLLAMA_MODEL
                    if active_model not in models:
                        # Fallback to any installed matching model
                        matching = [m for m in models if "gemma" in m or "qwen" in m]
                        if matching:
                            active_model = matching[0]
                        elif models:
                            active_model = models[0]
                        else:
                            active_model = settings.OLLAMA_MODEL

                    return {
                        "online": True,
                        "endpoint": self.base_url,
                        "installed_models": models,
                        "active_model": active_model,
                        "embed_model": settings.OLLAMA_EMBED_MODEL,
                        "has_embed_model": any(settings.OLLAMA_EMBED_MODEL in m for m in models)
                    }
                return {
                    "online": False,
                    "endpoint": self.base_url,
                    "error": f"Ollama HTTP {resp.status_code}",
                    "installed_models": [],
                    "active_model": settings.OLLAMA_MODEL
                }
        except Exception as e:
            return {
                "online": False,
                "endpoint": self.base_url,
                "error": f"Cannot connect to Ollama at {self.base_url}. Make sure Ollama is running (`ollama serve`).",
                "installed_models": [],
                "active_model": settings.OLLAMA_MODEL
            }

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        format_json: bool = False
    ) -> Dict[str, Any]:
        """Call Ollama to generate grounded text or JSON."""
        status = await self.get_status()
        if not status["online"]:
            raise RuntimeError(f"Ollama is offline: {status.get('error')}")

        use_model = model or status["active_model"]

        default_system = (
            "You are FirstPatch AI, a grounded open-source developer mentor. "
            "You MUST adhere strictly to the provided repository evidence and code snippets. "
            "Always include exact file paths and line ranges for technical claims. "
            "Distinguish verified facts from assumptions. If evidence is missing, state it honestly."
        )

        payload = {
            "model": use_model,
            "system": system_prompt or default_system,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": settings.MODEL_CONTEXT_TOKENS,
                "num_predict": settings.MODEL_OUTPUT_TOKENS
            }
        }
        if format_json:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama generation failed ({resp.status_code}): {resp.text}")
            result = resp.json()
            return {
                "model": use_model,
                "response": result.get("response", ""),
                "total_duration": result.get("total_duration", 0),
                "eval_count": result.get("eval_count", 0)
            }

    async def get_embedding(self, text: str, model: Optional[str] = None) -> Optional[List[float]]:
        """Get vector embedding for a piece of text using Ollama."""
        use_model = model or settings.OLLAMA_EMBED_MODEL
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": use_model, "prompt": text[:2000]}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("embedding")
        except Exception:
            pass
        return None

ollama_service = OllamaService()
