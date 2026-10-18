"""
FirstPatch AI — Phase 2 Source-Code Structure Analysis

Implements AST-based parsing for Python, structural pattern analysis for
JavaScript/TypeScript, and graceful fallback for other languages.
Preserves symbol names, types, line ranges, and source excerpts.
"""
from __future__ import annotations

import ast
import logging
import re

from app.services.repository_intelligence.schemas import (
    CodeSymbol,
    FileStructure,
    SymbolType,
)

logger = logging.getLogger(__name__)

# Excluded directories and file patterns (generated, minified, build artifacts)
_IGNORED_PATH_SUBSTRINGS = {
    "dist/", "build/", ".git/", "node_modules/", ".venv/", "venv/",
    "site-packages/", "__pycache__/", "target/", "out/",
}
_IGNORED_EXTENSIONS = {
    ".min.js", ".min.css", ".map", ".lock", ".wasm", ".pyc", ".pyo",
    ".class", ".o", ".obj", ".exe", ".dll", ".so", ".dylib",
}


def should_analyze_file(path: str) -> bool:
    """Determine if a file is suitable for source code analysis."""
    clean = path.replace("\\", "/").lower()
    if not clean.startswith("/"):
        clean_with_slash = f"/{clean}"
    else:
        clean_with_slash = clean

    for sub in _IGNORED_PATH_SUBSTRINGS:
        if sub in clean or f"/{sub}" in clean_with_slash:
            return False

    if any(clean.endswith(ext) for ext in _IGNORED_EXTENSIONS):
        return False
    return True


