/**
 * S4 — Explainability Screen
 * UI_UX_DESIGN §5 & APP_FLOW §4
 * Horizon tabs, diverging contribution bars, permutation importance, and non-causal plain-language text.
 */

import { api } from '../api.js';
import { store } from '../store.js';
import {
  el,
  createCard,
  createHorizonTabs,
  createAlertBanner,
  createErrorBlock,
  createSkeleton,
} from '../components.js';
import { formatDecimal } from '../format.js';

export function renderExplain(container) {
  while (container.firstChild) {
    container.removeChild(container.firstChild);
  }

  const root = el('div', { className: 'view-explain' });
  container.appendChild(root);

  let selectedH = store.state.horizon || 1;
  const disease = store.state.disease;
  const jurisdiction = store.state.jurisdiction;

  /* ── Page Header (A11Y-05) ───────────────────────────────────────── */
  const pageHeader = el('div', { className: 'page-header' },
    el('h1', { className: 'page-title', textContent: 'Forecast Explainability' }),
    el('p', { className: 'page-subtitle', textContent: 'Feature contribution breakdown and permutation importance attribution' })
  );
  root.appendChild(pageHeader);

  /* ── 1. Horizon Tabs Card (w-horizon-tabs) ──────────────────────── */
  const tabsCard = el('div', { className: 'card', id: 'w-horizon-tabs' });
  const tabsWrapper = el('div', { className: 'card-header' });
  tabsWrapper.appendChild(el('h2', { className: 'card-title', textContent: 'Select Forecast Horizon' }));
  const tabs = createHorizonTabs({
    selectedH,
    onSelectH: (h) => {
      selectedH = h;
      store.setHorizon(h);
      loadExplainData();
    },
  });
  tabsWrapper.appendChild(tabs);
  tabsCard.appendChild(tabsWrapper);
  root.appendChild(tabsCard);

  /* ── 2. Plain Language Explanation Card (w-explain-text) ────────── */
  const textCard = createCard({
    id: 'w-explain-text',
    className: 'col-12',
    title: 'Model Interpretation & Non-Causal Summary',
    subtitle: 'Plain-language review of top predictive signals',
    bodyNode: createSkeleton({ minHeight: '120px' }),
  });
  root.appendChild(textCard);

  /* ── 3. Diverging Contribution Bars (w-contrib) ─────────────────── */
  const contribCard = createCard({
    id: 'w-contrib',
    className: 'col-12',
    title: 'Feature Contributions to Point Forecast',
    subtitle: 'Additive shifts from the model baseline value to current prediction',
    bodyNode: createSkeleton({ minHeight: '220px' }),
  });
  root.appendChild(contribCard);

  /* ── 4. Permutation Importance Bars (w-importance) ──────────────── */
  const importanceCard = createCard({
    id: 'w-importance',
    className: 'col-12',
    title: 'Permutation Feature Importance',
    subtitle: 'Global loss increase when each feature is randomly permuted',
    bodyNode: createSkeleton({ minHeight: '220px' }),
  });
  root.appendChild(importanceCard);

  async function loadExplainData() {
    const res = await api.getExplain({ disease, jurisdiction, horizon: selectedH });
    if (!res.ok) {
      const errBlock = createErrorBlock({
        message: res.error.message,
        requestId: res.error.requestId,
        onRetry: loadExplainData,
      });
      textCard.querySelector('.card-body').replaceChildren(errBlock);
      contribCard.querySelector('.card-body').replaceChildren(errBlock.cloneNode(true));
      importanceCard.querySelector('.card-body').replaceChildren(errBlock.cloneNode(true));
      return;
    }

    const d = res.data;

    renderExplainText(d);
    renderContributions(d);
    renderImportance(d);
  }

  function renderExplainText(data) {
    const body = el('div');

    const noticeBanner = createAlertBanner({
      type: 'info',
      text: 'Associations, not causes: feature weights indicate statistical correlation in historical data, not clinical mechanisms.',
    });
    body.appendChild(noticeBanner);

    const modelBadge = el('div', { className: 'explain-tags' });
    modelBadge.appendChild(el('span', { className: 'tag-outline', textContent: `Model: ${data.model_name}` }));
    modelBadge.appendChild(el('span', {
      className: 'tag-filled',
      textContent: `Horizon ${data.horizon_weeks} Wk`,
    }));
    body.appendChild(modelBadge);

    const textP = el('p', { className: 'explain-text', textContent: data.text });
    body.appendChild(textP);

    if (data.note) {
      body.appendChild(el('p', { className: 'explain-note', textContent: data.note }));
    }

    textCard.querySelector('.card-body').replaceChildren(body);
  }

  function renderContributions(data) {
    const body = el('div');

    if (!data.contributions || data.contributions.length === 0) {
      const treeNotice = createAlertBanner({
        type: 'warning',
        text: 'Contributions are not available for the selected tree model; showing permutation importance only.',
      });
      body.appendChild(treeNotice);
      contribCard.querySelector('.card-body').replaceChildren(body);
      return;
    }

    if (data.base_value !== undefined && data.prediction !== undefined) {
      const summaryRow = el('div', { className: 'topbar-left' });
      summaryRow.appendChild(el('span', { className: 'text-muted', textContent: `Baseline value: ${formatDecimal(data.base_value)}` }));
      summaryRow.appendChild(el('span', { className: 'text-muted', textContent: `→ Forecast: ${formatDecimal(data.prediction)}` }));
      body.appendChild(summaryRow);
    }

    const contribList = el('div', { className: 'contrib-list' });
    const sorted = [...data.contributions].sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
    const maxAbs = Math.max(...sorted.map((item) => Math.abs(Number(item.value) || 0)), 1);

    sorted.forEach((item) => {
      const row = el('div', { className: 'contrib-row' });
      row.appendChild(el('span', { className: 'contrib-name', textContent: item.label || item.feature }));

      const barContainer = el('div', { className: 'contrib-bar-container' });
      barContainer.appendChild(el('div', { className: 'contrib-center-line' }));

      const svgBar = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svgBar.setAttribute('width', '100%');
      svgBar.setAttribute('height', '18');
      svgBar.setAttribute('viewBox', '0 0 100 18');
      svgBar.setAttribute('preserveAspectRatio', 'none');

      const mid = 50;
      const val = Number(item.value) || 0;
      const w = (Math.abs(val) / maxAbs) * 45;
      const x = val >= 0 ? mid : mid - w;
      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('x', String(x));
      rect.setAttribute('y', '2');
      rect.setAttribute('width', String(Math.max(1, w)));
      rect.setAttribute('height', '14');
      rect.setAttribute('rx', '2');
      rect.setAttribute('fill', val >= 0 ? '#1F7A74' : '#B45309');
      svgBar.appendChild(rect);

      barContainer.appendChild(svgBar);
      row.appendChild(barContainer);

      const valText = val >= 0 ? `+${formatDecimal(val)}` : formatDecimal(val);
      row.appendChild(el('span', { className: 'contrib-val', textContent: valText }));
      contribList.appendChild(row);
    });

    body.appendChild(contribList);
    contribCard.querySelector('.card-body').replaceChildren(body);
  }

  function renderImportance(data) {
    const body = el('div');
    const impList = data.permutation_importance || [];

    if (impList.length === 0) {
      body.appendChild(el('p', { className: 'text-muted', textContent: 'No permutation importance metrics available.' }));
      importanceCard.querySelector('.card-body').replaceChildren(body);
      return;
    }

    const sorted = [...impList].sort((a, b) => (Number(b.value) || 0) - (Number(a.value) || 0));
    const maxVal = Math.max(...sorted.map((item) => Number(item.value) || 0), 0.001);

    const container = el('div', { className: 'contrib-list' });
    sorted.forEach((item) => {
      const val = Number(item.value) || 0;
      const row = el('div', { className: 'contrib-row' });
      row.appendChild(el('span', { className: 'contrib-name', textContent: item.label || item.feature }));

      const barContainer = el('div', { className: 'contrib-bar-container' });

      const svgBar = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svgBar.setAttribute('width', '100%');
      svgBar.setAttribute('height', '18');
      svgBar.setAttribute('viewBox', '0 0 100 18');
      svgBar.setAttribute('preserveAspectRatio', 'none');

      const w = Math.max(1, (val / maxVal) * 90);
      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('x', '0');
      rect.setAttribute('y', '2');
      rect.setAttribute('width', String(w));
      rect.setAttribute('height', '14');
      rect.setAttribute('rx', '2');
      rect.setAttribute('fill', '#1F7A74');
      svgBar.appendChild(rect);

      barContainer.appendChild(svgBar);
      row.appendChild(barContainer);

      row.appendChild(el('span', { className: 'contrib-val', textContent: formatDecimal(val) }));
      container.appendChild(row);
    });

    body.appendChild(container);
    importanceCard.querySelector('.card-body').replaceChildren(body);
  }

  loadExplainData();

  return () => {};
}
