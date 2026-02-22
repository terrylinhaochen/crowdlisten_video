#!/usr/bin/env python3
"""
analyze_video.py — Visual scene analysis via Gemini Files API

Uploads a video to Gemini, asks it to find meme-worthy moments with timestamps,
and outputs a JSON analysis file you can use to pick clips for render_reels.py.

Usage:
    python3 scripts/analyze_video.py marketing_clips/siliconvalley1.mp4
    python3 scripts/analyze_video.py marketing_clips/siliconvalley1.mp4 --model gemini-1.5-pro
    python3 scripts/analyze_video.py marketing_clips/siliconvalley1.mp4 --audience "engineers"

Output: processing/<filename>_visual_analysis.json
"""

import os, sys, time, json, argparse
from pathlib import Path
from google import genai
from google.genai import types

# ── Config ────────────────────────────────────────────────────────────────────
BASE       = Path(__file__).parent.parent
TRANSCRIPTS = BASE / "processing"
API_KEY    = os.environ.get("GEMINI_API_KEY", "")

DEFAULT_MODEL    = "gemini-2.0-flash"
AUDIENCE_DEFAULT = "tech workers: PMs, engineers, founders, VCs. Familiar with startup culture, AI tools, vibe coding, DeepSeek, DOGE, sprint planning, product demos gone wrong."
# ─────────────────────────────────────────────────────────────────────────────

ANALYSIS_PROMPT = """
You are a meme content strategist for a TikTok/Instagram account targeting {audience}

Watch this video compilation carefully and identify the {n} most meme-worthy moments.

For each moment, provide:
1. TIMESTAMP: exact start time (MM:SS format)
2. DURATION: how many seconds the clip should be (aim for 8-15s, max 25s)
3. WHAT_HAPPENS_VISUALLY: describe what you SEE — body language, reactions, facial expressions, physical actions, setting. Be specific. This is what distinguishes visual analysis from transcript analysis.
4. DIALOGUE_HOOK: the key line(s) being said (the punchline)
5. MEME_CAPTION: a punchy 1-2 line caption (max 28 chars/line) that reframes the scene for the tech/startup audience. Write it how it would actually appear on TikTok — specific, confessional, unhinged if warranted.
6. NEWS_HOOK: optional — connect to a current event (DeepSeek, vibe coding, DOGE, YC, Claude, Cursor, etc.) if it strengthens the caption
7. MEME_SCORE: rate 1-10 (10 = instant viral)
8. AUDIENCE: who specifically shares this (engineers? founders? VCs? PMs?)
9. WHY_IT_WORKS: one sentence on the visual mechanism — what makes this SCENE (not just the words) land

Return ONLY valid JSON in this exact format:
{{
  "source_file": "{filename}",
  "model": "{model}",
  "clips": [
    {{
      "rank": 1,
      "timestamp": "MM:SS",
      "start_seconds": 123,
      "duration_seconds": 12,
      "what_happens_visually": "...",
      "dialogue_hook": "...",
      "meme_caption": "line 1\\nline 2",
      "news_hook": "...",
      "meme_score": 9,
      "audience": "...",
      "why_it_works": "..."
    }}
  ]
}}
"""

def upload_and_wait(client, video_path):
    """Upload video to Gemini Files API and wait for processing."""
    print(f"  Uploading {Path(video_path).name} ({Path(video_path).stat().st_size/1024/1024:.1f} MB)...")
    
    video_file = client.files.upload(file=video_path)
    print(f"  Upload complete. File URI: {video_file.uri}")
    print(f"  Waiting for Gemini to process video", end="", flush=True)
    
    while True:
        video_file = client.files.get(name=video_file.name)
        state = video_file.state.name
        if state == "ACTIVE":
            print(" ✅")
            return video_file
        elif state == "FAILED":
            raise RuntimeError(f"Video processing failed: {video_file.error}")
        else:
            print(".", end="", flush=True)
            time.sleep(4)


