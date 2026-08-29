from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Freeze a Phase 1 strict workbook as Phase 2 Generation 0.")
    parser.add_argument("source")
    parser.add_argument("--dataset-id", default="openstax-cs-ch01-strict-cso")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    src = Path(args.source).resolve()
    dst = root / "data" / "generation_0.xlsx"
    shutil.copy2(src, dst)
    digest = sha(dst)
    (root / "data" / "generation_0.sha256").write_text(digest + "  generation_0.xlsx\n", encoding="utf-8")
    manifest = {
        "dataset_id": args.dataset_id,
        "source_name": src.name,
        "domain": "computer_science",
        "ontology_name": "CSO",
        "phase1_variant": "main_strict_syntactic",
        "sha256": digest,
    }
    (root / "data" / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
