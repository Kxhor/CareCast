/**
 * Pure DOM Element Builders for CareCast — UI_UX_DESIGN & APP_FLOW
 * RULE: Strictly uses document.createElement, document.createTextNode,
 * and textContent ONLY. Zero forbidden DOM sinks (raw HTML assignment banned).
 */

import { formatInt, formatPercent, getTierInfo } from './format.js';

const SVG_NS = 'http://www.w3.org/2000/svg';

/**
 * Pure DOM helper: create an HTML element with attributes and children
 * @param {string} tag
 * @param {Record<string, any>} [attrs]
 * @param {...(Node|string|number|null|undefined)} children
 * @returns {HTMLElement}
 */
export function el(tag, attrs = {}, ...children) {
  const element = document.createElement(tag);

  for (const [key, val] of Object.entries(attrs)) {
    if (val === null || val === undefined) continue;

    if (key === 'className') {
      element.className = String(val);
    } else if (key === 'textContent') {
      element.textContent = String(val);
    } else if (key.startsWith('on') && typeof val === 'function') {
      const eventName = key.slice(2).toLowerCase();
      element.addEventListener(eventName, val);
    } else if (key === 'disabled' || key === 'checked' || key === 'selected') {
      if (val) {
        element.setAttribute(key, '');
        element[key] = true;
      } else {
        element[key] = false;
      }
    } else if (key === 'style') {
      // Hard ban on style string attributes per CSP
      console.warn('Inline style attribute forbidden by CSP; ignored:', val);
    } else {
      element.setAttribute(key, String(val));
    }
  }

  for (const child of children) {
    if (child === null || child === undefined) continue;
    if (child instanceof Node) {
      element.appendChild(child);
    } else {
      element.appendChild(document.createTextNode(String(child)));
    }
  }

  return element;
}

/**
 * Pure DOM helper: create an SVG element with attributes and children
 * @param {string} tag
 * @param {Record<string, any>} [attrs]
 * @param {...(Node|null|undefined)} children
 * @returns {SVGElement}
 */
export function svgEl(tag, attrs = {}, ...children) {
  const element = document.createElementNS(SVG_NS, tag);

  for (const [key, val] of Object.entries(attrs)) {
    if (val === null || val === undefined) continue;
    if (key === 'className') {
      element.setAttribute('class', String(val));
    } else if (key === 'textContent') {
      element.textContent = String(val);
    } else {
      element.setAttribute(key, String(val));
    }
  }

  for (const child of children) {
    if (child instanceof Node) {
      element.appendChild(child);
    }
  }

  return element;
}

/**
 * Create SVG icon referencing assets/icons.svg
 * @param {string} iconId
 * @param {string} [className]
 * @returns {SVGElement}
 */
export function createIcon(iconId, className = 'icon') {
  const svg = svgEl('svg', {
    className,
    'aria-hidden': 'true',
    viewBox: '0 0 24 24',
  });
  const use = svgEl('use', {
    href: `#${iconId}`,
  });
  use.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', `#${iconId}`);
  svg.appendChild(use);
  return svg;
}

/**
 * Card Component (C-07)
 */
export function createCard({ title, subtitle, headerAction, bodyNode, footerText, className = '', id = '' }) {
  const card = el('div', { className: `card ${className}`.trim() });
  if (id) card.id = id;

  if (title || headerAction) {
    const header = el('div', { className: 'card-header' });
    const titleBox = el('div');
    if (title) {
      titleBox.appendChild(el('h2', { className: 'card-title', textContent: title }));
    }
    if (subtitle) {
      titleBox.appendChild(el('div', { className: 'card-subtitle', textContent: subtitle }));
    }
    header.appendChild(titleBox);

    if (headerAction) {
      header.appendChild(headerAction);
    }
    card.appendChild(header);
  }

  const body = el('div', { className: 'card-body' });
  if (bodyNode) {
    body.appendChild(bodyNode);
  }
  card.appendChild(body);

  if (footerText) {
    card.appendChild(el('div', { className: 'card-footer', textContent: footerText }));
  }

  return card;
}

/**
 * Hero Banner (C-08)
 */
