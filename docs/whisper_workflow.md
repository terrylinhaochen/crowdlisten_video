# Whisper-First Clip Workflow (No Gemini)

Use this when the source video is too long for Gemini visual analysis.

## 1) Extract audio
```bash
ffmpeg -y -i marketing_clips/the_office_compilation.mp4 -vn -ar 16000 -ac 1 -b:a 32k \
  processing/the_office_compilation_audio.mp3
```

## 2) Transcribe (timestamps)
```bash
curl -sS https://api.openai.com/v1/audio/transcriptions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Accept: application/json" \
  -F "file=@processing/the_office_compilation_audio.mp3" \
  -F "model=whisper-1" \
  -F "response_format=verbose_json" \
  -o processing/the_office_compilation_transcript_verbose.json
```

## 3) Pick moments from transcript
Use `segments` from the verbose JSON. Choose 8–30s windows that:
- have clear comedic payoff
- map to PM/eng/AI pain points (budget, roadmap, estimates, stakeholders, prod incidents)
- include 1–2s of lead‑in before the punchline

## 4) Render (with CTA + logo)
Edit `scripts/render_reels.py`:
- bump `VERSION`
- set `OFFICE_COMP` to source video
- set `CLIPS` with `(name, source, start_sec, duration_sec, caption)`
- captions: 2 lines, punchy, PM‑relatable

Render:
```bash
python3 scripts/render_reels.py
```

Output: `reels_output/vX/`

## 5) Publish
Copy approved clips to `published/`:
```bash
cp reels_output/vX/*.mp4 published/
```

---

## Prompting (Clip Selection)
Use this checklist for selecting timestamps:
- **Lead‑in:** include ~1–2 seconds before the punchline
- **Tail:** include the reaction beat (1–3s)
- **Length:** 10–22s tends to land best
- **Captions:** make it unhinged but accurate (PM shame + empathy)

Example caption patterns:
- “When the stakeholder joins the wrong call”
- “Me shipping without a test plan”
- “End‑of‑quarter budget logic”
- “Competitor ships your feature then gaslights you”
