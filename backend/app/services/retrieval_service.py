import math
import uuid
from typing import List, Dict, Any, Optional, Tuple
from backend.app.database import get_db, get_iso_now
from backend.app.config import settings
from backend.app.services.ollama_service import ollama_service

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

class HybridRetrievalService:
    def __init__(self):
        pass

    def search_lexical(
        self,
        repository_id: str,
        query: str,
        limit: int = 15
    ) -> List[Dict[str, Any]]:
        results = []
        clean_query = "".join(c for c in query if c.isalnum() or c.isspace()).strip()
        if not clean_query:
            return []

        with get_db() as conn:
            cursor = conn.cursor()
            # 1. Try SQLite FTS5 search
            try:
                # Format FTS5 query tokens
                tokens = clean_query.split()[:5]
                fts_expr = " OR ".join(f'"{t}"*' for t in tokens)
                cursor.execute("""
                SELECT c.id, c.repository_id, c.commit_sha, c.file_path, c.symbol_name,
                       c.chunk_type, c.start_line, c.end_line, c.content, c.content_hash,
                       rank
                FROM code_chunks_fts f
                JOIN code_chunks c ON f.chunk_id = c.id
                WHERE f.repository_id = ? AND code_chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """, (repository_id, fts_expr, limit))
                rows = cursor.fetchall()
                for row in rows:
                    results.append(dict(row))
            except Exception:
                # 2. Fallback to SQL LIKE search
                like_pattern = f"%{clean_query[:30]}%"
                cursor.execute("""
                SELECT id, repository_id, commit_sha, file_path, symbol_name,
                       chunk_type, start_line, end_line, content, content_hash
                FROM code_chunks
                WHERE repository_id = ? AND (content LIKE ? OR file_path LIKE ? OR symbol_name LIKE ?)
                LIMIT ?
                """, (repository_id, like_pattern, like_pattern, like_pattern, limit))
                for row in cursor.fetchall():
                    results.append(dict(row))

        return results

    async def search_hybrid(
        self,
        repository_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        # Lexical candidates
        lexical_hits = self.search_lexical(repository_id, query, limit=limit * 2)

        # Build stable GitHub links and attach score
        scored_results = []
        for rank, hit in enumerate(lexical_hits):
            # Reciprocal Rank Fusion base score
            rrf_score = 1.0 / (60 + rank)
            
            # Boost test files if query contains 'test'
            if "test" in query.lower() and hit.get("chunk_type") == "test":
                rrf_score *= 1.3
            # Boost symbol matches
            if hit.get("symbol_name") and hit.get("symbol_name").lower() in query.lower():
                rrf_score *= 1.5

            commit_sha = hit.get("commit_sha") or "main"
            file_path = hit.get("file_path", "")
            s_line = hit.get("start_line", 1)
            e_line = hit.get("end_line", s_line)
            source_url = f"https://github.com/{repository_id}/blob/{commit_sha}/{file_path}#L{s_line}-L{e_line}"

            scored_results.append({
                **hit,
                "score": rrf_score,
                "source_url": source_url
            })

        # Sort by final score
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:limit]

    def build_grounded_context(
        self,
        chunks: List[Dict[str, Any]],
        max_chars: int = 18000
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Assembles evidence payload and records citations."""
        evidence_records = []
        context_parts = []
        current_len = 0

        for chunk in chunks:
            text = (
                f"--- FILE: {chunk['file_path']} (Lines {chunk['start_line']}-{chunk['end_line']}) "
                f"[Symbol: {chunk.get('symbol_name') or 'N/A'}] ---\n"
                f"{chunk['content']}\n"
            )
            if current_len + len(text) > max_chars:
                break

            context_parts.append(text)
            current_len += len(text)

            evidence_records.append({
                "id": str(uuid.uuid4()),
                "repository_id": chunk["repository_id"],
                "commit_sha": chunk.get("commit_sha", ""),
                "file_path": chunk["file_path"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "symbol_name": chunk.get("symbol_name"),
                "chunk_type": chunk.get("chunk_type"),
                "content_hash": chunk.get("content_hash"),
                "source_url": chunk.get("source_url", ""),
                "snippet": chunk["content"][:300],
                "status": "verified"
            })

        context_str = "\n".join(context_parts)
        return context_str, evidence_records

retrieval_service = HybridRetrievalService()
