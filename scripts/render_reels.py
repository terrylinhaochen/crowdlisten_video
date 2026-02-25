#!/usr/bin/env python3
"""
render_reels.py — Meme reels for TikTok/Instagram
Output: 1080x1920 (9:16), black background, video centered, Impact text burned in.

Versioning: bump VERSION for each new batch. Old batches stay untouched.
    python3 scripts/render_reels.py
"""

import subprocess, os, textwrap

FONT    = "/System/Library/Fonts/Supplemental/Impact.ttf"
BASE    = "/Users/terry/Desktop/crowdlisten_files/crowdlisten_marketing"
CLIPS_DIR = f"{BASE}/marketing_clips"
CHUNKS_DIR = f"{BASE}/processing/office_chunks"
OUTBASE = f"{BASE}/reels_output"

# Source files
OFFICE = f"{CLIPS_DIR}/The Office Best Scenes.mp4"
SV1    = f"{CLIPS_DIR}/siliconvalley1.mp4"
SV2    = f"{CLIPS_DIR}/siliconvalley2.mp4"
SV3    = f"{CLIPS_DIR}/siliconvalley3.mp4"
MF1    = f"{CLIPS_DIR}/modernfamily1.mp4"
MF2    = f"{CLIPS_DIR}/modernfamily2.mp4"
# v12: New SV cuts (Whisper transcript driven)
NSV1   = f"{CLIPS_DIR}/silicon_valley_1.mp4"
NSV2   = f"{CLIPS_DIR}/silicon_valley_2.mp4"
NSV3   = f"{CLIPS_DIR}/silicon_valley_3.mp4"
NSV4   = f"{CLIPS_DIR}/silicon_valley_4.mp4"

VERSION = "v12"   # ← bump for each new batch

OW, OH       = 1080, 1920
VH           = 608
VY           = (OH - VH) // 2   # 656 — y-offset of video top
BORDER       = 6
MAX_FONT     = 76
MIN_FONT     = 44
CHAR_W_RATIO = 0.50
CANVAS_W     = OW - 60

# ── CLIPS ────────────────────────────────────────────────────────────────────
# (name, source_file, start_sec, duration_sec, caption)
# v7: the_office_compilation.mp4 — Gemini visual analysis on 6 × 10-min chunks.
#     All clips score 8-9/10. CTA overlay added to all clips.

CLIPS = [

    # ── v12: New Silicon Valley cuts (Whisper transcript driven) ───────────

    (   # buzzword soup pitch — SV1 ~370s
        "01_making_the_world_a_better_place",
        NSV1, 370, 22,
        "Our pitch deck\nin 22 seconds",
    ),
    (   # asshole vacuum — SV1 ~281s
        "02_asshole_vacuum",
        NSV1, 281, 18,
        "Leadership advice\nnobody asked for",
    ),
    (   # startup nosedive speech — SV1 ~1292s
        "03_pulled_out_of_nosedive",
        NSV1, 1292, 18,
        "VC after the\nbridge round closes",
    ),
    (   # Peter Gregory is dead — SV2 ~58s
        "04_peter_gregory_is_dead",
        NSV2, 58, 10,
        "When your lead investor\ngoes quiet",
    ),
    (   # dick up and flat broke — SV2 ~743s
        "05_dick_up_flat_broke",
        NSV2, 743, 16,
        "PM at end of\nQ4 runway",
    ),
    (   # $14k smart fridge / fat and poor — SV2 ~903s
        "06_smart_fridge",
        NSV2, 903, 22,
        "When the eng team\nwants a new tool",
    ),
    (   # This guy fucks — Russ intro — SV3 ~6s
        "07_this_guy_fucks",
        NSV3, 6, 16,
        "Investors meeting\nthe founding team",
    ),
    (   # billionaire math: less than a CD — SV3 ~105s
        "08_less_than_a_cd",
        NSV3, 105, 20,
        "VC explaining\nROI to LPs",
    ),
    (   # new internet vision — SV3 ~679s
        "09_new_internet",
        NSV3, 679, 22,
        "Founder after\nreading Paul Graham",
    ),
    (   # 36 ICOs one worked — SV3 ~808s
        "10_36_icos",
        NSV3, 808, 24,
        "Me after my\ncrypto strategy",
    ),
    (   # Jared ghost-like features intro — SV4 ~0s
        "11_ghost_like_features",
        NSV4, 0, 14,
        "New hire on\nday one at a startup",
    ),
    (   # driverless car to Errolon — SV4 ~208s
        "12_driverless_car",
        NSV4, 208, 26,
        "When AI takes over\nyour calendar",
    ),

]
# ─────────────────────────────────────────────────────────────────────────────


