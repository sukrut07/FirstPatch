#!/usr/bin/env python3
"""
FirstPatch AI — Local LLM Benchmark Runner
Measures latency, token throughput, JSON schema compliance, and grounded accuracy.
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.services.benchmark_service import benchmark_service
from backend.app.services.ollama_service import ollama_service

async def main():
    parser = argparse.ArgumentParser(description="FirstPatch AI Local LLM Benchmark Suite")
    parser.add_argument("--model", type=str, default=None, help="Target Ollama model tag")
    parser.add_argument("--all", action="store_true", help="Benchmark all installed Ollama chat models")
    args = parser.parse_args()

    status = await ollama_service.get_status()
    if not status.get("online"):
        print("❌ Error: Ollama is offline. Make sure `ollama serve` is running.")
        sys.exit(1)

    models_to_test = []
    if args.all:
        models_to_test = [m for m in status.get("installed_models", []) if "embed" not in m]
    elif args.model:
        models_to_test = [args.model]
    else:
        models_to_test = [status.get("active_model", "gemma4:e2b")]

    print("\n" + "=" * 70)
    print("🚀 FirstPatch AI — Model Benchmark Execution")
    print(f"Ollama Endpoint: {status.get('endpoint')}")
    print(f"Target Models:   {', '.join(models_to_test)}")
    print("=" * 70 + "\n")

    for model_name in models_to_test:
        print(f"\n⚡ Benchmarking Model: {model_name}...")
        report = await benchmark_service.run_model_benchmark(model_name=model_name)

        print("-" * 70)
        print(f"Model: {report['model']} | Score: {report['tests_passed']}/{report['tests_run']} ({report['pass_rate_percent']}%) | Throughput: {report['average_tokens_per_sec']} tok/s")
        print("-" * 70)

        for res in report["results"]:
            status_icon = "✅" if res["passed"] else "❌"
            print(f"{status_icon} [{res['test_name']}]")
            print(f"   Latency: {res['latency_sec']}s | Speed: {res['tokens_per_sec']} tok/s | Tokens: {res['eval_tokens']}")
            if res.get("details"):
                print(f"   Details: {res['details']}")
            print()

    print("=" * 70)
    print("✨ Benchmark run complete.")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
