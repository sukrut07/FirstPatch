from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.app.services.retrieval_service import retrieval_service
from backend.app.database import get_db

router = APIRouter(tags=["Retrieval & Evidence"])

class SearchRequest(BaseModel):
    repository_id: str
    query: str
    limit: Optional[int] = 10

@router.post("/api/retrieval/search")
async def search_chunks(req: SearchRequest):
    results = await retrieval_service.search_hybrid(req.repository_id, req.query, limit=req.limit or 10)
    return {
        "repository_id": req.repository_id,
        "query": req.query,
        "total_results": len(results),
        "results": results
    }

@router.get("/api/evidence/{evidence_id}")
async def get_evidence(evidence_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence_records WHERE id = ?", (evidence_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Evidence record not found.")
        return dict(row)

@router.get("/api/repositories/{owner}/{repo}/evidence")
async def list_repo_evidence(owner: str, repo: str):
    repo_id = f"{owner}/{repo}"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM evidence_records
        WHERE repository_id = ?
        ORDER BY created_at DESC
        LIMIT 50
        """, (repo_id,))
        return [dict(r) for r in cursor.fetchall()]
