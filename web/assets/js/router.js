/**
 * Hash Router for CareCast — APP_FLOW §1 & WCAG A11Y-06
 * Focus management, document.title updates, live announcements, and route cleanup.
 */

import { store } from './store.js';
import { renderOverview } from './views/overview.js';
import { renderForecast } from './views/forecast.js';
import { renderPerformance } from './views/performance.js';
import { renderExplain } from './views/explain.js';
import { renderScenario } from './views/scenario.js';
import { renderDataLimitations } from './views/data.js';

const ROUTES = {
  '/overview': {
    title: 'Overview · CareCast',
    name: 'Overview',
    render: renderOverview,
  },
  '/forecast': {
    title: 'Forecast · CareCast',
    name: 'Forecast',
    render: renderForecast,
  },
  '/performance': {
    title: 'Model Performance · CareCast',
    name: 'Model Performance',
    render: renderPerformance,
  },
  '/explain': {
    title: 'Explainability · CareCast',
    name: 'Explainability',
    render: renderExplain,
  },
  '/scenario': {
    title: 'Scenario Planner · CareCast',
    name: 'Scenario Planner',
    render: renderScenario,
  },
  '/data': {
    title: 'Data & Limitations · CareCast',
    name: 'Data & Limitations',
    render: renderDataLimitations,
  },
};

class Router {
  constructor(mainContainer, breadcrumbContainer, announcerContainer) {
    this.main = mainContainer;
    this.breadcrumb = breadcrumbContainer;
    this.announcer = announcerContainer;
    this.currentCleanup = null;
    this.activeRoute = null;

    window.addEventListener('hashchange', () => this.handleHashChange());
  }

  init() {
    this.handleHashChange();
  }

  handleHashChange() {
    const rawHash = window.location.hash || '#/overview';
    const cleanHash = rawHash.startsWith('#') ? rawHash.slice(1) : rawHash;
    const [pathPart, queryPart] = cleanHash.split('?');

    // Parse and store query parameters
    store.parseHashParams(queryPart);

    const path = pathPart.startsWith('/') ? pathPart : `/${pathPart}`;
    const route = ROUTES[path];

    if (!route) {
      console.warn('Unknown route, redirecting to overview:', path);
      window.location.hash = '#/overview';
      return;
    }

    this.navigate(path, route);
  }

  navigate(path, route) {
    // 1. Cleanup previous view
    if (this.currentCleanup && typeof this.currentCleanup === 'function') {
      try {
        this.currentCleanup();
      } catch (err) {
        console.error('Error during view cleanup:', err);
      }
      this.currentCleanup = null;
    }

    this.activeRoute = path;

    // 2. Update document.title
    document.title = route.title;

    // 3. Update breadcrumb
    if (this.breadcrumb) {
      this.breadcrumb.textContent = route.name;
    }

    // 4. Update sidebar active state
    this.updateNavItems(path);

    // 5. Announce to screen readers
    if (this.announcer) {
      this.announcer.textContent = `Navigated to ${route.name}`;
    }

    // 6. Render new view
    try {
      this.currentCleanup = route.render(this.main);
    } catch (err) {
      console.error('Error rendering route:', err);
    }

    // 7. Move focus to main heading or container (WCAG A11Y-06)
    const h1 = this.main.querySelector('h1');
    if (h1) {
      h1.setAttribute('tabindex', '-1');
      h1.focus();
    } else {
      this.main.setAttribute('tabindex', '-1');
      this.main.focus();
    }
  }

  updateNavItems(path) {
    const navLinks = document.querySelectorAll('.nav-item');
    navLinks.forEach((link) => {
      const href = link.getAttribute('href') || '';
      const linkPath = href.replace(/^#/, '').split('?')[0];
      if (linkPath === path) {
        link.classList.add('active');
        link.setAttribute('aria-current', 'page');
      } else {
        link.classList.remove('active');
        link.removeAttribute('aria-current');
      }
    });
  }
}

export { Router };
