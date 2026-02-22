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
OUTBASE = f"{BASE}/reels_output"

# Source files
OFFICE = f"{CLIPS_DIR}/The Office Best Scenes.mp4"
SV1    = f"{CLIPS_DIR}/siliconvalley1.mp4"
SV2    = f"{CLIPS_DIR}/siliconvalley2.mp4"
SV3    = f"{CLIPS_DIR}/siliconvalley3.mp4"

VERSION = "v6"   # ← bump for each new batch

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
# v6: ALL clips selected via Gemini visual analysis — picking what LOOKS funny,
#     not just what sounds funny. Captions rewritten for unhinged TikTok energy.

CLIPS = [

    # ── THE OFFICE — visual analysis picks ───────────────────────────────

    (   # VISUAL: Dwight pointing in smoky chaos, people shoving past him
        # Gemini: [9/10] "PM tries to manage a Sev-1"
        "01_pm_managing_a_sev1_at_3am",
        OFFICE, 57, 12,
        "PM managing\na Sev-1 at 3am",
    ),
    (   # VISUAL: Michael declares door 'warm', everyone pivots to wrong door
        # Gemini: [8/10] "your solution breaks prod even worse"
        "02_your_hotfix_breaks_prod_even_worse",
        OFFICE, 77, 8,
        "your hotfix\nbreaks prod even worse",
    ),
    (   # VISUAL: Michael shoves past everyone — "everyone for himself!"
        # Gemini: [7/10] "CEO bails during layoff" — kept because it's 6s of pure gold
        "03_ceo_during_the_all_hands_layoff_call",
        OFFICE, 104, 6,
        "CEO during the\nall-hands layoff call",
    ),
    (   # Terry's favourite from v4 — keeping it
        # VISUAL: Michael drops last-minute demo changes with total sincerity
        "04_stakeholder_10_mins_before_the_demo",
        OFFICE, 1264, 7,
        "stakeholder 10 minutes\nbefore the demo",
    ),

    # ── SILICON VALLEY — visual analysis picks ────────────────────────────

    (   # VISUAL: Gavin: "That was horrible." — 6s reaction shot, no setup needed
        # Gemini: [8/10] "CEO seeing the AI demo"
        "05_ceo_seeing_the_ai_demo_we_built_for_3_months",
        SV1, 127, 7,
        "CEO seeing the AI demo\nwe built for 3 months",
    ),
    (   # VISUAL: entire room physically recoils at Gavin's billionaires comment
        # Gemini: [10/10] total shock reaction — maps to any unhinged CEO take
        "06_our_ceo_explaining_why_the_layoffs_are_good_actually",
        SV1, 308, 8,
        "our CEO explaining why\nthe layoffs are good actually",
    ),
    (   # VISUAL: man in suit aggressively pointing on private jet, scope creep
        # Gemini: [9/10] "one more thing to the sprint"
        "07_pm_adding_one_more_thing_to_the_sprint",
        SV2, 28, 13,
        "PM adding one more thing\nto the sprint",
    ),
    (   # VISUAL: Gavin looks at laptop, mutters "Goddamn motherfucker" — perfect loop
        # Gemini: [8/10] VC frustration — recaptioned for relatable dev energy
        "08_me_opening_slack_after_a_3day_weekend",
        SV2, 70, 10,
        "me opening Slack\nafter a 3-day weekend",
    ),
    (   # VISUAL: Erlich physically kicking a robot deer — the WHOLE JOKE is visual
        # Gemini: [9/10] completely missed by audio analysis
        "09_debugging_the_ai_agent_at_2am",
        SV3, 34, 10,
        "debugging the AI agent\nat 2am",
    ),
    (   # VISUAL: man in jail cell, orange jumpsuit, black eye — context we never had
        # Gemini: [8/10] recaptioned: AI agent left unsupervised
        "10_our_codebase_after_ai_had_unsupervised_access",
        SV3, 137, 10,
        "our codebase after the AI\nhad unsupervised access all weekend",
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


def build_vf(caption):
    lines   = auto_wrap(caption)
    fs      = font_size_for(lines)
    lh      = fs + 10
    block_h = len(lines) * lh
    block_y = max((VY - block_h) // 2, 24)

    filters = [f"scale={OW}:-2", f"pad={OW}:{OH}:(ow-iw)/2:(oh-ih)/2:black"]
    for i, line in enumerate(lines):
        filters.append(
            f"drawtext=fontfile='{FONT}':text='{esc(line)}':fontcolor=white"
            f":fontsize={fs}:borderw={BORDER}:bordercolor=black"
            f":x=(w-text_w)/2:y={block_y + i*lh}"
        )
    return ",".join(filters)


def render(out_dir, name, src, start, dur, caption):
    out = os.path.join(out_dir, f"{name}.mp4")
    r = subprocess.run([
        "ffmpeg", "-y", "-ss", str(start), "-i", src,
        "-t", str(dur), "-vf", build_vf(caption),
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
