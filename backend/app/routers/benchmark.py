from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from backend.app.services.benchmark_service import benchmark_service
from backend.app.services.ollama_service import ollama_service

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])

@router.post("/run")
async def run_benchmark(model: Optional[str] = Query(None, description="Optional model tag to benchmark")):
    """Run standardized LLM benchmarks measuring latency, throughput, and accuracy."""
    try:
        report = await benchmark_service.run_model_benchmark(model_name=model)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compare")
async def compare_installed_models():
    """Run benchmarks across all currently installed models in Ollama and compare performance."""
    status = await ollama_service.get_status()
    if not status.get("online"):
        raise HTTPException(status_code=503, detail="Ollama is currently offline")
    
    models = status.get("installed_models", [])
    chat_models = [m for m in models if "embed" not in m]
    
    comparison = []
    for model_name in chat_models:
        report = await benchmark_service.run_model_benchmark(model_name=model_name)
        comparison.append({
            "model": model_name,
            "pass_rate_percent": report["pass_rate_percent"],
            "average_tokens_per_sec": report["average_tokens_per_sec"],
            "total_eval_duration_sec": report["total_eval_duration_sec"],
            "total_tokens": report["total_tokens_generated"]
        })
        
    return {
        "models_benchmarked": len(comparison),
        "comparison": comparison
    }
