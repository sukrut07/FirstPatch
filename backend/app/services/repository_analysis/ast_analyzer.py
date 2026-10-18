"""
FirstPatch AI — AST and Code Structure Analyzer

Performs deterministic code inspection:
- Python AST extraction: classes, methods, functions, imports, decorators, line ranges
- Multi-language structural heuristics (JS/TS, Go, Rust) with honest limitation disclosures
- Generates verified EvidenceRef records with precise line numbers and file paths
"""
from __future__ import annotations

import ast
import logging
import re
from typing import Any, Optional
from uuid import uuid4

from app.schemas import EvidenceRef, EvidenceStatus, EvidenceType

logger = logging.getLogger(__name__)


class ASTFunctionInfo:
    def __init__(
        self,
        name: str,
        start_line: int,
        end_line: int,
        args: list[str],
        docstring: Optional[str] = None,
        is_async: bool = False,
        decorators: Optional[list[str]] = None,
        parent_class: Optional[str] = None,
    ):
        self.name = name
        self.start_line = start_line
        self.end_line = end_line
        self.args = args
        self.docstring = docstring
        self.is_async = is_async
        self.decorators = decorators or []
        self.parent_class = parent_class

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "args": self.args,
            "docstring": self.docstring,
            "is_async": self.is_async,
            "decorators": self.decorators,
            "parent_class": self.parent_class,
        }


class ASTClassInfo:
    def __init__(
        self,
        name: str,
        start_line: int,
        end_line: int,
        bases: list[str],
        docstring: Optional[str] = None,
        methods: Optional[list[str]] = None,
    ):
        self.name = name
        self.start_line = start_line
        self.end_line = end_line
        self.bases = bases
        self.docstring = docstring
        self.methods = methods or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "bases": self.bases,
            "docstring": self.docstring,
            "methods": self.methods,
        }


class ASTImportInfo:
    def __init__(
        self,
        module: str,
        names: list[str],
        start_line: int,
        is_from: bool = False,
    ):
        self.module = module
        self.names = names
        self.start_line = start_line
        self.is_from = is_from

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "names": self.names,
            "start_line": self.start_line,
            "is_from": self.is_from,
        }


class CodeStructureResult:
    """Represents analyzed code structure from a file."""

    def __init__(
        self,
        file_path: str,
        language: str,
        is_ast_parsed: bool,
        classes: list[ASTClassInfo],
        functions: list[ASTFunctionInfo],
        imports: list[ASTImportInfo],
        evidence_refs: list[EvidenceRef],
        warnings: list[str],
    ):
        self.file_path = file_path
        self.language = language
        self.is_ast_parsed = is_ast_parsed
        self.classes = classes
        self.functions = functions
        self.imports = imports
        self.evidence_refs = evidence_refs
        self.warnings = warnings

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "language": self.language,
            "is_ast_parsed": self.is_ast_parsed,
            "classes": [c.to_dict() for c in self.classes],
            "functions": [f.to_dict() for f in self.functions],
            "imports": [i.to_dict() for i in self.imports],
            "evidence_count": len(self.evidence_refs),
            "warnings": self.warnings,
        }


