/* CrowdListen Studio v2 — app.js */

const API = '';
let currentJobId = null;
let currentFilename = '';
let selectedClips = new Set();
let eventSource = null;

/* ── Tab nav ──────────────────────────────────────────────────── */

function switchTab(name) {
  document.querySelectorAll('.tab-page').forEach(p => p.classList.add('hidden'));
  document.getElementById('tab-' + name).classList.remove('hidden');
  document.querySelectorAll('.nav-link, .panel-tab').forEach(b => b.classList.remove('active'));
  const btns = document.querySelectorAll(`[data-tab=\"${name}\"]`);
  btns.forEach(btn => btn.classList.add('active'));
  const main = document.getElementById('main');
  if (main) main.classList.toggle('home-layout', name === 'home');
  if (name === 'published') loadPublished();
}

/* ── Step nav ─────────────────────────────────────────────────── */

function gotoStep(n) {
  document.querySelectorAll('.step-page').forEach(p => p.classList.add('hidden'));
  const page = document.getElementById('step-' + n);
  if (page) page.classList.remove('hidden');
  document.querySelectorAll('.step-item').forEach(el => {
    const s = parseInt(el.dataset.step);
    el.classList.toggle('active', s === n);
    el.classList.toggle('done', s < n);
  });
}

/* ── Step 1: Upload ───────────────────────────────────────────── */

function handleDragOver(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.add('drag-over');
}
function handleDragLeave(e) {
  document.getElementById('drop-zone').classList.remove('drag-over');
}
function handleDrop(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
}
function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) uploadFile(file);
}

async function uploadFile(file) {
  currentFilename = file.name;
  const progressEl = document.getElementById('upload-progress');
  const fillEl = document.getElementById('upload-fill');
  const labelEl = document.getElementById('upload-label');
  progressEl.classList.remove('hidden');
  labelEl.textContent = `Uploading ${file.name}…`;
  fillEl.style.width = '10%';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API}/api/upload`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        fillEl.style.width = Math.round(e.loaded / e.total * 95) + '%';
      }
    };
    xhr.onload = () => {
      if (xhr.status === 200) {
        const data = JSON.parse(xhr.responseText);
        currentJobId = data.job_id;
        fillEl.style.width = '100%';
        labelEl.textContent = `✅ ${file.name} uploaded`;
        setTimeout(() => gotoStep(2), 800);
        loadAdAssets();
      } else {
        labelEl.textContent = `❌ Upload failed: ${xhr.statusText}`;
      }
    };
    xhr.send(formData);
  } catch (err) {
    document.getElementById('upload-label').textContent = `❌ ${err.message}`;
  }
}

/* ── Step 2: Options ──────────────────────────────────────────── */

document.querySelectorAll('.type-card').forEach(card => {
  card.addEventListener('click', () => {
    const cb = card.querySelector('input[type="checkbox"]');
    cb.checked = !cb.checked;
    card.classList.toggle('selected', cb.checked);
  });
});

function toggleAdOptions(enabled) {
  document.getElementById('ad-options').classList.toggle('hidden', !enabled);
  if (enabled) loadAdAssets();
}

function toggleAdFrequency(val) {
  document.getElementById('ad-frequency-row').style.display =
    (val === 'between' || val === 'both') ? '' : 'none';
}

async function loadAdAssets() {
  try {
    const res = await fetch(`${API}/api/ads`);
    const data = await res.json();
    const sel = document.getElementById('ad-asset-select');
    const current = sel.value;
    sel.innerHTML = '<option value="">— select ad asset —</option>';
    data.ads.forEach(a => {
      const opt = document.createElement('option');
      opt.value = a.filename;
      opt.textContent = a.filename;
      sel.appendChild(opt);
    });
    if (current) sel.value = current;
  } catch (e) { /* no ads yet */ }
}

async function uploadAdAsset(e) {
  const file = e.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API}/api/ads/upload`, { method: 'POST', body: formData });
  if (res.ok) {
    await loadAdAssets();
    document.getElementById('ad-asset-select').value = file.name;
  }
}