def analyze(video_path, model=DEFAULT_MODEL, audience=AUDIENCE_DEFAULT, n_clips=12):
    if not API_KEY:
        sys.exit("❌ GEMINI_API_KEY not set")
    
    video_path = Path(video_path)
    if not video_path.exists():
        sys.exit(f"❌ File not found: {video_path}")
    
    out_path = TRANSCRIPTS / f"{video_path.stem}_visual_analysis.json"
    
    print(f"\n🎬 Analyzing: {video_path.name}")
    print(f"   Model: {model} | Clips: {n_clips}")

    client = genai.Client(api_key=API_KEY)

    # 1. Upload
    video_file = upload_and_wait(client, str(video_path))
    
    # 2. Build prompt
    prompt = ANALYSIS_PROMPT.format(
        audience=audience,
        n=n_clips,
        filename=video_path.name,
        model=model,
    )
    
    # 3. Query Gemini
    print(f"  Sending to {model} for visual analysis...")
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_uri(file_uri=video_file.uri, mime_type="video/mp4"),
            prompt,
        ],
        config=types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=8192,
        ),
    )
    
    # 4. Parse JSON
    raw = response.text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
    if raw.endswith("```"):
        raw = "\n".join(raw.split("\n")[:-1])
    
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON parse error: {e}")
        print("Raw response saved to processing/raw_response.txt")
        (TRANSCRIPTS / "raw_response.txt").write_text(raw)
        sys.exit(1)
    
    # 5. Save
    TRANSCRIPTS.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2))
    
    # 6. Print summary
    print(f"\n✅ Analysis saved → {out_path}\n")
    print(f"{'Rank':<5} {'Score':<6} {'Time':<8} {'Dur':<5} {'Caption'}")
    print("-" * 70)
    for clip in data.get("clips", []):
        caption_preview = clip.get("meme_caption","").replace("\n"," / ")[:40]
        print(f"  {clip.get('rank','?'):<4} {clip.get('meme_score','?'):<6} "
              f"{clip.get('timestamp','?'):<8} {clip.get('duration_seconds','?'):<5} {caption_preview}")
    
    # 7. Cleanup uploaded file
    try:
        client.files.delete(name=video_file.name)
        print(f"\n  🗑  Cleaned up Gemini upload ({video_file.name})")
    except Exception:
        pass
    
    return out_path


def print_clips_for_render(analysis_path):
    """Print CLIPS entries ready to paste into render_reels.py."""
    data = json.loads(Path(analysis_path).read_text())
    src_file = data.get("source_file", "")
    
    print(f"\n# ── Paste into render_reels.py CLIPS list ──")
    print(f"# Source: {src_file}\n")
    for clip in sorted(data["clips"], key=lambda x: -x.get("meme_score", 0)):
        score  = clip.get("meme_score", 0)
        name   = clip.get("meme_caption","caption").replace("\n","_").replace(" ","_")[:50].lower()
        name   = "".join(c if c.isalnum() or c == "_" else "" for c in name)
        start  = clip.get("start_seconds", 0)
        dur    = clip.get("duration_seconds", 12)
        caption = clip.get("meme_caption", "")
        why    = clip.get("why_it_works","")
        
        print(f"    (  # [{score}/10] {why[:60]}")
        print(f"        \"{name}\",")
        print(f"        SRC, {start}, {dur},")
        print(f"        \"{caption}\",")
        print(f"    ),")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze video for meme moments via Gemini")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        choices=["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
                        help="Gemini model (default: gemini-2.0-flash)")
    parser.add_argument("--audience", default=AUDIENCE_DEFAULT, help="Target audience description")
    parser.add_argument("--clips", type=int, default=12, help="Number of clips to find (default: 12)")
    parser.add_argument("--print-render", action="store_true",
                        help="Print CLIPS entries for render_reels.py after analysis")
    args = parser.parse_args()
    
    out = analyze(args.video, model=args.model, audience=args.audience, n_clips=args.clips)
    if args.print_render:
        print_clips_for_render(out)
