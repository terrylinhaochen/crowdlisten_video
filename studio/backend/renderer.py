"""
renderer.py — ffmpeg rendering for meme clips and speaker quotes
Output: 1080x1920 (9:16), black background
"""
import os
import subprocess
import textwrap
from pathlib import Path

FONT_IMPACT   = "/System/Library/Fonts/Supplemental/Impact.ttf"
FONT_HELVETICA = "/System/Library/Fonts/Helvetica.ttc"
OW, OH        = 1080, 1920
VH            = 608
VY            = (OH - VH) // 2   # video y-offset = 656
VIDEO_BOT     = VY + VH           # = 1264
BORDER        = 6
MAX_FONT      = 76
MIN_FONT      = 44
CHAR_W_RATIO  = 0.50
CANVAS_W      = OW - 60
CTA_COLOR     = "0xD97D55"
CTA_FONT_SIZE1 = 34
CTA_FONT_SIZE2 = 42
CTA_LINE1     = "The PM for AI Agents"
CTA_LINE2     = "crowdlisten.com"


def _esc(t: str) -> str:
    return (t
            .replace("\\", "\\\\")
            .replace("'", "\u2019")
            .replace("\u2018", "\u2019")
            .replace(":", "\\:")
            .replace(",", "\\,"))


def _auto_wrap(text: str, max_chars: int = 26) -> list[str]:
    result = []
    for seg in text.split("\n"):
        result.extend(textwrap.wrap(seg, width=max_chars) if len(seg) > max_chars else [seg])
    return result


def _font_size(lines: list[str]) -> int:
    max_len = max(len(l) for l in lines) if lines else 1
    return max(MIN_FONT, min(MAX_FONT, int(CANVAS_W / (max_len * CHAR_W_RATIO))))


