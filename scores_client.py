"""GitHub repository-backed score storage."""
import base64
import json
from datetime import datetime, timezone

import requests


class ScoresClient:
    def __init__(self, token: str, repo: str, branch: str, scores_path: str):
        self.token = token
        self.repo = repo
        self.branch = branch
        self.scores_path = scores_path.strip("/")
        self.last_error = ""
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    @property
    def url(self) -> str:
        return f"https://api.github.com/repos/{self.repo}/contents/{self.scores_path}"

    def _empty_scores(self) -> dict:
        return {"users": {}}

    def _normalize_scores(self, data: object) -> dict:
        if isinstance(data, dict) and isinstance(data.get("users"), dict):
            return data
        if isinstance(data, dict):
            return {"users": data}
        return self._empty_scores()

    def _load_scores_file(self) -> tuple[dict, str | None]:
        self.last_error = ""
        try:
            resp = requests.get(
                self.url,
                headers=self.headers,
                params={"ref": self.branch},
                timeout=10,
            )
            if resp.status_code == 404:
                return self._empty_scores(), None
            if resp.status_code != 200:
                self.last_error = (
                    f"成绩文件读取失败：HTTP {resp.status_code} {resp.text[:160]}"
                )
                return self._empty_scores(), None

            payload = resp.json()
            raw = base64.b64decode(payload.get("content", "")).decode("utf-8")
            data = json.loads(raw) if raw.strip() else self._empty_scores()
            return self._normalize_scores(data), payload.get("sha")
        except Exception as exc:
            self.last_error = f"成绩文件读取失败：{exc}"
            return self._empty_scores(), None

    def _answers_from_record(self, record: object) -> dict:
        if isinstance(record, dict) and isinstance(record.get("answers"), dict):
            return record["answers"]
        if isinstance(record, dict):
            return {
                str(qid): value
                for qid, value in record.items()
                if value in (0, 1) or value == "c" or (isinstance(value, str) and value.startswith("w"))
            }
        return {}

    def load_state(self, username: str) -> dict:
        data, _sha = self._load_scores_file()
        if self.last_error:
            return {}
        return self._answers_from_record(data.get("users", {}).get(username, {}))

    def load_all_states(self) -> dict:
        data, _sha = self._load_scores_file()
        if self.last_error:
            return {}
        return {
            username: self._answers_from_record(record)
            for username, record in data.get("users", {}).items()
        }

    def save_state(self, username: str, state: dict) -> bool:
        data, sha = self._load_scores_file()
        if self.last_error:
            return False

        data.setdefault("users", {})[username] = {
            "answers": state,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        content = json.dumps(data, ensure_ascii=False, indent=2)
        payload = {
            "message": f"Update score for {username}",
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": self.branch,
        }
        if sha:
            payload["sha"] = sha

        try:
            resp = requests.put(
                self.url,
                headers=self.headers,
                json=payload,
                timeout=10,
            )
            if resp.status_code in (200, 201):
                self.last_error = ""
                return True
            self.last_error = (
                f"成绩文件保存失败：HTTP {resp.status_code} {resp.text[:160]}"
            )
            return False
        except Exception as exc:
            self.last_error = f"成绩文件保存失败：{exc}"
            return False
