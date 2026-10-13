/**
 * S5 — Scenario Planner Screen
 * UI_UX_DESIGN §5 & APP_FLOW §4
 * Stress-testing with surge slider, capacity assumptions, base vs scenario chart, tier change table, and simulated capacity.
 */

import { api } from '../api.js';
import { store, CAPACITY_BOUNDS } from '../store.js';
import {
  el,
  createCard,
  createTierBadge,
  createHonestyBadge,
  createDataTable,
  createErrorBlock,
  createSkeleton,
} from '../components.js';
import { renderAccessibleChart } from '../charts.js';
import { formatDate, formatInt, formatPercent } from '../format.js';

export function renderScenario(container) {
  while (container.firstChild) {
    container.removeChild(container.firstChild);
  }

  const root = el('div', { className: 'grid-container view-scenario' });
  container.appendChild(root);

  let activeChartCleanup = null;
  let debounceTimer = null;

  const disease = store.state.disease;
  const jurisdiction = store.state.jurisdiction;

  /* ── Page Header (A11Y-05) ───────────────────────────────────────── */
  const pageHeader = el('div', { className: 'col-12 page-header' },
    el('h1', { className: 'page-title', textContent: 'Capacity Scenario Planner' }),
    el('p', { className: 'page-subtitle', textContent: 'Stress-testing respiratory surge scenarios and hospital capacity illustration' })
  );
  root.appendChild(pageHeader);

  /* ── LEFT COLUMN (col-4): Controls ──────────────────────────────── */
  const leftCol = el('div', { className: 'col-4', id: 'w-scenario-controls' });

  // Surge Slider Card
  const surgeCard = createCard({
    title: 'Surge Assumption Slider',
    subtitle: 'Simulate percentage surge relative to point forecast',
    bodyNode: buildSurgeControls(),
  });
  leftCol.appendChild(surgeCard);

  // Capacity Assumptions Card
  const capacityCard = createCard({
    title: 'Bed & Staffing Assumptions',
    subtitle: 'Operational multipliers for simulated resource needs',
    bodyNode: buildCapacityControls(),
  });
  leftCol.appendChild(capacityCard);

  root.appendChild(leftCol);

  /* ── RIGHT COLUMN (col-8): Results ──────────────────────────────── */
  const rightCol = el('div', { className: 'col-8', 'aria-live': 'polite' });

  // w-scenario-chart
  const chartCard = createCard({
    id: 'w-scenario-chart',
    className: 'col-12',
    title: 'Base Forecast vs Stress Scenario',
    subtitle: 'Point predictions with simulated surge line and planning threshold',
    headerAction: createHonestyBadge('scenario'),
    bodyNode: createSkeleton({ minHeight: '260px' }),
  });
  rightCol.appendChild(chartCard);

  // w-tier-changes
  const tierChangesCard = createCard({
    id: 'w-tier-changes',
    className: 'col-12',
    title: 'Alert Tier Shifts Across Horizons',
    subtitle: 'Operational consequence of simulated admission surge',
    bodyNode: createSkeleton({ minHeight: '140px' }),
  });
  rightCol.appendChild(tierChangesCard);

  // w-capacity-table
  const capacityTableCard = createCard({
    id: 'w-capacity-table',
    className: 'col-12',
    title: 'Simulated Capacity Demands',
    subtitle: 'Illustrative occupied beds and nursing requirements per shift',
    headerAction: createHonestyBadge('simulated'),
    bodyNode: createSkeleton({ minHeight: '180px' }),
  });
  rightCol.appendChild(capacityTableCard);

  // w-actions
  const actionsCard = createCard({
    id: 'w-actions',
    className: 'col-12',
    title: 'Scenario Planning Checklist',
    subtitle: 'Action checklist adapted to highest simulated scenario tier',
    bodyNode: createSkeleton({ minHeight: '100px' }),
  });
  rightCol.appendChild(actionsCard);

  root.appendChild(rightCol);

  function buildSurgeControls() {
    const wrapper = el('div');

    const sliderContainer = el('div', { className: 'slider-container' });
    const rangeInput = el('input', {
      type: 'range',
      className: 'form-range',
      min: '-50',
      max: '100',
      step: '1',
      value: String(store.state.surgePct),
      'aria-label': 'Surge percentage',
    });

    const numInput = el('input', {
      type: 'number',
      className: 'form-input',
      min: '-50',
      max: '100',
      value: String(store.state.surgePct),
      'aria-label': 'Surge percentage numeric value',
    });

    rangeInput.addEventListener('input', () => {
      numInput.value = rangeInput.value;
      store.setSurgePct(rangeInput.value);
      triggerDebouncedRun();
    });

    numInput.addEventListener('input', () => {
      rangeInput.value = numInput.value;
      store.setSurgePct(numInput.value);
      triggerDebouncedRun();
    });

    sliderContainer.appendChild(rangeInput);
    sliderContainer.appendChild(numInput);
    wrapper.appendChild(sliderContainer);

    const presetsDiv = el('div', { className: 'preset-buttons' });
    [0, 10, 20].forEach((pct) => {
      const btn = el('button', {
        type: 'button',
        className: 'btn-preset',
        textContent: `${pct >= 0 ? '+' : ''}${pct}% Preset`,
        onclick: () => {
          rangeInput.value = String(pct);
          numInput.value = String(pct);
          store.setSurgePct(pct);
          triggerDebouncedRun();
        },
      });
      presetsDiv.appendChild(btn);
    });
    wrapper.appendChild(presetsDiv);

    return wrapper;
  }

  function buildCapacityControls() {
    const wrapper = el('div');
    wrapper.appendChild(createHonestyBadge('simulated'));

    const fields = [
      { key: 'typical_weekly_admissions', label: 'Typical Weekly Admissions', step: '10' },
      { key: 'alos_days', label: 'Average Length of Stay (days)', step: '0.5' },
      { key: 'staffed_beds', label: 'Staffed Beds (total)', step: '10' },
      { key: 'patients_per_nurse', label: 'Patients Per Nurse Ratio', step: '0.5' },
    ];

    const currentAssumptions = { ...store.state.capacity };

    fields.forEach((field) => {
      const group = el('div', { className: 'form-group' });
      group.appendChild(el('label', { className: 'form-label', textContent: field.label }));
      const b = CAPACITY_BOUNDS[field.key];
      const inp = el('input', {
        type: 'number',
        className: 'form-input',
        min: String(b.min),
        max: String(b.max),
        step: field.step,
        value: String(currentAssumptions[field.key]),
      });

      inp.addEventListener('change', () => {
        const val = Number(inp.value);
        if (Number.isNaN(val) || val < b.min || val > b.max) {
          inp.classList.add('invalid');
          return;
        }
        inp.classList.remove('invalid');
        currentAssumptions[field.key] = val;
        store.saveCapacityAssumptions(currentAssumptions);
        triggerDebouncedRun();
      });

      group.appendChild(inp);
      wrapper.appendChild(group);
    });

    const resetBtn = el('button', {
      type: 'button',
      className: 'btn-secondary',
      textContent: 'Reset to demo placeholders',
      onclick: () => {
        store.resetCapacityToDemo();
        renderScenario(container);
      },
    });
    wrapper.appendChild(resetBtn);

    return wrapper;
  }

  function triggerDebouncedRun() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      runScenario();
    }, 300);
  }

  async function runScenario() {
    if (activeChartCleanup) {
      activeChartCleanup();
      activeChartCleanup = null;
    }

    const res = await api.postScenario({
      disease,
      jurisdiction,
      surgePct: store.state.surgePct,
      threshold: store.state.thresholdOverride,
      capacity: store.state.capacity,
    });

    if (!res.ok) {
      const err = createErrorBlock({
        message: res.error.message,
        requestId: res.error.requestId,
        onRetry: runScenario,
      });
      chartCard.querySelector('.card-body').replaceChildren(err);
      tierChangesCard.querySelector('.card-body').replaceChildren(err.cloneNode(true));
      capacityTableCard.querySelector('.card-body').replaceChildren(err.cloneNode(true));
      actionsCard.querySelector('.card-body').replaceChildren(err.cloneNode(true));
      return;
    }

    const d = res.data;

    renderScenarioChart(d);
    renderTierChanges(d);
    renderCapacityTable(d);
    renderActions(d);
  }

  function renderScenarioChart(data) {
    const labels = (data.horizons || []).map((h) => formatDate(h.target_week_end_date));
    const baseData = (data.horizons || []).map((h) => h.base.point);
    const scenData = (data.horizons || []).map((h) => h.scenario.point);
    const thresholdVal = data.threshold ? data.threshold.value : null;
    const threshData = labels.map(() => thresholdVal);

    const datasets = [
      {
        label: 'Base Forecast',
        data: baseData,
        borderColor: '#1F7A74',
        borderWidth: 2.5,
        borderDash: [5, 5],
        backgroundColor: 'transparent',
        pointRadius: 4,
      },
      {
        label: `Scenario (${formatPercent(data.surge_pct, true)})`,
        data: scenData,
        borderColor: '#B45309',
        borderWidth: 2.5,
        borderDash: [4, 4],
        backgroundColor: 'transparent',
        pointRadius: 4,
        pointStyle: 'rectRot',
      },
    ];

    if (thresholdVal !== null && thresholdVal !== undefined) {
      datasets.push({
        label: `Threshold (${formatInt(thresholdVal)})`,
        data: threshData,
        borderColor: '#B3261E',
        borderWidth: 2,
        borderDash: [2, 2],
        backgroundColor: 'transparent',
        pointRadius: 0,
      });
    }

    const chartObj = renderAccessibleChart({
      title: `Scenario comparison (${formatPercent(data.surge_pct, true)} surge)`,
      ariaLabel: 'Chart comparing base forecast against scenario curve with threshold line',
      labels,
      datasets,
      tableColumns: [
        { key: 'horizon', label: 'Horizon' },
        { key: 'week', label: 'Target Week Ending' },
        { key: 'base', label: 'Base Forecast' },
        { key: 'scen', label: 'Scenario Forecast' },
        { key: 'threshold', label: 'Threshold' },
      ],
      tableRows: (data.horizons || []).map((h) => ({
        horizon: `${h.horizon_weeks} Wk`,
        week: formatDate(h.target_week_end_date),
        base: formatInt(h.base.point),
        scen: formatInt(h.scenario.point),
        threshold: formatInt(thresholdVal),
      })),
    });

    activeChartCleanup = chartObj.destroy;
    chartCard.querySelector('.card-body').replaceChildren(chartObj.figure);
  }

  function renderTierChanges(data) {
    const columns = [
      { key: 'horizon_weeks', label: 'Horizon', render: (val) => `${val} Week${val > 1 ? 's' : ''}` },
      { key: 'target_week_end_date', label: 'Target Week Ending', render: (val) => formatDate(val) },
      { key: 'base_tier', label: 'Base Tier', render: (val, row) => createTierBadge(row.base.tier) },
      { key: 'scenario_tier', label: 'Scenario Tier', render: (val, row) => createTierBadge(row.scenario.tier) },
      {
        key: 'tier_change',
        label: 'Tier Trajectory',
        render: (val, row) => {
          const base = row.base.tier.toLowerCase();
          const scen = row.scenario.tier.toLowerCase();
          if (base === scen) return 'Unchanged';
          if (scen === 'elevated') return 'Rises to Elevated ⚠';
          if (scen === 'watch') return 'Rises to Watch 👁';
          return 'Falls';
        },
      },
    ];

    const tableNode = createDataTable({
      caption: 'Tier shifts under simulated surge',
      columns,
      rows: data.horizons || [],
    });

    tierChangesCard.querySelector('.card-body').replaceChildren(tableNode);
  }

  function renderCapacityTable(data) {
    const wrapper = el('div');
    const capHorizons = (data.capacity && data.capacity.horizons) ? data.capacity.horizons : [];

    const columns = [
      { key: 'horizon_weeks', label: 'Horizon', render: (val) => `${val} Wk` },
      { key: 'relative_change', label: 'Surge', render: (val) => formatPercent((val || 0) * 100, true) },
      { key: 'hospital_weekly_admissions', label: 'Est. Admissions', render: (val) => formatInt(val) },
      { key: 'est_occupied_beds', label: 'Est. Occupied Beds', render: (val) => formatInt(val) },
      {
        key: 'staffed_beds',
        label: 'Staffed Beds',
        render: () => formatInt(data.capacity.inputs.staffed_beds),
      },
      {
        key: 'bed_gap',
        label: 'Bed Balance',
        render: (val) => {
          const num = Number(val);
          const formatted = formatInt(Math.abs(num));
          return num > 0 ? `+${formatted} surplus` : num < 0 ? `-${formatted} shortfall` : '0';
        },
      },
      { key: 'nurses_per_shift', label: 'Nurses / Shift', render: (val) => formatInt(val) },
    ];

    const tableNode = createDataTable({
      caption: 'Simulated operational capacity demands',
      columns,
      rows: capHorizons,
    });
    wrapper.appendChild(tableNode);

    const details = el('details', { className: 'chart-details' });
    const summary = el('summary', { textContent: 'How this is calculated (simulation formulae)' });
    details.appendChild(summary);

    const formulae = (data.capacity && data.capacity.formulae) || [];
    const formList = el('ul', { className: 'checklist' });
    formulae.forEach((formula) => {
      const item = el('li', { className: 'checklist-item' });
      item.appendChild(el('span', { className: 'bound-dot' }));
      item.appendChild(el('span', { textContent: formula }));
      formList.appendChild(item);
    });
    details.appendChild(formList);
    wrapper.appendChild(details);

    capacityTableCard.querySelector('.card-body').replaceChildren(wrapper);
  }

  function renderActions(data) {
    const actions = (data.actions && data.actions.items) ? data.actions.items : [];
    const body = el('div');

    if (actions.length === 0) {
      body.appendChild(el('p', { className: 'text-muted', textContent: 'Standard operations checklist.' }));
    } else {
      const list = el('ul', { className: 'checklist' });
      actions.forEach((act) => {
        const item = el('li', { className: 'checklist-item' });
        item.appendChild(el('span', { className: 'bound-dot' }));
        item.appendChild(el('span', { textContent: act }));
        list.appendChild(item);
      });
      body.appendChild(list);
    }

    actionsCard.querySelector('.card-body').replaceChildren(body);
  }

  runScenario();

  return () => {
    if (activeChartCleanup) activeChartCleanup();
    if (debounceTimer) clearTimeout(debounceTimer);
  };
}
