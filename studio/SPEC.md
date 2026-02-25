# CrowdListen Studio — Redesign Spec v2

## Overview
A local FastAPI + vanilla JS app for generating short-form video clips from uploaded source videos.
Designed to work both manually (via browser UI) and programmatically (via OpenClaw/API).

---

## User Flow

### Step 1 — Upload
- Home page shows a large drag-and-drop upload panel (full-width, prominent)
- Accepts: .mp4, .mov, .avi, .mkv
- Shows upload progress bar
- Video is stored in `uploads/` directory with a unique job ID
- After upload completes → auto-advance to Step 2

### Step 2 — Clip Type Selection
After upload, the user sees:
- **Clip Type** (choose one or both):
  - 🎭 Meme Clips — funny/relatable moments, punchy 2-line captions, 10–30s
  - 🗣️ Speaker Quotes — clean talking head moments, quote text overlay, 10–45s
- **Add-ons** (optional toggles):
  - 🎙️ Narrated CTA — appends TTS voiceover + CrowdListen branding at the end
- **Count** — how many clips to generate (default: 10, max: 20)
- **Target audience** — short text field (default: "engineers, PMs, AI community")

→ "Process Video" button launches the pipeline

### Step 3 — Processing (with live progress)
Pipeline steps shown as a progress timeline:
1. Extract audio (ffmpeg)
2. Transcribe (Whisper API)
3. Detect clip candidates (LLM — Claude or GPT)
4. Render clips (ffmpeg)

Live SSE progress updates shown in UI.

### Step 4 — Library / Review
- Grid of generated clips (video previews, auto-play on hover)
- Each clip card shows:
  - Thumbnail / inline video player
  - Caption text
  - Duration
  - Type badge (Meme / Quote)
  - Score (1–10)
  - ✅ Select / ❌ Reject toggle
- "Save Selected" button → saves approved clips to `published/YYYY-MM-DD/`

### Step 5 — Published
- Published clips tab shows all saved clips by date
- Can re-preview any clip
- Can delete from published

---

## API Endpoints

### Upload
- `POST /api/upload` — upload video file, returns `{job_id, filename}`

### Pipeline
- `POST /api/pipeline/start` — body: `{job_id, clip_types: ["meme"|"quote"], add_narration: bool, count: int, audience: str}`
- `GET /api/pipeline/{job_id}/status` — returns pipeline step + progress
- `GET /api/events` — SSE stream for live progress

### Clips / Library
- `GET /api/library/{job_id}` — list generated clips for a job
- `GET /api/library/{job_id}/{clip_name}` — serve clip video file
- `POST /api/library/{job_id}/save` — body: `{clips: ["clip1.mp4", ...]}` → saves to published/

### Published
- `GET /api/published` — list all published clips (recursive by date)
- `DELETE /api/published/{date}/{filename}` — remove from published

---

## Directory Structure

```
studio/
  uploads/          ← uploaded source videos (by job_id)
  processing/       ← transcripts, analysis JSON per job
  library/          ← rendered clips awaiting approval (by job_id)
  ads/              ← reusable ad assets (mp4, jpg, png)
  backend/
    main.py         ← FastAPI app + routes
    pipeline.py     ← end-to-end orchestrator (audio → whisper → LLM → render)
    whisper.py      ← Whisper API wrapper
    detector.py     ← LLM clip detector (meme + quote)
    renderer.py     ← ffmpeg render (meme + quote styles)
    config.py       ← paths, API keys, brand config
  frontend/
    index.html
    app.js
    style.css
```

---

## Clip Detection Prompts

### Meme Clip Detection
Given transcript segments, find moments that are:
- Visually or verbally absurd/relatable
- Map to PM / eng / AI / startup pain points
- Score 1–10 for meme potential
- Output: timestamp, duration, 2-line caption (max 26 chars/line)

### Speaker Quote Detection
Given transcript segments, find moments that are:
- Clear standalone insight or opinion
- Confident, quotable delivery
- 10–45 seconds
- Output: timestamp, duration, quote text (1–2 lines)

---

## Rendering