class CodeStructureAnalyzer:
    """
    Deterministic code analyzer using Python AST for Python files and
    regex heuristics for other languages.
    """

    def analyze_source(
        self,
        file_path: str,
        content: str,
        owner: str = "",
        repo: str = "",
        commit_sha: Optional[str] = None,
    ) -> CodeStructureResult:
        """
        Analyze code content. If Python, use AST. If other, use structured heuristics.
        """
        lower_path = file_path.lower()
        if lower_path.endswith(".py"):
            return self._analyze_python(file_path, content, owner, repo, commit_sha)
        elif lower_path.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs")):
            return self._analyze_javascript_typescript(file_path, content, owner, repo, commit_sha)
        elif lower_path.endswith(".go"):
            return self._analyze_go(file_path, content, owner, repo, commit_sha)
        elif lower_path.endswith(".rs"):
            return self._analyze_rust(file_path, content, owner, repo, commit_sha)
        else:
            return CodeStructureResult(
                file_path=file_path,
                language="unknown",
                is_ast_parsed=False,
                classes=[],
                functions=[],
                imports=[],
                evidence_refs=[],
                warnings=[f"AST / syntax parsing is not supported for file type: {file_path}"],
            )

    def _analyze_python(
        self,
        file_path: str,
        content: str,
        owner: str,
        repo: str,
        commit_sha: Optional[str],
    ) -> CodeStructureResult:
        classes: list[ASTClassInfo] = []
        functions: list[ASTFunctionInfo] = []
        imports: list[ASTImportInfo] = []
        evidence_refs: list[EvidenceRef] = []
        warnings: list[str] = []

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as exc:
            warnings.append(f"Python syntax error in {file_path} at line {exc.lineno}: {exc.msg}")
            return CodeStructureResult(
                file_path=file_path,
                language="python",
                is_ast_parsed=False,
                classes=[],
                functions=[],
                imports=[],
                evidence_refs=[],
                warnings=warnings,
            )

        for node in ast.walk(tree):
            # Imports
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
                import_info = ASTImportInfo(
                    module=", ".join(names),
                    names=names,
                    start_line=node.lineno,
                    is_from=False,
                )
                imports.append(import_info)
                evidence_refs.append(
                    EvidenceRef(
                        id=uuid4(),
                        owner=owner,
                        repo=repo,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        evidence_type=EvidenceType.AST_IMPORT,
                        excerpt=f"import {', '.join(names)}"[:500],
                        status=EvidenceStatus.VERIFIED,
                        confidence_note="Extracted via Python AST",
                    )
                )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                import_info = ASTImportInfo(
                    module=module,
                    names=names,
                    start_line=node.lineno,
                    is_from=True,
                )
                imports.append(import_info)
                evidence_refs.append(
                    EvidenceRef(
                        id=uuid4(),
                        owner=owner,
                        repo=repo,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        evidence_type=EvidenceType.AST_IMPORT,
                        excerpt=f"from {module} import {', '.join(names)}"[:500],
                        status=EvidenceStatus.VERIFIED,
                        confidence_note="Extracted via Python AST",
                    )
                )

            # Classes
            elif isinstance(node, ast.ClassDef):
                bases = [self._get_name(b) for b in node.bases]
                docstring = ast.get_docstring(node)
                method_names = [
                    item.name
                    for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                class_info = ASTClassInfo(
                    name=node.name,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    bases=bases,
                    docstring=docstring,
                    methods=method_names,
                )
                classes.append(class_info)
                evidence_refs.append(
                    EvidenceRef(
                        id=uuid4(),
                        owner=owner,
                        repo=repo,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        evidence_type=EvidenceType.AST_FUNCTION,
                        excerpt=f"class {node.name}({', '.join(bases)}) with methods: {', '.join(method_names[:5])}"[:500],
                        status=EvidenceStatus.VERIFIED,
                        confidence_note="Extracted via Python AST",
                    )
                )

            # Top-level functions or standalone functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Determine if inside class
                is_method = False
                parent_class: Optional[str] = None
                for cls_node in classes:
                    if cls_node.start_line <= node.lineno <= cls_node.end_line:
                        is_method = True
                        parent_class = cls_node.name
                        break

                arg_names = [a.arg for a in node.args.args]
                decorators = [self._get_name(d) for d in node.decorator_list]
                docstring = ast.get_docstring(node)
                fn_info = ASTFunctionInfo(
                    name=node.name,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    args=arg_names,
                    docstring=docstring,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    decorators=decorators,
                    parent_class=parent_class,
                )
                functions.append(fn_info)
                evidence_refs.append(
                    EvidenceRef(
                        id=uuid4(),
                        owner=owner,
                        repo=repo,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        evidence_type=EvidenceType.AST_FUNCTION,
                        excerpt=f"def {node.name}({', '.join(arg_names[:4])})"[:500],
                        status=EvidenceStatus.VERIFIED,
                        confidence_note="Extracted via Python AST",
                    )
                )

        return CodeStructureResult(
            file_path=file_path,
            language="python",
            is_ast_parsed=True,
            classes=classes,
            functions=functions,
            imports=imports,
            evidence_refs=evidence_refs,
            warnings=warnings,
        )

    def _analyze_javascript_typescript(
        self,
        file_path: str,
        content: str,
        owner: str,
        repo: str,
        commit_sha: Optional[str],
    ) -> CodeStructureResult:
        """Regex heuristics for JS/TS with clear disclosure of non-AST method."""
        classes: list[ASTClassInfo] = []
        functions: list[ASTFunctionInfo] = []
        imports: list[ASTImportInfo] = []
        evidence_refs: list[EvidenceRef] = []
        warnings: list[str] = [
            "JavaScript/TypeScript parsed using structural regex heuristics, not full AST parser."
        ]

        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Import pattern: import ... from '...'
            m_imp = re.match(r"^import\s+(?:\{([^}]+)\}|\*\s+as\s+(\w+)|(\w+))\s+from\s+['\"]([^'\"]+)['\"]", stripped)
            if m_imp:
                names = [n.strip() for n in (m_imp.group(1) or m_imp.group(2) or m_imp.group(3) or "").split(",") if n.strip()]
                module = m_imp.group(4)
                imports.append(ASTImportInfo(module=module, names=names, start_line=idx, is_from=True))
                evidence_refs.append(
                    EvidenceRef(
                        id=uuid4(),
                        owner=owner,
                        repo=repo,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx,
                        evidence_type=EvidenceType.AST_IMPORT,
                        excerpt=stripped[:500],
                        status=EvidenceStatus.INFERRED,
                        confidence_note="Extracted via JS/TS regex pattern",
                    )
                )

            # Class pattern: class Foo (extends Bar)?
            m_cls = re.match(r"^(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?", stripped)
            if m_cls:
                cname = m_cls.group(1)
                bases = [m_cls.group(2)] if m_cls.group(2) else []
                classes.append(ASTClassInfo(name=cname, start_line=idx, end_line=idx, bases=bases))
                evidence_refs.append(
                    EvidenceRef(
                        id=uuid4(),
                        owner=owner,
                        repo=repo,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx,
                        evidence_type=EvidenceType.AST_FUNCTION,
                        excerpt=stripped[:500],
                        status=EvidenceStatus.INFERRED,
                        confidence_note="Extracted via JS/TS regex pattern",
                    )
                )

            # Function pattern: function foo() or const foo = () =>
            m_fn = re.match(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)", stripped)
            if not m_fn:
                m_fn = re.match(r"^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>", stripped)
            if m_fn:
                fname = m_fn.group(1)
                args = [a.strip() for a in m_fn.group(2).split(",") if a.strip()]
                functions.append(ASTFunctionInfo(name=fname, start_line=idx, end_line=idx, args=args))
                evidence_refs.append(
                    EvidenceRef(
                        id=uuid4(),
                        owner=owner,
                        repo=repo,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx,
                        evidence_type=EvidenceType.AST_FUNCTION,
                        excerpt=stripped[:500],
                        status=EvidenceStatus.INFERRED,
                        confidence_note="Extracted via JS/TS regex pattern",
                    )
                )

        return CodeStructureResult(
            file_path=file_path,
            language="javascript/typescript",
            is_ast_parsed=False,
            classes=classes,
            functions=functions,
            imports=imports,
            evidence_refs=evidence_refs,
            warnings=warnings,
        )

    def _analyze_go(
        self,
        file_path: str,
        content: str,
        owner: str,
        repo: str,
        commit_sha: Optional[str],
    ) -> CodeStructureResult:
        """Regex heuristics for Go with honest limitation disclosure."""
        functions: list[ASTFunctionInfo] = []
        classes: list[ASTClassInfo] = []
        imports: list[ASTImportInfo] = []
        evidence_refs: list[EvidenceRef] = []
        warnings = ["Go parsed using structural regex heuristics, not full AST parser."]

        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            # func FuncName(...)
            m_fn = re.match(r"^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(([^)]*)\)", stripped)
            if m_fn:
                fname = m_fn.group(1)
                args = [a.strip() for a in m_fn.group(2).split(",") if a.strip()]
                functions.append(ASTFunctionInfo(name=fname, start_line=idx, end_line=idx, args=args))
                evidence_refs.append(
                    EvidenceRef(
                        id=uuid4(),
                        owner=owner,
                        repo=repo,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx,
                        evidence_type=EvidenceType.AST_FUNCTION,
                        excerpt=stripped[:500],
                        status=EvidenceStatus.INFERRED,
                        confidence_note="Extracted via Go regex pattern",
                    )
                )
            # type StructName struct
            m_st = re.match(r"^type\s+(\w+)\s+struct", stripped)
            if m_st:
                sname = m_st.group(1)
                classes.append(ASTClassInfo(name=sname, start_line=idx, end_line=idx, bases=[]))

        return CodeStructureResult(
            file_path=file_path,
            language="go",
            is_ast_parsed=False,
            classes=classes,
            functions=functions,
            imports=imports,
            evidence_refs=evidence_refs,
            warnings=warnings,
        )

    def _analyze_rust(
        self,
        file_path: str,
        content: str,
        owner: str,
        repo: str,
        commit_sha: Optional[str],
    ) -> CodeStructureResult:
        """Regex heuristics for Rust with honest limitation disclosure."""
        functions: list[ASTFunctionInfo] = []
        classes: list[ASTClassInfo] = []
        imports: list[ASTImportInfo] = []
        evidence_refs: list[EvidenceRef] = []
        warnings = ["Rust parsed using structural regex heuristics, not full AST parser."]

        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            m_fn = re.match(r"^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*\(([^)]*)\)", stripped)
            if m_fn:
                fname = m_fn.group(1)
                args = [a.strip() for a in m_fn.group(2).split(",") if a.strip()]
                functions.append(ASTFunctionInfo(name=fname, start_line=idx, end_line=idx, args=args))
            m_st = re.match(r"^(?:pub\s+)?struct\s+(\w+)", stripped)
            if m_st:
                sname = m_st.group(1)
                classes.append(ASTClassInfo(name=sname, start_line=idx, end_line=idx, bases=[]))

        return CodeStructureResult(
            file_path=file_path,
            language="rust",
            is_ast_parsed=False,
            classes=classes,
            functions=functions,
            imports=imports,
            evidence_refs=evidence_refs,
            warnings=warnings,
        )

    @staticmethod
    def _get_name(node: Any) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{CodeStructureAnalyzer._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return CodeStructureAnalyzer._get_name(node.func)
        return str(node)
