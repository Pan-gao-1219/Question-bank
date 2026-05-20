"""GitHub Gist client for per-user state storage."""
import json
import requests

GIST_API = "https://api.github.com/gists"


class GistClient:
    def __init__(self, token: str, gist_id: str):
        self.token = token
        self.gist_id = gist_id
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def _filename(self, username: str) -> str:
        # Sanitize username to safe filename
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in username)
        return f"user_{safe}.json"

    def load_state(self, username: str) -> dict:
        """Load state dict for user. Returns {} if not found."""
        try:
            resp = requests.get(
                f"{GIST_API}/{self.gist_id}",
                headers=self.headers,
                timeout=10,
            )
            if resp.status_code != 200:
                return {}
            gist = resp.json()
            fname = self._filename(username)
            if fname in gist.get("files", {}):
                content = gist["files"][fname].get("content", "{}")
                return json.loads(content)
            return {}
        except Exception:
            return {}

    def save_state(self, username: str, state: dict) -> bool:
        """Save state dict for user. Returns True on success."""
        fname = self._filename(username)
        payload = {
            "files": {
                fname: {"content": json.dumps(state, ensure_ascii=False)}
            }
        }
        try:
            resp = requests.patch(
                f"{GIST_API}/{self.gist_id}",
                headers=self.headers,
                json=payload,
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False
