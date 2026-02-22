# CrowdListen Marketing — Meme Reels System

Short-form video content for TikTok + Instagram. AI/PM/Eng audience.

---

## How This Works

This is a two-interface system. You can drive it visually (Studio web app) or conversationally (OpenClaw AI agent). Both talk to the same files and the same rendering pipeline.

```
You (chat or browser)
        │
        ├── OpenClaw (AI agent)          ← chat via Signal/Telegram/web
        │     │  talks to you in natural language
        │     │  reads/writes files, starts jobs, monitors status
        │     │
        └── Studio (web app)             ← open in browser at localhost:8000
              │  visual clip browser, caption editor, queue + review
              │
              ▼
        Studio API (FastAPI, port 8000)
              │
        ┌─────┴──────────────┐
        │                    │
   Clip library          Render pipeline
   (Gemini JSON)         (ffmpeg)
        │                    │
   38 pre-analyzed       studio/review/     ← approve/reject here
   moments from          studio/published/  ← final clips
   Office + SV 1–3
```

### The pipeline, step by step

**1. Source video** → drop an `.mp4` into `marketing_clips/`

**2. Gemini analysis** → the Studio (or `scripts/analyze_video.py`) uploads the video to Gemini, which watches it and returns timestamped "meme moments" ranked by energy score. Output: `processing/*_visual_analysis.json`

**3. Clip library** → the Studio reads those JSON files and shows 38 browsable clips with scores, captions, and visual descriptions. No re-analyzing needed unless you add a new source video.

**4. Create** → pick a clip in Studio (or tell OpenClaw what you want), write a caption, choose Meme or Narration mode → hit Render

**5. Render** → ffmpeg cuts the clip, burns in the caption, appends the branded CTA card. For Narration, it also runs TTS and assembles hook + voiceover + CTA. Output: `studio/review/`

**6. Review → Publish** → Studio's Published tab shows all clips for approval. Approve → moves to `published/`. That's your posting queue.

---

## OpenClaw Integration

