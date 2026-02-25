"""
detector.py — LLM-based clip candidate detection (meme + quote)
"""
import json
from pathlib import Path

import httpx

from .config import PROCESSING_DIR, OPENAI_API_KEY

AUDIENCE_DEFAULT = "engineers, PMs, founders, and the broader AI / startup community"

MEME_PROMPT = """You are a meme content strategist for a TikTok/Instagram account targeting {audience}.

Given this video transcript (with timestamps), identify the {count} best meme-worthy moments.

For each moment output:
- timestamp: start time in seconds (float)
- duration: clip length in seconds (8–25)
- caption: exactly 2 lines, max 26 chars per line, punchy and relatable to tech/startup culture
- score: 1–10 meme potential
- why: one sentence on why this works visually/verbally

Rules:
- Caption must use curly apostrophes \u2019 not straight apostrophes
- Match the ENERGY of the scene, not just the words
- Specific > generic ("Cursor write access to main" beats "using AI tools")
- Think: confessional, cringe-relatable, unhinged if warranted

Transcript:
{transcript}

Return ONLY valid JSON: {{"clips": [{{...}}]}}"""

QUOTE_PROMPT = """You are a content editor finding quotable speaker moments for social media.
Target audience: {audience}.

Given this transcript (with timestamps), find the {count} best standalone quotable moments.

For each moment output:
- timestamp: start time in seconds (float)
- duration: clip length in seconds (10–45)
- quote: the exact quote text (1–3 sentences max)
- score: 1–10 quote quality
- context: one sentence on why this quote is valuable/insightful

Rules:
- Quote must be a complete, standalone thought
- Strong opinions, surprising insights, or punchy takeaways preferred
- No mid-sentence starts or ends

Transcript:
{transcript}

Return ONLY valid JSON: {{"clips": [{{...}}]}}"""


def _build_transcript_text(transcript: dict) -> str:
    segments = transcript.get("segments", [])
    lines = []
    for s in segments:
        start = s.get("start", 0)
        text = s.get("text", "").strip()
        if text:
            lines.append(f"[{start:.1f}s] {text}")
    return "\n".join(lines)


def _call_gpt(prompt: str) -> dict:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "max_tokens": 4096,
        },
        timeout=60,
    )
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"].strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
    if raw.endswith("```"):
        raw = "\n".join(raw.split("\n")[:-1])
    return json.loads(raw)


def detect_clips(
    transcript: dict,
    job_id: str,
    clip_types: list[str],
    count: int = 10,
    audience: str = AUDIENCE_DEFAULT,
) -> list[dict]:
    """Run clip detection for specified types. Returns merged list of candidates."""
    clips_path = PROCESSING_DIR / f"{job_id}_clips.json"
    if clips_path.exists():
        return json.loads(clips_path.read_text())

    transcript_text = _build_transcript_text(transcript)
    all_clips = []

    if "meme" in clip_types:
        prompt = MEME_PROMPT.format(
            audience=audience, count=count,
            transcript=transcript_text[:12000]
        )
        data = _call_gpt(prompt)
        for c in data.get("clips", []):
            c["type"] = "meme"
            all_clips.append(c)

    if "quote" in clip_types:
        prompt = QUOTE_PROMPT.format(
            audience=audience, count=count,
            transcript=transcript_text[:12000]
        )
        data = _call_gpt(prompt)
        for c in data.get("clips", []):
            c["type"] = "quote"
            all_clips.append(c)

    # Sort by score desc
    all_clips.sort(key=lambda x: x.get("score", 0), reverse=True)

    clips_path.write_text(json.dumps(all_clips, indent=2))
    return all_clips
