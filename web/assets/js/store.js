/**
 * CareCast Central State Store — APP_FLOW §2.1 & BACKEND_SCHEMA §8
 * Handles route params, meta defaults, and safe localStorage.
 */

const STORAGE_KEY = 'carecast.capacity.v1';

export const CAPACITY_BOUNDS = {
  typical_weekly_admissions: { min: 1.0, max: 1000000.0, default: 100.0 },
  alos_days: { min: 0.5, max: 60.0, default: 5.0 },
  staffed_beds: { min: 1.0, max: 100000.0, default: 250.0 },
  patients_per_nurse: { min: 1.0, max: 50.0, default: 6.0 },
};

class Store {
  constructor() {
    this.state = {
      disease: 'flu',
      jurisdiction: 'US',
      from: null,
      to: null,
      thresholdOverride: null,
      horizon: 1,
      surgePct: 0,
      meta: null,
      capacity: this.loadCapacityAssumptions(),
    };
    this.subscribers = new Set();
  }

  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  notify(changedKeys = []) {
    for (const sub of this.subscribers) {
      try {
        sub(this.state, changedKeys);
      } catch (err) {
        console.error('Store subscriber error:', err);
      }
    }
  }

  setMeta(meta) {
    this.state.meta = meta;
    if (meta && meta.defaults && meta.defaults.capacity) {
      const defs = meta.defaults.capacity;
      if (defs.typical_weekly_admissions !== undefined) {
        CAPACITY_BOUNDS.typical_weekly_admissions.default = defs.typical_weekly_admissions;
      }
      if (defs.alos_days !== undefined) {
        CAPACITY_BOUNDS.alos_days.default = defs.alos_days;
      }
      if (defs.staffed_beds !== undefined) {
        CAPACITY_BOUNDS.staffed_beds.default = defs.staffed_beds;
      }
      if (defs.patients_per_nurse !== undefined) {
        CAPACITY_BOUNDS.patients_per_nurse.default = defs.patients_per_nurse;
      }
      this.state.capacity = this.loadCapacityAssumptions();
    }

    if (meta && Array.isArray(meta.diseases)) {
      const valid = meta.diseases.some((d) => d.code === this.state.disease && d.available !== false);
      if (!valid) {
        const firstAvailable = meta.diseases.find((d) => d.available !== false);
        if (firstAvailable) {
          this.state.disease = firstAvailable.code;
        }
      }
    }

    this.notify(['meta', 'capacity', 'disease']);
  }

  setDisease(disease) {
    if (!disease || typeof disease !== 'string') return;
    const clean = disease.toLowerCase().trim();
    if (this.state.disease !== clean) {
      this.state.disease = clean;
      this.notify(['disease']);
    }
  }

  setThresholdOverride(val) {
    const num = val === null || val === undefined || val === '' ? null : Number(val);
    if (num !== null && (Number.isNaN(num) || num < 0)) return;
    if (this.state.thresholdOverride !== num) {
      this.state.thresholdOverride = num;
      this.notify(['thresholdOverride']);
    }
  }

  setHorizon(h) {
    const num = parseInt(h, 10);
    if (num >= 1 && num <= 4 && this.state.horizon !== num) {
      this.state.horizon = num;
      this.notify(['horizon']);
    }
  }

  setSurgePct(val) {
    const num = Number(val);
    if (!Number.isNaN(num) && num >= -50 && num <= 100) {
      if (this.state.surgePct !== num) {
        this.state.surgePct = num;
        this.notify(['surgePct']);
      }
    }
  }

  setDateRange(from, to) {
    this.state.from = from || null;
    this.state.to = to || null;
    this.notify(['from', 'to']);
  }

  /**
   * Safe localStorage capacity assumptions load
   */
  loadCapacityAssumptions() {
    const defaults = {
      typical_weekly_admissions: CAPACITY_BOUNDS.typical_weekly_admissions.default,
      alos_days: CAPACITY_BOUNDS.alos_days.default,
      staffed_beds: CAPACITY_BOUNDS.staffed_beds.default,
      patients_per_nurse: CAPACITY_BOUNDS.patients_per_nurse.default,
    };

    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaults;
      const parsed = JSON.parse(raw);
      if (typeof parsed !== 'object' || parsed === null) return defaults;

      const result = { ...defaults };
      for (const key of Object.keys(defaults)) {
        if (parsed[key] !== undefined && parsed[key] !== null) {
          const val = Number(parsed[key]);
          const b = CAPACITY_BOUNDS[key];
          if (!Number.isNaN(val) && val >= b.min && val <= b.max) {
            result[key] = val;
          }
        }
      }
      return result;
    } catch (err) {
      console.warn('Could not read capacity assumptions from localStorage, using defaults:', err);
      return defaults;
    }
  }

  /**
   * Safe localStorage capacity assumptions save
   */
  saveCapacityAssumptions(assumptions) {
    const validated = { ...this.state.capacity };
    for (const [key, val] of Object.entries(assumptions)) {
      if (CAPACITY_BOUNDS[key]) {
        const num = Number(val);
        const b = CAPACITY_BOUNDS[key];
        if (!Number.isNaN(num) && num >= b.min && num <= b.max) {
          validated[key] = num;
        }
      }
    }
    this.state.capacity = validated;

    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(validated));
    } catch (err) {
      console.warn('Could not write capacity assumptions to localStorage:', err);
    }
    this.notify(['capacity']);
  }

  resetCapacityToDemo() {
    const defaults = {
      typical_weekly_admissions: CAPACITY_BOUNDS.typical_weekly_admissions.default,
      alos_days: CAPACITY_BOUNDS.alos_days.default,
      staffed_beds: CAPACITY_BOUNDS.staffed_beds.default,
      patients_per_nurse: CAPACITY_BOUNDS.patients_per_nurse.default,
    };
    this.state.capacity = defaults;
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch (err) {
      console.warn('Could not remove capacity assumptions from localStorage:', err);
    }
    this.notify(['capacity']);
  }

  parseHashParams(searchStr) {
    if (!searchStr) return;
    const params = new URLSearchParams(searchStr);

    if (params.has('disease')) {
      const d = params.get('disease');
      if (d && typeof d === 'string') {
        const clean = d.toLowerCase().trim();
        if (clean.length > 0 && clean.length <= 32) {
          this.state.disease = clean;
        }
      }
    }

    if (params.has('threshold')) {
      const t = Number(params.get('threshold'));
      if (!Number.isNaN(t) && t >= 0 && t <= 1e9) {
        this.state.thresholdOverride = t;
      }
    }

    if (params.has('h')) {
      const h = parseInt(params.get('h'), 10);
      if (h >= 1 && h <= 4) {
        this.state.horizon = h;
      }
    }

    if (params.has('surge')) {
      const s = Number(params.get('surge'));
      if (!Number.isNaN(s) && s >= -50 && s <= 100) {
        this.state.surgePct = s;
      }
    }

    const isoRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (params.has('from') && isoRegex.test(params.get('from'))) {
      this.state.from = params.get('from');
    }
    if (params.has('to') && isoRegex.test(params.get('to'))) {
      this.state.to = params.get('to');
    }
  }
}

export const store = new Store();
