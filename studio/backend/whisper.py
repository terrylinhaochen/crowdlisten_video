"""
whisper.py — Audio extraction + OpenAI Whisper transcription
"""
import json
import os
import subprocess
from pathlib import Path

import httpx

from .config import PROCESSING_DIR, OPENAI_API_KEY


def extract_audio(video_path: Path, job_id: str) -> Path:
    """Extract mono 16kHz audio from video using ffmpeg."""
    audio_path = PROCESSING_DIR / f"{job_id}_audio.mp3"
    result = subprocess.run([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-ar", "16000", "-ac", "1", "-b:a", "32k",
        str(audio_path)
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr[-500:]}")
    return audio_path


def transcribe(audio_path: Path, job_id: str) -> dict:
    """Transcribe audio via OpenAI Whisper API. Returns verbose_json with segments."""
    transcript_path = PROCESSING_DIR / f"{job_id}_transcript.json"

    # Return cached if exists
    if transcript_path.exists():
        return json.loads(transcript_path.read_text())

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    response = httpx.post(
        "https://api.openai.com/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        data={"model": "whisper-1", "response_format": "verbose_json"},
        files={"file": (audio_path.name, audio_bytes, "audio/mpeg")},
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    transcript_path.write_text(json.dumps(data, indent=2))
    return data
