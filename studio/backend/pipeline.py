"""
pipeline.py — ffmpeg video assembly: hook → body → CTA → concat
All output is 1080x1920 (9:16 vertical), libx264, aac.
"""
import asyncio
import os
import subprocess
import textwrap
import uuid
from pathlib import Path

from .config import BASE_DIR, FONT_PATH, LOGO_PATH, PUBLISHED_DIR, TMP_DIR
from .tts import generate_tts, get_audio_duration

OW, OH = 1080, 1920
VH = 608                         # video content height after scale
VY = (OH - VH) // 2             # y-offset where video content sits (656)
MAX_FONT, MIN_FONT = 76, 44
CHAR_W_RATIO = 0.50
CANVAS_W = OW - 60
BORDER = 6


# ── helpers ────────────────────────────────────────────────────────────────

def esc(t: str) -> str:
    return (
        t.replace("\\", "\\\\")
         .replace("'", "\u2019")
         .replace("\u2018", "\u2019")
         .replace(":", "\\:")
         .replace(",", "\\,")
    )


def auto_wrap(text: str, max_chars: int = 26) -> list[str]:
    result = []
    for seg in text.split("\n"):
        result.extend(textwrap.wrap(seg, width=max_chars) if len(seg) > max_chars else [seg])
    return result


def font_size_for(lines: list[str]) -> int:
    max_len = max(len(l) for l in lines) if lines else 1
    return max(MIN_FONT, min(MAX_FONT, int(CANVAS_W / (max_len * CHAR_W_RATIO))))


def run_ff(*args, check=True):
    """Run ffmpeg, raise on failure."""
    cmd = ["ffmpeg", "-y", *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-800:]}")
    return result


# ── step 1: hook ────────────────────────────────────────────────────────────