export function createHeroBanner({
  greeting = 'Weekly Planning Brief',
  title = 'Respiratory Capacity Cockpit',
  subtitle = 'US-wide operational early-warning forecast',
  kpiChips = [],
  motifId = 'hero-motif',
}) {
  const banner = el('section', { className: 'hero-banner', 'aria-label': 'Planning Brief' });

  const content = el('div', { className: 'hero-content' });
  content.appendChild(el('div', { className: 'hero-greeting', textContent: greeting }));
  content.appendChild(el('h1', { className: 'hero-title', textContent: title }));
  content.appendChild(el('div', { className: 'hero-subtitle', textContent: subtitle }));

  const chipsContainer = el('div', { className: 'hero-chips' });
  for (const chip of kpiChips) {
    chipsContainer.appendChild(chip);
  }
  content.appendChild(chipsContainer);
  banner.appendChild(content);

  // SVG motif (pure decorative, aria-hidden)
  const motif = svgEl('svg', {
    className: 'hero-motif',
    'aria-hidden': 'true',
    viewBox: '0 0 240 160',
  });
  const use = svgEl('use', { href: `#${motifId}` });
  use.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', `#${motifId}`);
  motif.appendChild(use);
  banner.appendChild(motif);

  return banner;
}

/**
 * KPI Chip (C-09)
 */
export function createKpiChip({ iconId = 'icon-stethoscope', numberText, labelText }) {
  const chip = el('div', { className: 'kpi-chip' });
  const circle = el('div', { className: 'kpi-icon-circle' }, createIcon(iconId));
  const data = el(
    'div',
    { className: 'kpi-data' },
    el('span', { className: 'kpi-number', textContent: numberText }),
    el('span', { className: 'kpi-label', textContent: labelText })
  );
  chip.appendChild(circle);
  chip.appendChild(data);
  return chip;
}

/**
 * Tier Badge (C-12)
 */
export function createTierBadge(tier) {
  const info = getTierInfo(tier);
  const pill = el('span', { className: `tier-pill ${info.className}` });
  pill.appendChild(createIcon(info.iconId, 'tier-icon'));
  pill.appendChild(document.createTextNode(` ${info.label}`));
  return pill;
}

/**
 * Honesty Badges (C-21)
 */
export function createHonestyBadge(type) {
  if (type === 'simulated') {
    const badge = el('span', { className: 'badge-simulated' });
    badge.appendChild(createIcon('icon-info', 'badge-icon'));
    badge.appendChild(document.createTextNode(' SIMULATED — assumption-based'));
    return badge;
  }
  if (type === 'scenario') {
    const badge = el('span', { className: 'badge-scenario' });
    badge.appendChild(createIcon('icon-scenario', 'badge-icon'));
    badge.appendChild(document.createTextNode(' SCENARIO — not a prediction'));
    return badge;
  }
  const badge = el('span', { className: 'badge-placeholder' });
  badge.appendChild(document.createTextNode('DEMO DATA PLACEHOLDER'));
  return badge;
}

/**
 * Watchlist Row Button (C-11)
 */
export function createWatchlistRow({
  diseaseCode,
  name,
  admissionsText,
  tier,
  isSelected = false,
  isUnavailable = false,
  unavailableReason = '',
  onSelect,
}) {
  const btn = el('button', {
    type: 'button',
    className: `watchlist-row ${isSelected ? 'selected' : ''} ${isUnavailable ? 'unavailable' : ''}`.trim(),
    'aria-pressed': isSelected ? 'true' : 'false',
    disabled: isUnavailable,
    onclick: () => {
      if (!isUnavailable && onSelect) onSelect(diseaseCode);
    },
  });

  const main = el('div', { className: 'watchlist-main' });
  const iconBox = el('div', { className: 'watchlist-icon' }, createIcon('icon-virus'));
  const info = el('div', { className: 'watchlist-info' });
  info.appendChild(el('span', { className: 'watchlist-name', textContent: name }));

  const sub = isUnavailable
    ? `Unavailable: ${unavailableReason || 'Not loaded'}`
    : `Latest week: ${admissionsText}`;
  info.appendChild(el('span', { className: 'watchlist-detail', textContent: sub }));

  main.appendChild(iconBox);
  main.appendChild(info);
  btn.appendChild(main);

  btn.appendChild(createTierBadge(isUnavailable ? 'unavailable' : tier));
  return btn;
}

/**
 * Ring Gauge (C-14)
 * SVG dashed arc with stroke-dashoffset, zero inline styles
 */