def _render_meme(source: Path, out: Path, start: float, duration: float,
                 caption: str, add_cta: bool = False):
    lines = _auto_wrap(caption)
    fs = _font_size(lines)
    lh = fs + 10
    block_h = len(lines) * lh
    block_y = max((VY - block_h) // 2, 24)

    filters = [
        f"scale={OW}:-2",
        f"pad={OW}:{OH}:(ow-iw)/2:(oh-ih)/2:black",
    ]

    for i, line in enumerate(lines):
        filters.append(
            f"drawtext=fontfile='{FONT_IMPACT}':text='{_esc(line)}':fontcolor=white"
            f":fontsize={fs}:borderw={BORDER}:bordercolor=black"
            f":x=(w-text_w)/2:y={block_y + i * lh}"
        )

    if add_cta:
        bottom_space = OH - VIDEO_BOT
        cta_block_h = CTA_FONT_SIZE1 + 10 + CTA_FONT_SIZE2 + 10
        text_top = VIDEO_BOT + (bottom_space - cta_block_h) // 2
        filters.append(
            f"drawtext=fontfile='{FONT_HELVETICA}':text='{_esc(CTA_LINE1)}'"
            f":fontcolor={CTA_COLOR}:fontsize={CTA_FONT_SIZE1}"
            f":borderw=3:bordercolor=black:x=(w-text_w)/2:y={text_top}"
        )
        filters.append(
            f"drawtext=fontfile='{FONT_HELVETICA}':text='{_esc(CTA_LINE2)}'"
            f":fontcolor=white:fontsize={CTA_FONT_SIZE2}"
            f":borderw=3:bordercolor=black:x=(w-text_w)/2:y={text_top + CTA_FONT_SIZE1 + 10}"
        )

    r = subprocess.run([
        "ffmpeg", "-y", "-i", str(source),
        "-ss", str(start), "-t", str(duration),
        "-vf", ",".join(filters),
        "-map", "0:v", "-map", "0:a",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Meme render failed: {r.stderr[-300:]}")


def _render_quote(source: Path, out: Path, start: float, duration: float,
                  quote: str, add_cta: bool = False):
    lines = _auto_wrap(quote, max_chars=32)
    fs = 52
    lh = fs + 14
    block_h = len(lines) * lh
    block_y = (OH - block_h) // 2

    filters = [
        f"scale={OW}:{OH}:force_original_aspect_ratio=increase",
        f"crop={OW}:{OH}",
        # dark overlay
        f"drawbox=x=0:y=0:w={OW}:h={OH}:color=black@0.55:t=fill",
    ]

    for i, line in enumerate(lines):
        filters.append(
            f"drawtext=fontfile='{FONT_HELVETICA}':text='{_esc(line)}':fontcolor=white"
            f":fontsize={fs}:borderw=3:bordercolor=black@0.8"
            f":x=(w-text_w)/2:y={block_y + i * lh}"
        )

    if add_cta:
        cta_y = OH - 140
        filters.append(
            f"drawtext=fontfile='{FONT_HELVETICA}':text='{_esc(CTA_LINE1)}'"
            f":fontcolor={CTA_COLOR}:fontsize=30:borderw=2:bordercolor=black"
            f":x=(w-text_w)/2:y={cta_y}"
        )
        filters.append(
            f"drawtext=fontfile='{FONT_HELVETICA}':text='{_esc(CTA_LINE2)}'"
            f":fontcolor=white:fontsize=36:borderw=2:bordercolor=black"
            f":x=(w-text_w)/2:y={cta_y + 40}"
        )

    r = subprocess.run([
        "ffmpeg", "-y", "-i", str(source),
        "-ss", str(start), "-t", str(duration),
        "-vf", ",".join(filters),
        "-map", "0:v", "-map", "0:a",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Quote render failed: {r.stderr[-300:]}")


def _render_ad_image(image_path: Path, out: Path, duration: int = 5):
    """Convert static image to video segment."""
    r = subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
        "-t", str(duration), "-vf", f"scale={OW}:{OH}:force_original_aspect_ratio=increase,crop={OW}:{OH}",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-an", "-movflags", "+faststart", str(out),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Ad image render failed: {r.stderr[-300:]}")


def _normalize_clip(src: Path, out: Path):
    """Normalize any clip to 1080x1920 for concat."""
    r = subprocess.run([
        "ffmpeg", "-y", "-i", str(src),
        "-vf", f"scale={OW}:{OH}:force_original_aspect_ratio=increase,crop={OW}:{OH},setsar=1",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k", str(out),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Normalize failed: {r.stderr[-300:]}")


def concat_with_ad(clip_paths: list[Path], ad_path: Path, out: Path,
                   placement: str = "end", frequency: int = 2,
                   image_duration: int = 5):
    """Concatenate clips with ad insertion."""
    tmp_dir = out.parent / "tmp_concat"
    tmp_dir.mkdir(exist_ok=True)

    # Prepare ad segment
    ad_ext = ad_path.suffix.lower()
    ad_video = tmp_dir / "ad_norm.mp4"
    if ad_ext in (".jpg", ".jpeg", ".png", ".webp"):
        _render_ad_image(ad_path, ad_video, duration=image_duration)
    else:
        _normalize_clip(ad_path, ad_video)

    # Build sequence
    sequence = []
    for i, clip in enumerate(clip_paths):
        norm = tmp_dir / f"clip_{i:03d}.mp4"
        _normalize_clip(clip, norm)
        sequence.append(norm)
        if placement in ("between", "both") and (i + 1) % frequency == 0 and i < len(clip_paths) - 1:
            sequence.append(ad_video)

    if placement in ("end", "both"):
        sequence.append(ad_video)

    # Write concat list
    concat_list = tmp_dir / "concat.txt"
    concat_list.write_text("\n".join(f"file '{p}'" for p in sequence))

    r = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Concat failed: {r.stderr[-300:]}")


def render_clip(source: Path, out_dir: Path, index: int, clip: dict,
                add_cta: bool = False) -> Path:
    """Render a single clip candidate. Returns output path."""
    clip_type = clip.get("type", "meme")
    start = float(clip.get("timestamp", 0))
    duration = float(clip.get("duration", 15))

    if clip_type == "meme":
        caption = clip.get("caption", "")
        name = f"{index:02d}_meme_{int(start)}s.mp4"
        out = out_dir / name
        _render_meme(source, out, start, duration, caption, add_cta=add_cta)
    else:
        quote = clip.get("quote", "")
        name = f"{index:02d}_quote_{int(start)}s.mp4"
        out = out_dir / name
        _render_quote(source, out, start, duration, quote, add_cta=add_cta)

    return out