function getOptions() {
  const clipTypes = Array.from(document.querySelectorAll('input[name="clip_type"]:checked'))
    .map(cb => cb.value);
  const addNarration = document.getElementById('opt-narration').checked;
  const count = parseInt(document.getElementById('opt-count').value);
  const audience = document.getElementById('opt-audience').value;
  const adsEnabled = document.getElementById('opt-ads').checked;

  let adConfig = null;
  if (adsEnabled) {
    const asset = document.getElementById('ad-asset-select').value;
    adConfig = {
      enabled: true,
      asset: asset || null,
      placement: document.getElementById('ad-placement').value,
      frequency: parseInt(document.getElementById('ad-frequency').value),
      image_duration: parseInt(document.getElementById('ad-img-duration').value),
    };
  }
  return { clipTypes, addNarration, count, audience, adConfig };
}

async function startPipeline() {
  if (!currentJobId) { alert('No video uploaded.'); return; }
  const opts = getOptions();
  if (!opts.clipTypes.length) { alert('Select at least one clip type.'); return; }

  document.getElementById('processing-filename').textContent = currentFilename;
  gotoStep(3);
  resetPipelineUI();

  // Subscribe to SSE
  if (eventSource) eventSource.close();
  eventSource = new EventSource(`${API}/api/events`);
  eventSource.onmessage = (e) => {
    try { handlePipelineEvent(JSON.parse(e.data)); } catch (_) {}
  };

  const body = {
    job_id: currentJobId,
    clip_types: opts.clipTypes,
    add_narration: opts.addNarration,
    count: opts.count,
    audience: opts.audience,
    ad_config: opts.adConfig,
  };
  await fetch(`${API}/api/pipeline/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function resetPipelineUI() {
  ['audio','transcribe','detect','render'].forEach(s => {
    document.getElementById('pss-' + s).textContent = '–';
    document.getElementById('ps-' + s).className = 'pipeline-step';
  });
  document.getElementById('pipeline-fill').style.width = '0%';
  document.getElementById('pipeline-msg').textContent = 'Starting…';
}

function handlePipelineEvent(evt) {
  if (evt.job_id !== currentJobId) return;
  const step = evt.step;
  const status = evt.status;

  const stepMap = { audio: 'audio', transcribe: 'transcribe', detect: 'detect', render: 'render' };
  const key = stepMap[step];
  if (key) {
    const statusEl = document.getElementById('pss-' + key);
    const rowEl = document.getElementById('ps-' + key);
    if (status === 'running') {
      statusEl.textContent = '⏳';
      rowEl.classList.add('running');
    } else if (status === 'done') {
      statusEl.textContent = '✅';
      rowEl.classList.remove('running');
      rowEl.classList.add('done');
    } else if (status === 'error') {
      statusEl.textContent = '❌';
      rowEl.classList.add('error');
    }
  }

  document.getElementById('pipeline-fill').style.width = (evt.progress || 0) + '%';
  document.getElementById('pipeline-msg').textContent = evt.msg || '';

  if (step === 'render' && status === 'done') {
    eventSource.close();
    setTimeout(() => loadLibrary(), 500);
  }
}

/* ── Step 4: Library ──────────────────────────────────────────── */

async function loadLibrary() {
  gotoStep(4);
  selectedClips.clear();
  updateSaveButton();

  const res = await fetch(`${API}/api/library/${currentJobId}`);
  const data = await res.json();
  const grid = document.getElementById('library-grid');

  if (!data.clips || !data.clips.length) {
    grid.innerHTML = '<div class="empty-state">No clips generated. Try processing again.</div>';
    return;
  }

  grid.innerHTML = data.clips.map(clip => `
    <div class="clip-card" id="card-${clip.filename}" onclick="toggleClip('${clip.filename}')">
      <div class="clip-video-wrap">
        <video class="clip-video" src="${clip.url}" muted loop preload="metadata"
               onmouseenter="this.play()" onmouseleave="this.pause();this.currentTime=0"></video>
        <div class="clip-select-overlay">
          <span class="clip-check" id="check-${clip.filename}">☐</span>
        </div>
      </div>
      <div class="clip-info">
        <div class="clip-caption">${clip.caption || clip.filename}</div>
        <div class="clip-meta">
          <span class="clip-badge ${clip.type}">${clip.type}</span>
          <span class="clip-duration">${Math.round(clip.duration)}s</span>
          <span class="clip-score">★ ${clip.score}</span>
        </div>
      </div>
    </div>
  `).join('');
}

function toggleClip(filename) {
  const card = document.getElementById('card-' + filename);
  const check = document.getElementById('check-' + filename);
  if (selectedClips.has(filename)) {
    selectedClips.delete(filename);
    card.classList.remove('selected');
    check.textContent = '☐';
  } else {
    selectedClips.add(filename);
    card.classList.add('selected');
    check.textContent = '☑';
  }
  updateSaveButton();
}

function updateSaveButton() {
  const n = selectedClips.size;
  document.getElementById('selected-count').textContent = `${n} selected`;
  document.getElementById('save-btn').disabled = n === 0;
  document.getElementById('save-btn').textContent = n > 0 ? `Save Selected (${n}) →` : 'Save Selected →';
}

async function saveSelected() {
  if (!currentJobId || !selectedClips.size) return;
  const res = await fetch(`${API}/api/library/${currentJobId}/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ clips: Array.from(selectedClips) }),
  });
  const data = await res.json();
  if (data.ok) {
    alert(`✅ Saved ${data.saved} clip${data.saved !== 1 ? 's' : ''} to ${data.dest}`);
    switchTab('published');
  }
}

