"""GitHub Gist client for per-user state storage."""
import json
import requests

GIST_API = "https://api.github.com/gists"


class GistClient:
    def __init__(self, token: str, gist_id: str):
        self.token = token
        self.gist_id = gist_id
        self.last_error = ""
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
        self.last_error = ""
        try:
            resp = requests.get(
                f"{GIST_API}/{self.gist_id}",
                headers=self.headers,
                timeout=10,
            )
            if resp.status_code != 200:
                self.last_error = f"Gist 读取失败：HTTP {resp.status_code} {resp.text[:160]}"
                return {}
            gist = resp.json()
            fname = self._filename(username)
            if fname in gist.get("files", {}):
                content = gist["files"][fname].get("content", "{}")
                return json.loads(content)
            return {}
        except Exception as exc:
            self.last_error = f"Gist 读取失败：{exc}"
            return {}

    def load_all_states(self) -> dict:
        """Load all user state files from the configured Gist."""
        self.last_error = ""
        try:
            resp = requests.get(
                f"{GIST_API}/{self.gist_id}",
                headers=self.headers,
                timeout=10,
            )
            if resp.status_code != 200:
                self.last_error = f"Gist 读取失败：HTTP {resp.status_code} {resp.text[:160]}"
                return {}

            users = {}
            for fname, meta in resp.json().get("files", {}).items():
                if not fname.startswith("user_") or not fname.endswith(".json"):
                    continue
                username = fname[len("user_"):-len(".json")]
                try:
                    users[username] = json.loads(meta.get("content", "{}"))
                except json.JSONDecodeError:
                    users[username] = {}
            return users
        except Exception as exc:
            self.last_error = f"Gist 读取失败：{exc}"
            return {}

    def save_state(self, username: str, state: dict) -> bool:
        """Save state dict for user. Returns True on success."""
        self.last_error = ""
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
            if resp.status_code == 200:
                return True
            self.last_error = f"Gist 保存失败：HTTP {resp.status_code} {resp.text[:160]}"
            return False
        except Exception as exc:
            self.last_error = f"Gist 保存失败：{exc}"
            return False
