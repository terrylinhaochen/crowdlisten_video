# SKILLS.md — CrowdListen Reels Requirements

This doc distills the current rules + workflow requirements for short‑form reels. It is the **single source of truth** for what we consider “ready to publish.”

---

## 1) Goals

- Produce **high‑energy, highly relatable** short‑form clips (20–60s) that fit platform norms.
- Stay **on‑brand** for CrowdListen and drive curiosity without sounding like ads.
- When relevant, **tie to trending news/content** for higher resonance.
- Primary audiences: **engineers, PMs, and the broader AI community**.

---

## 2) Trend Relevance (required when appropriate)

Use trends **selectively**—only if the clip naturally aligns.

**Inputs to check (lightweight):**
- Trending topics on X / Reddit / TikTok / IG
- Current product/news cycle in AI, startups, PM/eng, SaaS, venture

**Rules:**
- If a trend is **highly aligned**, include it in the caption or narrative framing.
- If it feels forced, **don’t use it** (evergreen wins).
- Avoid anything sensitive, political, or controversial unless explicitly requested.

---

## 3) Caption Rules (hard requirements)

- **Max 2 lines**, ~26 chars per line
- Must match **scene energy** (not just transcript)
- **Specific > generic**
- Should feel like a **confession / relatable callout**
- Use **curly apostrophes** `’` (ffmpeg drawtext limitation)

---

## 4) CTA / Branding (when present)

- CTA is **soft** and non‑salesy
- Examples:
  - “Try CrowdListen now”
  - “The PM for AI Agents”
  - “crowdlisten.com”
- No hard‑sell language (“Buy now”, “Limited time”) unless requested

---

## 5) Clip Selection Rules

- Prefer clips with **meme_score ≥ 8** (high energy, strong hook)
- Mix sources to avoid repetition (Office + SV1/2/3)
- Avoid similar themes in same batch

---

## 6) File / Folder Flow

**Render output:**
- `reels_output/vX/` (versioned batches)

**Review:**
- `studio/review/` (awaiting approval)

**Published:**
- `published/` (archived by date)

---

## 7) Quality Checklist (must pass)

- [ ] Hook is instantly clear (first 1–2 seconds)
- [ ] Caption respects 2‑line rule
- [ ] Caption matches scene energy
- [ ] No invented facts
- [ ] Trend used only if strongly relevant
- [ ] CTA/branding is subtle (if present)

---

## 8) Operating Notes

- Use the Studio API for queue/review/publish.
- If a clip fails render, re‑queue with a simplified caption (often fixes drawtext issues).

---

**Location:** `/Users/terry/Desktop/crowdlisten_files/crowdlisten_marketing/SKILLS.md`
