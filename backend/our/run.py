"""Compatibility entry point for the unified Our experiment."""
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from run_method import run


if __name__ == "__main__":
    raise SystemExit(run("our"))
