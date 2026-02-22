import json
import subprocess
import uuid
from pathlib import Path
import httpx
from .config import ELEVENLABS_API_KEY, OPENAI_API_KEY, TMP_DIR

OPENAI_VOICES = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}

ELEVENLABS_VOICE_IDS = {
    "Rachel": "21m00Tcm4TlvDq8ikWAM",
    "Bella":  "EXAVITQu4vr4xnSDxMaL",
    "Adam":   "pNInz6obpgDQGcFmaJgB",
    "Antoni": "ErXwobaYiN019PkySvjV",
}


def get_audio_duration(filepath: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", filepath],
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    for stream in data.get("streams", []):
        if "duration" in stream:
            return float(stream["duration"])
    return 10.0


async def _tts_openai(script: str, voice: str, out_path: Path) -> Path:
    if voice not in OPENAI_VOICES:
        voice = "shimmer"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": "tts-1", "input": script, "voice": voice},
        )
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
    return out_path


async def _tts_elevenlabs(script: str, voice: str, out_path: Path) -> Path:
    voice_id = ELEVENLABS_VOICE_IDS.get(voice, ELEVENLABS_VOICE_IDS["Rachel"])
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text": script,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
        )
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
    return out_path


async def generate_tts(
    script: str,
    voice: str = "shimmer",
    provider: str = "openai",
) -> dict:
    filename = f"{uuid.uuid4()}.mp3"
    out_path = TMP_DIR / filename

    if provider == "elevenlabs":
        await _tts_elevenlabs(script, voice, out_path)
    else:
        await _tts_openai(script, voice, out_path)

    duration = get_audio_duration(str(out_path))
    return {
        "audio_file": str(out_path),
        "duration": round(duration, 2),
        "audio_url": f"/api/audio/{filename}",
    }
