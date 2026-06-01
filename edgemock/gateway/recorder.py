import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SESSION_DIR = Path.home() / ".edgemock" / "sessions"


class Recorder:
    def __init__(self, session: str):
        self._path = _SESSION_DIR / f"{session}.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self._path.open("a")

    def record(self, method: str, path: str, req_headers: dict, req_body: Any,
               status: int, resp_headers: dict, resp_body: Any):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "path": path,
            "req_headers": req_headers,
            "req_body": req_body,
            "status": status,
            "resp_headers": resp_headers,
            "resp_body": resp_body,
        }
        self._file.write(json.dumps(entry) + "\n")
        self._file.flush()

    def close(self):
        self._file.close()


class Replay:
    def __init__(self, session: str):
        self._path = _SESSION_DIR / f"{session}.jsonl"

    def load(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            raise FileNotFoundError(f"session not found: {self._path}")
        entries = []
        with self._path.open() as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries