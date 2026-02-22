from pathlib import Path
from datetime import datetime, timezone, date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import PUBLISHED_DIR, TMP_DIR
from . import clips as clip_lib
from . import queue as q

app = FastAPI(title="CrowdListen Studio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    from .queue import start_processor
    start_processor()


# ── Clips ────────────────────────────────────────────────────────────────────

@app.get("/api/clips")
def list_clips(source: str | None = None, min_score: int = 0):
    return clip_lib.load_clips(source=source, min_score=min_score)


@app.get("/api/clips/{clip_id}")
def get_clip(clip_id: str):
    c = clip_lib.get_clip(clip_id)
    if not c:
        raise HTTPException(404, "Clip not found")
    return c


@app.get("/api/clips/{clip_id}/video")
def clip_video(clip_id: str):
    mp4 = clip_lib.find_rendered_mp4(clip_id)
    if not mp4:
        raise HTTPException(404, "No rendered video for this clip")
    return FileResponse(str(mp4), media_type="video/mp4")


# ── TTS ──────────────────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    script: str
    voice: str = "shimmer"
    provider: str = "openai"


@app.post("/api/tts")
async def generate_tts(req: TTSRequest):
    from .tts import generate_tts as do_tts
    result = await do_tts(req.script, req.voice, req.provider)
    return result


@app.get("/api/audio/{filename}")
def serve_audio(filename: str):
    path = TMP_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Audio file not found")
    return FileResponse(str(path), media_type="audio/mpeg")


# ── Render ───────────────────────────────────────────────────────────────────

class RenderRequest(BaseModel):
    hook_clip_id: str
    hook_caption: str
    body_script: str
    body_audio_file: str | None = None
    cta_tagline: str = "Understand your audience."
    output_name: str


@app.post("/api/render", status_code=202)
def submit_render(req: RenderRequest):
    clip = clip_lib.get_clip(req.hook_clip_id)
    if not clip:
        raise HTTPException(404, f"Clip not found: {req.hook_clip_id}")

    job = q.build_job(
        hook_clip_id=req.hook_clip_id,
        hook_caption=req.hook_caption,
        body_script=req.body_script,
        body_audio_file=req.body_audio_file,
        cta_tagline=req.cta_tagline,
        output_name=req.output_name,
        source_file=clip["source_file"],
        start_sec=clip["start_seconds"],
        duration_sec=clip["duration_seconds"],
    )
    q.add_job(job)
    return job


# ── Queue ────────────────────────────────────────────────────────────────────

@app.get("/api/queue")
def get_queue():
    return list(reversed(q.load_queue()))


@app.delete("/api/queue/{job_id}")
def delete_job(job_id: str):
    if not q.remove_job(job_id):
        raise HTTPException(404, "Job not found")
    return {"ok": True}


# ── Published ────────────────────────────────────────────────────────────────

@app.get("/api/published")
def list_published():
    today = date.today()
    videos = []
    today_count = 0

    if PUBLISHED_DIR.exists():
        for mp4 in sorted(PUBLISHED_DIR.glob("*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True):
            mtime = datetime.fromtimestamp(mp4.stat().st_mtime, tz=timezone.utc)
            size_mb = round(mp4.stat().st_size / 1024 / 1024, 1)
            if mtime.date() == today:
                today_count += 1
            videos.append({
                "filename": mp4.name,
                "size_mb": size_mb,
                "created_at": mtime.isoformat(),
                "url": f"/api/published/{mp4.name}",
            })

    return {"videos": videos, "today_count": today_count, "daily_target": 2}


@app.get("/api/published/{filename}")
def serve_published(filename: str):
    path = PUBLISHED_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Video not found")
    return FileResponse(str(path), media_type="video/mp4")


# ── Static frontend (must be last) ──────────────────────────────────────────

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
