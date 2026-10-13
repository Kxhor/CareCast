/**
 * CareCast API Client — TRD §6 & BACKEND_SCHEMA §8
 * Pure fetch wrapper with timeout, request-id tracking, and generic error mapping.
 */

const API_BASE = '/api/v1';
const DEFAULT_TIMEOUT_MS = 10000;

class ApiClient {
  /**
   * Helper to perform fetch with timeout and error envelope extraction
   * @param {string} endpoint
   * @param {RequestInit} [options]
   * @returns {Promise<{ ok: boolean, data?: any, error?: { message: string, status: number, requestId?: string, retryAfter?: number } }>}
   */
  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeoutMs || DEFAULT_TIMEOUT_MS);

    try {
      const headers = {
        Accept: 'application/json',
        ...(options.headers || {}),
      };

      if (options.body && typeof options.body === 'object') {
        headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(options.body);
      }

      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      const requestId = response.headers.get('x-request-id') || response.headers.get('X-Request-ID') || undefined;
      const retryAfterHeader = response.headers.get('retry-after') || response.headers.get('Retry-After');
      const retryAfter = retryAfterHeader ? parseInt(retryAfterHeader, 10) : undefined;

      let payload = null;
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        try {
          payload = await response.json();
        } catch {
          payload = null;
        }
      }

      if (!response.ok) {
        let message = 'We could not load this section. Please try again.';
        if (response.status === 429) {
          message = retryAfter
            ? `Too many requests. Try again in ${retryAfter} seconds.`
            : 'Too many requests. Please wait a moment and try again.';
        } else if (response.status === 503) {
          message = 'The forecast database has not been built.';
        } else if (payload && payload.error && payload.error.message) {
          message = payload.error.message;
        } else if (payload && payload.detail) {
          message = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail);
        }

        return {
          ok: false,
          error: {
            message,
            status: response.status,
            requestId,
            retryAfter,
          },
        };
      }

      return {
        ok: true,
        data: payload,
      };
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        return {
          ok: false,
          error: {
            message: 'The server did not respond. Check your connection and retry.',
            status: 408,
          },
        };
      }
      return {
        ok: false,
        error: {
          message: 'The server did not respond. Check your connection and retry.',
          status: 0,
        },
      };
    }
  }

  // E1: Health
  getHealth() {
    return this.request('/health');
  }

  // E2: Meta
  getMeta() {
    return this.request('/meta');
  }

  // E3: Summary
  getSummary({ disease = 'flu', jurisdiction = 'US', threshold = null } = {}) {
    const params = new URLSearchParams({ disease, jurisdiction });
    if (threshold !== null && threshold !== undefined) {
      params.append('threshold', String(threshold));
    }
    return this.request(`/summary?${params.toString()}`);
  }

  // E4: Observations
  getObservations({ disease = 'flu', jurisdiction = 'US', from = null, to = null } = {}) {
    const params = new URLSearchParams({ disease, jurisdiction });
    if (from) params.append('from', from);
    if (to) params.append('to', to);
    return this.request(`/observations?${params.toString()}`);
  }

  // E5: Forecast
  getForecast({ disease = 'flu', jurisdiction = 'US', threshold = null } = {}) {
    const params = new URLSearchParams({ disease, jurisdiction });
    if (threshold !== null && threshold !== undefined) {
      params.append('threshold', String(threshold));
    }
    return this.request(`/forecast?${params.toString()}`);
  }

  // E6: Evaluation
  getEvaluation({ disease = 'flu', jurisdiction = 'US', horizon = null } = {}) {
    const params = new URLSearchParams({ disease, jurisdiction });
    if (horizon !== null && horizon !== undefined) {
      params.append('horizon', String(horizon));
    }
    return this.request(`/evaluation?${params.toString()}`);
  }

  // E7: Explain
  getExplain({ disease = 'flu', jurisdiction = 'US', horizon = 1 } = {}) {
    const params = new URLSearchParams({ disease, jurisdiction, horizon: String(horizon) });
    return this.request(`/explain?${params.toString()}`);
  }

  // E8: Scenario
  postScenario({ disease = 'flu', jurisdiction = 'US', surgePct = 0, threshold = null, capacity = null } = {}) {
    const body = {
      disease,
      jurisdiction,
      surge_pct: surgePct,
    };
    if (threshold !== null && threshold !== undefined) {
      body.threshold = threshold;
    }
    if (capacity) {
      body.capacity = capacity;
    }
    return this.request('/scenario', {
      method: 'POST',
      body,
    });
  }
}

export const api = new ApiClient();