export function createRingGauge({ ratio = 0.8, pctText = '80%', lowerText = '—', upperText = '—', tier = 'normal', lowerVal = '', upperVal = '' }) {
  const container = el('div', { className: 'gauge-container' });

  const svgWrapper = el('div', { className: 'gauge-svg-wrapper' });
  const radius = 64;
  const circumference = 2 * Math.PI * radius; // ~402.12
  const clampedRatio = Math.max(0, Math.min(1.5, Number(ratio) || 0));
  // Arc spans 80% of circle circumference at 100% capacity
  const maxArc = circumference * 0.8;
  const offset = maxArc * (1 - Math.min(1.0, clampedRatio));

  const svg = svgEl('svg', {
    className: 'gauge-svg',
    viewBox: '0 0 160 160',
    'aria-hidden': 'true',
  });

  const bgCircle = svgEl('circle', {
    className: 'gauge-circle-bg',
    cx: '80',
    cy: '80',
    r: String(radius),
    'stroke-dasharray': `${maxArc} ${circumference - maxArc}`,
    'stroke-dashoffset': '0',
  });

  const arcClass = tier === 'elevated' ? 'gauge-circle-arc gauge-elevated' : tier === 'watch' ? 'gauge-circle-arc gauge-watch' : 'gauge-circle-arc';
  const arcCircle = svgEl('circle', {
    className: arcClass,
    cx: '80',
    cy: '80',
    r: String(radius),
    'stroke-dasharray': `${maxArc} ${circumference - maxArc}`,
    'stroke-dashoffset': String(offset),
  });

  svg.appendChild(bgCircle);
  svg.appendChild(arcCircle);
  svgWrapper.appendChild(svg);

  const center = el('div', { className: 'gauge-center' });
  center.appendChild(el('div', { className: 'gauge-pct', textContent: pctText }));
  center.appendChild(el('div', { className: 'gauge-label', textContent: 'of threshold' }));
  svgWrapper.appendChild(center);

  container.appendChild(svgWrapper);

  const pills = el('div', { className: 'gauge-pills' });
  const lowerPill = el('div', { className: 'bound-pill' },
    el('div', { className: 'bound-pill-icon' }, createIcon('icon-forecast')),
    el('div', { className: 'bound-pill-data' },
      el('span', { className: 'bound-pill-val', textContent: lowerVal || lowerText }),
      el('span', { className: 'bound-pill-label', textContent: `Lower (${lowerText})` })
    )
  );
  const upperPill = el('div', { className: 'bound-pill' },
    el('div', { className: 'bound-pill-icon' }, createIcon('icon-alert')),
    el('div', { className: 'bound-pill-data' },
      el('span', { className: 'bound-pill-val', textContent: upperVal || upperText }),
      el('span', { className: 'bound-pill-label', textContent: `Upper (${upperText})` })
    )
  );
  pills.appendChild(lowerPill);
  pills.appendChild(upperPill);
  container.appendChild(pills);

  return container;
}

/**
 * Data Table Component (C-15)
 */
export function createDataTable({
  caption,
  columns,
  rows = [],
  rowActions = [],
  emptyMessage = 'No data available.',
}) {
  const container = el('div', { className: 'table-container' });
  const table = el('table', { className: 'data-table' });

  if (caption) {
    table.appendChild(el('caption', { textContent: caption }));
  }

  const thead = el('thead');
  const headerRow = el('tr');
  for (const col of columns) {
    headerRow.appendChild(el('th', { scope: 'col', textContent: col.label }));
  }
  if (rowActions.length > 0) {
    headerRow.appendChild(el('th', { scope: 'col', textContent: 'Actions' }));
  }
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = el('tbody');
  if (rows.length === 0) {
    const emptyRow = el('tr');
    const td = el('td', {
      colspan: String(columns.length + (rowActions.length > 0 ? 1 : 0)),
      textContent: emptyMessage,
    });
    emptyRow.appendChild(td);
    tbody.appendChild(emptyRow);
  } else {
    rows.forEach((row, rowIdx) => {
      const tr = el('tr');
      columns.forEach((col) => {
        const val = row[col.key];
        const td = el('td');
        if (col.render && typeof col.render === 'function') {
          const rendered = col.render(val, row, rowIdx);
          if (rendered instanceof Node) {
            td.appendChild(rendered);
          } else {
            td.textContent = String(rendered ?? '—');
          }
        } else {
          td.textContent = String(val ?? '—');
        }
        tr.appendChild(td);
      });

      if (rowActions.length > 0) {
        const tdAction = el('td');
        const actionsDiv = el('div', { className: 'table-actions' });
        for (const action of rowActions) {
          const btn = el('button', {
            type: 'button',
            className: `btn-icon-action ${action.className || ''}`.trim(),
            'aria-label': action.ariaLabel ? action.ariaLabel(row, rowIdx) : action.label,
            title: action.label,
            onclick: () => action.onClick(row, rowIdx),
          }, createIcon(action.iconId || 'icon-info'));
          actionsDiv.appendChild(btn);
        }
        tdAction.appendChild(actionsDiv);
        tr.appendChild(tdAction);
      }

      tbody.appendChild(tr);
    });
  }

  table.appendChild(tbody);
  container.appendChild(table);
  return container;
}

