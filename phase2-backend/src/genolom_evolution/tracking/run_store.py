from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, uuid


class RunStore:
    def __init__(self, root: str | Path, run_id: str | None = None):
        self.root = Path(root)
        self.run_id = run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        self.path = self.root / self.run_id
        self.path.mkdir(parents=True, exist_ok=False)

    def write_json_once(self, relative_path: str, data) -> Path:
        path = self.path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError(f"Immutable run artifact already exists: {path}")
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def append_jsonl(self, relative_path: str, data) -> Path:
        path = self.path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
        return path

    def write_generation_snapshot(self, generation: int, data) -> Path:
        if generation < 0:
            raise ValueError("generation must be >= 0")
        return self.write_json_once(
            f"generations/generation_{generation:04d}.json",
            data,
        )

    def append_rejected_attempt(self, data) -> Path:
        return self.append_jsonl("rejected_attempts.jsonl", data)
