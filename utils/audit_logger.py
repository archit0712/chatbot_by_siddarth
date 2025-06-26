"""Simple audit logger that writes JSON lines to a local file."""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path


class AuditLogger:
    def __init__(self, log_path: str = "./audit_logs.jsonl", collection_name: str | None = None) -> None:
        self.log_file = Path(log_path)
        self.collection_name = collection_name or "logs"
        if not self.log_file.exists():
            self.log_file.touch()

    def log_sensitive_query(self, log_data: Dict[str, Any]) -> Optional[str]:
        log_data = dict(log_data)
        log_data.setdefault("timestamp", datetime.utcnow().isoformat())
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_data) + "\n")
        return log_data.get("timestamp")

    def get_logs_for_user(self, user_email: str, limit: int = 100) -> List[Dict[str, Any]]:
        return [
            json.loads(line)
            for line in self.log_file.read_text().splitlines()
            if json.loads(line).get("user_email") == user_email
        ][-limit:][::-1]

    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        lines = self.log_file.read_text().splitlines()
        return [json.loads(line) for line in lines][-limit:][::-1]
