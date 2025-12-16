import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Training endpoints
export const training = {
  startRun: (startDate, endDate, holdYears = [2, 5]) =>
    api.post('/training/run', {
      start_date: startDate,
      end_date: endDate,
      hold_years: holdYears,
    }),

  getStatus: (runId) => api.get(`/training/${runId}/status`),

  getResults: (runId) => api.get(`/training/${runId}/results`),

  listRuns: () => api.get('/training/runs'),

  deleteRun: (runId) => api.delete(`/training/${runId}`),

  evaluate: (picks, weights, threshold, holdYears = 2) =>
    api.post('/training/evaluate', {
      picks,
      weights,
      threshold,
      hold_years: holdYears,
    }),

  getDefaults: () => api.get('/training/defaults'),
};

// Analysis endpoints
export const analysis = {
  startRun: (startDate, endDate, holdYears, weights, threshold, scoringModelId = null) =>
    api.post('/analysis/run', {
      start_date: startDate,
      end_date: endDate,
      hold_years: holdYears,
      weights,
      threshold,
      scoring_model_id: scoringModelId,
    }),

  getStatus: (runId) => api.get(`/analysis/${runId}/status`),

  getResults: (runId) => api.get(`/analysis/${runId}/results`),

  exportCsv: (runId) => `${API_BASE_URL}/analysis/${runId}/export`,
};

// Models endpoints
export const models = {
  list: () => api.get('/models/'),

  create: (name, weights, threshold, trainingRunId = null, avgReturn = null, winRate = null) =>
    api.post('/models/', {
      name,
      weights,
      threshold,
      training_run_id: trainingRunId,
      avg_return: avgReturn,
      win_rate: winRate,
    }),

  get: (modelId) => api.get(`/models/${modelId}`),

  delete: (modelId) => api.delete(`/models/${modelId}`),

  getDefaultWeights: () => api.get('/models/defaults/weights'),
};

// Data endpoints
export const data = {
  getSp500Tickers: (forDate = null) =>
    api.get('/data/sp500/tickers', { params: forDate ? { for_date: forDate } : {} }),

  getDateRange: () => api.get('/data/sp500/date-range'),

  getMetadata: (ticker = null) =>
    api.get('/data/metadata', { params: ticker ? { ticker } : {} }),

  getIndustries: () => api.get('/data/industries'),
};

export default api;
