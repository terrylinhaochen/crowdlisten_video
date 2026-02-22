"""Smart semantic clip search using OpenAI."""

import json
import os
import re
from openai import OpenAI


def smart_search(topic: str, clips: list[dict], limit: int = 5) -> list[dict]:
    """
    Search clips semantically using OpenAI.
    Falls back to keyword matching if API fails.

    Returns list of clips with match_reason and relevance_score added.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _keyword_fallback(topic, clips, limit)

    # Build compact clip summaries for the prompt
    clip_summaries = []
    for c in clips:
        clip_summaries.append({
            "clip_id": c["clip_id"],
            "meme_caption": c.get("meme_caption", ""),
            "what_happens_visually": c.get("what_happens_visually", ""),
            "why_it_works": c.get("why_it_works", ""),
            "meme_score": c.get("meme_score", 0),
        })

    prompt = f"""You are a clip search assistant. Given a search topic and a list of video clips, rank the clips by relevance to the topic.

TOPIC: "{topic}"

CLIPS:
{json.dumps(clip_summaries, indent=2)}

Return a JSON array of the top {limit} most relevant clips, ranked by relevance. Each item should have:
- clip_id: the clip's ID
- match_reason: a brief explanation (10-15 words max) of why this clip matches the topic
- relevance_score: a number from 0.0 to 1.0 indicating how well it matches

Only return the JSON array, no other text. Example format:
[{{"clip_id": "sv1_42", "match_reason": "Shows team struggling with endless feature requests", "relevance_score": 0.92}}]"""

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000,
        )

        content = response.choices[0].message.content.strip()
        # Extract JSON from response (handle markdown code blocks)
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n?", "", content)
            content = re.sub(r"\n?```$", "", content)

        results = json.loads(content)

        # Merge results back with full clip data
        clip_map = {c["clip_id"]: c for c in clips}
        matched = []
        for r in results[:limit]:
            clip_id = r.get("clip_id")
            if clip_id and clip_id in clip_map:
                clip = clip_map[clip_id].copy()
                clip["match_reason"] = r.get("match_reason", "")
                clip["relevance_score"] = r.get("relevance_score", 0.5)
                matched.append(clip)

        return matched

    except Exception:
        # Fall back to keyword search on any error
        return _keyword_fallback(topic, clips, limit)


def _keyword_fallback(topic: str, clips: list[dict], limit: int) -> list[dict]:
    """Simple keyword matching fallback when AI search fails."""
    topic_lower = topic.lower()
    keywords = topic_lower.split()

    scored = []
    for c in clips:
        text = " ".join([
            c.get("meme_caption", ""),
            c.get("what_happens_visually", ""),
            c.get("why_it_works", ""),
        ]).lower()

        # Count keyword matches
        matches = sum(1 for kw in keywords if kw in text)
        if matches > 0:
            score = matches / len(keywords)
            clip = c.copy()
            clip["match_reason"] = f"Contains: {', '.join(kw for kw in keywords if kw in text)}"
            clip["relevance_score"] = round(score, 2)
            scored.append((score, clip))

    # Sort by score descending, then by meme_score
    scored.sort(key=lambda x: (x[0], x[1].get("meme_score", 0)), reverse=True)
    return [clip for _, clip in scored[:limit]]
