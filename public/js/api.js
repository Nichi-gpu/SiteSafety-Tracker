/**
 * SiteSafety Tracker — API Client
 * Connects frontend UI to the Flask SQLite backend.
 * Works seamlessly whether loaded via http://localhost:8000, VS Code Live Server, or file protocol.
 */
const API = (() => {
  // Determine API root URL automatically
  const isFlaskPort = window.location.port === '8000';
  const BASE = isFlaskPort ? '/api' : 'http://127.0.0.1:8000/api';

  let _isOnline = null;

  async function request(endpoint, options = {}) {
    const url = `${BASE}${endpoint}`;
    const config = {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      },
      ...options
    };

    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body);
    }

    try {
      const res = await fetch(url, config);
      _isOnline = true;

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText || `HTTP ${res.status}` }));
        throw new Error(err.error || `HTTP ${res.status}`);
      }

      const ct = res.headers.get('content-type') || '';
      if (ct.includes('text/csv')) return res.text();
      return res.json();
    } catch (err) {
      if (err.name === 'TypeError' || err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        _isOnline = false;
        throw new Error('Cannot connect to backend server. Make sure "python server/app.py" is running in your terminal.');
      }
      throw err;
    }
  }

  // ── Auth ──────────────────────────────────────────────
  const auth = {
    async login(identifier, password) {
      return request('/auth/login', {
        method: 'POST',
        body: { email: identifier, password }
      });
    },

    async signup({ company, username, email, password, role }) {
      return request('/auth/signup', {
        method: 'POST',
        body: { company, username, email, password, role }
      });
    },

    async logout() {
      return request('/auth/logout', { method: 'POST' });
    },

    async me() {
      return request('/auth/me');
    }
  };

  // ── Admin & DB Inspection ─────────────────────────────
  const admin = {
    async getUsers() {
      return request('/admin/users');
    },

    async getLoginLogs(limit = 100) {
      return request(`/admin/login-logs?limit=${limit}`);
    }
  };

  // ── Hazards ───────────────────────────────────────────
  const hazards = {
    async list(filters = {}) {
      const params = new URLSearchParams();
      if (filters.status) params.set('status', filters.status);
      if (filters.urgency) params.set('urgency', filters.urgency);
      if (filters.search) params.set('search', filters.search);
      if (filters.page) params.set('page', filters.page);
      if (filters.limit) params.set('limit', filters.limit);
      const qs = params.toString();
      return request(`/hazards${qs ? '?' + qs : ''}`);
    },

    async get(ticket) {
      return request(`/hazards/${encodeURIComponent(ticket)}`);
    },

    async create(data) {
      return request('/hazards', { method: 'POST', body: data });
    },

    async resolve(ticket) {
      return request(`/hazards/${encodeURIComponent(ticket)}/resolve`, { method: 'PATCH' });
    },

    async exportCSV() {
      return request('/hazards/export/csv');
    }
  };

  // ── Inspections ───────────────────────────────────────
  const inspections = {
    async list(page = 1, limit = 50) {
      return request(`/inspections?page=${page}&limit=${limit}`);
    },

    async create(data) {
      return request('/inspections', { method: 'POST', body: data });
    },

    async delete(id) {
      return request(`/inspections/${id}`, { method: 'DELETE' });
    }
  };

  // ── Notifications ─────────────────────────────────────
  const notifications = {
    async list() {
      return request('/notifications');
    },

    async create(title) {
      return request('/notifications', { method: 'POST', body: { title } });
    },

    async clear() {
      return request('/notifications/clear', { method: 'POST' });
    }
  };

  return {
    BASE,
    isOnline: () => _isOnline,
    auth,
    admin,
    hazards,
    inspections,
    notifications
  };
})();

// Export globally for browser
if (typeof window !== 'undefined') {
  window.API = API;
}
