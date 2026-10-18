import time
import json
from typing import Dict, Any, List, Optional
from backend.app.services.ollama_service import ollama_service
from backend.app.config import settings

BENCHMARK_SUITE = [
    {
        "id": "ast_code_reasoning",
        "name": "AST Code Understanding & Citation",
        "prompt": """[CODE CONTEXT]
File: src/auth/token_validator.py
Lines: 15-32
Function: validate_session_token(token: str, max_age_seconds: int = 3600) -> bool
Docstring: Validates bearer token expiration and HMAC signature. Raises InvalidTokenError if malformed.

[QUESTION]
What arguments does `validate_session_token` accept, what is the default expiration, and which exception is raised when malformed?
State your answer directly citing the line coordinates.""",
        "expected_keywords": ["token", "max_age_seconds", "3600", "InvalidTokenError"]
    },
    {
        "id": "structured_plan_generation",
        "name": "Contribution Plan (Strict JSON)",
        "prompt": """[ISSUE #42]
Title: Flask app crashes with KeyError when SECRET_KEY is missing from environment
Description: When booting in production mode without SECRET_KEY set, Config.from_prefixed_env raises unhandled KeyError instead of ConfigError with helpful message.

[TASK]
Output a strictly valid JSON object with these keys:
{
  "root_cause": "concise explanation",
  "files_to_modify": ["src/flask/config.py"],
  "learning_gap": "name of Python exception concept to understand",
  "recommended_test": "pytest command to verify fix"
}""",
        "format_json": True,
        "expected_keys": ["root_cause", "files_to_modify", "learning_gap", "recommended_test"]
    },
    {
        "id": "security_diff_audit",
        "name": "PR Review Security & Diff Audit",
        "prompt": """[PROPOSED DIFF]
--- a/config/settings.py
+++ b/config/settings.py
@@ -10,3 +10,4 @@
+print("Loading auth configuration...")
+DEFAULT_DATABASE_AUTH_KEY = "dummy_auth_token_99881122"

[TASK]
Audit this diff for security and code quality risks. What is the critical issue and what is the code quality warning?""",
        "expected_keywords": ["auth", "secret", "print", "credential"]
    }
]

class BenchmarkService:
    def __init__(self):
        pass

    async def run_model_benchmark(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs the standard benchmark suite against the specified Ollama model.
        Measures latency, token throughput, schema compliance, and keyword grounding.
        """
        target_model = model_name or settings.OLLAMA_MODEL
        results = []
        total_eval_tokens = 0
        total_eval_duration_sec = 0.0

        for test in BENCHMARK_SUITE:
            start_time = time.perf_counter()
            try:
                gen_res = await ollama_service.generate_response(
                    prompt=test["prompt"],
                    model=target_model,
                    temperature=0.1,
                    format_json=test.get("format_json", False)
                )
                wall_time = time.perf_counter() - start_time
                response_text = gen_res.get("response", "")
                eval_count = gen_res.get("eval_count", 0)
                total_duration_ns = gen_res.get("total_duration", 0)
                duration_sec = total_duration_ns / 1e9 if total_duration_ns > 0 else wall_time

                total_eval_tokens += eval_count
                total_eval_duration_sec += duration_sec

                # Check keyword grounding or JSON structure
                passed_criteria = True
                details = {}

                if test.get("format_json"):
                    try:
                        parsed = json.loads(response_text)
                        missing_keys = [k for k in test["expected_keys"] if k not in parsed]
                        passed_criteria = len(missing_keys) == 0
                        details["json_valid"] = True
                        details["missing_keys"] = missing_keys
                    except Exception as e:
                        passed_criteria = False
                        details["json_valid"] = False
                        details["parse_error"] = str(e)
                else:
                    lower_resp = response_text.lower()
                    matched_keywords = [kw for kw in test["expected_keywords"] if kw.lower() in lower_resp]
                    passed_criteria = len(matched_keywords) >= len(test["expected_keywords"]) // 2
                    details["matched_keywords"] = matched_keywords
                    details["expected_count"] = len(test["expected_keywords"])

                tokens_per_sec = (eval_count / duration_sec) if duration_sec > 0 else 0.0

                results.append({
                    "test_id": test["id"],
                    "test_name": test["name"],
                    "passed": passed_criteria,
                    "latency_sec": round(wall_time, 2),
                    "tokens_per_sec": round(tokens_per_sec, 1),
                    "eval_tokens": eval_count,
                    "details": details,
                    "sample_output": response_text[:200] + "..." if len(response_text) > 200 else response_text
                })

            except Exception as e:
                wall_time = time.perf_counter() - start_time
                results.append({
                    "test_id": test["id"],
                    "test_name": test["name"],
                    "passed": False,
                    "latency_sec": round(wall_time, 2),
                    "tokens_per_sec": 0.0,
                    "eval_tokens": 0,
                    "error": str(e)
                })

        avg_throughput = (total_eval_tokens / total_eval_duration_sec) if total_eval_duration_sec > 0 else 0.0
        passed_count = sum(1 for r in results if r.get("passed", False))

        return {
            "model": target_model,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tests_run": len(BENCHMARK_SUITE),
            "tests_passed": passed_count,
            "pass_rate_percent": round((passed_count / len(BENCHMARK_SUITE)) * 100, 1),
            "average_tokens_per_sec": round(avg_throughput, 1),
            "total_tokens_generated": total_eval_tokens,
            "total_eval_duration_sec": round(total_eval_duration_sec, 2),
            "results": results
        }

benchmark_service = BenchmarkService()
