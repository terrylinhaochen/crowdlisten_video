"""
pipeline.py — End-to-end video processing orchestrator
Runs: extract audio → whisper → detect clips → render
Emits SSE progress events at each step.
"""
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path

from .config import UPLOADS_DIR, PROCESSING_DIR, LIBRARY_DIR
from . import sse as sse_bus
from .whisper import extract_audio, transcribe
from .detector import detect_clips
from .renderer import render_clip


def _emit(job_id: str, step: str, status: str, msg: str = "", progress: int = 0):
    sse_bus.publish({
        "job_id": job_id,
        "step": step,
        "status": status,  # running | done | error
        "msg": msg,
        "progress": progress,
    })


def _save_state(job_id: str, state: dict):
    path = PROCESSING_DIR / f"{job_id}_state.json"
    state["updated_at"] = datetime.utcnow().isoformat()
    path.write_text(json.dumps(state, indent=2))


def load_state(job_id: str) -> dict:
    path = PROCESSING_DIR / f"{job_id}_state.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def run_pipeline(
    job_id: str,
    video_path: Path,
    clip_types: list[str],
    add_narration: bool,
    count: int,
    audience: str,
    ad_config: dict | None = None,
):
    state = {
        "job_id": job_id,
        "status": "running",
        "clip_types": clip_types,
        "add_narration": add_narration,
        "count": count,
        "audience": audience,
        "steps": {},
        "clips": [],
    }
    _save_state(job_id, state)

    try:
        # Step 1 — Extract audio
        _emit(job_id, "audio", "running", "Extracting audio...")
        audio_path = extract_audio(video_path, job_id)
        state["steps"]["audio"] = "done"
        _save_state(job_id, state)
        _emit(job_id, "audio", "done", "Audio extracted", 25)

        # Step 2 — Transcribe
        _emit(job_id, "transcribe", "running", "Transcribing with Whisper...")
        transcript = transcribe(audio_path, job_id)
        state["steps"]["transcribe"] = "done"
        _save_state(job_id, state)
        _emit(job_id, "transcribe", "done", "Transcription complete", 50)

        # Step 3 — Detect clips
        _emit(job_id, "detect", "running", "Detecting clip candidates...")
        candidates = detect_clips(transcript, job_id, clip_types, count, audience)
        state["steps"]["detect"] = "done"
        state["candidates"] = len(candidates)
        _save_state(job_id, state)
        _emit(job_id, "detect", "done", f"Found {len(candidates)} candidates", 75)

        # Step 4 — Render
        lib_dir = LIBRARY_DIR / job_id
        lib_dir.mkdir(parents=True, exist_ok=True)
        _emit(job_id, "render", "running", "Rendering clips...")

        rendered = []
        for i, clip in enumerate(candidates):
            try:
                out = render_clip(video_path, lib_dir, i + 1, clip, add_cta=add_narration)
                clip["output_file"] = out.name
                rendered.append(clip)
                _emit(job_id, "render", "running",
                      f"Rendered {i+1}/{len(candidates)}: {out.name}",
                      75 + int(25 * (i + 1) / len(candidates)))
            except Exception as e:
                _emit(job_id, "render", "error", f"Clip {i+1} failed: {e}")

        state["steps"]["render"] = "done"
        state["clips"] = rendered
        state["status"] = "done"
        state["ad_config"] = ad_config or {}
        _save_state(job_id, state)
        _emit(job_id, "render", "done", f"Done! {len(rendered)} clips ready", 100)

    except Exception as e:
        state["status"] = "error"
        state["error"] = str(e)
        _save_state(job_id, state)
        _emit(job_id, "error", "error", str(e))


def start_pipeline(
    job_id: str,
    video_path: Path,
    clip_types: list[str],
    add_narration: bool,
    count: int,
    audience: str,
    ad_config: dict | None = None,
):
    """Launch pipeline in background thread."""
    t = threading.Thread(
        target=run_pipeline,
        args=(job_id, video_path, clip_types, add_narration, count, audience, ad_config),
        daemon=True,
    )
    t.start()
    return job_id