class CodeStructureAnalyzer:
    """
    Parses repository source files and extracts structural symbols:
    functions, classes, imports, routes, and test cases.
    """

    def analyze_file(
        self,
        file_path: str,
        content: str,
        snapshot_sha: str,
    ) -> FileStructure:
        """Analyze a single file and return its extracted structure."""
        if not should_analyze_file(file_path):
            return FileStructure(file_path=file_path, language="ignored")

        lower = file_path.lower()
        if lower.endswith(".py"):
            return self._analyze_python(file_path, content, snapshot_sha)
        elif lower.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
            return self._analyze_javascript_typescript(file_path, content, snapshot_sha)
        else:
            return self._analyze_generic_fallback(file_path, content, snapshot_sha)

    # -----------------------------------------------------------------------
    # Python AST Analysis
    # -----------------------------------------------------------------------

    def _analyze_python(
        self,
        file_path: str,
        content: str,
        snapshot_sha: str,
    ) -> FileStructure:
        symbols: list[CodeSymbol] = []
        imports: list[str] = []
        routes: list[CodeSymbol] = []
        test_cases: list[CodeSymbol] = []
        parse_errors: list[str] = []

        lines = content.splitlines()

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as exc:
            parse_errors.append(f"Python SyntaxError at line {exc.lineno}: {exc.msg}")
            return FileStructure(
                file_path=file_path,
                language="Python",
                symbols=[],
                imports=[],
                routes=[],
                test_cases=[],
                parse_errors=parse_errors,
            )
        except Exception as exc:
            parse_errors.append(f"AST parse failure: {exc}")
            return FileStructure(
                file_path=file_path,
                language="Python",
                symbols=[],
                imports=[],
                routes=[],
                test_cases=[],
                parse_errors=parse_errors,
            )

        for node in ast.walk(tree):
            # Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imp_str = alias.name + (f" as {alias.asname}" if alias.asname else "")
                    imports.append(imp_str)
                    start_l = getattr(node, "lineno", 1)
                    end_l = getattr(node, "end_lineno", start_l)
                    excerpt = _get_excerpt(lines, start_l, end_l)
                    symbols.append(CodeSymbol(
                        snapshot_sha=snapshot_sha,
                        file_path=file_path,
                        name=imp_str,
                        symbol_type=SymbolType.IMPORT,
                        start_line=start_l,
                        end_line=end_l,
                        excerpt=excerpt,
                    ))

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    as_suffix = f" as {alias.asname}" if alias.asname else ""
                    imp_str = f"from {module} import {alias.name}{as_suffix}"
                    imports.append(imp_str)
                    start_l = getattr(node, "lineno", 1)
                    end_l = getattr(node, "end_lineno", start_l)
                    excerpt = _get_excerpt(lines, start_l, end_l)
                    symbols.append(CodeSymbol(
                        snapshot_sha=snapshot_sha,
                        file_path=file_path,
                        name=imp_str,
                        symbol_type=SymbolType.IMPORT,
                        start_line=start_l,
                        end_line=end_l,
                        excerpt=excerpt,
                    ))

            # Functions & Async Functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sym_type = (
                    SymbolType.ASYNC_FUNCTION
                    if isinstance(node, ast.AsyncFunctionDef)
                    else SymbolType.FUNCTION
                )
                start_l = getattr(node, "lineno", 1)
                end_l = getattr(node, "end_lineno", start_l)
                doc = ast.get_docstring(node)
                params = [arg.arg for arg in node.args.args]
                decorators = [_get_decorator_name(dec) for dec in node.decorator_list]
                excerpt = _get_excerpt(lines, start_l, min(start_l + 5, end_l))

                # Check if it's a test case
                is_test = node.name.startswith("test_")
                if is_test:
                    sym_type = SymbolType.TEST_CASE

                # Check if it's a route
                is_route = any(
                    any(method in dec.lower() for method in ["get", "post", "put", "delete", "patch", "route"])
                    for dec in decorators
                )

                sym = CodeSymbol(
                    snapshot_sha=snapshot_sha,
                    file_path=file_path,
                    name=node.name,
                    symbol_type=SymbolType.ROUTE if is_route else sym_type,
                    start_line=start_l,
                    end_line=end_l,
                    excerpt=excerpt,
                    docstring=doc,
                    parameters=params,
                    decorators=decorators,
                )
                symbols.append(sym)

                if is_route:
                    routes.append(sym)
                if is_test:
                    test_cases.append(sym)

            # Classes
            elif isinstance(node, ast.ClassDef):
                start_l = getattr(node, "lineno", 1)
                end_l = getattr(node, "end_lineno", start_l)
                doc = ast.get_docstring(node)
                decorators = [_get_decorator_name(dec) for dec in node.decorator_list]
                excerpt = _get_excerpt(lines, start_l, min(start_l + 5, end_l))

                is_test_class = node.name.startswith("Test") or node.name.endswith("Test") or node.name.endswith("Tests")
                sym_type = SymbolType.TEST_CASE if is_test_class else SymbolType.CLASS

                sym = CodeSymbol(
                    snapshot_sha=snapshot_sha,
                    file_path=file_path,
                    name=node.name,
                    symbol_type=sym_type,
                    start_line=start_l,
                    end_line=end_l,
                    excerpt=excerpt,
                    docstring=doc,
                    decorators=decorators,
                )
                symbols.append(sym)
                if is_test_class:
                    test_cases.append(sym)

        return FileStructure(
            file_path=file_path,
            language="Python",
            symbols=symbols,
            imports=imports,
            routes=routes,
            test_cases=test_cases,
            parse_errors=parse_errors,
        )

    # -----------------------------------------------------------------------
    # JavaScript / TypeScript Structural Analysis
    # -----------------------------------------------------------------------

    def _analyze_javascript_typescript(
        self,
        file_path: str,
        content: str,
        snapshot_sha: str,
    ) -> FileStructure:
        symbols: list[CodeSymbol] = []
        imports: list[str] = []
        routes: list[CodeSymbol] = []
        test_cases: list[CodeSymbol] = []
        parse_errors: list[str] = []

        lines = content.splitlines()

        # Regular expressions for JS/TS patterns
        func_pattern = re.compile(
            r"^(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(",
            re.MULTILINE,
        )
        arrow_func_pattern = re.compile(
            r"^(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::\s*[^=]+)?\s*=>",
            re.MULTILINE,
        )
        class_pattern = re.compile(
            r"^(?:export\s+(?:default\s+)?)?class\s+([a-zA-Z0-9_$]+)",
            re.MULTILINE,
        )
        import_pattern = re.compile(
            r"^import\s+(?:.*?\s+from\s+)?['\"]([^'\"]+)['\"]",
            re.MULTILINE,
        )
        require_pattern = re.compile(
            r"(?:const|let|var)\s+.*?\s*=\s*require\(['\"]([^'\"]+)['\"]\)",
            re.MULTILINE,
        )
        route_pattern = re.compile(
            r"(?:app|router)\.(get|post|put|delete|patch|use)\(\s*['\"]([^'\"]+)['\"]",
            re.MULTILINE,
        )
        test_pattern = re.compile(
            r"^(?:describe|it|test)\(\s*['\"]([^'\"]+)['\"]",
            re.MULTILINE,
        )

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Imports
            imp_match = import_pattern.match(stripped) or require_pattern.search(stripped)
            if imp_match:
                imp_name = imp_match.group(1)
                imports.append(imp_name)
                symbols.append(CodeSymbol(
                    snapshot_sha=snapshot_sha,
                    file_path=file_path,
                    name=imp_name,
                    symbol_type=SymbolType.IMPORT,
                    start_line=line_num,
                    end_line=line_num,
                    excerpt=stripped[:200],
                ))
                continue

            # Route definitions
            route_match = route_pattern.search(stripped)
            if route_match:
                method, path = route_match.group(1), route_match.group(2)
                route_name = f"{method.upper()} {path}"
                sym = CodeSymbol(
                    snapshot_sha=snapshot_sha,
                    file_path=file_path,
                    name=route_name,
                    symbol_type=SymbolType.ROUTE,
                    start_line=line_num,
                    end_line=line_num,
                    excerpt=stripped[:200],
                )
                symbols.append(sym)
                routes.append(sym)
                continue

            # Test cases
            test_match = test_pattern.match(stripped)
            if test_match:
                test_title = test_match.group(1)
                sym = CodeSymbol(
                    snapshot_sha=snapshot_sha,
                    file_path=file_path,
                    name=test_title,
                    symbol_type=SymbolType.TEST_CASE,
                    start_line=line_num,
                    end_line=line_num,
                    excerpt=stripped[:200],
                )
                symbols.append(sym)
                test_cases.append(sym)
                continue

            # Functions
            f_match = func_pattern.match(stripped) or arrow_func_pattern.match(stripped)
            if f_match:
                f_name = f_match.group(1)
                symbols.append(CodeSymbol(
                    snapshot_sha=snapshot_sha,
                    file_path=file_path,
                    name=f_name,
                    symbol_type=SymbolType.FUNCTION,
                    start_line=line_num,
                    end_line=line_num,
                    excerpt=stripped[:200],
                ))
                continue

            # Classes
            c_match = class_pattern.match(stripped)
            if c_match:
                c_name = c_match.group(1)
                symbols.append(CodeSymbol(
                    snapshot_sha=snapshot_sha,
                    file_path=file_path,
                    name=c_name,
                    symbol_type=SymbolType.CLASS,
                    start_line=line_num,
                    end_line=line_num,
                    excerpt=stripped[:200],
                ))
                continue

        lang = "TypeScript" if file_path.lower().endswith((".ts", ".tsx")) else "JavaScript"

        return FileStructure(
            file_path=file_path,
            language=lang,
            symbols=symbols,
            imports=imports,
            routes=routes,
            test_cases=test_cases,
            parse_errors=parse_errors,
        )

    # -----------------------------------------------------------------------
    # Fallback Generic Analysis
    # -----------------------------------------------------------------------

    def _analyze_generic_fallback(
        self,
        file_path: str,
        content: str,
        snapshot_sha: str,
    ) -> FileStructure:
        """Fallback line-based extractor for Go, Rust, Java, C++, etc."""
        symbols: list[CodeSymbol] = []
        imports: list[str] = []
        lines = content.splitlines()

        generic_func = re.compile(r"^\s*(?:pub\s+|public\s+|private\s+)?(?:func|fn|def)\s+([a-zA-Z0-9_]+)\s*\(")
        generic_class = re.compile(r"^\s*(?:pub\s+|public\s+|private\s+)?(?:class|struct|interface|type)\s+([a-zA-Z0-9_]+)")

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            f_match = generic_func.match(stripped)
            if f_match:
                symbols.append(CodeSymbol(
                    snapshot_sha=snapshot_sha,
                    file_path=file_path,
                    name=f_match.group(1),
                    symbol_type=SymbolType.FUNCTION,
                    start_line=line_num,
                    end_line=line_num,
                    excerpt=stripped[:200],
                ))
                continue
            c_match = generic_class.match(stripped)
            if c_match:
                symbols.append(CodeSymbol(
                    snapshot_sha=snapshot_sha,
                    file_path=file_path,
                    name=c_match.group(1),
                    symbol_type=SymbolType.CLASS,
                    start_line=line_num,
                    end_line=line_num,
                    excerpt=stripped[:200],
                ))
                continue

        ext = file_path.split(".")[-1] if "." in file_path else "unknown"

        return FileStructure(
            file_path=file_path,
            language=ext.upper(),
            symbols=symbols,
            imports=imports,
            routes=[],
            test_cases=[],
            parse_errors=[],
        )


def _get_excerpt(lines: list[str], start_line: int, end_line: int) -> str:
    """Safely extract lines [start_line, end_line] 1-indexed."""
    if not lines or start_line < 1:
        return ""
    start_idx = max(0, start_line - 1)
    end_idx = min(len(lines), end_line)
    return "\n".join(lines[start_idx:end_idx]).strip()


def _get_decorator_name(decorator_node: ast.AST) -> str:
    """Extract decorator string representation from AST node."""
    if isinstance(decorator_node, ast.Name):
        return decorator_node.id
    elif isinstance(decorator_node, ast.Attribute):
        value_name = _get_decorator_name(decorator_node.value)
        return f"{value_name}.{decorator_node.attr}"
    elif isinstance(decorator_node, ast.Call):
        return _get_decorator_name(decorator_node.func)
    return "decorator"