def render_hook(clip_id: str, source_file: str, start_sec: int, duration_sec: int, caption: str) -> str:
    out = str(TMP_DIR / f"hook_{clip_id}.mp4")
    lines = auto_wrap(caption)
    fs = font_size_for(lines)
    lh = fs + 10
    block_h = len(lines) * lh
    block_y = max((VY - block_h) // 2, 24)

    filters = [
        f"scale={OW}:-2",
        f"pad={OW}:{OH}:(ow-iw)/2:(oh-ih)/2:black",
    ]
    for i, line in enumerate(lines):
        filters.append(
            f"drawtext=fontfile='{FONT_PATH}':text='{esc(line)}':fontcolor=white"
            f":fontsize={fs}:borderw={BORDER}:bordercolor=black"
            f":x=(w-text_w)/2:y={block_y + i * lh}"
        )

    run_ff(
        "-ss", str(start_sec), "-i", source_file, "-t", str(duration_sec),
        "-vf", ",".join(filters),
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        out,
    )
    return out


# ── step 2: body ────────────────────────────────────────────────────────────

def render_body(job_id: str, script: str, audio_file: str, audio_duration: float) -> str:
    out = str(TMP_DIR / f"body_{job_id}.mp4")
    lines = auto_wrap(script, max_chars=32)
    fs = 54
    lh = fs + 12
    # Position: bottom third, start at ~75% down
    base_y = int(OH * 0.72)

    subtitle_filters = []
    for i, line in enumerate(lines[:6]):  # max 6 subtitle lines
        subtitle_filters.append(
            f"drawtext=fontfile='{FONT_PATH}':text='{esc(line)}':fontcolor=white"
            f":fontsize={fs}:borderw=4:bordercolor=black"
            f":x=(w-text_w)/2:y={base_y + i * lh}"
        )

    # filter_complex: color bg → overlay logo → drawtext subtitles
    # [0] = color source (bg), [1] = logo
    logo_filter = (
        "[1:v]scale=120:-1,format=rgba,colorchannelmixer=aa=0.5[logo];"
        "[0:v][logo]overlay=W-120-20:20[bg_logo]"
    )
    sub_chain = "[bg_logo]" + ",".join(subtitle_filters) + "[v]" if subtitle_filters else "[bg_logo]copy[v]"
    filter_complex = f"{logo_filter};{sub_chain}"

    run_ff(
        "-f", "lavfi",
        "-i", f"color=c=0x0f0f0f:s={OW}x{OH}:r=30",
        "-i", LOGO_PATH,
        "-i", audio_file,
        "-t", str(audio_duration),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "2:a",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        out,
    )
    return out


# ── step 3: CTA card ────────────────────────────────────────────────────────

def render_cta(job_id: str, tagline: str) -> str:
    out = str(TMP_DIR / f"cta_{job_id}.mp4")

    logo_y = OH // 2 - 300 - 40
    tagline_y = OH // 2 + 40
    url_y = OH // 2 + 120

    filter_complex = (
        "[1:v]scale=300:-1,format=rgba[logo];"
        f"[0:v][logo]overlay=(W-300)/2:{logo_y}[bg_logo];"
        f"[bg_logo]"
        f"drawtext=fontfile='{FONT_PATH}':text='{esc(tagline)}':fontcolor=white"
        f":fontsize=48:borderw=4:bordercolor=black:x=(w-text_w)/2:y={tagline_y},"
        f"drawtext=fontfile='{FONT_PATH}':text='crowdlisten.com':fontcolor=#cccccc"
        f":fontsize=36:borderw=3:bordercolor=black:x=(w-text_w)/2:y={url_y}"
        "[v]"
    )

    run_ff(
        "-f", "lavfi",
        "-i", f"color=c=black:s={OW}x{OH}:r=30",
        "-i", LOGO_PATH,
        "-t", "5",
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-movflags", "+faststart",
        out,
    )
    return out


def add_silent_audio(video_path: str, duration: float) -> str:
    """Add a silent audio track to a video (needed for concat)."""
    out = video_path.replace(".mp4", "_audio.mp4")
    run_ff(
        "-i", video_path,
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(duration),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        out,
    )
    return out


# ── step 4: assemble ────────────────────────────────────────────────────────

def assemble(job_id: str, hook_file: str, body_file: str, cta_file: str, output_name: str) -> str:
    cta_with_audio = add_silent_audio(cta_file, 5.0)
    out = str(PUBLISHED_DIR / f"{output_name}.mp4")

    run_ff(
        "-i", hook_file,
        "-i", body_file,
        "-i", cta_with_audio,
        "-filter_complex",
        "[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        out,
    )
    # cleanup cta_with_audio temp
    try:
        os.remove(cta_with_audio)
    except Exception:
        pass
    return out


# ── step 5: cleanup ─────────────────────────────────────────────────────────

def cleanup_tmp(job_id: str, clip_id: str):
    for prefix in [f"hook_{clip_id}", f"body_{job_id}", f"cta_{job_id}"]:
        for f in TMP_DIR.glob(f"{prefix}*.mp4"):
            try:
                f.unlink()
            except Exception:
                pass


# ── main entry ──────────────────────────────────────────────────────────────

def run_pipeline(job: dict) -> dict:
    """
    Synchronous pipeline runner (called from background thread in queue.py).
    job keys: id, hook_clip_id, source_file, start_sec, duration_sec,
              hook_caption, body_script, body_audio_file (optional),
              cta_tagline, output_name
    """
    job_id = job["id"]
    clip_id = job["hook_clip_id"]

    hook_file = None
    body_file = None
    cta_file = None

    try:
        # Step 1 — Hook
        hook_file = render_hook(
            clip_id,
            job["source_file"],
            job["start_sec"],
            job["duration_sec"],
            job["hook_caption"],
        )

        # Step 2 — Body (TTS if no audio provided)
        audio_file = job.get("body_audio_file")
        if audio_file and Path(audio_file).exists():
            audio_duration = get_audio_duration(audio_file)
        else:
            # Run async TTS in a new event loop from this sync thread
            tts_result = asyncio.run(
                generate_tts(job["body_script"], voice="shimmer", provider="openai")
            )
            audio_file = tts_result["audio_file"]
            audio_duration = tts_result["duration"]

        body_file = render_body(job_id, job["body_script"], audio_file, audio_duration)

        # Step 3 — CTA
        cta_file = render_cta(job_id, job.get("cta_tagline", "Understand your audience."))

        # Step 4 — Assemble
        output_file = assemble(job_id, hook_file, body_file, cta_file, job["output_name"])

        # Step 5 — Cleanup
        cleanup_tmp(job_id, clip_id)

        return {"output_file": output_file, "status": "done"}

    except Exception:
        # Cleanup on error
        for f in [hook_file, body_file, cta_file]:
            if f:
                try:
                    Path(f).unlink()
                except Exception:
                    pass
        raise
