/**
 * S1 — Overview Screen (CareCast Cockpit)
 * UI_UX_DESIGN §5 & APP_FLOW §4
 * Layout at >=1280px: 9/3 · 4/4/4 · 12 · 4/4/4
 */

import { api } from '../api.js';
import { store } from '../store.js';
import {
  el,
  createCard,
  createHeroBanner,
  createKpiChip,
  createWatchlistRow,
  createTierBadge,
  createRingGauge,
  createDataTable,
  createTile,
  createErrorBlock,
  createSkeleton,
} from '../components.js';
import { renderAccessibleChart, renderTrendSparkline } from '../charts.js';
import { formatDate, formatInt, formatPercent, formatDiseaseName } from '../format.js';

export function renderOverview(container) {
  while (container.firstChild) {
    container.removeChild(container.firstChild);
  }

  const root = el('div', { className: 'grid-container view-overview' });
  container.appendChild(root);

  const chartCleanups = [];

  const disease = store.state.disease;
  const jurisdiction = store.state.jurisdiction;
  const threshold = store.state.thresholdOverride;

  /* ── ROW 1: 9 (Hero) · 3 (Trend) ────────────────────────────────── */
  const heroWrapper = el('div', { className: 'col-9', id: 'w-hero' },
    el('h1', { className: 'sr-only', textContent: 'CareCast Early Warning Cockpit' }),
    createSkeleton({ minHeight: '160px' })
  );
  const trendWrapper = el('div', { className: 'col-3 card trend-card', id: 'w-trend' }, createSkeleton({ minHeight: '160px' }));
  root.appendChild(heroWrapper);
  root.appendChild(trendWrapper);

  /* ── ROW 2: 4 (Watchlist) · 4 (Explain) · 4 (Gauge) ─────────────── */
  const watchlistCard = createCard({
    id: 'w-watchlist',
    className: 'col-4',
    title: 'Disease Watchlist',
    subtitle: 'National respiratory monitoring',
    bodyNode: createSkeleton({ minHeight: '160px' }),
  });
  const explainCard = createCard({
    id: 'w-explain',
    className: 'col-4',
    title: 'Forecast Explanation',
    subtitle: 'Next-week model associations',
    bodyNode: createSkeleton({ minHeight: '160px' }),
  });
  const gaugeCard = createCard({
    id: 'w-gauge',
    className: 'col-4',
    title: 'Capacity Gauge',
    subtitle: '1-week forecast vs planning threshold',
    bodyNode: createSkeleton({ minHeight: '160px' }),
  });
  root.appendChild(watchlistCard);
  root.appendChild(explainCard);
  root.appendChild(gaugeCard);

  /* ── ROW 3: 12 (Forecast Table) ─────────────────────────────────── */
  const tableCard = createCard({
    id: 'w-forecast-table',
    className: 'col-12',
    title: 'Weekly Forecast Schedule',
    subtitle: '1–4 week horizon admissions with prediction intervals and alert tiers',
    bodyNode: createSkeleton({ minHeight: '200px' }),
  });
  root.appendChild(tableCard);

  /* ── ROW 4: 4 (Backtest) · 4 (Drivers) · 4 (Capacity Tiles) ─────── */
  const backtestCard = createCard({
    id: 'w-backtest',
    className: 'col-4',
    title: 'Model Backtest',
    subtitle: 'Held-out test performance (Horizon 1)',
    bodyNode: createSkeleton({ minHeight: '200px' }),
  });
  const driversCard = createCard({
    id: 'w-drivers',
    className: 'col-4',
    title: 'Top Drivers',
    subtitle: 'Feature contributions for current forecast',
    bodyNode: createSkeleton({ minHeight: '200px' }),
  });
  const capacityCard = createCard({
    id: 'w-capacity',
    className: 'col-4',
    title: 'Capacity Illustration',
    subtitle: 'Estimated beds & nurse shifts (SIMULATED)',
    bodyNode: createSkeleton({ minHeight: '200px' }),
  });
  root.appendChild(backtestCard);
  root.appendChild(driversCard);
  root.appendChild(capacityCard);

  /* ── FETCH & POPULATE WIDGETS INDEPENDENTLY ─────────────────────── */

  // 1. E3: Summary
  async function loadSummary() {
    const res = await api.getSummary({ disease, jurisdiction, threshold });
    if (!res.ok) {
      const err = createErrorBlock({
        message: res.error.message,
        requestId: res.error.requestId,
        onRetry: loadSummary,
      });
      heroWrapper.replaceChildren(
        el('h1', { className: 'hero-title', textContent: 'Overview Unavailable' }),
        err
      );
      trendWrapper.replaceChildren(err.cloneNode(true));
      return;
    }

    const d = res.data;
    const nw = d.selected.next_week;
    const latest = d.selected.latest;

    // w-hero
    const nextVal = nw.point;
    const nextInterval = `[${formatInt(nw.lower)} – ${formatInt(nw.upper)}]`;
    const heroBanner = createHeroBanner({
      greeting: `Weekly planning brief — Data as of ${formatDate(d.data_as_of)}`,
      title: `${formatDiseaseName(d.selected.disease)} Operations Cockpit`,
      subtitle: `Target: ${d.selected.jurisdiction} · Latest actual week: ${formatDate(latest.week_end_date)} (${formatInt(latest.value)} admissions)`,
      kpiChips: [
        createKpiChip({
          iconId: 'icon-forecast',
          numberText: formatInt(nextVal),
          labelText: `Next-week forecast ${nextInterval}`,
        }),
        createKpiChip({
          iconId: 'icon-alert',
          numberText: nw.tier.toUpperCase(),
          labelText: 'Operational alert tier',
        }),
      ],
    });
    heroWrapper.replaceChildren(heroBanner);

    // w-trend
    const trendBody = el('div');
    trendBody.appendChild(el('h2', { className: 'card-title', textContent: 'Recent Admissions' }));
    trendBody.appendChild(el('div', { className: 'card-subtitle', textContent: 'Last 8 weeks trajectory' }));

    const sparkCanvasContainer = el('div', { className: 'trend-chart-container' });
    const sparkCanvas = el('canvas', { role: 'img', 'aria-label': 'Recent admissions sparkline' });
    sparkCanvasContainer.appendChild(sparkCanvas);
    trendBody.appendChild(sparkCanvasContainer);

    const chg = latest.change_pct_vs_prior_week;
    const chgBadge = el('span', { className: 'trend-badge', textContent: formatPercent(chg, true, 'n/a') });
    const trendCap = el('div', { className: 'trend-caption' },
      document.createTextNode('Admissions changed by '),
      chgBadge,
      document.createTextNode(' vs prior week.')
    );
    trendBody.appendChild(trendCap);
    trendWrapper.replaceChildren(trendBody);

    const recentPoints = (d.selected.recent || []).map((p) => ({
      week_end: p.week_end_date,
      admissions: p.value,
    }));
    if (recentPoints.length > 0) {
      const spark = renderTrendSparkline(sparkCanvas, recentPoints);
      if (spark) chartCleanups.push(() => spark.destroy());
    }

    // w-watchlist
    const wlBody = el('div', { className: 'watchlist-container' });
    for (const item of d.watchlist) {
      const isCur = item.disease === disease;
      const row = createWatchlistRow({
        diseaseCode: item.disease,
        name: item.label || formatDiseaseName(item.disease),
        admissionsText: formatInt(item.latest_value),
        tier: item.tier || 'normal',
        isSelected: isCur,
        isUnavailable: !item.available,
        unavailableReason: item.available ? '' : 'Fewer than minimum required seasons',
        onSelect: (code) => {
          store.setDisease(code);
          window.location.hash = `#/overview?disease=${code}`;
        },
      });
      wlBody.appendChild(row);
    }
    watchlistCard.querySelector('.card-body').replaceChildren(wlBody);

    // w-gauge
    const ring = d.selected.ring;
    const gaugeBody = createRingGauge({
      ratio: (ring.forecast_pct_of_threshold || 0) / 100,
      pctText: formatPercent(ring.forecast_pct_of_threshold, false),
      lowerText: formatPercent(ring.lower_pct, false),
      upperText: formatPercent(ring.upper_pct, false),
      lowerVal: formatInt(nw.lower),
      upperVal: formatInt(nw.upper),
      tier: nw.tier,
    });
    gaugeCard.querySelector('.card-body').replaceChildren(gaugeBody);
  }

  // 2. E5: Forecast Table
  async function loadForecastTable() {
    const res = await api.getForecast({ disease, jurisdiction, threshold });
    if (!res.ok) {
      tableCard.querySelector('.card-body').replaceChildren(
        createErrorBlock({
          message: res.error.message,
          requestId: res.error.requestId,
          onRetry: loadForecastTable,
        })
      );
      return;
    }

    const d = res.data;
    const threshVal = d.threshold ? d.threshold.value : null;

    const tableColumns = [
      { key: 'horizon_weeks', label: 'Horizon', render: (val) => `${val} Wk` },
      { key: 'target_week_end_date', label: 'Target Week Ending', render: (val) => formatDate(val) },
      { key: 'point', label: 'Forecast', render: (val) => formatInt(val) },
      { key: 'lower', label: 'Lower (80%)', render: (val) => formatInt(val) },
      { key: 'upper', label: 'Upper (80%)', render: (val) => formatInt(val) },
      { key: 'threshold', label: 'Threshold', render: () => formatInt(threshVal) },
      { key: 'tier', label: 'Tier', render: (val) => createTierBadge(val) },
    ];

    const rowActions = [
      {
        label: 'Explain',
        iconId: 'icon-action-explain',
        className: 'btn-action-explain',
        ariaLabel: (row) => `Explain horizon ${row.horizon_weeks} forecast`,
        onClick: (row) => {
          window.location.hash = `#/explain?disease=${disease}&h=${row.horizon_weeks}`;
        },
      },
      {
        label: 'Scenario',
        iconId: 'icon-action-scenario',
        className: 'btn-action-scenario',
        ariaLabel: (row) => `Test scenario with horizon ${row.horizon_weeks}`,
        onClick: () => {
          window.location.hash = `#/scenario?disease=${disease}`;
        },
      },
      {
        label: 'Details',
        iconId: 'icon-action-details',
        className: 'btn-action-details',
        ariaLabel: () => `View full forecast details`,
        onClick: () => {
          window.location.hash = `#/forecast?disease=${disease}`;
        },
      },
    ];

    const tableNode = createDataTable({
      caption: `4-Week Forecast Schedule for ${formatDiseaseName(disease)}`,
      columns: tableColumns,
      rows: d.horizons,
      rowActions,
    });

    tableCard.querySelector('.card-body').replaceChildren(tableNode);
  }

  // 3. E7: Explanation Card & Drivers
  async function loadExplain() {
    const res = await api.getExplain({ disease, jurisdiction, horizon: 1 });
    if (!res.ok) {
      const err = createErrorBlock({
        message: res.error.message,
        requestId: res.error.requestId,
        onRetry: loadExplain,
      });
      explainCard.querySelector('.card-body').replaceChildren(err);
      driversCard.querySelector('.card-body').replaceChildren(err.cloneNode(true));
      return;
    }

    const d = res.data;

    // w-explain card
    const expBody = el('div');
    const tagsDiv = el('div', { className: 'explain-tags' });
    tagsDiv.appendChild(el('span', { className: 'tag-outline', textContent: `Model: ${d.model_name}` }));
    tagsDiv.appendChild(el('span', {
      className: 'tag-outline',
      textContent: `Horizon 1 Wk`,
    }));
    expBody.appendChild(tagsDiv);

    expBody.appendChild(el('p', { className: 'explain-text', textContent: d.text }));
    const beatsBaseline = d.beats_baseline !== false;
    const verdictTag = el('span', {
      className: beatsBaseline ? 'tag-filled tag-success' : 'tag-filled tag-warning',
      textContent: beatsBaseline ? '✔ Beats persistence baseline' : '✖ Did not beat baseline',
    });
    expBody.appendChild(verdictTag);
    expBody.appendChild(el('div', { className: 'explain-note', textContent: 'Associations, not causes.' }));
    explainCard.querySelector('.card-body').replaceChildren(expBody);

    // w-drivers card
    const driversBody = el('div', { className: 'contrib-list' });
    const driversList = d.contributions || d.permutation_importance || [];
    const topDrivers = driversList.slice(0, 5);

    if (topDrivers.length === 0) {
      driversBody.appendChild(el('p', { className: 'text-muted', textContent: 'No driver feature contributions available.' }));
    } else {
      const maxAbs = Math.max(...topDrivers.map((item) => Math.abs(Number(item.value) || 0)), 1);

      topDrivers.forEach((driver) => {
        const name = driver.label || driver.feature;
        const val = Number(driver.value) || 0;
        const row = el('div', { className: 'contrib-row' });
        row.appendChild(el('span', { className: 'contrib-name', textContent: name }));

        const barContainer = el('div', { className: 'contrib-bar-container' });
        barContainer.appendChild(el('div', { className: 'contrib-center-line' }));

        const svgBar = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svgBar.setAttribute('width', '100%');
        svgBar.setAttribute('height', '18');
        svgBar.setAttribute('viewBox', '0 0 100 18');
        svgBar.setAttribute('preserveAspectRatio', 'none');

        const mid = 50;
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

        row.appendChild(el('span', { className: 'contrib-val', textContent: val >= 0 ? `+${val.toFixed(1)}` : val.toFixed(1) }));
        driversBody.appendChild(row);
      });
    }

    driversCard.querySelector('.card-body').replaceChildren(driversBody);
  }

  // 4. E6: Backtest Chart
  async function loadBacktest() {
    const res = await api.getEvaluation({ disease, jurisdiction, horizon: 1 });
    if (!res.ok) {
      backtestCard.querySelector('.card-body').replaceChildren(
        createErrorBlock({
          message: res.error.message,
          requestId: res.error.requestId,
          onRetry: loadBacktest,
        })
      );
      return;
    }

    const d = res.data;
    const pts = (d.backtest && d.backtest.points) ? d.backtest.points.slice(-16) : [];

    const labels = pts.map((p) => formatDate(p.target_week_end_date));
    const actualData = pts.map((p) => p.actual);
    const predData = pts.map((p) => p.predicted_selected);

    const datasets = [
      {
        label: 'Actual',
        data: actualData,
        borderColor: '#1F7A74',
        borderWidth: 2.5,
        backgroundColor: 'transparent',
        pointRadius: 3,
      },
      {
        label: 'Predicted',
        data: predData,
        borderColor: '#3F9690',
        borderWidth: 2,
        borderDash: [5, 5],
        backgroundColor: 'transparent',
        pointRadius: 3,
        pointStyle: 'rect',
      },
    ];

    const chartObj = renderAccessibleChart({
      title: 'Backtest: Actual vs Predicted Admissions (Horizon 1)',
      ariaLabel: 'Backtest line chart comparing actual and predicted admissions',
      labels,
      datasets,
      tableColumns: [
        { key: 'target_week_end_date', label: 'Week Ending', render: (val) => formatDate(val) },
        { key: 'actual', label: 'Actual', render: (val) => formatInt(val) },
        { key: 'predicted_selected', label: 'Predicted', render: (val) => formatInt(val) },
      ],
      tableRows: pts,
    });

    chartCleanups.push(chartObj.destroy);
    backtestCard.querySelector('.card-body').replaceChildren(chartObj.figure);
  }

  // 5. E8: Capacity Illustration Tiles
  async function loadCapacity() {
    const res = await api.postScenario({
      disease,
      jurisdiction,
      surgePct: 0,
      threshold,
      capacity: store.state.capacity,
    });
    if (!res.ok) {
      capacityCard.querySelector('.card-body').replaceChildren(
        createErrorBlock({
          message: res.error.message,
          requestId: res.error.requestId,
          onRetry: loadCapacity,
        })
      );
      return;
    }

    const d = res.data;
    const h1 = d.capacity && d.capacity.horizons && d.capacity.horizons[0] ? d.capacity.horizons[0] : null;

    const tilesGrid = el('div', { className: 'tiles-grid' });
    if (h1) {
      tilesGrid.appendChild(
        createTile({
          iconId: 'icon-bed',
          label: 'Est. Occupied Beds',
          value: formatInt(h1.est_occupied_beds),
          badgeText: true,
        })
      );
      tilesGrid.appendChild(
        createTile({
          iconId: 'icon-calendar',
          label: 'Staffed Beds Total',
          value: formatInt(d.capacity.inputs.staffed_beds),
          badgeText: true,
        })
      );
      tilesGrid.appendChild(
        createTile({
          iconId: 'icon-staff',
          label: 'Nurses Per Shift',
          value: formatInt(h1.nurses_per_shift),
          badgeText: true,
        })
      );
    } else {
      tilesGrid.appendChild(el('p', { className: 'text-muted', textContent: 'No capacity illustration available.' }));
    }

    capacityCard.querySelector('.card-body').replaceChildren(tilesGrid);
  }

  loadSummary();
  loadForecastTable();
  loadExplain();
  loadBacktest();
  loadCapacity();

  return () => {
    chartCleanups.forEach((cleanup) => cleanup());
  };
}
