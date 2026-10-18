import hashlib
import uuid
from typing import List, Dict, Any
from backend.app.services.ast_service import analyze_python_source, analyze_generic_source

def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def chunk_file_content(
    file_path: str,
    content: str,
    repository_id: str,
    commit_sha: str
) -> List[Dict[str, Any]]:
    chunks = []
    lines = content.split("\n")
    total_lines = len(lines)
    
    # 1. Python source chunking by AST symbols
    if file_path.endswith(".py"):
        analysis = analyze_python_source(content)
        # Class chunks
        for cls in analysis["classes"]:
            s_line = max(1, cls["line_start"])
            e_line = min(total_lines, cls["line_end"])
            chunk_text = "\n".join(lines[s_line - 1:e_line])
            chunks.append({
                "id": str(uuid.uuid4()),
                "repository_id": repository_id,
                "commit_sha": commit_sha,
                "file_path": file_path,
                "symbol_name": cls["name"],
                "chunk_type": "class",
                "start_line": s_line,
                "end_line": e_line,
                "content": chunk_text,
                "content_hash": compute_sha256(chunk_text)
            })

        # Function chunks (top-level or standalone)
        for fn in analysis["functions"]:
            s_line = max(1, fn["line_start"])
            e_line = min(total_lines, fn["line_end"])
            chunk_text = "\n".join(lines[s_line - 1:e_line])
            is_test = fn["name"].startswith("test_") or "test" in file_path.lower()
            chunks.append({
                "id": str(uuid.uuid4()),
                "repository_id": repository_id,
                "commit_sha": commit_sha,
                "file_path": file_path,
                "symbol_name": fn["name"],
                "chunk_type": "test" if is_test else "function",
                "start_line": s_line,
                "end_line": e_line,
                "content": chunk_text,
                "content_hash": compute_sha256(chunk_text)
            })

    # 2. Markdown files (README, CONTRIBUTING, docs)
    elif file_path.endswith(".md"):
        # Split by markdown headers
        current_header = "Documentation"
        current_lines = []
        start_line = 1
        
        for idx, line in enumerate(lines, start=1):
            if line.startswith("#"):
                if current_lines:
                    chunk_text = "\n".join(current_lines).strip()
                    if chunk_text:
                        chunks.append({
                            "id": str(uuid.uuid4()),
                            "repository_id": repository_id,
                            "commit_sha": commit_sha,
                            "file_path": file_path,
                            "symbol_name": current_header,
                            "chunk_type": "doc",
                            "start_line": start_line,
                            "end_line": idx - 1,
                            "content": chunk_text,
                            "content_hash": compute_sha256(chunk_text)
                        })
                current_header = line.lstrip("#").strip() or "Section"
                current_lines = [line]
                start_line = idx
            else:
                current_lines.append(line)
                
        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                chunks.append({
                    "id": str(uuid.uuid4()),
                    "repository_id": repository_id,
                    "commit_sha": commit_sha,
                    "file_path": file_path,
                    "symbol_name": current_header,
                    "chunk_type": "doc",
                    "start_line": start_line,
                    "end_line": total_lines,
                    "content": chunk_text,
                    "content_hash": compute_sha256(chunk_text)
                })

    # 3. Fallback or other code files (JS, TS, config, etc.)
    if not chunks and content.strip():
        # Windowed chunking (up to 50 lines per chunk)
        step = 50
        for i in range(0, total_lines, step):
            sub_lines = lines[i:i + step]
            chunk_text = "\n".join(sub_lines).strip()
            if chunk_text:
                chunks.append({
                    "id": str(uuid.uuid4()),
                    "repository_id": repository_id,
                    "commit_sha": commit_sha,
                    "file_path": file_path,
                    "symbol_name": file_path.split("/")[-1],
                    "chunk_type": "module",
                    "start_line": i + 1,
                    "end_line": min(total_lines, i + step),
                    "content": chunk_text,
                    "content_hash": compute_sha256(chunk_text)
                })

    return chunks
