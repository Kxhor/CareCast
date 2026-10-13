/**
 * CareCast Main Application Entry Point
 * Bootstraps store, meta fetching, top bar controls, and accessible router.
 */

import { api } from './api.js';
import { store } from './store.js';
import { Router } from './router.js';
import { el, createAlertBanner, createIcon } from './components.js';
import { formatDate, formatDiseaseName } from './format.js';

async function initApp() {
  const mainContainer = document.getElementById('main');
  const breadcrumbContainer = document.getElementById('breadcrumb-current');
  const announcerContainer = document.getElementById('sr-announcer');
  const diseaseSelect = document.getElementById('topbar-disease-select');
  const dataAsOfEl = document.getElementById('topbar-data-as-of');
  const bannersContainer = document.getElementById('global-banners');
  const sidebar = document.getElementById('sidebar');
  const menuToggle = document.getElementById('menu-toggle');

  // Mobile menu drawer toggle
  if (menuToggle && sidebar) {
    menuToggle.addEventListener('click', () => {
      const isOpen = sidebar.classList.toggle('open');
      menuToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && sidebar.classList.contains('open')) {
        sidebar.classList.remove('open');
        menuToggle.setAttribute('aria-expanded', 'false');
        menuToggle.focus();
      }
    });
  }

  // First load sequence: GET /api/v1/meta (APP_FLOW §2.3)
  const metaRes = await api.getMeta();

  if (!metaRes.ok) {
    // Full-page Data Unavailable State (APP_FLOW §5.1 / J5)
    while (mainContainer.firstChild) {
      mainContainer.removeChild(mainContainer.firstChild);
    }

    const unavailDiv = el('div', { className: 'card error-block col-12' });
    unavailDiv.appendChild(createIcon('icon-alert', 'empty-icon'));
    unavailDiv.appendChild(el('h1', { className: 'card-title', textContent: 'Data Not Loaded' }));
    unavailDiv.appendChild(
      el('p', {
        className: 'explain-text',
        textContent: 'The forecast database has not been built or is currently unavailable.',
      })
    );

    const pre = el('pre', { className: 'card' });
    pre.appendChild(el('code', { textContent: 'python -m carecast.pipeline rebuild' }));
    unavailDiv.appendChild(pre);

    const retryBtn = el('button', {
      type: 'button',
      className: 'btn-primary',
      textContent: 'Retry',
      onclick: () => window.location.reload(),
    });
    unavailDiv.appendChild(retryBtn);

    mainContainer.appendChild(unavailDiv);
    return;
  }

  const meta = metaRes.data;
  store.setMeta(meta);

  // Sidebar collapse toggle (rail mode on desktop)
  const collapseBtn = document.getElementById('sidebar-collapse-btn');
  if (collapseBtn && sidebar) {
    collapseBtn.addEventListener('click', () => {
      sidebar.classList.toggle('rail');
    });
  }

  // Populate data-as-of chip
  const dateTextEl = document.getElementById('topbar-date-text');
  if (dateTextEl && meta.data_as_of) {
    dateTextEl.textContent = `Data as of: ${formatDate(meta.data_as_of)}`;
  } else if (dataAsOfEl && meta.data_as_of) {
    dataAsOfEl.textContent = `Data as of: ${formatDate(meta.data_as_of)}`;
  }

  // Populate breadcrumb range text
  const breadcrumbRangeEl = document.getElementById('breadcrumb-range-text');
  if (breadcrumbRangeEl && meta.data_as_of) {
    breadcrumbRangeEl.textContent = `Surveillance to ${formatDate(meta.data_as_of)}`;
  }

  // Populate disease select
  if (diseaseSelect && Array.isArray(meta.diseases)) {
    while (diseaseSelect.firstChild) {
      diseaseSelect.removeChild(diseaseSelect.firstChild);
    }

    meta.diseases.forEach((d) => {
      const opt = el('option', {
        value: d.code,
        textContent: formatDiseaseName(d.code),
        selected: d.code === store.state.disease,
        disabled: d.available === false,
      });
      diseaseSelect.appendChild(opt);
    });

    diseaseSelect.addEventListener('change', (e) => {
      const val = e.target.value;
      store.setDisease(val);
      const hash = window.location.hash || '#/overview';
      const [path] = hash.split('?');
      window.location.hash = `${path}?disease=${val}`;
    });
  }

  // Check for stale data or quality warnings
  if (bannersContainer) {
    if (meta.stale) {
      bannersContainer.appendChild(
        createAlertBanner({
          type: 'warning',
          text: `Data last updated ${formatDate(meta.data_as_of)}. Newer public CDC surveillance reports may exist.`,
        })
      );
    }
  }

  // Initialize Router
  const router = new Router(mainContainer, breadcrumbContainer, announcerContainer);
  router.init();

  // Listen for external store disease changes
  store.subscribe((state, changedKeys) => {
    if (changedKeys.includes('disease') && diseaseSelect) {
      diseaseSelect.value = state.disease;
    }
  });
}

document.addEventListener('DOMContentLoaded', initApp);
