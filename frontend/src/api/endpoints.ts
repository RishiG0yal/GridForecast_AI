import client from './client';

export const fetchDashboardOverview = () =>
  client.get('/api/dashboard/overview').then(r => r.data);

export const fetchDemandChart = (hours = 48) =>
  client.get('/api/dashboard/demand-chart', { params: { hours } }).then(r => r.data);

export const fetchAreaBreakdown = () =>
  client.get('/api/dashboard/area-breakdown').then(r => r.data);

export const fetchWeatherCorrelation = (hours = 168) =>
  client.get('/api/dashboard/weather-correlation', { params: { hours } }).then(r => r.data);

export const fetchCapacityUtilization = () =>
  client.get('/api/dashboard/capacity-utilization').then(r => r.data);

export const fetchModelPerformance = () =>
  client.get('/api/dashboard/model-performance').then(r => r.data);

export const fetchPredictions = (hours = 48, lat = 28.6139, lon = 77.209) =>
  client.get('/api/predict', { params: { hours, lat, lon } }).then(r => r.data);

export const fetchPredictHorizons = (lat = 28.6139, lon = 77.209) =>
  client.get('/api/predict/horizons', { params: { lat, lon } }).then(r => r.data);

export const fetchRiskAnalysis = () =>
  client.get('/api/risk/analysis').then(r => r.data);

export const fetchRiskAlerts = () =>
  client.get('/api/risk/alerts').then(r => r.data);

export const fetchRiskSummary = () =>
  client.get('/api/risk/summary').then(r => r.data);

export const fetchConsumerBreakdown = () =>
  client.get('/api/areas/consumer-breakdown').then(r => r.data);

export const fetchLoadBalancing = () =>
  client.get('/api/areas/load-balancing').then(r => r.data);

export const fetchSolarPrediction = () =>
  client.get('/api/solar/prediction').then(r => r.data);

export const fetchLiveSnapshot = () =>
  client.get('/api/live/snapshot').then(r => r.data);

export const fetchLiveHistory = (days = 7) =>
  client.get('/api/live/history', { params: { days } }).then(r => r.data);

export const startTraining = (config: any) =>
  client.post('/api/train', config).then(r => r.data);

export const getTrainingStatus = () =>
  client.get('/api/train/status').then(r => r.data);

export const getModelComparison = () =>
  client.get('/api/models/comparison').then(r => r.data);

export const getDataStatus = () =>
  client.get('/api/data/status').then(r => r.data);

export const triggerScrapeNow = () =>
  client.post('/api/live/scrape-now').then(r => r.data);

export const buildDataset = (days = 365) =>
  client.post('/api/live/build-dataset', null, { params: { days } }).then(r => r.data);

export const uploadLoadData = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return client.post('/api/data/upload/load', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(r => r.data);
};

export const uploadCapacityData = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return client.post('/api/data/upload/capacity', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(r => r.data);
};
