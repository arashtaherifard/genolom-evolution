from __future__ import annotations
from pathlib import Path
import hashlib, json


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_manifest_dataset(manifest_path: str | Path, dataset_path: str | Path) -> bool:
    manifest = load_manifest(manifest_path)
    return sha256_file(dataset_path) == manifest["sha256"]
