/**
 * CareCast formatting utilities — UI_UX_DESIGN §7
 * Strict use of Intl and pure deterministic formatting.
 */

const numIntFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 0,
});

const numDecimalFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const numTwoDecimalFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * Format integer or null to comma-separated string
 * @param {number|null|undefined} val
 * @param {string} fallback
 * @returns {string}
 */
export function formatInt(val, fallback = '—') {
  if (val === null || val === undefined || Number.isNaN(Number(val))) {
    return fallback;
  }
  return numIntFormatter.format(Math.round(Number(val)));
}

/**
 * Format decimal value to 1 decimal place
 * @param {number|null|undefined} val
 * @param {string} fallback
 * @returns {string}
 */
export function formatDecimal(val, fallback = '—') {
  if (val === null || val === undefined || Number.isNaN(Number(val))) {
    return fallback;
  }
  return numDecimalFormatter.format(Number(val));
}

/**
 * Format decimal value to 2 decimal places (e.g. for metrics)
 * @param {number|null|undefined} val
 * @param {string} fallback
 * @returns {string}
 */
export function formatTwoDecimals(val, fallback = '—') {
  if (val === null || val === undefined || Number.isNaN(Number(val))) {
    return fallback;
  }
  return numTwoDecimalFormatter.format(Number(val));
}

/**
 * Format percentage with optional sign
 * @param {number|null|undefined} val - in percent (e.g. 15.2 for 15.2%)
 * @param {boolean} includeSign
 * @param {string} fallback
 * @returns {string}
 */
export function formatPercent(val, includeSign = false, fallback = '—') {
  if (val === null || val === undefined || Number.isNaN(Number(val))) {
    return fallback;
  }
  const n = Number(val);
  const formatted = numDecimalFormatter.format(n);
  if (includeSign && n > 0) {
    return `+${formatted}%`;
  }
  return `${formatted}%`;
}

/**
 * Format ISO date string (YYYY-MM-DD) into unambiguous '10 Oct 2026' format
 * Avoids browser timezone shift by parsing YYYY, MM, DD components directly.
 * @param {string|null|undefined} isoStr
 * @param {string} fallback
 * @returns {string}
 */
export function formatDate(isoStr, fallback = '—') {
  if (!isoStr || typeof isoStr !== 'string') {
    return fallback;
  }
  const parts = isoStr.trim().split('-');
  if (parts.length !== 3) {
    return isoStr;
  }
  const year = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10);
  const day = parseInt(parts[2], 10);
  if (Number.isNaN(year) || Number.isNaN(month) || Number.isNaN(day) || month < 1 || month > 12) {
    return isoStr;
  }
  return `${day} ${MONTHS[month - 1]} ${year}`;
}

/**
 * Map tier to display label, CSS class, and icon id
 * @param {string|null|undefined} tier
 * @returns {{ label: string, className: string, iconId: string }}
 */
export function getTierInfo(tier) {
  const norm = String(tier || '').toLowerCase().trim();
  if (norm === 'normal') {
    return {
      label: 'Normal',
      className: 'tier-normal',
      iconId: 'icon-check',
    };
  }
  if (norm === 'watch') {
    return {
      label: 'Watch',
      className: 'tier-watch',
      iconId: 'icon-eye',
    };
  }
  if (norm === 'elevated') {
    return {
      label: 'Elevated',
      className: 'tier-elevated',
      iconId: 'icon-alert',
    };
  }
  return {
    label: tier || 'Unavailable',
    className: 'tier-unavailable',
    iconId: 'icon-info',
  };
}

/**
 * Title case helper for disease codes
 * @param {string} disease
 * @returns {string}
 */
export function formatDiseaseName(disease) {
  if (!disease) return '';
  const d = String(disease).toLowerCase();
  if (d === 'flu') return 'Influenza';
  if (d === 'covid' || d === 'covid19') return 'COVID-19';
  if (d === 'rsv') return 'RSV';
  return d.charAt(0).toUpperCase() + d.slice(1);
}