**OpenClaw** is the AI agent that runs on your machine (same one you're chatting with). It has full access to this folder and the Studio API.

**What OpenClaw can do right now:**
- Start/stop the Studio server
- Read and edit any file here — render scripts, clip data, captions, this README
- Answer questions about the system ("what clips are ready?", "what's the meme score on clip X?")
- Make changes you describe in plain English ("add a clip about scope creep to the render script")
- Check what's in published/ vs review/ and give you a status summary

**What's coming next (not built yet):**
- `"Make me a clip about AI agents"` → OpenClaw searches the library by topic, picks best match, queues the render, notifies you when it's ready
- Scheduled content drops — OpenClaw checks the calendar, renders a week's worth of clips overnight, asks for approval Monday morning
- Auto-posting to TikTok/Instagram via their APIs
- Analytics loop — track which clips perform, feed that back into clip selection

**The mental model:** Studio is the GUI for when you want to see and click. OpenClaw is the LUI (language interface) for when you want to just say what you want. Right now OpenClaw is a smart assistant for this system. The goal is for it to run most of the pipeline autonomously with you just approving the output.

---

## Studio — Visual Video Editor

A local web app for creating meme clips and narration videos without touching the CLI.

**Start it:**
```bash
cd studio && ./start.sh
# → http://localhost:8000
```

### Landing — pick your format

![Landing page](studio/docs/screenshot-landing.png)

Two modes: **Meme Clip** (caption overlay + branded CTA) or **Narration + CTA** (hook clip + voiceover + call to action).

### Clip Browser — pick the moment

![Clip browser](studio/docs/screenshot-clips.png)

38 clips pre-analyzed by Gemini from The Office + Silicon Valley 1–3. Filter by source, score threshold. Or upload a new video and Gemini extracts the best moments automatically.

### Composer — write the caption and render

![Composer](studio/docs/screenshot-composer.png)

Caption auto-filled from Gemini's analysis. Edit, rename, hit Render → clip lands in the Queue tab for review.

---

## Folder Structure

```
crowdlisten_marketing/
│
├── marketing_clips/        SOURCE — raw input videos (drop new ones here)
│   ├── The Office Best Scenes.mp4
│   ├── siliconvalley1.mp4
│   ├── siliconvalley2.mp4
│   └── siliconvalley3.mp4
│
├── processing/             INTERMEDIATE — auto-generated, don't edit by hand
│   ├── *_transcript.json       Whisper audio transcripts
│   └── *_visual_analysis.json  Gemini visual scene analysis
│
├── reels_output/           RENDERS — versioned work-in-progress (keep all versions)
│   ├── v1/ … v5/               archived batches
│   └── v6/                     current render batch
│
├── published/              FINAL — ready-to-post clips (copy best from reels_output/)
│   └── *.mp4                   11 clips from v6 (current best)
│
└── scripts/                TOOLS
    ├── analyze_video.py    step 1: visual analysis via Gemini
    ├── render_reels.py     step 2: render clips with text overlay
    └── clip_rationale.md   why each clip works + audience notes
```

---

## Workflow — Adding New Source Video

### Step 1 — Drop video in `marketing_clips/`

### Step 2 — Analyze (visual + audio)
```bash
cd crowdlisten_marketing

# Visual analysis via Gemini (watches the video, returns timestamped meme moments)
python3 scripts/analyze_video.py marketing_clips/YOUR_VIDEO.mp4

# Audio transcript via Whisper (if video > 25MB, extract audio first)
ffmpeg -y -i marketing_clips/YOUR_VIDEO.mp4 -vn -ar 16000 -ac 1 -b:a 32k processing/YOUR_VIDEO_audio.mp3
curl -sS https://api.openai.com/v1/audio/transcriptions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F "file=@processing/YOUR_VIDEO_audio.mp3" \
  -F "model=whisper-1" -F "response_format=verbose_json" -F "language=en" \
  -o processing/YOUR_VIDEO_transcript.json
```

### Step 3 — Pick clips
Open `processing/YOUR_VIDEO_visual_analysis.json` — Gemini has already ranked scenes
by meme score with visual descriptions. Cross-reference with the transcript for dialogue.

**What to look for:**
- Scene ENERGY matches a PM/Eng/AI scenario (don't just match words)
- 8–15 second clips (sweet spot)
- Physical comedy, reaction shots, visual props — these only show in visual analysis

### Step 4 — Edit `scripts/render_reels.py`
```python
VERSION = "v7"   # ← bump from v6

CLIPS = [
    (
        "descriptive_filename_for_the_clip",
        SOURCE_FILE, START_SECONDS, DURATION_SECONDS,
        "caption line 1\ncaption line 2",
    ),
    # ...
]
```

**Caption rules:**
- 2 lines max, ~26 chars per line
- Match scene energy, not transcript words
- Specific > generic ("Cursor write access to main" not "using AI tools")
- Sounds like a confession or a relatable callout
- Use `\n` for line breaks; use curly quotes `'` not straight `'`

### Step 5 — Render
```bash
python3 scripts/render_reels.py
# → clips appear in reels_output/v7/
```

### Step 6 — Publish
Review clips in `reels_output/v7/`. Copy the ones that are ready to post:
```bash
cp reels_output/v7/CLIP_NAME.mp4 published/
```
`published/` = the single source of truth for what's ready to post.

---

## Current State (v6, Feb 2026)

11 clips in `published/` — all selected via Gemini visual analysis:

| File | Source | Caption |
|---|---|---|
| `01_pm_managing_a_sev1_at_3am` | The Office | PM managing a Sev-1 at 3am |
| `02_your_hotfix_breaks_prod_even_worse` | The Office | your hotfix breaks prod even worse |
| `03_ceo_during_the_all_hands_layoff_call` | The Office | CEO during the all-hands layoff call |
| `04_stakeholder_10_mins_before_the_demo` ⭐ | The Office | stakeholder 10 minutes before the demo |
| `04_the_stakeholder_who_has_no_capacity` | The Office | the stakeholder who always has 'no capacity' this sprint |
| `05_ceo_seeing_the_ai_demo_we_built_for_3_months` | SV1 | CEO seeing the AI demo we built for 3 months |
| `06_our_ceo_explaining_why_the_layoffs_are_good_actually` | SV1 | our CEO explaining why the layoffs are good actually |
| `07_pm_adding_one_more_thing_to_the_sprint` | SV2 | PM adding one more thing to the sprint |
| `08_me_opening_slack_after_a_3day_weekend` | SV2 | me opening Slack after a 3-day weekend |
| `09_debugging_the_ai_agent_at_2am` ⭐ | SV3 | debugging the AI agent at 2am |
| `10_our_codebase_after_ai_had_unsupervised_access` | SV3 | our codebase after the AI had unsupervised access all weekend |

---

## Posting Order (Feb 2026)
1. `09_debugging_the_ai_agent_at_2am` — robot deer kick, pure visual, instant
2. `04_stakeholder_10_mins_before_the_demo` — 7s, devastating
3. `06_our_ceo_explaining_why_why_layoffs_are_good` — room recoil shot
4. `01_pm_managing_a_sev1_at_3am` — fire drill chaos, relatable
5. Space the rest 3-4x/week

Don't explain the joke. Ever.
