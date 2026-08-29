from pathlib import Path

from cso_common import run_cso_pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_ROOT / "data" / "ch01_annotated.xlsx"
OUTPUT_FILE = PROJECT_ROOT / "data" / "ch01_cso_extended.xlsx"


if __name__ == "__main__":
    run_cso_pipeline(
        INPUT_FILE,
        OUTPUT_FILE,
        include_extended=True,
    )
