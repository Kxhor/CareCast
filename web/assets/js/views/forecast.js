/**
 * S2 — Forecast Screen
 * UI_UX_DESIGN §5 & APP_FLOW §4
 * Controls, large forecast chart with interval band & threshold, table, and review actions.
 */

import { api } from '../api.js';
import { store } from '../store.js';
import {
  el,
  createCard,
  createTierBadge,
  createDataTable,
  createHorizonTabs,
  createAlertBanner,
  createErrorBlock,
  createSkeleton,
} from '../components.js';
import { renderAccessibleChart } from '../charts.js';
import { formatDate, formatInt, formatDiseaseName } from '../format.js';

export function renderForecast(container) {
  while (container.firstChild) {
    container.removeChild(container.firstChild);
  }

  const root = el('div', { className: 'view-forecast' });
  container.appendChild(root);

  let activeChartCleanup = null;
  let selectedH = store.state.horizon || 1;

  const disease = store.state.disease;
  const jurisdiction = store.state.jurisdiction;
  let thresholdOverride = store.state.thresholdOverride;

  /* ── Page Header (A11Y-05) ───────────────────────────────────────── */
  const pageHeader = el('div', { className: 'page-header' },
    el('h1', { className: 'page-title', textContent: 'Forecast Trajectory & Threshold Alerts' }),
    el('p', { className: 'page-subtitle', textContent: 'Multi-horizon admissions projections with 95% prediction intervals and early warning tiers' })
  );
  root.appendChild(pageHeader);

  /* ── 1. Controls Row (w-controls) ───────────────────────────────── */
  const controlsCard = el('div', { className: 'card', id: 'w-controls' });
  const controlsGrid = el('div', { className: 'grid-container' });

  // Threshold override input
  const threshGroup = el('div', { className: 'col-6 form-group' });
  threshGroup.appendChild(el('label', { className: 'form-label', textContent: 'Planning Threshold (admissions/week)' }));
  const threshInputRow = el('div', { className: 'topbar-left' });
  const threshInput = el('input', {
    type: 'number',
    className: 'form-input',
    min: '0',
    max: '1000000',
    step: '100',
    value: thresholdOverride !== null ? String(thresholdOverride) : '',
    placeholder: 'Default (historical 80th %ile)',
  });
  const resetBtn = el('button', {
    type: 'button',
    className: 'btn-secondary',
    textContent: 'Reset to default',
    onclick: () => {
      store.setThresholdOverride(null);
      threshInput.value = '';
      reloadAll();
    },
  });
  threshInput.addEventListener('change', () => {
    const val = threshInput.value ? Number(threshInput.value) : null;
    store.setThresholdOverride(val);
    reloadAll();
  });
  threshInputRow.appendChild(threshInput);
  threshInputRow.appendChild(resetBtn);
  threshGroup.appendChild(threshInputRow);
  controlsGrid.appendChild(threshGroup);

  // Horizon tabs
  const tabsGroup = el('div', { className: 'col-6 form-group' });
  tabsGroup.appendChild(el('label', { className: 'form-label', textContent: 'Highlight Horizon' }));
  const tabs = createHorizonTabs({
    selectedH,
    onSelectH: (h) => {
      selectedH = h;
      store.setHorizon(h);
      updateAlertSection();
    },
  });
  tabsGroup.appendChild(tabs);
  controlsGrid.appendChild(tabsGroup);

  controlsCard.appendChild(controlsGrid);
  root.appendChild(controlsCard);

  /* ── 2. Large Forecast Chart (w-forecast-chart) ─────────────────── */
  const chartCard = createCard({
    id: 'w-forecast-chart',
    className: 'col-12',
    title: 'Admissions History & 4-Week Forecast with Uncertainty',
    subtitle: 'Recent 16 weeks actual admissions + 1–4 week forecast with 80% prediction interval and threshold',
    bodyNode: createSkeleton({ minHeight: '320px' }),
  });
  root.appendChild(chartCard);

  /* ── 3. Forecast Table (w-forecast-table) ────────────────────────── */
  const tableCard = createCard({
    id: 'w-forecast-table',
    className: 'col-12',
    title: 'Forecast Table & Alert Tiers',
    subtitle: 'Deterministic point predictions and interval bounds',
    bodyNode: createSkeleton({ minHeight: '180px' }),
  });
  root.appendChild(tableCard);

  /* ── 4. Operational Alert Card & Checklist (w-alert) ────────────── */
  const alertCard = createCard({
    id: 'w-alert',
    className: 'col-12',
    title: 'Operational Planning Signal & Action Checklist',
    subtitle: 'Review checklist corresponding to current alert tier',
    bodyNode: createSkeleton({ minHeight: '140px' }),
  });
  root.appendChild(alertCard);

  let cachedForecastData = null;

  async function loadData() {
    if (activeChartCleanup) {
      activeChartCleanup();
      activeChartCleanup = null;
    }

    const [obsRes, fcRes] = await Promise.all([
      api.getObservations({ disease, jurisdiction }),
      api.getForecast({ disease, jurisdiction, threshold: store.state.thresholdOverride }),
    ]);

    if (!obsRes.ok || !fcRes.ok) {
      const err = obsRes.ok ? fcRes.error : obsRes.error;
      const errBlock = createErrorBlock({
        message: err.message,
        requestId: err.requestId,
        onRetry: loadData,
      });
      chartCard.querySelector('.card-body').replaceChildren(errBlock);
      tableCard.querySelector('.card-body').replaceChildren(errBlock.cloneNode(true));
      alertCard.querySelector('.card-body').replaceChildren(errBlock.cloneNode(true));
      return;
    }

    const obsPoints = (obsRes.data.points || []).slice(-16);
    cachedForecastData = fcRes.data;

    renderChart(obsPoints, cachedForecastData);
    renderTable(cachedForecastData);
    updateAlertSection();
  }

  function renderChart(obsPoints, fcData) {
    const labels = [];
    const actualData = [];
    const forecastData = [];
    const lowerData = [];
    const upperData = [];
    const threshData = [];

    const thresholdVal = fcData.threshold ? fcData.threshold.value : null;

    obsPoints.forEach((p) => {
      labels.push(formatDate(p.week_end_date));
      actualData.push(p.value);
      forecastData.push(null);
      lowerData.push(null);
      upperData.push(null);
      threshData.push(thresholdVal);
    });

    if (obsPoints.length > 0 && fcData.horizons.length > 0) {
      const lastObs = obsPoints[obsPoints.length - 1];
      forecastData[forecastData.length - 1] = lastObs.value;
      lowerData[lowerData.length - 1] = lastObs.value;
      upperData[upperData.length - 1] = lastObs.value;
    }

    fcData.horizons.forEach((h) => {
      labels.push(formatDate(h.target_week_end_date));
      actualData.push(null);
      forecastData.push(h.point);
      lowerData.push(h.lower);
      upperData.push(h.upper);
      threshData.push(thresholdVal);
    });

    const datasets = [
      {
        label: 'Actual Admissions',
        data: actualData,
        borderColor: '#1F7A74',
        borderWidth: 2.5,
        backgroundColor: 'transparent',
        pointRadius: 4,
        pointBackgroundColor: '#1F7A74',
      },
      {
        label: 'Forecast',
        data: forecastData,
        borderColor: '#B45309',
        borderWidth: 2.5,
        borderDash: [6, 4],
        backgroundColor: 'transparent',
        pointRadius: 4,
        pointStyle: 'rectRot',
        pointBackgroundColor: '#B45309',
      },
      {
        label: '80% Interval Upper',
        data: upperData,
        borderColor: 'transparent',
        backgroundColor: 'rgba(31, 122, 116, 0.18)',
        fill: '+1',
        pointRadius: 0,
      },
      {
        label: '80% Interval Lower',
        data: lowerData,
        borderColor: 'transparent',
        backgroundColor: 'transparent',
        pointRadius: 0,
      },
    ];

    if (thresholdVal !== null) {
      datasets.push({
        label: `Threshold (${formatInt(thresholdVal)})`,
        data: threshData,
        borderColor: '#B3261E',
        borderWidth: 2,
        borderDash: [3, 3],
        backgroundColor: 'transparent',
        pointRadius: 0,
      });
    }

    const tableRows = fcData.horizons.map((h) => ({
      week: formatDate(h.target_week_end_date),
      horizon: `${h.horizon_weeks} Wk`,
      forecast: formatInt(h.point),
      lower: formatInt(h.lower),
      upper: formatInt(h.upper),
      threshold: formatInt(thresholdVal),
      tier: h.tier,
    }));

    const chartObj = renderAccessibleChart({
      title: 'Historical trajectory and 4-week prediction cone',
      ariaLabel: 'Historical admissions and 4-week forecast cone with threshold line',
      labels,
      datasets,
      tableColumns: [
        { key: 'horizon', label: 'Horizon' },
        { key: 'week', label: 'Target Week Ending' },
        { key: 'forecast', label: 'Forecast' },
        { key: 'lower', label: 'Lower Bound' },
        { key: 'upper', label: 'Upper Bound' },
        { key: 'threshold', label: 'Threshold' },
        { key: 'tier', label: 'Tier' },
      ],
      tableRows,
      containerClass: 'chart-canvas-wrapper',
    });

    activeChartCleanup = chartObj.destroy;
    chartCard.querySelector('.card-body').replaceChildren(chartObj.figure);
  }

  function renderTable(fcData) {
    const thresholdVal = fcData.threshold ? fcData.threshold.value : null;

    const tableColumns = [
      { key: 'horizon_weeks', label: 'Horizon', render: (val) => `${val} Week${val > 1 ? 's' : ''}` },
      { key: 'target_week_end_date', label: 'Target Week Ending', render: (val) => formatDate(val) },
      { key: 'point', label: 'Forecast', render: (val) => formatInt(val) },
      { key: 'lower', label: 'Lower (80%)', render: (val) => formatInt(val) },
      { key: 'upper', label: 'Upper (80%)', render: (val) => formatInt(val) },
      { key: 'threshold', label: 'Threshold', render: () => formatInt(thresholdVal) },
      { key: 'tier', label: 'Tier', render: (val) => createTierBadge(val) },
    ];

    const rowActions = [
      {
        label: 'Explain',
        iconId: 'icon-action-explain',
        ariaLabel: (row) => `Explain horizon ${row.horizon_weeks}`,
        onClick: (row) => {
          window.location.hash = `#/explain?disease=${disease}&h=${row.horizon_weeks}`;
        },
      },
      {
        label: 'Scenario',
        iconId: 'icon-action-scenario',
        ariaLabel: (row) => `Scenario planner with horizon ${row.horizon_weeks}`,
        onClick: () => {
          window.location.hash = `#/scenario?disease=${disease}`;
        },
      },
    ];

    const tableNode = createDataTable({
      caption: `4-Week Forecast Schedule with Prediction Intervals`,
      columns: tableColumns,
      rows: fcData.horizons,
      rowActions,
    });

    tableCard.querySelector('.card-body').replaceChildren(tableNode);
  }

  function updateAlertSection() {
    if (!cachedForecastData) return;

    const horizonData = cachedForecastData.horizons.find((h) => h.horizon_weeks === selectedH) || cachedForecastData.horizons[0];
    if (!horizonData) return;

    const alertBox = el('div');
    const tier = horizonData.tier;

    const alertType = tier === 'elevated' ? 'error' : tier === 'watch' ? 'warning' : 'info';
    alertBox.appendChild(
      createAlertBanner({
        type: alertType,
        text: `Planning signal for Week ${selectedH} (${formatDate(horizonData.target_week_end_date)}): Tier ${tier.toUpperCase()}. Planning signal — not a bed-shortage prediction.`,
      })
    );

    const checklistTitle = el('h3', {
      className: 'card-title',
      textContent: `Operational Checklist for ${tier.toUpperCase()} Tier:`,
    });
    alertBox.appendChild(checklistTitle);

    const checklist = el('ul', { className: 'checklist' });
    const actions = (cachedForecastData.actions && cachedForecastData.actions.items)
      ? cachedForecastData.actions.items
      : [
          'Monitor incoming respiratory admissions daily.',
          'Verify bed and staffing capacity assumptions.',
          'Review regional surveillance data.',
        ];

    actions.forEach((act) => {
      const item = el('li', { className: 'checklist-item' });
      const bullet = el('span', { className: 'bound-dot' });
      item.appendChild(bullet);
      item.appendChild(el('span', { textContent: act }));
      checklist.appendChild(item);
    });

    alertBox.appendChild(checklist);
    alertCard.querySelector('.card-body').replaceChildren(alertBox);
  }

  function reloadAll() {
    loadData();
  }

  loadData();

  return () => {
    if (activeChartCleanup) activeChartCleanup();
  };
}