def auto_wrap(text, max_chars=26):
    result = []
    for seg in text.split("\n"):
        result.extend(textwrap.wrap(seg, width=max_chars) if len(seg) > max_chars else [seg])
    return result


def font_size_for(lines):
    max_len = max(len(l) for l in lines) if lines else 1
    return max(MIN_FONT, min(MAX_FONT, int(CANVAS_W / (max_len * CHAR_W_RATIO))))


def esc(t):
    return (t
            .replace("\\", "\\\\")
            .replace("'",  "\u2019")   # curly apostrophe — no ffmpeg escape issues
            .replace("'",  "\u2019")   # curly open-quote too
            .replace(":",  "\\:")
            .replace(",",  "\\,"))


CTA_LINE1 = "The PM for AI Agents"
CTA_LINE2 = "crowdlisten.com"
CTA_FONT  = "/System/Library/Fonts/Helvetica.ttc"   # clean sans-serif for CTA
CTA_FS1   = 34    # brand tagline
CTA_FS2   = 42    # URL — slightly bigger for readability
CTA_COLOR = "0xD97D55"  # CrowdListen coral
VIDEO_BOT = VY + VH     # y where video ends = 1264
LOGO_PATH = f"{BASE}/brand_assets/CRD.png"
LOGO_W    = 220


def build_vf(caption):
    lines   = auto_wrap(caption)
    fs      = font_size_for(lines)
    lh      = fs + 10
    block_h = len(lines) * lh
    block_y = max((VY - block_h) // 2, 24)

    bottom_space = OH - VIDEO_BOT
    cta_block_h  = CTA_FS1 + 10 + CTA_FS2 + 10
    text_top     = VIDEO_BOT + (bottom_space - cta_block_h) // 2

    filters = [f"scale={OW}:-2", f"pad={OW}:{OH}:(ow-iw)/2:(oh-ih)/2:black"]

    # Meme caption (top area, white Impact)
    for i, line in enumerate(lines):
        filters.append(
            f"drawtext=fontfile='{FONT}':text='{esc(line)}':fontcolor=white"
            f":fontsize={fs}:borderw={BORDER}:bordercolor=black"
            f":x=(w-text_w)/2:y={block_y + i*lh}"
        )

    # CTA tagline
    filters.append(
        f"drawtext=fontfile='{CTA_FONT}':text='{esc(CTA_LINE1)}':fontcolor={CTA_COLOR}"
        f":fontsize={CTA_FS1}:borderw=3:bordercolor=black"
        f":x=(w-text_w)/2:y={text_top}"
    )
    # CTA URL
    filters.append(
        f"drawtext=fontfile='{CTA_FONT}':text='{esc(CTA_LINE2)}':fontcolor=white"
        f":fontsize={CTA_FS2}:borderw=3:bordercolor=black"
        f":x=(w-text_w)/2:y={text_top + CTA_FS1 + 10}"
    )

    return ",".join(filters)


def render(out_dir, name, src, start, dur, caption):
    out = os.path.join(out_dir, f"{name}.mp4")
    r = subprocess.run([
        "ffmpeg", "-y", "-i", src,
        "-ss", str(start), "-t", str(dur),
        "-vf", build_vf(caption),
        "-map", "0:v", "-map", "0:a",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out,
    ], capture_output=True, text=True)

    if r.returncode == 0:
        mb = os.path.getsize(out) / 1024 / 1024
        fs = font_size_for(auto_wrap(caption))
        src_name = os.path.basename(src).replace(".mp4","")
        print(f"  ✅  [{dur:2d}s] {name}  ({mb:.1f} MB, {fs}px) [{src_name}]")
    else:
        print(f"  ❌  {name}\n{r.stderr[-300:]}")


if __name__ == "__main__":
    out_dir = os.path.join(OUTBASE, VERSION)
    os.makedirs(out_dir, exist_ok=True)
    print(f"Rendering {len(CLIPS)} clips → {out_dir}\n")
    for name, src, start, dur, caption in CLIPS:
        render(out_dir, name, src, start, dur, caption)
    print(f"\nDone → {out_dir}")
