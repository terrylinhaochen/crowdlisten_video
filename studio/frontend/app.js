// CrowdListen Studio — app.js
// Pure vanilla JS, no dependencies.

const state = {
  clips: [],
  selectedClip: null,
  filters: { source: 'all', minScore: 7 },
  ttsAudio: null,       // { audio_url, duration, audio_file }
  queueJobs: [],
  published: { videos: [], today_count: 0, daily_target: 2 },
  composerState: {
    caption: '',
    bodyScript: '',
    voice: 'shimmer',
    provider: 'openai',
    ctaTagline: 'Understand your audience.',
    outputName: '',
    renderSteps: [false, false, false, false],
  },
  knownDoneJobs: new Set(),
};

// ── Utils ────────────────────────────────────────────────────────────────────

function slugify(text) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40);
}

function relTime(isoStr) {
  const d = new Date(isoStr);
  const diff = (Date.now() - d) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function wordCount(text) {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function estDuration(text) {
  return Math.ceil(wordCount(text) / 2.5);
}

function scoreClass(score) {
  if (score >= 9) return 'score-high';
  if (score >= 7) return 'score-mid';
  return 'score-low';
}

function showToast(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
  el.innerHTML = `<span>${icon}</span><span>${msg}</span>`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// ── Clips / Library ──────────────────────────────────────────────────────────

async function fetchClips() {
  const params = new URLSearchParams({ min_score: state.filters.minScore });
  if (state.filters.source !== 'all') params.set('source', state.filters.source);
  try {
    state.clips = await api(`/api/clips?${params}`);
    renderLibrary();
  } catch (e) {
    document.getElementById('clip-list').innerHTML =
      `<div class="empty-state" style="color:#ef4444">Failed to load clips: ${e.message}</div>`;
  }
}

function renderLibrary() {
  const el = document.getElementById('clip-list');
  if (!state.clips.length) {
    el.innerHTML = '<div class="empty-state">No clips match filters</div>';
    return;
  }
  el.innerHTML = state.clips.map(c => {
    const active = state.selectedClip?.clip_id === c.clip_id ? ' active' : '';
    return `
      <div class="clip-card${active}" data-id="${c.clip_id}" onclick="selectClip('${c.clip_id}')">
        <div class="clip-card-top">
          <span class="score-badge ${scoreClass(c.meme_score)}">${c.meme_score}/10</span>
          <span class="source-tag">${c.source_label}</span>
          <span class="clip-timestamp">${c.timestamp}</span>
        </div>
        <div class="clip-caption">${escHtml(c.meme_caption)}</div>
        <div class="clip-visual">${escHtml(c.what_happens_visually)}</div>
        <div class="clip-card-bottom">
          <span class="audience-tag">${escHtml(c.audience)}</span>
          <span class="rendered-dot ${c.rendered ? 'yes' : 'no'}" title="${c.rendered ? 'Rendered' : 'Not rendered'}"></span>
        </div>
      </div>`;
  }).join('');
}

function escHtml(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function selectClip(clipId) {
  state.selectedClip = state.clips.find(c => c.clip_id === clipId) || null;
  if (!state.selectedClip) return;
  state.ttsAudio = null;
  state.composerState.caption = state.selectedClip.meme_caption;
  state.composerState.outputName = slugify(state.selectedClip.meme_caption);
  state.composerState.renderSteps = [false, false, false, false];
  renderLibrary();       // update active state
  renderComposer();
  document.getElementById('composer-subtitle').textContent =
    `${state.selectedClip.source_label} · ${state.selectedClip.timestamp}`;
}

// ── Composer ─────────────────────────────────────────────────────────────────

function renderComposer() {
  const el = document.getElementById('composer-body');
  if (!state.selectedClip) {
    el.innerHTML = `
      <div class="empty-state composer-empty">
        <div class="empty-icon">🎬</div>
        <p>Select a clip from the library to get started</p>
      </div>`;
    return;
  }
  const c = state.selectedClip;
  const cs = state.composerState;

  const openaiVoices = ['shimmer','alloy','echo','fable','onyx','nova'];
  const elevenlabsVoices = ['Rachel','Bella','Adam','Antoni'];
  const voiceOptions = (cs.provider === 'openai' ? openaiVoices : elevenlabsVoices)
    .map(v => `<option value="${v}" ${v === cs.voice ? 'selected' : ''}>${v}</option>`)
    .join('');

  const audioHtml = state.ttsAudio
    ? `<div class="audio-player-row">
         <audio controls src="${state.ttsAudio.audio_url}"></audio>
         <span class="duration-badge">⏱ ${state.ttsAudio.duration}s</span>
       </div>`
    : '';

  const steps = cs.renderSteps;
  const stepHtml = ['Hook','Body','CTA','Assemble'].map((s, i) =>
    `<span class="step ${steps[i] ? 'done' : ''}">${steps[i] ? '✓' : '○'} ${s}</span>`
  ).join('<span class="step-sep">→</span>');

  el.innerHTML = `
    <!-- Section A: Hook -->
    <div class="composer-section">
      <div class="section-header" onclick="toggleSection(this)">
        <span class="section-title">🎣 Hook Clip</span>
        <span class="section-chevron open">▾</span>
      </div>
      <div class="section-body">
        <div class="clip-info-box">
          <div class="clip-info-row">
            <span class="source-tag">${c.source_label}</span>
            <span class="score-badge ${scoreClass(c.meme_score)}">${c.meme_score}/10</span>
            <span class="info-label">@${c.timestamp}</span>
            <span class="info-value">${c.duration_seconds}s</span>
          </div>
          <div class="clip-visual-desc">${escHtml(c.what_happens_visually)}</div>
          <div class="clip-dialogue">"${escHtml(c.dialogue_hook)}"</div>
        </div>
        <div class="form-group">
          <label>Caption (burned into video)</label>
          <textarea id="caption-input" rows="2" oninput="state.composerState.caption=this.value">${escHtml(cs.caption)}</textarea>
        </div>
        ${c.rendered
          ? `<button class="btn btn-secondary btn-sm preview-btn" onclick="openVideoPreview('${c.clip_id}')">▶ Preview Clip</button>`
          : `<button class="btn btn-secondary btn-sm preview-btn" disabled title="Clip not yet rendered">▶ Preview (not rendered)</button>`
        }
      </div>
    </div>

    <!-- Section B: Body -->
    <div class="composer-section">
      <div class="section-header" onclick="toggleSection(this)">
        <span class="section-title">🎙 Body Narration</span>
        <span class="section-chevron open">▾</span>
      </div>
      <div class="section-body">
        <div class="form-group">
          <label>Narration script</label>
          <textarea id="body-script" rows="5" placeholder="Write the body narration here (15–30 seconds of speech)..."
            oninput="onScriptInput(this)">${escHtml(cs.bodyScript)}</textarea>
          <div class="word-count" id="word-count">≈ ${estDuration(cs.bodyScript)}s estimated · ${wordCount(cs.bodyScript)} words</div>
        </div>
        <div class="voice-row">
          <div class="form-group">
            <label>Voice</label>
            <select id="voice-select" onchange="onVoiceChange(this)">${voiceOptions}</select>
          </div>
          <div class="form-group">
            <label>Provider</label>
            <div class="provider-toggle">
              <button class="provider-btn ${cs.provider==='openai'?'active':''}" onclick="setProvider('openai')">OpenAI</button>
              <button class="provider-btn ${cs.provider==='elevenlabs'?'active':''}" onclick="setProvider('elevenlabs')">ElevenLabs</button>
            </div>
          </div>
        </div>
        <button class="btn btn-primary" id="tts-btn" onclick="generateTTS()" ${!cs.bodyScript.trim() ? 'disabled' : ''}>
          🎤 Generate Voice
        </button>
        ${audioHtml}
      </div>
    </div>

    <!-- Section C: CTA -->
    <div class="composer-section">
      <div class="section-header" onclick="toggleSection(this)">
        <span class="section-title">📣 CTA Card</span>
        <span class="section-chevron open">▾</span>
      </div>
      <div class="section-body">
        <div class="form-group">
          <label>Tagline</label>
          <input type="text" id="cta-tagline" value="${escHtml(cs.ctaTagline)}" oninput="onTaglineInput(this)" />
        </div>
        <div class="cta-preview">
          <div class="cta-logo-placeholder">CRD</div>
          <div class="cta-tagline-preview" id="cta-preview-text">${escHtml(cs.ctaTagline)}</div>
          <div class="cta-url-preview">crowdlisten.com</div>
        </div>
      </div>
    </div>

    <!-- Section D: Render -->
    <div class="composer-section">
      <div class="section-header" onclick="toggleSection(this)">
        <span class="section-title">🚀 Render</span>
        <span class="section-chevron open">▾</span>
      </div>
      <div class="section-body">
        <div class="output-name-row">
          <div class="form-group" style="flex:1;margin-bottom:0">
            <label>Output filename</label>
            <input type="text" id="output-name" value="${escHtml(cs.outputName)}" oninput="state.composerState.outputName=this.value" />
          </div>
        </div>
        <button class="btn btn-primary btn-full" id="render-btn" onclick="submitRender()" style="margin-top:12px">
          🎬 Render Full Video
        </button>
        <div class="steps-row" id="steps-row">${stepHtml}</div>
      </div>
    </div>
  `;
}

function toggleSection(header) {
  const body = header.nextElementSibling;
  const chevron = header.querySelector('.section-chevron');
  body.classList.toggle('collapsed');
  chevron.classList.toggle('open');
}

function onScriptInput(el) {
  state.composerState.bodyScript = el.value;
  const wc = document.getElementById('word-count');
  if (wc) wc.textContent = `≈ ${estDuration(el.value)}s estimated · ${wordCount(el.value)} words`;
  const ttsBtn = document.getElementById('tts-btn');
  if (ttsBtn) ttsBtn.disabled = !el.value.trim();
}

function onTaglineInput(el) {
  state.composerState.ctaTagline = el.value;
  const preview = document.getElementById('cta-preview-text');
  if (preview) preview.textContent = el.value;
}

function onVoiceChange(el) {
  state.composerState.voice = el.value;
}

function setProvider(provider) {
  state.composerState.provider = provider;
  renderComposer(); // re-render to update voice options
}

// ── TTS ───────────────────────────────────────────────────────────────────────

async function generateTTS() {
  const btn = document.getElementById('tts-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Generating...';
  try {
    const result = await api('/api/tts', {
      method: 'POST',
      body: JSON.stringify({
        script: state.composerState.bodyScript,
        voice: state.composerState.voice,
        provider: state.composerState.provider,
      }),
    });
    state.ttsAudio = result;
    showToast(`Voice generated · ${result.duration}s`, 'success');
    renderComposer();
  } catch (e) {
    showToast(`TTS failed: ${e.message}`, 'error');
    btn.disabled = false;
    btn.textContent = '🎤 Generate Voice';
  }
}

// ── Render ────────────────────────────────────────────────────────────────────

async function submitRender() {
  const cs = state.composerState;
  const c = state.selectedClip;
  if (!c) return;

  if (!cs.bodyScript.trim()) {
    showToast('Write a narration script first', 'error'); return;
  }
  if (!cs.outputName.trim()) {
    showToast('Set an output filename', 'error'); return;
  }

  const btn = document.getElementById('render-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Adding to queue...';

  try {
    await api('/api/render', {
      method: 'POST',
      body: JSON.stringify({
        hook_clip_id: c.clip_id,
        hook_caption: cs.caption,
        body_script: cs.bodyScript,
        body_audio_file: state.ttsAudio?.audio_file || null,
        cta_tagline: cs.ctaTagline,
        output_name: cs.outputName,
      }),
    });
    showToast('Added to render queue!', 'success');
    cs.renderSteps = [true, true, true, true];
    updateSteps();
    fetchQueue();
  } catch (e) {
    showToast(`Render failed: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '🎬 Render Full Video';
  }
}

function updateSteps() {
  const row = document.getElementById('steps-row');
  if (!row) return;
  const steps = state.composerState.renderSteps;
  row.innerHTML = ['Hook','Body','CTA','Assemble'].map((s, i) =>
    `<span class="step ${steps[i] ? 'done' : ''}">${steps[i] ? '✓' : '○'} ${s}</span>`
  ).join('<span class="step-sep">→</span>');
}

// ── Video Preview Modal ───────────────────────────────────────────────────────

function openVideoPreview(clipId) {
  const modal = document.getElementById('video-modal');
  const video = document.getElementById('modal-video');
  video.src = `/api/clips/${clipId}/video`;
  modal.classList.remove('hidden');
}

document.getElementById('modal-close').addEventListener('click', closeModal);
document.getElementById('modal-backdrop').addEventListener('click', closeModal);

function closeModal() {
  const modal = document.getElementById('video-modal');
  const video = document.getElementById('modal-video');
  video.pause();
  video.src = '';
  modal.classList.add('hidden');
}

// ── Queue ─────────────────────────────────────────────────────────────────────

async function fetchQueue() {
  try {
    state.queueJobs = await api('/api/queue');
    renderQueue();
  } catch (e) { /* silent fail */ }
}

function renderQueue() {
  const el = document.getElementById('queue-list');
  const count = document.getElementById('queue-count');
  const active = state.queueJobs.filter(j => j.status !== 'done' && j.status !== 'failed').length;
  count.textContent = active;

  if (!state.queueJobs.length) {
    el.innerHTML = '<div class="empty-state" style="padding:16px;font-size:12px">No jobs yet</div>';
    return;
  }

  // Notify on newly completed jobs
  state.queueJobs.forEach(job => {
    if (job.status === 'done' && !state.knownDoneJobs.has(job.id)) {
      state.knownDoneJobs.add(job.id);
      showToast(`✅ Video ready: ${job.output_name}`, 'success');
      fetchPublished(); // refresh published list
    }
  });

  el.innerHTML = state.queueJobs.map(job => {
    const removable = job.status === 'done' || job.status === 'failed';
    return `
      <div class="job-card">
        <div class="job-card-top">
          <span class="job-name" title="${escHtml(job.output_name)}">${escHtml(job.output_name)}</span>
          ${removable ? `<button class="btn btn-danger btn-sm" onclick="removeJob('${job.id}')">✕</button>` : ''}
        </div>
        <div class="job-status">
          <span class="status-badge status-${job.status}">${job.status}</span>
          <span class="job-time">${relTime(job.created_at)}</span>
        </div>
        ${job.error ? `<div class="job-error" title="${escHtml(job.error)}">⚠ ${escHtml(job.error)}</div>` : ''}
      </div>`;
  }).join('');
}

async function removeJob(jobId) {
  try {
    await api(`/api/queue/${jobId}`, { method: 'DELETE' });
    fetchQueue();
  } catch (e) {
    showToast(`Failed to remove: ${e.message}`, 'error');
  }
}

// ── Published ─────────────────────────────────────────────────────────────────

async function fetchPublished() {
  try {
    state.published = await api('/api/published');
    renderPublished();
  } catch (e) { /* silent */ }
}

function renderPublished() {
  const el = document.getElementById('published-list');
  const tracker = document.getElementById('daily-tracker');
  const { videos, today_count, daily_target } = state.published;

  const trackerClass = today_count >= daily_target ? 'badge-green' : 'badge-orange';
  tracker.className = `badge ${trackerClass}`;
  tracker.textContent = `${today_count}/${daily_target} today`;

  if (!videos.length) {
    el.innerHTML = '<div class="empty-state" style="padding:16px;font-size:12px">No published videos yet</div>';
    return;
  }

  el.innerHTML = videos.map(v => `
    <div class="pub-card">
      <div class="pub-info">
        <div class="pub-name" title="${escHtml(v.filename)}">${escHtml(v.filename)}</div>
        <div class="pub-meta">${v.size_mb}MB · ${relTime(v.created_at)}</div>
      </div>
      <a class="btn btn-secondary btn-sm" href="${v.url}" download="${escHtml(v.filename)}">↓</a>
    </div>`
  ).join('');
}

// ── Filters ───────────────────────────────────────────────────────────────────

document.querySelectorAll('.pill').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.filters.source = btn.dataset.source;
    fetchClips();
  });
});

document.getElementById('score-slider').addEventListener('input', function() {
  state.filters.minScore = parseInt(this.value);
  document.getElementById('score-val').textContent = this.value;
  fetchClips();
});

document.getElementById('refresh-btn').addEventListener('click', fetchClips);

// ── Polling ───────────────────────────────────────────────────────────────────

function pollQueue() {
  setInterval(async () => {
    await fetchQueue();
    await fetchPublished();
  }, 5000);
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  fetchClips();
  fetchQueue();
  fetchPublished();
  pollQueue();
});
