from __future__ import annotations

from pathlib import Path
import importlib
import sys


def run_content_gen(payload: dict) -> dict:
    """Lightweight wrapper so Studio can trigger the content_gen pipeline."""
    base_dir = Path(__file__).resolve().parents[2]
    scripts_dir = base_dir / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    content_gen = importlib.import_module("content_gen")
    return content_gen.run_from_payload(payload)
