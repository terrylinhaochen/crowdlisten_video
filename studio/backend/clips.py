import json
from pathlib import Path
from .config import PROCESSING_DIR, MARKETING_CLIPS_DIR, REELS_OUTPUT_DIR

SOURCE_MAP = {
    "The Office Best Scenes_visual_analysis": {
        "slug": "office",
        "label": "The Office",
        "file": "The Office Best Scenes.mp4",
    },
    "siliconvalley1_visual_analysis": {
        "slug": "sv1",
        "label": "Silicon Valley 1",
        "file": "siliconvalley1.mp4",
    },
    "siliconvalley2_visual_analysis": {
        "slug": "sv2",
        "label": "Silicon Valley 2",
        "file": "siliconvalley2.mp4",
    },
    "siliconvalley3_visual_analysis": {
        "slug": "sv3",
        "label": "Silicon Valley 3",
        "file": "siliconvalley3.mp4",
    },
}


def _rendered_slugs() -> set[str]:
    """Build a set of slugs present in any reels_output subfolder."""
    slugs: set[str] = set()
    if REELS_OUTPUT_DIR.exists():
        for mp4 in REELS_OUTPUT_DIR.rglob("*.mp4"):
            slugs.add(mp4.stem)
    return slugs


def load_clips(source: str | None = None, min_score: int = 0) -> list[dict]:
    rendered = _rendered_slugs()
    clips: list[dict] = []

    for json_path in PROCESSING_DIR.glob("*_visual_analysis.json"):
        stem = json_path.stem  # e.g. "siliconvalley1_visual_analysis"
        meta = SOURCE_MAP.get(stem)
        if not meta:
            continue

        slug = meta["slug"]
        if source and source != slug:
            continue

        try:
            data = json.loads(json_path.read_text())
        except Exception:
            continue

        raw_clips = data.get("top_clips") or data.get("clips") or []
        source_file = str(MARKETING_CLIPS_DIR / meta["file"])

        for c in raw_clips:
            score = c.get("meme_score", 0)
            if score < min_score:
                continue
            start = c.get("start_seconds", 0)
            clip_id = f"{slug}_{start}"

            # Check if rendered: look for any filename containing clip_id OR source+start pattern
            is_rendered = any(clip_id in s for s in rendered)

            clips.append(
                {
                    "clip_id": clip_id,
                    "source_slug": slug,
                    "source_label": meta["label"],
                    "source_file": source_file,
                    "rank": c.get("rank"),
                    "timestamp": c.get("timestamp", ""),
                    "start_seconds": start,
                    "duration_seconds": c.get("duration_seconds", 10),
                    "what_happens_visually": c.get("what_happens_visually", ""),
                    "dialogue_hook": c.get("dialogue_hook", ""),
                    "meme_caption": c.get("meme_caption", ""),
                    "news_hook": c.get("news_hook"),
                    "meme_score": score,
                    "audience": c.get("audience", ""),
                    "why_it_works": c.get("why_it_works", ""),
                    "rendered": is_rendered,
                }
            )

    clips.sort(key=lambda x: x["meme_score"], reverse=True)
    return clips


def get_clip(clip_id: str) -> dict | None:
    for c in load_clips():
        if c["clip_id"] == clip_id:
            return c
    return None


def find_rendered_mp4(clip_id: str) -> Path | None:
    """Find the actual .mp4 file for a rendered clip."""
    if REELS_OUTPUT_DIR.exists():
        for mp4 in REELS_OUTPUT_DIR.rglob("*.mp4"):
            if clip_id in mp4.stem:
                return mp4
    return None
