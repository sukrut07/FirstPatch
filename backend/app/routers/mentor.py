import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.app.services.mentor_service import mentor_service
from backend.app.services.ollama_service import ollama_service
from backend.app.services.cloud_llm_service import cloud_llm_service
from backend.app.services.retrieval_service import retrieval_service

router = APIRouter(prefix="/api/mentor", tags=["AI Mentor"])

class AskMentorRequest(BaseModel):
    repository_id: str
    question: str
    mode: Optional[str] = "learn"  # "learn" or "copilot"
    conversation_id: Optional[str] = None
    skill_level: Optional[str] = "Beginner"
    api_key: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None

class ExplainCodeRequest(BaseModel):
    repository_id: str
    file_path: str
    start_line: Optional[int] = 1
    end_line: Optional[int] = 50
    code_snippet: str
    api_key: Optional[str] = None
    provider: Optional[str] = None

class PlanContributionRequest(BaseModel):
    repository_id: str
    issue_id: Optional[str] = None
    issue_title: str
    issue_description: str
    api_key: Optional[str] = None
    provider: Optional[str] = None

@router.post("/ask")
async def ask_mentor(req: AskMentorRequest):
    result = await mentor_service.ask_question(
        repository_id=req.repository_id,
        question=req.question,
        mode=req.mode or "learn",
        conversation_id=req.conversation_id,
        skill_level=req.skill_level or "Beginner",
        api_key=req.api_key,
        provider=req.provider,
        model=req.model
    )
    return result

@router.post("/explain-code")
async def explain_code(req: ExplainCodeRequest):
    prompt = (
        f"Explain this code snippet from file `{req.file_path}` (Lines {req.start_line}-{req.end_line}):\n\n"
        f"```\n{req.code_snippet[:4000]}\n```\n\n"
        "Provide:\n"
        "1. High-level summary of what this code accomplishes.\n"
        "2. Step-by-step walkthrough of the key logic.\n"
        "3. Any edge cases or potential failure modes to consider."
    )
    explanation = None
    if req.api_key:
        try:
            cloud_res = await cloud_llm_service.generate_response(
                prompt=prompt,
                api_key=req.api_key,
                provider=req.provider,
                temperature=0.1
            )
            explanation = cloud_res["response"]
        except Exception:
            pass

    if not explanation:
        ollama_status = await ollama_service.get_status()
        if ollama_status["online"]:
            try:
                res = await ollama_service.generate_response(prompt=prompt, temperature=0.1)
                explanation = res["response"]
            except Exception:
                explanation = f"Code in `{req.file_path}` ({req.start_line}-{req.end_line}) defines functional logic for this module."
        else:
            explanation = (
                f"### 📍 Code Analysis for `{req.file_path}` (Lines {req.start_line}-{req.end_line})\n"
                f"- Defines core logic and interface boundaries.\n"
                f"- Connect local Ollama (`ollama serve`) or provide an API Key for full interactive architectural explanations."
            )

    return {
        "file_path": req.file_path,
        "start_line": req.start_line,
        "end_line": req.end_line,
        "explanation": explanation
    }

@router.post("/plan-contribution")
async def plan_contribution(req: PlanContributionRequest):
    # Retrieve relevant code chunks for the issue
    chunks = await retrieval_service.search_hybrid(req.repository_id, f"{req.issue_title} {req.issue_description}", limit=6)
    context_str, evidence = retrieval_service.build_grounded_context(chunks)

    prompt = f"""[ISSUE TITLE]
{req.issue_title}

[ISSUE DESCRIPTION]
{req.issue_description}

[REPOSITORY EVIDENCE]
{context_str}

[TASK]
Generate a grounded step-by-step contribution plan. Return valid JSON with this schema:
{{
  "understanding": "Core reason behind the issue grounded in repository evidence",
  "files_to_modify": ["src/config.py"],
  "learning_gaps": ["Relevant concept to learn first"],
  "step_by_step_plan": [
    {{"title": "Step 1", "description": "...", "expected_result": "..."}},
    {{"title": "Step 2", "description": "...", "expected_result": "..."}}
  ],
  "verification_strategy": "pytest tests/test_config.py",
  "definition_of_done": "All tests pass without regression and PR checklist fulfilled."
}}
"""
    plan_data = None
    if req.api_key:
        try:
            cloud_res = await cloud_llm_service.generate_response(
                prompt=prompt,
                system_prompt="You are FirstPatch AI. Return strictly valid JSON adhering to the requested schema.",
                api_key=req.api_key,
                provider=req.provider,
                temperature=0.1
            )
            raw = cloud_res["response"].strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            plan_data = json.loads(raw)
        except Exception:
            pass

    if not plan_data:
        ollama_status = await ollama_service.get_status()
        if ollama_status["online"]:
            try:
                res = await ollama_service.generate_response(
                    prompt=prompt,
                    format_json=True,
                    temperature=0.1
                )
                plan_data = json.loads(res["response"])
            except Exception:
                pass

    if not plan_data:
        # High quality deterministic template
        files_suggested = [c["file_path"] for c in chunks[:3]] if chunks else ["src/main.py", "tests/test_main.py"]
        plan_data = {
            "understanding": f"Issue '{req.issue_title}' touches core repository behaviors. Grounded in {len(chunks)} indexed files.",
            "files_to_modify": files_suggested,
            "learning_gaps": ["Git feature branch workflow", "Local test suite runner (pytest/npm)"],
            "step_by_step_plan": [
                {
                    "title": "1. Understand Problem & Trace Relevant Function",
                    "description": f"Inspect {files_suggested[0] if files_suggested else 'source files'} to locate where the issue occurs.",
                    "expected_result": "Exact function and line numbers pinpointed."
                },
                {
                    "title": "2. Reproduce Locally Before Fixing",
                    "description": "Run the existing test suite or reproduce the reported error in a local environment.",
                    "expected_result": "Reproduce expected error or failing assertion."
                },
                {
                    "title": "3. Implement Scoped Solution",
                    "description": "Apply minimal, clean changes following the project's coding conventions.",
                    "expected_result": "Fix implemented without modifying unrelated files."
                },
                {
                    "title": "4. Verify with Automated Tests",
                    "description": "Execute local unit tests to ensure no regressions were introduced.",
                    "expected_result": "All existing and new unit tests pass with exit code 0."
                }
            ],
            "verification_strategy": "Run unit test suite locally before creating pull request.",
            "definition_of_done": "Code addresses issue, passes tests, follows project guidelines, and has a clear PR description."
        }

    return {
        "repository_id": req.repository_id,
        "issue_id": req.issue_id,
        "plan": plan_data,
        "evidence": evidence
    }
