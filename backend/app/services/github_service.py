import httpx
import re
from typing import Dict, Any, List, Optional, Tuple
from backend.app.config import settings

def parse_repo_identifier(input_str: str) -> Tuple[str, str]:
    """Extracts (owner, repo) from a GitHub URL or 'owner/repo' string."""
    clean = input_str.strip()
    # Remove trailing slashes and .git
    clean = re.sub(r'\.git$', '', clean)
    clean = clean.rstrip('/')

    # Format: https://github.com/owner/repo or github.com/owner/repo
    match = re.search(r'(?:github\.com[/:]|^)([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)$', clean)
    if match:
        return match.group(1), match.group(2)

    # Format: owner/repo
    parts = clean.split('/')
    if len(parts) == 2 and parts[0] and parts[1]:
        return parts[0], parts[1]

    raise ValueError(f"Invalid GitHub repository identifier or URL: '{input_str}'. Expected format 'owner/repo' or 'https://github.com/owner/repo'.")

class GitHubService:
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN
        self.base_url = "https://api.github.com"

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "FirstPatch-AI-Mentor"
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def get_repo_metadata(self, owner: str, repo: str) -> Dict[str, Any]:
        url = f"{self.base_url}/repos/{owner}/{repo}"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code == 404:
                raise ValueError(f"Repository '{owner}/{repo}' not found on GitHub. Please check if the repository is public and spelled correctly.")
            if resp.status_code == 403:
                rate_limit_reset = resp.headers.get("x-ratelimit-reset", "")
                raise RuntimeError(f"GitHub API rate limit exceeded or access forbidden. Status 403. Rate limit reset timestamp: {rate_limit_reset}")
            resp.raise_for_status()
            data = resp.json()
            return {
                "owner": data.get("owner", {}).get("login", owner),
                "name": data.get("name", repo),
                "full_name": data.get("full_name", f"{owner}/{repo}"),
                "description": data.get("description", ""),
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "open_issues_count": data.get("open_issues_count", 0),
                "default_branch": data.get("default_branch", "main"),
                "language": data.get("language") or "Python",
                "topics": data.get("topics", []),
                "license_name": data.get("license", {}).get("name") if data.get("license") else "Not Specified",
                "html_url": data.get("html_url", f"https://github.com/{owner}/{repo}")
            }

    async def get_latest_commit_sha(self, owner: str, repo: str, branch: str) -> str:
        url = f"{self.base_url}/repos/{owner}/{repo}/commits/{branch}"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code == 200:
                data = resp.json()
                return data.get("sha", "head")
            return "head"

    async def get_file_tree(self, owner: str, repo: str, sha: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{sha}?recursive=1"
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code == 200:
                data = resp.json()
                tree = data.get("tree", [])
                # Filter out unwanted items (.git, node_modules, binary images, etc.)
                allowed_extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".json", ".toml", ".yml", ".yaml", ".cfg", ".txt", ".rs", ".go"}
                filtered = []
                for item in tree:
                    path = item.get("path", "")
                    if item.get("type") == "blob":
                        # Skip hidden files or lockfiles or node_modules
                        if any(ignored in path for ignored in ["node_modules/", ".git/", "__pycache__/", "package-lock.json", ".venv/", "venv/"]):
                            continue
                        ext = "." + path.split(".")[-1] if "." in path else ""
                        if ext.lower() in allowed_extensions or path.lower() in ["dockerfile", "makefile", "license", "readme"]:
                            filtered.append({
                                "path": path,
                                "size": item.get("size", 0),
                                "sha": item.get("sha", "")
                            })
                return filtered[:100]  # Bound to top 100 relevant files for responsive ingestion
            return []

    async def get_raw_file_content(self, owner: str, repo: str, path: str, branch: str = "main") -> str:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.text
            # Fallback to API contents
            api_url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}?ref={branch}"
            api_resp = await client.get(api_url, headers=self._get_headers())
            if api_resp.status_code == 200:
                import base64
                data = api_resp.json()
                if "content" in data and data.get("encoding") == "base64":
                    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            return ""

    async def get_open_issues(self, owner: str, repo: str, limit: int = 30) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/repos/{owner}/{repo}/issues?state=open&per_page={limit}"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code != 200:
                return []
            raw_issues = resp.json()
            parsed = []
            for item in raw_issues:
                # Exclude pull requests (GitHub issues API returns PRs unless filtered)
                if "pull_request" in item:
                    continue
                labels = [l.get("name", "") for l in item.get("labels", []) if isinstance(l, dict)]
                parsed.append({
                    "github_issue_id": item.get("id"),
                    "number": item.get("number"),
                    "title": item.get("title", ""),
                    "body": item.get("body") or "",
                    "state": item.get("state", "open"),
                    "author": item.get("user", {}).get("login", "anonymous"),
                    "comments_count": item.get("comments", 0),
                    "labels": labels,
                    "html_url": item.get("html_url", ""),
                    "created_at": item.get("created_at", ""),
                    "updated_at": item.get("updated_at", "")
                })
            return parsed

github_service = GitHubService()
