import ast
import re
from typing import Dict, Any, List, Optional

class PythonASTExtractor(ast.NodeVisitor):
    def __init__(self):
        self.current_class_depth = 0
        self.stats = {
            "classes": [],
            "functions": [],
            "imports": [],
            "test_functions": [],
            "symbols": []
        }

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.name
            self.stats["imports"].append(name)
            self.stats["symbols"].append({
                "type": "import",
                "name": name,
                "line_start": node.lineno,
                "line_end": getattr(node, 'end_lineno', node.lineno)
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            self.stats["imports"].append(full_name)
            self.stats["symbols"].append({
                "type": "import_from",
                "name": full_name,
                "line_start": node.lineno,
                "line_end": getattr(node, 'end_lineno', node.lineno)
            })
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append({
                    "name": item.name,
                    "line_start": item.lineno,
                    "line_end": getattr(item, 'end_lineno', item.lineno),
                    "docstring": ast.get_docstring(item)
                })
        
        class_info = {
            "name": node.name,
            "line_start": node.lineno,
            "line_end": getattr(node, 'end_lineno', node.lineno),
            "docstring": ast.get_docstring(node),
            "methods": methods,
            "bases": [ast.unparse(b) for b in node.bases if hasattr(ast, 'unparse')]
        }
        self.stats["classes"].append(class_info)
        self.stats["symbols"].append({
            "type": "class",
            "name": node.name,
            "line_start": node.lineno,
            "line_end": class_info["line_end"]
        })
        self.current_class_depth += 1
        self.generic_visit(node)
        self.current_class_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if self.current_class_depth == 0:
            self._record_function(node, is_async=False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if self.current_class_depth == 0:
            self._record_function(node, is_async=True)
        self.generic_visit(node)

    def _record_function(self, node: Any, is_async: bool):
        args = [arg.arg for arg in node.args.args]
        func_info = {
            "name": node.name,
            "args": args,
            "is_async": is_async,
            "line_start": node.lineno,
            "line_end": getattr(node, 'end_lineno', node.lineno),
            "docstring": ast.get_docstring(node)
        }
        self.stats["functions"].append(func_info)
        self.stats["symbols"].append({
            "type": "function",
            "name": node.name,
            "line_start": node.lineno,
            "line_end": func_info["line_end"]
        })
        if node.name.startswith("test_") or node.name.endswith("_test"):
            self.stats["test_functions"].append(func_info)

def analyze_python_source(code: str) -> Dict[str, Any]:
    try:
        tree = ast.parse(code)
        extractor = PythonASTExtractor()
        extractor.visit(tree)
        return {
            "success": True,
            "error": None,
            "classes": extractor.stats["classes"],
            "functions": extractor.stats["functions"],
            "imports": list(set(extractor.stats["imports"])),
            "test_functions": extractor.stats["test_functions"],
            "symbols": extractor.stats["symbols"]
        }
    except SyntaxError as e:
        return {
            "success": False,
            "error": f"Python SyntaxError at line {e.lineno}: {e.msg}",
            "classes": [],
            "functions": [],
            "imports": [],
            "test_functions": [],
            "symbols": []
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "classes": [],
            "functions": [],
            "imports": [],
            "test_functions": [],
            "symbols": []
        }

def analyze_generic_source(code: str, file_type: str) -> Dict[str, Any]:
    """Lightweight regex symbol extractor for JS/TS/Go/Rust/etc."""
    symbols = []
    lines = code.split("\n")
    
    # Matches functions: function foo(), const foo = () =>, export default function
    func_pattern = re.compile(r'(?:function\s+([A-Za-z0-9_$]+)|const\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>|def\s+([A-Za-z0-9_$]+)|fn\s+([A-Za-z0-9_$]+))')
    class_pattern = re.compile(r'(?:class\s+([A-Za-z0-9_$]+)|struct\s+([A-Za-z0-9_$]+)|interface\s+([A-Za-z0-9_$]+))')
    import_pattern = re.compile(r'(?:import\s+.*?from\s+[\'"]([^\'"]+)[\'"]|require\([\'"]([^\'"]+)[\'"]\))')

    imports = []
    classes = []
    functions = []

    for idx, line in enumerate(lines, start=1):
        f_match = func_pattern.search(line)
        if f_match:
            name = next(filter(None, f_match.groups()), "anonymous")
            functions.append({"name": name, "line_start": idx, "line_end": idx, "args": []})
            symbols.append({"type": "function", "name": name, "line_start": idx, "line_end": idx})

        c_match = class_pattern.search(line)
        if c_match:
            name = next(filter(None, c_match.groups()), "anonymous")
            classes.append({"name": name, "line_start": idx, "line_end": idx, "methods": []})
            symbols.append({"type": "class", "name": name, "line_start": idx, "line_end": idx})

        i_match = import_pattern.search(line)
        if i_match:
            mod = next(filter(None, i_match.groups()), "")
            if mod:
                imports.append(mod)

    return {
        "success": True,
        "error": None,
        "classes": classes,
        "functions": functions,
        "imports": list(set(imports)),
        "test_functions": [f for f in functions if "test" in f["name"].lower()],
        "symbols": symbols
    }