### Meme Style
- 1080×1920 (9:16)
- Black background, video centered (608px tall)
- Impact font caption — top area
- CTA text (optional) — bottom area: "The PM for AI Agents / crowdlisten.com"
- Coral #D97D55 for brand text

### Quote Style
- 1080×1920 (9:16)
- Dark semi-transparent overlay on video (full bleed)
- Helvetica quote text — centered over video
- Speaker name / handle (optional) — bottom
- CTA text (optional) — very bottom

---

## Ad Placement Configuration

### Overview
Ads can be inserted between clips or appended at the very end. Each ad is a short video segment (MP4) or a static image (PNG/JPG) with optional audio.

### Ad Slot Types
| Type | Description |
|---|---|
| `between` | Inserted between every N clips |
| `end` | Appended after the last clip |
| `both` | Between clips AND at the end |

### Config (UI + API)

In the Step 2 options panel, users see an **Ad Placement** section:
- Toggle: **Enable Ads** (off by default)
- **Ad Asset** — upload a short video or image (≤30s / ≤5MB)
- **Placement** — dropdown: "Between clips", "End only", "Both"
- **Frequency** — "Every N clips" slider (1–5, default: 2) — only shown for `between` or `both`
- **Duration** — if asset is image, set display duration (3–10s, default: 5s)

### API
```bash
# Include ad config in pipeline start request
curl -X POST http://localhost:8000/api/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "abc123",
    "clip_types": ["meme"],
    "add_narration": false,
    "count": 10,
    "audience": "engineers, PMs",
    "ad_config": {
      "enabled": true,
      "asset_path": "/path/to/ad.mp4",
      "placement": "between",
      "frequency": 2,
      "image_duration": 5
    }
  }'
```

### Ad Assets Storage
- Uploaded ad assets stored in `studio/ads/`
- Referenced by filename in pipeline config
- Reusable across jobs

### Rendering Logic
- For `between`: ffmpeg concat — clip1 + ad + clip2 + ad + clip3...
- For `end`: ffmpeg concat — [...all clips] + ad
- Image ads: ffmpeg `loop=1:duration=N` to create video segment before concat
- Audio from ad asset is preserved; clip audio is preserved
- All segments normalized to 1080×1920 before concat

### OpenClaw Usage
```bash
# Upload ad asset once
curl -X POST http://localhost:8000/api/ads/upload -F "file=@crowdlisten_ad.mp4"

# List saved ad assets
curl http://localhost:8000/api/ads

# Use in pipeline
curl -X POST http://localhost:8000/api/pipeline/start \
  -d '{"job_id":"abc123","ad_config":{"enabled":true,"asset":"crowdlisten_ad.mp4","placement":"end"}}'
```

---

## OpenClaw API Usage Pattern

```bash
# 1. Upload
curl -X POST http://localhost:8000/api/upload -F "file=@video.mp4"
# → {"job_id": "abc123", "filename": "video.mp4"}

# 2. Start pipeline
curl -X POST http://localhost:8000/api/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{"job_id":"abc123","clip_types":["meme"],"add_narration":false,"count":10,"audience":"engineers, PMs"}'

# 3. Poll status
curl http://localhost:8000/api/pipeline/abc123/status

# 4. List library
curl http://localhost:8000/api/library/abc123

# 5. Save selected
curl -X POST http://localhost:8000/api/library/abc123/save \
  -H "Content-Type: application/json" \
  -d '{"clips":["01_clip.mp4","03_clip.mp4"]}'
```

---

## Brand Config
- Primary color: #D97D55 (coral)
- Background: #F7F5F2 (cream)
- Font: Helvetica / system-ui for UI; Impact for meme captions
- CTA Line 1: "The PM for AI Agents"
- CTA Line 2: "crowdlisten.com"

---

## Tech Stack
- Backend: Python 3.12, FastAPI, uvicorn
- Transcription: OpenAI Whisper API (whisper-1)
- Clip detection: OpenAI GPT-4o or Anthropic Claude (configurable)
- Rendering: ffmpeg (system)
- Frontend: Vanilla JS, no framework, minimal dependencies
