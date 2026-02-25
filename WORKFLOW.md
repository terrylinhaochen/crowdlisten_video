# WORKFLOW.md — CrowdListen Reels End‑to‑End

This document describes the **full short‑form content pipeline**: source → analysis → selection → render → review → publish. It is the operational playbook for the CrowdListen marketing reels workflow.

---

## 0) Quick Start (TL;DR)

**Target audiences:** engineers, PMs, and the broader AI community.

1. **Start Studio** (API server)  
   ```bash
   cd /Users/terry/Desktop/crowdlisten_files/crowdlisten_marketing/studio
   /opt/anaconda3/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> /tmp/studio.log 2>&1 &
   ```

2. **Check it’s running**  
   ```bash
   curl -s -o /dev/null -w "%{http_code}" http://localhost:8000
   ```

3. **Render batch** (best clips by score)  
   ```bash
   curl -X POST http://localhost:8000/api/batch \
     -H "Content-Type: application/json" \
     -d '[
       {"clip_id": "sv2_307", "caption": "PM adding one more thing to the sprint", "mode": "meme", "output_name": "pm_scope_creep"}
     ]'
   ```

4. **Review**  
   - Open `http://localhost:8000` and review in the UI

5. **Publish**  
   - Move approved clips to `published/YYYY_MM_DD/`

---

## 1) Sources & Inputs

**Primary sources:**
- The Office
- Silicon Valley (seasons 1–3)

**Location:**
- Source videos: `marketing_clips/`
- Analyses: `processing/*_visual_analysis.json`

---

## 2) Analysis (Clip Discovery)

**Goal:** generate candidate meme moments with scores, captions, and visual rationale.

**Inputs:** source videos in `marketing_clips/`

**Outputs:** `processing/*_visual_analysis.json`

**Notes:**
- Visual analysis is more reliable than transcript‑only.
- Favor clips that are **visually expressive** and **high‑energy**.

---

## 3) Clip Selection

**Rules (from SKILLS.md):**
- Prefer meme_score ≥ 8
- Mix sources (avoid Office‑only batches)
- Avoid repetition of themes in same batch

**Selection method:**
1. Read JSON analysis
2. Rank by meme_score
3. Screen for theme diversity
4. Pick ~10–15 for a batch

---

## 4) Captioning

**Hard requirements:**
- Max 2 lines (~26 chars per line)
- Match scene **energy** (not just words)
- Specific > generic
- Feels like a confession / relatable callout
- Use curly apostrophes `’` (ffmpeg limitation)

**Trend guidance:**
- Use trends **only if strongly aligned**
- Skip trends if forced or sensitive

---

## 5) Rendering

### Single render (meme)
```bash
curl -X POST http://localhost:8000/api/queue \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "meme",
    "output_name": "scope_creep_meme",
    "source_file": "/path/to/siliconvalley2.mp4",
    "start_sec": 307,
    "duration_sec": 11,
    "hook_caption": "PM adding one more thing to the sprint",
    "hook_clip_id": "sv2_307"
  }'
```

### Batch render
```bash
curl -X POST http://localhost:8000/api/batch \
  -H "Content-Type: application/json" \
  -d '[
    {"clip_id": "sv2_307", "caption": "PM adding one more thing to the sprint", "mode": "meme", "output_name": "pm_scope_creep"},
    {"clip_id": "office_183", "caption": "CEO during the all‑hands layoff call", "mode": "meme", "output_name": "ceo_layoff"}
  ]'
```

**Render output:**
- `reels_output/vX/` (versioned batches)

---

## 6) Review & Approval

**Review queue:**
- `studio/review/`
- Review in the UI: `http://localhost:8000`

**Approve (API):**
```bash
curl -X POST http://localhost:8000/api/review/FILENAME.mp4/approve
```

---

## 7) Publishing

**Published folder:**
- `published/` (date‑stamped subfolders)

**Flow:**
1. Move approved clips to `published/YYYY_MM_DD/`
2. Optional: split into `publish` vs `prepped` folders

---

## 8) Folder Map

| Folder | Purpose |
|---|---|
| `marketing_clips/` | Source videos |
| `processing/` | Visual analysis JSON |
| `studio/tmp/` | Temporary render artifacts |
| `studio/review/` | Awaiting approval |
| `reels_output/vX/` | Render batches |
| `published/` | Approved / ready to post |

---

## 9) QA Checklist

- [ ] Hook is clear in 1–2 seconds
- [ ] Caption is 2 lines max
- [ ] Caption matches energy of scene
- [ ] No invented facts
- [ ] Trend used only if highly relevant
- [ ] CTA is soft (if present)

---

## 10) Troubleshooting

**FFmpeg caption errors:**
- Most common cause: straight apostrophes `'`
- Fix: use curly apostrophes `’`

**Render failed (SIGTERM or crash):**
- Re‑queue with simpler caption
- Check disk space + CPU load

**Nothing shows in review:**
- Ensure render output exists in `reels_output/vX/`
- Check Studio logs: `/tmp/studio.log`

---

**Source of truth:**
- `SKILLS.md` for requirements + rules
- `STUDIO.md` for API details
