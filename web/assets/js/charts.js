/**
 * Accessible Chart.js Wrapper for CareCast — UI_UX_DESIGN §4 (C-16) & A11Y-08
 * Pure DOM construction: <figure> + <figcaption> + <canvas> + <details> table fallback.
 */

import { el, createDataTable } from './components.js';
import { formatDate, formatInt } from './format.js';

const COLORS = {
  actual: '#1F7A74',
  comparison: '#3F9690',
  forecast: '#B45309',
  threshold: '#B3261E',
  intervalBand: 'rgba(31, 122, 116, 0.18)',
  grid: '#DDE9E9',
  textMuted: '#5B6B6B',
  white: '#FFFFFF',
  accentGreen: '#7AD672',
};

/**
 * Check if user prefers reduced motion
 * @returns {boolean}
 */
function prefersReducedMotion() {
  return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Render Accessible Chart Card (C-16)
 * @param {Object} options
 * @param {string} options.title - Caption / summary
 * @param {string} options.ariaLabel - Accessible label for canvas
 * @param {Array<string>} options.labels - X-axis labels
 * @param {Array<Object>} options.datasets - Chart.js datasets
 * @param {Array<Object>} [options.tableColumns] - Columns for fallback table
 * @param {Array<Object>} [options.tableRows] - Rows for fallback table
 * @param {string} [options.containerClass] - CSS class for wrapper
 * @param {Object} [options.extraChartOptions]
 * @returns {{ figure: HTMLElement, chart: any, destroy: () => void }}
 */
export function renderAccessibleChart({
  title,
  ariaLabel,
  labels = [],
  datasets = [],
  tableColumns = [],
  tableRows = [],
  containerClass = 'chart-canvas-wrapper',
  extraChartOptions = {},
}) {
  const figure = el('figure', { className: 'chart-figure' });

  if (title) {
    const figcaption = el('figcaption', { className: 'chart-figcaption', textContent: title });
    figure.appendChild(figcaption);
  }

  const canvasWrapper = el('div', { className: containerClass });
  const canvas = el('canvas', {
    role: 'img',
    'aria-label': ariaLabel || title || 'Data chart',
  });
  canvasWrapper.appendChild(canvas);
  figure.appendChild(canvasWrapper);

  // Fallback accessible data table inside <details>
  if (tableColumns.length > 0 && tableRows.length > 0) {
    const details = el('details', { className: 'chart-details' });
    const summary = el('summary', { textContent: 'View data table (accessible alternative)' });
    details.appendChild(summary);

    const tableNode = createDataTable({
      caption: title || 'Chart numerical data',
      columns: tableColumns,
      rows: tableRows,
    });
    details.appendChild(tableNode);
    figure.appendChild(details);
  }

  // Initialize Chart.js
  let chartInstance = null;
  if (window.Chart) {
    const ctx = canvas.getContext('2d');
    const isReduced = prefersReducedMotion();

    const chartConfig = {
      type: 'line',
      data: {
        labels,
        datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: isReduced ? false : { duration: 300 },
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              boxWidth: 16,
              usePointStyle: true,
              color: COLORS.textMuted,
              font: { size: 12 },
            },
          },
          tooltip: {
            enabled: true,
            backgroundColor: '#1F2D2D',
            titleFont: { size: 12, weight: 'bold' },
            bodyFont: { size: 12 },
            padding: 8,
            callbacks: {
              label: (ctx) => {
                const label = ctx.dataset.label || '';
                const val = ctx.parsed.y;
                return `${label}: ${formatInt(val)}`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: {
              color: COLORS.grid,
              drawBorder: false,
            },
            ticks: {
              color: COLORS.textMuted,
              font: { size: 11 },
              maxRotation: 45,
            },
          },
          y: {
            grid: {
              color: COLORS.grid,
              drawBorder: false,
            },
            ticks: {
              color: COLORS.textMuted,
              font: { size: 11 },
              callback: (val) => formatInt(val),
            },
          },
        },
        ...extraChartOptions,
      },
    };

    chartInstance = new window.Chart(ctx, chartConfig);
  } else {
    console.warn('Chart.js not loaded on window.');
  }

  return {
    figure,
    chart: chartInstance,
    destroy: () => {
      if (chartInstance) {
        chartInstance.destroy();
        chartInstance = null;
      }
    },
  };
}

/**
 * Build mini trend chart for S1 w-trend
 * Single line on teal background with green circular markers
 */
export function renderTrendSparkline(canvasElement, points = []) {
  if (!window.Chart || !canvasElement) return null;

  const labels = points.map((p) => formatDate(p.week_end));
  const data = points.map((p) => p.admissions);

  const ctx = canvasElement.getContext('2d');
  return new window.Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          data,
          borderColor: COLORS.white,
          borderWidth: 2.5,
          backgroundColor: 'transparent',
          pointBackgroundColor: COLORS.accentGreen,
          pointBorderColor: COLORS.white,
          pointRadius: 4,
          pointHoverRadius: 6,
          tension: 0.2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => (items[0] ? items[0].label : ''),
            label: (item) => `Admissions: ${formatInt(item.parsed.y)}`,
          },
        },
      },
      scales: {
        x: {
          display: true,
          grid: { display: false },
          ticks: {
            color: 'rgba(255, 255, 255, 0.8)',
            font: { size: 10 },
            maxTicksLimit: 4,
          },
        },
        y: {
          display: false,
          grid: { display: false },
        },
      },
    },
  });
}