/**
 * Capacity Stat Tile (C-17)
 */
export function createTile({ iconId = 'icon-bed', label, value, badgeText }) {
  const tile = el('div', { className: 'stat-tile' });
  tile.appendChild(el('div', { className: 'stat-tile-icon' }, createIcon(iconId)));

  const middle = el('div', { className: 'stat-tile-middle' });
  middle.appendChild(el('div', { className: 'stat-tile-label', textContent: label }));
  if (badgeText) {
    middle.appendChild(el('div', { className: 'stat-tile-badge' }, createHonestyBadge('simulated')));
  }
  tile.appendChild(middle);

  tile.appendChild(el('div', { className: 'stat-tile-value', textContent: value }));
  return tile;
}

/**
 * Alert Banner (C-19)
 */
export function createAlertBanner({ type = 'info', text, role = 'status' }) {
  const banner = el('div', {
    className: `alert-banner alert-${type}`,
    role,
  });
  const iconId = type === 'error' ? 'icon-alert' : type === 'warning' ? 'icon-eye' : 'icon-info';
  banner.appendChild(createIcon(iconId, 'alert-icon'));
  banner.appendChild(el('div', { className: 'alert-text', textContent: text }));
  return banner;
}

/**
 * Error Block with Retry (C-20)
 */
export function createErrorBlock({ message, requestId, onRetry }) {
  const block = el('div', { className: 'error-block', role: 'alert' });
  block.appendChild(createIcon('icon-alert', 'empty-icon'));
  block.appendChild(el('p', {
    textContent: message || 'We could not load this section. Please try again.',
  }));

  if (requestId) {
    block.appendChild(el('div', {
      className: 'error-request-id',
      textContent: `Request ID: ${requestId}`,
    }));
  }

  if (onRetry) {
    block.appendChild(el('button', {
      type: 'button',
      className: 'btn-secondary',
      textContent: 'Retry',
      onclick: onRetry,
    }));
  }

  return block;
}

/**
 * Skeleton Block (C-20)
 */
export function createSkeleton({ minHeight = '140px' } = {}) {
  const sk = el('div', { className: 'skeleton-block', 'aria-busy': 'true', 'aria-label': 'Loading...' });
  return sk;
}

/**
 * Empty State (C-20)
 */
export function createEmptyState({ message = 'No data available.', actionText, onAction }) {
  const container = el('div', { className: 'empty-state' });
  container.appendChild(createIcon('icon-info', 'empty-icon'));
  container.appendChild(el('p', { textContent: message }));
  if (actionText && onAction) {
    container.appendChild(el('button', {
      type: 'button',
      className: 'btn-secondary',
      textContent: actionText,
      onclick: onAction,
    }));
  }
  return container;
}

/**
 * Horizon Tabs (C-23)
 */
export function createHorizonTabs({ selectedH = 1, onSelectH }) {
  const tablist = el('div', {
    className: 'tablist',
    role: 'tablist',
    'aria-label': 'Forecast horizons',
  });

  [1, 2, 3, 4].forEach((h) => {
    const isSelected = h === selectedH;
    const btn = el('button', {
      type: 'button',
      className: 'tab-btn',
      role: 'tab',
      id: `tab-h-${h}`,
      'aria-selected': isSelected ? 'true' : 'false',
      tabindex: isSelected ? '0' : '-1',
      textContent: `${h} Week${h > 1 ? 's' : ''}`,
      onclick: () => onSelectH(h),
      onkeydown: (e) => {
        let targetH = null;
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
          targetH = h === 4 ? 1 : h + 1;
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
          targetH = h === 1 ? 4 : h - 1;
        } else if (e.key === 'Home') {
          targetH = 1;
        } else if (e.key === 'End') {
          targetH = 4;
        }
        if (targetH !== null) {
          e.preventDefault();
          onSelectH(targetH);
          const nextTab = document.getElementById(`tab-h-${targetH}`);
          if (nextTab) nextTab.focus();
        }
      },
    });
    tablist.appendChild(btn);
  });

  return tablist;
}
