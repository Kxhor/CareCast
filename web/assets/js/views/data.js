/**
 * S6 — Data & Limitations Screen
 * UI_UX_DESIGN §5 & APP_FLOW §4
 * Read mode: comfortable line length, full provenance, quality audit, limitations L-01..L-12, reproduction commands.
 */

import { api } from '../api.js';
import {
  el,
  createCard,
  createDataTable,
  createErrorBlock,
  createSkeleton,
} from '../components.js';
import { formatDate } from '../format.js';

export function renderDataLimitations(container) {
  while (container.firstChild) {
    container.removeChild(container.firstChild);
  }

  const root = el('div', { className: 'view-data-limitations' });
  container.appendChild(root);

  /* ── Page Header (A11Y-05) ───────────────────────────────────────── */
  const pageHeader = el('div', { className: 'page-header' },
    el('h1', { className: 'page-title', textContent: 'Data Provenance & System Limitations' }),
    el('p', { className: 'page-subtitle', textContent: 'Source data verification, reporting regimes, and operational boundaries L-01 through L-12' })
  );
  root.appendChild(pageHeader);

  /* ── 1. Provenance Card (w-provenance) ───────────────────────────── */
  const provCard = createCard({
    id: 'w-provenance',
    className: 'col-12',
    title: 'Data Provenance & Source Integrity',
    subtitle: 'Cryptographic SHA-256 validation and CDC ingestion metadata',
    bodyNode: createSkeleton({ minHeight: '160px' }),
  });
  root.appendChild(provCard);

  /* ── 2. Data Quality Audit (w-quality) ───────────────────────────── */
  const qualityCard = createCard({
    id: 'w-quality',
    className: 'col-12',
    title: 'Data Quality & Ingestion Findings',
    subtitle: 'Audit log of missing values, anomalies, and imputation passes',
    bodyNode: createSkeleton({ minHeight: '120px' }),
  });
  root.appendChild(qualityCard);

  /* ── 3. Reporting Regime Note (w-regime) ─────────────────────────── */
  const regimeCard = createCard({
    id: 'w-regime',
    className: 'col-12',
    title: 'Surveillance Reporting Regime & Shifts (L-07)',
    subtitle: 'Context on institutional hospital reporting mandates',
    bodyNode: buildRegimeNote(),
  });
  root.appendChild(regimeCard);

  /* ── 4. Limitations L-01 to L-12 (w-limitations) ─────────────────── */
  const limitationsCard = createCard({
    id: 'w-limitations',
    className: 'col-12',
    title: 'System Limitations & Boundary Manifesto (L-01 – L-12)',
    subtitle: 'Mandatory clinical and operational boundaries per PRD §9',
    bodyNode: createSkeleton({ minHeight: '200px' }),
  });
  root.appendChild(limitationsCard);

  /* ── 5. Pipeline Reproduction Commands (w-reproduce) ─────────────── */
  const reproduceCard = createCard({
    id: 'w-reproduce',
    className: 'col-12',
    title: 'Pipeline Reproduction & Verification Commands',
    subtitle: 'Deterministic audit replication steps from TRD §12',
    bodyNode: buildReproduceCommands(),
  });
  root.appendChild(reproduceCard);

  /* ── 6. Attributions & Licensing (w-attribution) ─────────────────── */
  const attrCard = createCard({
    id: 'w-attribution',
    className: 'col-12',
    title: 'Attributions, Data License & Vendored Components',
    subtitle: 'Public open data and open-source licenses',
    bodyNode: buildAttributions(),
  });
  root.appendChild(attrCard);

  async function loadData() {
    const res = await api.getMeta();
    if (!res.ok) {
      const err = createErrorBlock({
        message: res.error.message,
        requestId: res.error.requestId,
        onRetry: loadData,
      });
      provCard.querySelector('.card-body').replaceChildren(err);
      qualityCard.querySelector('.card-body').replaceChildren(err.cloneNode(true));
      limitationsCard.querySelector('.card-body').replaceChildren(err.cloneNode(true));
      return;
    }

    const d = res.data;

    // 1. Provenance
    renderProvenance(d);

    // 2. Quality
    renderQuality(d);

    // 4. Limitations
    renderLimitations(d);
  }

  function renderProvenance(data) {
    const p = data.provenance || {};
    const dl = el('dl', { className: 'checklist' });

    const entries = [
      { term: 'Source Organization', desc: p.source_agency || 'CDC (Centers for Disease Control and Prevention)' },
      { term: 'Dataset Identifier', desc: p.dataset_id || 'NHSN Hospital Respiratory Admissions' },
      { term: 'Source URL', desc: p.source_url || 'https://data.cdc.gov/api/views/mpgq-jmmr/rows.csv' },
      { term: 'Data Retrieved At', desc: p.retrieved_at ? formatDate(p.retrieved_at) : 'Historical run' },
      { term: 'Data As Of Date', desc: formatDate(data.data_as_of) },
      { term: 'Target Series Kind', desc: p.target_kind || 'Weekly inpatient admissions' },
      { term: 'Raw File SHA-256', desc: p.raw_sha256 || 'Recorded in database audit manifest' },
    ];

    entries.forEach(({ term, desc }) => {
      const row = el('div', { className: 'checklist-item' });
      row.appendChild(el('dt', { className: 'stat-tile-label', textContent: `${term}: ` }));
      row.appendChild(el('dd', { className: 'text-strong', textContent: desc }));
      dl.appendChild(row);
    });

    provCard.querySelector('.card-body').replaceChildren(dl);
  }

  function renderQuality(data) {
    const issues = data.quality_issues || [];
    if (issues.length === 0) {
      qualityCard.querySelector('.card-body').replaceChildren(
        el('p', { className: 'text-muted', textContent: 'No data-quality issues were recorded.' })
      );
      return;
    }

    const formattedRows = issues.map((iss) => {
      let disease = 'National';
      const detLower = (iss.detail || '').toLowerCase();
      if (detLower.includes('rsv')) disease = 'RSV';
      else if (detLower.includes('covid')) disease = 'COVID-19';
      else if (detLower.includes('flu') || detLower.includes('influenza')) disease = 'Influenza';

      const checkNameFormatted = (iss.check_name || 'quality_check')
        .split('_')
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');

      return {
        check: checkNameFormatted,
        disease,
        severity: (iss.severity || 'info').toUpperCase(),
        detail: iss.detail || '—',
      };
    });

    const columns = [
      { key: 'check', label: 'Check Type' },
      { key: 'disease', label: 'Pathogen' },
      {
        key: 'severity',
        label: 'Severity',
        render: (sev) => {
          const s = String(sev || 'info').toLowerCase();
          const badgeClass =
            s === 'critical' || s === 'elevated'
              ? 'tier-badge-elevated'
              : s === 'warning' || s === 'watch'
              ? 'tier-badge-watch'
              : 'tier-badge-normal';
          return el('span', { className: `tier-badge ${badgeClass}`, textContent: String(sev) });
        },
      },
      { key: 'detail', label: 'Finding / Description' },
    ];

    const tableNode = createDataTable({
      caption: 'Data ingestion quality validation findings',
      columns,
      rows: formattedRows,
    });

    qualityCard.querySelector('.card-body').replaceChildren(tableNode);
  }

  function buildRegimeNote() {
    const div = el('div');
    const p1 = el('p', {
      className: 'explain-text',
      textContent: 'Surveillance reporting rules changed during the observation period. Under COVID-19 and post-PHE emergency rules, federal hospital reporting mandates transitioned from mandatory daily submissions to voluntary or weekly CDC NHSN reporting regimes. Consequently, sudden baseline shifts may reflect changes in surveillance reporting policy rather than clinical epidemiological incidence.',
    });
    div.appendChild(p1);
    return div;
  }

  function renderLimitations(data) {
    const list = data.limitations || [];
    const div = el('div');

    if (list.length === 0) {
      div.appendChild(el('p', { className: 'text-muted', textContent: 'No explicit limitations configured.' }));
    } else {
      const ul = el('ul', { className: 'checklist' });
      list.forEach((item) => {
        const li = el('li', { className: 'checklist-item' });
        li.appendChild(el('span', { className: 'bound-dot' }));
        li.appendChild(el('span', { textContent: typeof item === 'string' ? item : `${item.id}: ${item.text}` }));
        ul.appendChild(li);
      });
      div.appendChild(ul);
    }

    limitationsCard.querySelector('.card-body').replaceChildren(div);
  }

  function buildReproduceCommands() {
    const div = el('div');
    const pre = el('pre', {
      className: 'card',
      style: undefined,
    });
    const code = el('code', {
      textContent: `# 1. Download official CDC NHSN dataset
python -m carecast.pipeline ingest

# 2. Re-run complete walk-forward training & evaluation
python -m carecast.pipeline train

# 3. Verify SQLite audit constraints and models
pytest tests/ -q

# 4. Start local read-only production API
uvicorn carecast.api.main:app --port 8000`,
    });
    pre.appendChild(code);
    div.appendChild(pre);
    return div;
  }

  function buildAttributions() {
    const div = el('div');
    const ul = el('ul', { className: 'checklist' });

    const atts = [
      'Data Source: CDC National Healthcare Safety Network (NHSN) Public Data. Public domain under CDC open data guidelines.',
      'Chart Engine: Chart.js v4.4.7 (vendored in web/vendor/chart.umd.js). Licensed under the MIT License.',
      'Icons: Self-authored SVG outline icon set for CareCast (zero third-party icon libraries or external CDNs).',
      'Disclaimer: CareCast is an undergraduate engineering capstone prototype. Designed for operational planning decision-support; not clinically validated for patient triage.',
    ];

    atts.forEach((att) => {
      const li = el('li', { className: 'checklist-item' });
      li.appendChild(el('span', { className: 'bound-dot' }));
      li.appendChild(el('span', { textContent: att }));
      ul.appendChild(li);
    });

    div.appendChild(ul);
    return div;
  }

  loadData();

  return () => {};
}