/* ── Published tab (Scheduler) ───────────────────────────────── */

function fmtDate(iso) {
  try { return new Date(iso).toLocaleString(); } catch { return iso || ''; }
}

function renderVideoCard(clip, actionsHtml='') {
  return `
    <div class="clip-card scheduler-item-card">
      <div class="clip-video-wrap">
        <video class="clip-video" src="${clip.url}"
               muted loop preload="metadata"
               onmouseenter="this.play()" onmouseleave="this.pause();this.currentTime=0"></video>
      </div>
      <div class="clip-info">
        <div class="clip-caption">${clip.filename}</div>
        <div class="clip-meta">
          <span class="clip-date">${clip.folder || ''}</span>
          <span class="clip-duration">${clip.size_mb || 0}MB</span>
          <span class="clip-date">${clip.schedule_date || ''}</span>
        </div>
        ${actionsHtml}
      </div>
    </div>
  `;
}

async function setSchedule(relPath, val) {
  await fetch(`${API}/api/published/schedule`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rel_path: relPath, schedule_date: val }),
  });
  loadPublished();
}

async function toggleArchive(relPath, archived=true) {
  await fetch(`${API}/api/published/archive`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rel_path: relPath, archived }),
  });
  loadPublished();
}

async function loadPublished() {
  const grid = document.getElementById('published-grid');
  grid.innerHTML = '<div class="loading-state">Loading scheduler…</div>';

  const res = await fetch(`${API}/api/published`);
  const data = await res.json();

  const newly = data.newly_generated || [];
  const groups = data.to_be_published_groups || [];
  const archived = data.archived || [];

  let html = '';

  html += `<section class="option-section"><div class="option-section-title">Newly Generated</div>`;
  if (!newly.length) {
    html += '<div class="empty-state" style="padding:16px">No newly generated videos in review.</div>';
  } else {
    html += `<div class="scheduler-row">${newly.map(v => renderVideoCard(v)).join('')}</div>`;
  }
  html += `</section>`;

  html += `<section class="option-section"><div class="option-section-title">To Be Published</div>`;
  if (!groups.length) {
    html += '<div class="empty-state" style="padding:16px">Nothing scheduled yet.</div>';
  } else {
    for (const g of groups) {
      html += `<h3 style="margin:8px 0 12px;font-size:18px">${g.label}</h3>`;
      html += `<div class="scheduler-row">`;
      html += g.items.map(v => {
        const actions = `
          <div style="margin-top:10px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <input type="date" value="${v.schedule_date || ''}" onchange="setSchedule('${v.rel_path}', this.value)" class="text-input" style="width:170px"/>
            <button class="btn-small" onclick="toggleArchive('${v.rel_path}', true)">Archive</button>
            <button class="btn-danger-small" onclick="deletePublished('${v.rel_path}')">Delete</button>
          </div>
        `;
        return renderVideoCard(v, actions);
      }).join('');
      html += `</div>`;
    }
  }
  html += `</section>`;

  html += `<section class="option-section"><div class="option-section-title">Archived</div>`;
  if (!archived.length) {
    html += '<div class="empty-state" style="padding:16px">No archived items.</div>';
  } else {
    html += `<div class="scheduler-row">`;
    html += archived.map(v => {
      const actions = `
        <div style="margin-top:10px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <button class="btn-small" onclick="toggleArchive('${v.rel_path}', false)">Unarchive</button>
          <button class="btn-danger-small" onclick="deletePublished('${v.rel_path}')">Delete</button>
        </div>
      `;
      return renderVideoCard(v, actions);
    }).join('');
    html += `</div>`;
  }
  html += `</section>`;

  grid.innerHTML = html;
}

