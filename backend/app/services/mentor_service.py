import uuid
import json
from typing import Dict, Any, List, Optional
from backend.app.services.ollama_service import ollama_service
from backend.app.services.retrieval_service import retrieval_service
from backend.app.database import get_db, get_iso_now

class MentorService:
    def __init__(self):
        pass

    async def ask_question(
        self,
        repository_id: str,
        question: str,
        mode: str = "learn",  # "learn" or "copilot"
        conversation_id: Optional[str] = None,
        skill_level: str = "Beginner"
    ) -> Dict[str, Any]:
        # 1. Retrieve grounded code evidence
        chunks = await retrieval_service.search_hybrid(repository_id, question, limit=8)
        context_str, evidence_records = retrieval_service.build_grounded_context(chunks)

        # 2. Persist evidence records to database
        with get_db() as conn:
            cursor = conn.cursor()
            for ev in evidence_records:
                cursor.execute("""
                INSERT OR IGNORE INTO evidence_records (
                    id, repository_id, commit_sha, file_path, start_line, end_line,
                    symbol_name, chunk_type, content_hash, source_url, snippet, claim, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ev["id"], ev["repository_id"], ev["commit_sha"], ev["file_path"],
                    ev["start_line"], ev["end_line"], ev["symbol_name"], ev["chunk_type"],
                    ev["content_hash"], ev["source_url"], ev["snippet"], question, "verified", get_iso_now()
                ))

        # 3. System prompt based on mode
        if mode == "learn":
            system_prompt = (
                f"You are FirstPatch AI in LEARN MODE, mentoring a {skill_level} open-source contributor. "
                "Structure your response in markdown with these clear sections:\n"
                "### 1. 💡 Conceptual Overview\n(Explain what the code does in plain language)\n"
                "### 2. 🔍 Code Walkthrough & Line Citations\n(Reference exact files, line numbers, and functions based strictly on the provided Context)\n"
                "### 3. 🧠 Key Prerequisite Concepts\n(Explain any framework patterns or language idioms needed)\n"
                "### 4. 🎯 Quick Knowledge Check\n(A small 1-question exercise to verify understanding before writing code)\n"
                "RULES: Ground all statements in the context. Never invent unverified functions or filenames."
            )
        else:
            system_prompt = (
                f"You are FirstPatch AI in COPILOT MODE, assisting an engineer with precision repository tasks. "
                "Structure your response with:\n"
                "### 1. 🎯 Direct Answer & Targeted Architecture\n"
                "### 2. 📂 Relevant Files & Line Locations\n"
                "### 3. 🛠️ Actionable Patch / Suggestion\n"
                "### 4. 🧪 Verification & Test Commands\n"
                "RULES: Always provide exact file paths, line numbers, and commands. State unknowns explicitly."
            )

        prompt = (
            f"=== VERIFIED REPOSITORY EVIDENCE ===\n"
            f"{context_str if context_str else 'No direct code chunk matches found. Reason strictly on repository structure.'}\n\n"
            f"=== CONTRIBUTOR QUESTION ===\n"
            f"{question}\n"
        )

        # 4. Generate answer with local AI or fallback
        ollama_status = await ollama_service.get_status()
        if ollama_status["online"]:
            try:
                gen_result = await ollama_service.generate_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=0.1
                )
                answer = gen_result["response"]
                model_used = gen_result["model"]
            except Exception as e:
                answer = self._generate_offline_answer(question, chunks, mode, str(e))
                model_used = "deterministic-fallback"
        else:
            answer = self._generate_offline_answer(question, chunks, mode, ollama_status.get("error"))
            model_used = "offline-fallback"

        # 5. Persist message in conversation
        conv_id = conversation_id or str(uuid.uuid4())
        msg_id = str(uuid.uuid4())
        now = get_iso_now()

        with get_db() as conn:
            cursor = conn.cursor()
            # Ensure conversation exists
            cursor.execute("""
            INSERT OR IGNORE INTO conversations (id, repository_id, mode, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (conv_id, repository_id, mode, question[:40], now, now))
            
            # Save user message
            cursor.execute("""
            INSERT INTO messages (id, conversation_id, role, content, citations, evidence_ids, mode, created_at)
            VALUES (?, ?, 'user', ?, '', '', ?, ?)
            """, (str(uuid.uuid4()), conv_id, question, mode, now))

            # Save assistant message
            ev_ids = json.dumps([e["id"] for e in evidence_records])
            citations = json.dumps([
                {"file": e["file_path"], "lines": f"L{e['start_line']}-L{e['end_line']}", "url": e["source_url"]}
                for e in evidence_records
            ])
            cursor.execute("""
            INSERT INTO messages (id, conversation_id, role, content, citations, evidence_ids, mode, created_at)
            VALUES (?, ?, 'assistant', ?, ?, ?, ?, ?)
            """, (msg_id, conv_id, answer, citations, ev_ids, mode, now))

        return {
            "conversation_id": conv_id,
            "message_id": msg_id,
            "answer": answer,
            "mode": mode,
            "model_used": model_used,
            "evidence": evidence_records,
            "offline_mode": not ollama_status["online"]
        }

    def _generate_offline_answer(self, question: str, chunks: List[Dict[str, Any]], mode: str, note: Optional[str] = None) -> str:
        """Deterministic fallback explanation when Ollama is offline or warming up."""
        citations = []
        for c in chunks[:4]:
            citations.append(f"- **`{c['file_path']}`** (lines {c['start_line']}-{c['end_line']}) — *{c.get('symbol_name') or 'code block'}*")
        
        c_list = "\n".join(citations) if citations else "- *No direct matching files found in the indexed snapshot.*"

        return (
            f"### 📍 Grounded Repository Evidence\n"
            f"Here are the primary files and symbols matching your query (`{question}`):\n\n"
            f"{c_list}\n\n"
            f"> **Note:** Local model inference is currently offline ({note or 'Ollama unreachable'}). "
            f"Start Ollama locally (`ollama serve`) to activate full conversational mentoring.\n\n"
            f"### 💡 Next Steps:\n"
            f"1. Inspect the referenced files above in the **File Explorer** tab.\n"
            f"2. Follow the line markers to locate the function or class definition.\n"
            f"3. Check for corresponding test files in `tests/` before drafting any changes."
        )

mentor_service = MentorService()
