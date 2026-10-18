import re
from typing import Dict, Any, List

class SetupFailureDoctor:
    def __init__(self):
        pass

    def diagnose_error(self, error_log: str, repo_language: str = "Python") -> Dict[str, Any]:
        text = error_log.strip()
        causes = []
        suggestions = []
        category = "Unknown Environment Error"

        # 1. Python ModuleNotFoundError / ImportError
        mod_match = re.search(r"ModuleNotFoundError:\s+No module named ['\"]([^'\"]+)['\"]", text)
        if mod_match:
            missing_mod = mod_match.group(1)
            category = "Missing Python Package"
            causes.append(f"The Python runtime could not locate module '{missing_mod}' in your current environment.")
            suggestions.append({
                "command": f"pip install {missing_mod}",
                "explanation": f"Installs '{missing_mod}' into your active Python environment.",
                "safe": True
            })
            suggestions.append({
                "command": "pip install -r requirements.txt",
                "explanation": "Ensures all repository dependencies are installed in one pass.",
                "safe": True
            })

        # 2. Node npm ERESOLVE peer dependency conflict
        elif "ERESOLVE" in text or "conflicting peer dependency" in text:
            category = "NPM Peer Dependency Conflict"
            causes.append("Two or more installed packages demand conflicting versions of a shared peer dependency.")
            suggestions.append({
                "command": "npm install --legacy-peer-deps",
                "explanation": "Bypasses strict peer dependency resolution, allowing package installation to succeed.",
                "safe": True
            })

        # 3. Missing Environment Variable
        elif "KeyError:" in text or "Missing required environment variable" in text or "EnvironmentError" in text:
            category = "Missing Configuration / Environment Variable"
            key_match = re.search(r"KeyError:\s+['\"]([^'\"]+)['\"]", text)
            key_name = key_match.group(1) if key_match else "CONFIG_KEY"
            causes.append(f"The application expects environment variable '{key_name}' to be set before booting.")
            suggestions.append({
                "command": f"export {key_name}='your_value_here'",
                "explanation": f"Defines '{key_name}' in your current terminal session.",
                "safe": True
            })
            suggestions.append({
                "command": "cp .env.example .env",
                "explanation": "Creates a local .env configuration file from the template.",
                "safe": True
            })

        # 4. C-Compiler / header files missing (e.g. gcc, clang, python-dev)
        elif "fatal error:" in text and (".h: No such file or directory" in text or "clang: error:" in text):
            category = "Missing Native C/C++ Headers"
            causes.append("A Python package requires native C compilation, but required system headers or compiler tools are missing.")
            suggestions.append({
                "command": "xcode-select --install",
                "explanation": "Installs macOS Command Line Tools (compilers and system headers).",
                "safe": True
            })

        # 5. Port already in use / Address already in use
        elif "EADDRINUSE" in text or "Address already in use" in text or "Errno 48" in text:
            category = "Port Conflict"
            causes.append("Another local process is already listening on the requested port.")
            suggestions.append({
                "command": "lsof -i :8000 | awk 'NR>1 {print $2}' | xargs kill -9",
                "explanation": "Terminates the previous zombie process bound to port 8000.",
                "safe": True
            })

        # 6. Generic failure
        else:
            causes.append("General build, runtime, or test execution failure.")
            suggestions.append({
                "command": "python3 -m venv .venv && source .venv/bin/activate",
                "explanation": "Creates an isolated clean virtual environment to prevent package version pollution.",
                "safe": True
            })

        return {
            "category": category,
            "detected_causes": causes,
            "remediation_plan": suggestions,
            "verified": False,
            "note": "Suggested commands must be reviewed and authorized before execution."
        }

setup_doctor = SetupFailureDoctor()
