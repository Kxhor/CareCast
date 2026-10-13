/**
 * S3 — Model Performance Screen
 * UI_UX_DESIGN §5 & APP_FLOW §4
 * Split timeline, verdict cards per horizon, metrics comparison table, and full backtest chart.
 */

import { api } from '../api.js';
import { store } from '../store.js';
import {
  el,
  createCard,
  createDataTable,
  createHorizonTabs,
  createErrorBlock,
  createSkeleton,
} from '../components.js';
import { renderAccessibleChart } from '../charts.js';
import { formatDate, formatInt, formatDecimal, formatPercent } from '../format.js';

export function renderPerformance(container) {
  while (container.firstChild) {
    container.removeChild(container.firstChild);
  }

  const root = el('div', { className: 'view-performance' });
  container.appendChild(root);

  let activeChartCleanup = null;
  let selectedH = store.state.horizon || 1;
  let activeSplit = 'test';

  const disease = store.state.disease;
  const jurisdiction = store.state.jurisdiction;

  /* ── Page Header (A11Y-05) ───────────────────────────────────────── */
  const pageHeader = el('div', { className: 'page-header' },
    el('h1', { className: 'page-title', textContent: 'Model Performance & Evaluation' }),
    el('p', { className: 'page-subtitle', textContent: 'Strict walk-forward evaluation protocol and baseline comparison benchmarks' })
  );
  root.appendChild(pageHeader);

  /* ── 1. Split Timeline Bar (w-splits) ───────────────────────────── */
  const splitsCard = createCard({
    id: 'w-splits',
    className: 'col-12',
    title: 'Evaluation Protocol & Split Timeline',
    subtitle: 'Strict walk-forward temporal splits (no future data leakage)',
    bodyNode: createSkeleton({ minHeight: '80px' }),
  });
  root.appendChild(splitsCard);

  /* ── 2. Baseline Verdict Cards (w-verdicts) ─────────────────────── */
  const verdictsCard = createCard({
    id: 'w-verdicts',
    className: 'col-12',
    title: 'Baseline Comparison & Test Interval Coverage',
    subtitle: 'Evaluated on held-out test block against the naive persistence baseline',
    bodyNode: createSkeleton({ minHeight: '160px' }),
  });
  root.appendChild(verdictsCard);

  /* ── 3. Metrics Table (w-metrics) ───────────────────────────────── */
  const metricsCard = createCard({
    id: 'w-metrics',
    className: 'col-12',
    title: 'Model Evaluation Metrics',
    subtitle: 'MAE and RMSE per horizon across candidate models',
    bodyNode: createSkeleton({ minHeight: '180px' }),
  });
  root.appendChild(metricsCard);

  /* ── 4. Full Backtest Chart (w-backtest-full) ───────────────────── */
  const backtestCard = createCard({
    id: 'w-backtest-full',
    className: 'col-12',
    title: 'Backtest Trajectory: Actual vs Selected vs Persistence',
    subtitle: 'Out-of-sample predictions across historical test weeks',
    bodyNode: createSkeleton({ minHeight: '300px' }),
  });
  root.appendChild(backtestCard);

  let cachedEvaluationData = null;

  async function loadData() {
    const res = await api.getEvaluation({ disease, jurisdiction, horizon: selectedH });
    if (!res.ok) {
      const errBlock = createErrorBlock({
        message: res.error.message,
        requestId: res.error.requestId,
        onRetry: loadData,
      });
      splitsCard.querySelector('.card-body').replaceChildren(errBlock);
      verdictsCard.querySelector('.card-body').replaceChildren(errBlock.cloneNode(true));
      metricsCard.querySelector('.card-body').replaceChildren(errBlock.cloneNode(true));
      backtestCard.querySelector('.card-body').replaceChildren(errBlock.cloneNode(true));
      return;
    }

    cachedEvaluationData = res.data;
    renderSplits(cachedEvaluationData);
    renderVerdicts(cachedEvaluationData);
    renderMetricsTable(cachedEvaluationData);
    renderBacktestChart(cachedEvaluationData);
  }

  function renderSplits(data) {
    const run = data.run || {};
    const body = el('div');

    const timelineBar = el('div', { className: 'timeline-bar', role: 'img', 'aria-label': 'Timeline of train, validation, and test splits' });
    timelineBar.appendChild(el('div', { className: 'timeline-segment segment-train', textContent: 'Train (60%)' }));
    timelineBar.appendChild(el('div', { className: 'timeline-segment segment-val', textContent: 'Val (20%)' }));
    timelineBar.appendChild(el('div', { className: 'timeline-segment segment-test', textContent: 'Test (20%)' }));
    body.appendChild(timelineBar);

    const legend = el('div', { className: 'timeline-legend' });
    const trainText = (run.train && run.train.length > 0)
      ? `${formatDate(run.train[0])} – ${formatDate(run.train[run.train.length - 1])}`
      : 'Historical';
    const valText = (run.validation && run.validation.length > 0)
      ? `${formatDate(run.validation[0])} – ${formatDate(run.validation[run.validation.length - 1])}`
      : 'Tuning';
    const testText = (run.test && run.test.length > 0)
      ? `${formatDate(run.test[0])} – ${formatDate(run.test[run.test.length - 1])}`
      : 'Held-out';

    const item1 = el('div', { className: 'timeline-legend-item' },
      el('span', { className: 'bound-dot' }),
      el('span', { textContent: `Train: ${trainText}` })
    );
    const item2 = el('div', { className: 'timeline-legend-item' },
      el('span', { className: 'bound-dot' }),
      el('span', { textContent: `Validation: ${valText}` })
    );
    const item3 = el('div', { className: 'timeline-legend-item' },
      el('span', { className: 'bound-dot' }),
      el('span', { textContent: `Test: ${testText}` })
    );

    legend.appendChild(item1);
    legend.appendChild(item2);
    legend.appendChild(item3);
    body.appendChild(legend);

    splitsCard.querySelector('.card-body').replaceChildren(body);
  }

  function renderVerdicts(data) {
    const verdictsGrid = el('div', { className: 'grid-container' });
    const selectedMap = new Map((data.selected || []).map((s) => [s.horizon_weeks, s]));

    (data.verdicts || []).forEach((v) => {
      const cardCol = el('div', { className: 'col-3 card' });
      const hTitle = el('h3', { className: 'card-title', textContent: `Horizon ${v.horizon_weeks} (${v.horizon_weeks} Wk)` });
      cardCol.appendChild(hTitle);

      const selInfo = selectedMap.get(v.horizon_weeks);
      const modelName = selInfo ? selInfo.model_name : 'Selected model';
      cardCol.appendChild(el('div', { className: 'card-subtitle', textContent: `Selected model: ${modelName}` }));

      const verdictTag = el('div', {
        className: v.beats_persistence ? 'tag-filled' : 'tag-filled tag-warn',
      });
      verdictTag.appendChild(document.createTextNode(`Beats persistence: ${v.beats_persistence ? 'Yes' : 'No'}`));

      const verdictText = v.beats_persistence
        ? "On the held-out test weeks, the selected model's MAE is lower than the persistence baseline's."
        : "On the held-out test weeks, the selected model did not improve on the persistence baseline.";

      const verdictDesc = el('p', {
        className: 'explain-text',
        textContent: verdictText,
      });

      const covVal = (selInfo && selInfo.test_interval_coverage !== null && selInfo.test_interval_coverage !== undefined)
        ? formatPercent(selInfo.test_interval_coverage * 100, false)
        : '—';
      const covText = el('div', {
        className: 'text-muted',
        textContent: `Test 80% interval empirical coverage: ${covVal}`,
      });

      cardCol.appendChild(verdictTag);
      cardCol.appendChild(verdictDesc);
      cardCol.appendChild(covText);
      verdictsGrid.appendChild(cardCol);
    });

    verdictsCard.querySelector('.card-body').replaceChildren(verdictsGrid);
  }

  function renderMetricsTable(data) {
    const wrapper = el('div');

    const toggleRow = el('div', { className: 'topbar-left' });
    toggleRow.appendChild(el('span', { className: 'form-label', textContent: 'Evaluation Split: ' }));

    const btnVal = el('button', {
      type: 'button',
      className: activeSplit === 'validation' ? 'btn-primary' : 'btn-secondary',
      textContent: 'Validation Split',
      onclick: () => {
        activeSplit = 'validation';
        renderMetricsTable(data);
      },
    });
    const btnTest = el('button', {
      type: 'button',
      className: activeSplit === 'test' ? 'btn-primary' : 'btn-secondary',
      textContent: 'Held-out Test Split',
      onclick: () => {
        activeSplit = 'test';
        renderMetricsTable(data);
      },
    });
    toggleRow.appendChild(btnVal);
    toggleRow.appendChild(btnTest);
    wrapper.appendChild(toggleRow);

    const splitMetrics = (data.metrics || []).filter((m) => m.split === activeSplit);
    const models = Array.from(new Set(splitMetrics.map((m) => m.model_name)));
    const selectedModels = new Set((data.selected || []).map((s) => s.model_name));

    const rows = models.map((mod) => {
      const row = {
        model: mod,
        isSelected: selectedModels.has(mod),
      };
      [1, 2, 3, 4].forEach((h) => {
        const entry = splitMetrics.find((m) => m.model_name === mod && m.horizon_weeks === h);
        row[`h${h}_mae`] = entry ? formatDecimal(entry.mae) : '—';
        row[`h${h}_rmse`] = entry ? formatDecimal(entry.rmse) : '—';
      });
      return row;
    });

    const columns = [
      {
        key: 'model',
        label: 'Model Name',
        render: (val, row) => {
          const container = el('div', { className: 'topbar-left' });
          container.appendChild(el('span', { textContent: val }));
          if (row.isSelected) {
            container.appendChild(el('span', { className: 'trend-badge', textContent: 'Selected' }));
          }
          return container;
        },
      },
      { key: 'h1_mae', label: 'H1 MAE' },
      { key: 'h1_rmse', label: 'H1 RMSE' },
      { key: 'h2_mae', label: 'H2 MAE' },
      { key: 'h2_rmse', label: 'H2 RMSE' },
      { key: 'h3_mae', label: 'H3 MAE' },
      { key: 'h3_rmse', label: 'H3 RMSE' },
      { key: 'h4_mae', label: 'H4 MAE' },
      { key: 'h4_rmse', label: 'H4 RMSE' },
    ];

    const tableNode = createDataTable({
      caption: `Model metrics comparison on ${activeSplit} split`,
      columns,
      rows,
    });
    wrapper.appendChild(tableNode);

    metricsCard.querySelector('.card-body').replaceChildren(wrapper);
  }

  function renderBacktestChart(data) {
    if (activeChartCleanup) {
      activeChartCleanup();
      activeChartCleanup = null;
    }

    const wrapper = el('div');

    const tabs = createHorizonTabs({
      selectedH,
      onSelectH: (h) => {
        selectedH = h;
        store.setHorizon(h);
        loadData();
      },
    });
    wrapper.appendChild(tabs);

    const pts = (data.backtest && data.backtest.points) ? data.backtest.points : [];
    const labels = pts.map((p) => formatDate(p.target_week_end_date));
    const actualData = pts.map((p) => p.actual);
    const selectedData = pts.map((p) => p.predicted_selected);
    const persistenceData = pts.map((p) => p.predicted_persistence);

    const datasets = [
      {
        label: 'Actual Admissions',
        data: actualData,
        borderColor: '#1F7A74',
        borderWidth: 2.5,
        backgroundColor: 'transparent',
        pointRadius: 3,
      },
      {
        label: 'Selected Model',
        data: selectedData,
        borderColor: '#3F9690',
        borderWidth: 2,
        borderDash: [5, 5],
        backgroundColor: 'transparent',
        pointRadius: 3,
        pointStyle: 'rect',
      },
      {
        label: 'Persistence Baseline',
        data: persistenceData,
        borderColor: '#B45309',
        borderWidth: 2,
        borderDash: [2, 2],
        backgroundColor: 'transparent',
        pointRadius: 2,
      },
    ];

    const chartObj = renderAccessibleChart({
      title: `Backtest series for Horizon ${selectedH} on held-out test weeks`,
      ariaLabel: `Line chart comparing actual admissions, selected model, and persistence baseline for horizon ${selectedH}`,
      labels,
      datasets,
      tableColumns: [
        { key: 'target_week_end_date', label: 'Week Ending', render: (val) => formatDate(val) },
        { key: 'actual', label: 'Actual', render: (val) => formatInt(val) },
        { key: 'predicted_selected', label: 'Selected Model', render: (val) => formatInt(val) },
        { key: 'predicted_persistence', label: 'Persistence Baseline', render: (val) => formatInt(val) },
      ],
      tableRows: pts,
    });

    activeChartCleanup = chartObj.destroy;
    wrapper.appendChild(chartObj.figure);

    backtestCard.querySelector('.card-body').replaceChildren(wrapper);
  }

  loadData();

  return () => {
    if (activeChartCleanup) activeChartCleanup();
  };
}