async function deletePublished(relPath) {
  if (!confirm(`Delete ${relPath}?`)) return;
  await fetch(`${API}/api/published/${relPath}`, { method: 'DELETE' });
  loadPublished();
}


/* ── Repurpose tab ───────────────────────────────────────────── */

async function runRepurpose() {
  const resultEl = document.getElementById('repurpose-result');
  resultEl.textContent = 'Running...';

  const text = (document.getElementById('repurpose-text')?.value || '').trim();
  const platformSel = document.getElementById('repurpose-platforms');
  const selectedPlatforms = platformSel ? Array.from(platformSel.selectedOptions).map(o => o.value) : [];
  const platforms = (selectedPlatforms.length ? selectedPlatforms : ['blog','linkedin','newsletter','thread']).join(',');
  const version = (document.getElementById('repurpose-version')?.value || '').trim();
  const srcFile = document.getElementById('repurpose-file')?.files?.[0];
  const images = document.getElementById('repurpose-images')?.files || [];

  if (!text && !srcFile && images.length === 0) {
    resultEl.textContent = 'Please provide text, or upload a source file/image(s).';
    return;
  }

  const fd = new FormData();
  if (text) fd.append('text_content', text);
  fd.append('platforms', platforms);
  if (version) fd.append('version', version);
  fd.append('style', 'every');
  if (srcFile) fd.append('source_file', srcFile);
  for (const img of images) fd.append('images', img);

  try {
    const res = await fetch(`${API}/api/content-gen/upload`, { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    resultEl.textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    resultEl.textContent = `Error: ${e.message}`;
  }
}


const REPURPOSE_GUIDES = {
  blog: `BLOG
- Lead with clear thesis in first 2-3 sentences.
- Keep structure: problem → insight → examples → takeaway.
- Prefer depth and concrete examples over punchlines.`,
  linkedin: `LINKEDIN
- Strong opening hook in first line.
- 1 idea per short paragraph; skimmable spacing.
- End with one question to invite comments.`,
  newsletter: `NEWSLETTER
- Conversational voice + clear narrative arc.
- Include concise section headers and practical takeaways.
- Keep reader-oriented: why this matters now.`,
  thread: `THREAD
- Start with a high-contrast claim.
- Break into short standalone points (1 idea per post).
- Keep each line compact and momentum-driven.`
};

function updateRepurposeGuide() {
  const p = document.getElementById('repurpose-guide-platform')?.value || 'blog';
  const box = document.getElementById('repurpose-guide');
  if (box) box.textContent = REPURPOSE_GUIDES[p] || '';
}

function copyRepurposeGuidePrompt() {
  const p = document.getElementById('repurpose-guide-platform')?.value || 'blog';
  const text = `Rewrite for ${p} using this guide:

${REPURPOSE_GUIDES[p]}`;
  navigator.clipboard.writeText(text).then(() => {
    const r = document.getElementById('repurpose-result');
    if (r) r.textContent = 'Copied OpenClaw guide prompt to clipboard.';
  });
}


/* ── Init ─────────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
  switchTab('home');
  gotoStep(1);
  updateRepurposeGuide();
});
