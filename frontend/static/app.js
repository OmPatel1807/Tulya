/**
 * Tulya (तुल्य) - Glass Workspace Application Controller
 * Handles Bilingual Dual Reader, Discrepancy Drawer, SVG Connectors, and Review State.
 */

(function () {
  'use strict';

  // --- State ---
  let currentJobId = null;
  let currentReport = null;
  let currentFilter = 'ALL';
  let activeFindingId = null;
  let reviewDecisions = {}; // finding_id -> 'CONFIRMED' | 'DISMISSED'

  // Diagnostic flags for automated verification
  window.__appLoaded = false;
  window.__selectedFindingId = null;
  window.__connectorRendered = false;
  window.__currentJobId = null;
  window.__getReviewDecisions = () => reviewDecisions;

  // --- DOM Elements ---
  const sampleSelect = document.getElementById('sample-select');
  const btnRunAnalysis = document.getElementById('btn-run-analysis');
  const btnUploadModal = document.getElementById('btn-open-upload');
  const uploadModal = document.getElementById('upload-modal');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const uploadForm = document.getElementById('upload-form');

  const progressPanel = document.getElementById('progress-panel');
  const progressFill = document.getElementById('progress-fill');
  const progressPercentText = document.getElementById('progress-percent');
  const progressStageMsg = document.getElementById('progress-stage-msg');

  const readerEn = document.getElementById('reader-en');
  const readerHi = document.getElementById('reader-hi');
  const findingsListEl = document.getElementById('findings-list');
  const findingsCountBadge = document.getElementById('findings-count-badge');
  const connectorSvg = document.getElementById('connector-svg');
  const filterChips = document.querySelectorAll('.filter-chip');

  const btnExportJson = document.getElementById('export-json');
  const btnExportCsv = document.getElementById('export-csv');
  const btnExportMd = document.getElementById('export-md');

  // --- Initialization ---
  async function init() {
    loadPersistedDecisions();
    setupEventListeners();
    await loadSamples();
    window.__appLoaded = true;
  }

  // --- Event Listeners ---
  function setupEventListeners() {
    if (sampleSelect) {
      sampleSelect.addEventListener('change', () => {
        const sampleId = sampleSelect.value;
        if (sampleId) runSampleAnalysis(sampleId);
      });
    }

    if (btnRunAnalysis && sampleSelect) {
      btnRunAnalysis.addEventListener('click', () => {
        const sampleId = sampleSelect.value;
        if (sampleId) runSampleAnalysis(sampleId);
      });
    }

    if (btnUploadModal && uploadModal) {
      btnUploadModal.addEventListener('click', () => {
        uploadModal.style.display = 'flex';
      });
    }

    if (btnCloseModal && uploadModal) {
      btnCloseModal.addEventListener('click', () => {
        uploadModal.style.display = 'none';
      });
    }

    if (uploadForm) {
      uploadForm.addEventListener('submit', handlePdfUpload);
    }

    // Filter Chips
    filterChips.forEach(chip => {
      chip.addEventListener('click', () => {
        filterChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        currentFilter = chip.getAttribute('data-filter') || 'ALL';
        renderFindingsList();
      });
    });

    // Exports
    if (btnExportJson) btnExportJson.addEventListener('click', () => triggerExport('json'));
    if (btnExportCsv) btnExportCsv.addEventListener('click', () => triggerExport('csv'));
    if (btnExportMd) btnExportMd.addEventListener('click', () => triggerExport('md'));

    // Redraw SVG connector on scroll or resize
    window.addEventListener('resize', redrawConnector);
    if (readerEn) readerEn.addEventListener('scroll', redrawConnector, { passive: true });
    if (readerHi) readerHi.addEventListener('scroll', redrawConnector, { passive: true });
  }

  // --- Persistence: LocalStorage Review Decisions ---
  function loadPersistedDecisions() {
    try {
      const stored = localStorage.getItem('tulya_review_decisions');
      if (stored) {
        reviewDecisions = JSON.parse(stored);
      }
    } catch (e) {
      console.warn('Failed to parse stored review decisions:', e);
    }
  }

  function saveDecision(findingId, decision) {
    reviewDecisions[findingId] = decision;
    try {
      localStorage.setItem('tulya_review_decisions', JSON.stringify(reviewDecisions));
    } catch (e) {
      console.warn('Failed to persist decision:', e);
    }
    renderFindingsList();
  }

  // --- Samples Catalog ---
  async function loadSamples() {
    try {
      const res = await fetch('/api/samples');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      sampleSelect.innerHTML = '';

      data.samples.forEach(sample => {
        const opt = document.createElement('option');
        opt.value = sample.id;
        opt.textContent = `${sample.title} (${sample.pages_en} EN / ${sample.pages_hi} HI p.)`;
        sampleSelect.appendChild(opt);
      });

      // Automatically analyze first sample if available
      if (data.samples && data.samples.length > 0) {
        runSampleAnalysis(data.samples[0].id);
      }
    } catch (err) {
      console.error('Failed to load sample list:', err);
    }
  }

  // --- Run Sample Analysis ---
  async function runSampleAnalysis(sampleId) {
    showProgress(true);
    updateProgressUI(10, 'Initializing pipeline job...');

    try {
      const res = await fetch(`/api/samples/${sampleId}/analyze?force_deterministic=true`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error(`Failed to start job: ${res.statusText}`);
      const jobData = await res.json();
      currentJobId = jobData.job_id;
      window.__currentJobId = currentJobId;

      await pollJobCompletion(currentJobId);
    } catch (err) {
      showProgress(false);
      alert(`Analysis error: ${err.message}`);
    }
  }

  // --- PDF Upload Handler ---
  async function handlePdfUpload(e) {
    e.preventDefault();
    const enFile = document.getElementById('upload-en-file').files[0];
    const hiFile = document.getElementById('upload-hi-file').files[0];

    if (!enFile || !hiFile) {
      alert('Please select both English and Hindi PDF files.');
      return;
    }

    if (uploadModal) uploadModal.style.display = 'none';
    showProgress(true);
    updateProgressUI(5, 'Uploading documents to Tulya engine...');

    const formData = new FormData();
    formData.append('en_file', enFile);
    formData.append('hi_file', hiFile);
    formData.append('force_deterministic', 'true');

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || res.statusText);
      }

      const jobData = await res.json();
      currentJobId = jobData.job_id;
      window.__currentJobId = currentJobId;

      await pollJobCompletion(currentJobId);
    } catch (err) {
      showProgress(false);
      alert(`Upload rejected: ${err.message}`);
    }
  }

  // --- Poll Job Status ---
  async function pollJobCompletion(jobId) {
    const startTime = Date.now();
    const maxPollMs = 30000;

    while (Date.now() - startTime < maxPollMs) {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const p = await res.json();

        updateProgressUI(p.progress_percent, `[${p.stage}] ${p.stage_message}`);

        if (p.status === 'COMPLETED') {
          showProgress(false);
          await loadJobReport(jobId);
          return;
        }

        if (p.status === 'FAILED') {
          showProgress(false);
          alert(`Pipeline failed: ${p.error}`);
          return;
        }
      } catch (err) {
        console.warn('Poll error:', err);
      }
      await new Promise(r => setTimeout(r, 400));
    }

    showProgress(false);
    alert('Pipeline execution timed out.');
  }

  function showProgress(visible) {
    if (progressPanel) {
      progressPanel.style.display = visible ? 'block' : 'none';
    }
  }

  function updateProgressUI(percent, msg) {
    if (progressFill) progressFill.style.width = `${percent}%`;
    if (progressPercentText) progressPercentText.textContent = `${Math.round(percent)}%`;
    if (progressStageMsg) progressStageMsg.textContent = msg;
  }

  // --- Load and Render Job Report ---
  async function loadJobReport(jobId) {
    try {
      const res = await fetch(`/api/jobs/${jobId}/report`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      currentReport = await res.json();

      renderReader();
      renderFindingsList();

      // Automatically select first finding if available
      if (currentReport.findings && currentReport.findings.length > 0) {
        selectFinding(currentReport.findings[0].finding_id);
      }
    } catch (err) {
      console.error('Failed to load report:', err);
      alert(`Report load failed: ${err.message}`);
    }
  }

  // --- Render Reader Panes ---
  function renderReader() {
    if (!readerEn || !readerHi || !currentReport) return;

    readerEn.innerHTML = '';
    readerHi.innerHTML = '';

    const pairs = currentReport.aligned_pairs || [];

    pairs.forEach((pair, idx) => {
      const pairId = `pair-${idx}`;

      // English clause block
      const blockEn = document.createElement('div');
      blockEn.className = 'clause-block';
      blockEn.id = `en-${pairId}`;
      blockEn.setAttribute('data-pair-id', pairId);

      const headerEn = document.createElement('div');
      headerEn.className = 'clause-header';
      headerEn.innerHTML = `
        <span class="clause-num">${pair.en_paths && pair.en_paths.length ? pair.en_paths.join(' > ') : `Provision #${idx+1}`}</span>
        <span class="badge-lang en">EN</span>
      `;

      const textEn = document.createElement('div');
      textEn.className = 'clause-text';
      textEn.id = `text-en-${pairId}`;
      textEn.textContent = pair.en_text || '(Omitted or structural preamble)';

      blockEn.appendChild(headerEn);
      blockEn.appendChild(textEn);
      readerEn.appendChild(blockEn);

      // Hindi clause block
      const blockHi = document.createElement('div');
      blockHi.className = 'clause-block';
      blockHi.id = `hi-${pairId}`;
      blockHi.setAttribute('data-pair-id', pairId);

      const headerHi = document.createElement('div');
      headerHi.className = 'clause-header';
      headerHi.innerHTML = `
        <span class="clause-num">${pair.hi_paths && pair.hi_paths.length ? pair.hi_paths.join(' > ') : `उपबंध #${idx+1}`}</span>
        <span class="badge-lang hi">HI</span>
      `;

      const textHi = document.createElement('div');
      textHi.className = 'clause-text hindi';
      textHi.id = `text-hi-${pairId}`;
      textHi.textContent = pair.hi_text || '(छोड़ा गया या संरचनात्मक प्रस्तावना)';

      blockHi.appendChild(headerHi);
      blockHi.appendChild(textHi);
      readerHi.appendChild(blockHi);
    });
  }

  // --- Render Findings List ---
  function renderFindingsList() {
    if (!findingsListEl || !currentReport) return;

    findingsListEl.innerHTML = '';
    const allFindings = currentReport.findings || [];

    const filtered = allFindings.filter(f => {
      if (currentFilter === 'ALL') return true;
      return f.category === currentFilter;
    });

    if (findingsCountBadge) {
      findingsCountBadge.textContent = `${filtered.length} of ${allFindings.length}`;
    }

    filtered.forEach(f => {
      const card = document.createElement('div');
      card.className = `finding-card ${f.finding_id === activeFindingId ? 'selected' : ''}`;
      card.id = `card-${f.finding_id}`;
      card.setAttribute('data-finding-id', f.finding_id);

      const decision = reviewDecisions[f.finding_id];
      let decisionBadgeHtml = '';
      if (decision === 'CONFIRMED') {
        decisionBadgeHtml = `<span class="badge-decision confirmed">&check; CONFIRMED</span>`;
      } else if (decision === 'DISMISSED') {
        decisionBadgeHtml = `<span class="badge-decision dismissed">&times; DISMISSED</span>`;
      }

      const quoteEnPreview = f.quote_en ? f.quote_en.substring(0, 80) : 'None';
      const quoteHiPreview = f.quote_hi ? f.quote_hi.substring(0, 80) : 'None';

      card.innerHTML = `
        <div class="finding-badges">
          <span class="badge-cat">${f.category}</span>
          <span class="badge-sev ${f.severity}">${f.severity}</span>
          <span class="badge-src">${f.source}</span>
          ${decisionBadgeHtml}
        </div>
        <div class="finding-citation">${f.metadata && f.metadata.provision_en ? f.metadata.provision_en : 'Clause Reference'}</div>
        <div class="finding-desc">${escapeHtml(f.explanation)}</div>
        <div class="finding-quotes">
          <div class="fq-item"><strong>EN:</strong> "${escapeHtml(quoteEnPreview)}..."</div>
          <div class="fq-item" style="font-family: var(--font-hindi);"><strong>HI:</strong> "${escapeHtml(quoteHiPreview)}..."</div>
        </div>
        <div class="finding-actions">
          <button class="btn btn-sm btn-glass btn-confirm" data-fid="${f.finding_id}">Confirm</button>
          <button class="btn btn-sm btn-glass btn-dismiss" data-fid="${f.finding_id}">Dismiss</button>
        </div>
      `;

      // Select finding on card click
      card.addEventListener('click', (e) => {
        if (e.target.closest('.btn-confirm') || e.target.closest('.btn-dismiss')) return;
        selectFinding(f.finding_id);
      });

      // Confirm button
      const btnConfirm = card.querySelector('.btn-confirm');
      if (btnConfirm) {
        btnConfirm.addEventListener('click', (e) => {
          e.stopPropagation();
          saveDecision(f.finding_id, 'CONFIRMED');
        });
      }

      // Dismiss button
      const btnDismiss = card.querySelector('.btn-dismiss');
      if (btnDismiss) {
        btnDismiss.addEventListener('click', (e) => {
          e.stopPropagation();
          saveDecision(f.finding_id, 'DISMISSED');
        });
      }

      findingsListEl.appendChild(card);
    });
  }

  // --- Select Finding & Highlight Quotes ---
  function selectFinding(findingId) {
    activeFindingId = findingId;
    window.__selectedFindingId = findingId;

    if (!currentReport || !currentReport.findings) return;
    const finding = currentReport.findings.find(f => f.finding_id === findingId);
    if (!finding) return;

    // Highlight finding card in drawer
    document.querySelectorAll('.finding-card').forEach(c => {
      c.classList.toggle('selected', c.getAttribute('data-finding-id') === findingId);
    });

    // Reset previous clause highlights and clean unwrapped marks
    document.querySelectorAll('.clause-block').forEach(b => b.classList.remove('active-pair'));
    document.querySelectorAll('mark.highlight-en, mark.highlight-hi').forEach(m => {
      const parent = m.parentNode;
      if (parent) {
        while (m.firstChild) parent.insertBefore(m.firstChild, m);
        parent.removeChild(m);
      }
    });

    // Locate target pair index
    const pairs = currentReport.aligned_pairs || [];
    let targetIndex = -1;

    for (let i = 0; i < pairs.length; i++) {
      const p = pairs[i];
      if (p.finding_ids && p.finding_ids.includes(findingId)) {
        targetIndex = i;
        break;
      }
      if (finding.quote_en && p.en_text && p.en_text.includes(finding.quote_en.trim())) {
        targetIndex = i;
        break;
      }
    }

    if (targetIndex === -1 && pairs.length > 0) targetIndex = 0;

    const pairId = `pair-${targetIndex}`;
    const elEn = document.getElementById(`en-${pairId}`);
    const elHi = document.getElementById(`hi-${pairId}`);

    if (elEn && elHi) {
      elEn.classList.add('active-pair');
      elHi.classList.add('active-pair');

      // Scroll into view smoothly
      elEn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      elHi.scrollIntoView({ behavior: 'smooth', block: 'center' });

      // Apply highlighted marks inside texts
      applyTextHighlight(`text-en-${pairId}`, finding.quote_en, 'highlight-en');
      applyTextHighlight(`text-hi-${pairId}`, finding.quote_hi, 'highlight-hi');

      // Render connector
      setTimeout(redrawConnector, 150);
    }
  }

  function applyTextHighlight(containerId, quote, highlightClass) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const rawText = el.textContent || '';
    const cleanQuote = (quote || '').trim();

    if (!cleanQuote) {
      // Omission / absent in this text: highlight omission marker so visual diff is explicit
      el.innerHTML = `<mark class="${highlightClass}">[Statutory Omission: Not present in this text]</mark> ` + escapeHtml(rawText);
      return;
    }

    const pos = rawText.indexOf(cleanQuote);
    if (pos >= 0) {
      const before = rawText.substring(0, pos);
      const matched = rawText.substring(pos, pos + cleanQuote.length);
      const after = rawText.substring(pos + cleanQuote.length);
      el.innerHTML = `${escapeHtml(before)}<mark class="${highlightClass}">${escapeHtml(matched)}</mark>${escapeHtml(after)}`;
    } else {
      // Fuzzy / word-based match
      const words = cleanQuote.split(/\s+/).filter(w => w.length > 1).slice(0, 3).join(' ');
      const subPos = words ? rawText.indexOf(words) : -1;
      if (subPos >= 0) {
        const before = rawText.substring(0, subPos);
        const matched = rawText.substring(subPos, subPos + words.length);
        const after = rawText.substring(subPos + words.length);
        el.innerHTML = `${escapeHtml(before)}<mark class="${highlightClass}">${escapeHtml(matched)}</mark>${escapeHtml(after)}`;
      } else {
        // Fallback: highlight leading provision anchor so connector has valid target
        const prefixLen = Math.min(rawText.length, 35);
        el.innerHTML = `<mark class="${highlightClass}">${escapeHtml(rawText.substring(0, prefixLen))}</mark>${escapeHtml(rawText.substring(prefixLen))}`;
      }
    }
  }

  // --- SVG Connector Line Drawing ---
  function redrawConnector() {
    if (!connectorSvg) return;

    const markEn = document.querySelector('.highlight-en');
    const markHi = document.querySelector('.highlight-hi');

    if (!markEn || !markHi) {
      connectorSvg.innerHTML = '';
      window.__connectorRendered = false;
      return;
    }

    const svgRect = connectorSvg.getBoundingClientRect();
    const rectEn = markEn.getBoundingClientRect();
    const rectHi = markHi.getBoundingClientRect();

    // Start point at right edge of English quote
    const x1 = rectEn.right - svgRect.left;
    const y1 = rectEn.top + rectEn.height / 2 - svgRect.top;

    // End point at left edge of Hindi quote
    const x2 = rectHi.left - svgRect.left;
    const y2 = rectHi.top + rectHi.height / 2 - svgRect.top;

    // Bezier control points for smooth bridge curve
    const dx = Math.abs(x2 - x1) * 0.5;
    const cx1 = x1 + dx;
    const cy1 = y1;
    const cx2 = x2 - dx;
    const cy2 = y2;

    const pathData = `M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`;

    connectorSvg.innerHTML = `
      <defs>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <circle cx="${x1}" cy="${y1}" r="4" fill="#f59e0b" />
      <path d="${pathData}" class="connector-path" filter="url(#glow)" />
      <circle cx="${x2}" cy="${y2}" r="4" fill="#ef4444" />
    `;

    window.__connectorRendered = true;
  }

  // --- Export Report ---
  function triggerExport(format) {
    if (!currentJobId) {
      alert('No active job report to export.');
      return;
    }
    window.location.href = `/api/jobs/${currentJobId}/export?format=${format}`;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();

