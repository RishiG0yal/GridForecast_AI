import { useQuery } from '@tanstack/react-query';
import {
  fetchDashboardOverview, fetchDemandChart, fetchAreaBreakdown,
  fetchWeatherCorrelation, fetchCapacityUtilization, fetchModelPerformance,
  fetchRiskAlerts, fetchRiskSummary, fetchRiskAnalysis,
  getTrainingStatus, getModelComparison, fetchPredictions,
  getDataStatus, fetchConsumerBreakdown, fetchLoadBalancing,
  fetchSolarPrediction, fetchLiveSnapshot, fetchLiveHistory,
  fetchPredictHorizons
} from '../api/endpoints';

export const useDashboardOverview = () =>
  useQuery({ queryKey: ['dashboard-overview'], queryFn: fetchDashboardOverview, refetchInterval: 60000 });

export const useDemandChart = (hours = 48) =>
  useQuery({ queryKey: ['demand-chart', hours], queryFn: () => fetchDemandChart(hours), refetchInterval: 60000 });

export const useAreaBreakdown = () =>
  useQuery({ queryKey: ['area-breakdown'], queryFn: fetchAreaBreakdown, refetchInterval: 120000 });

export const useWeatherCorrelation = (hours = 168) =>
  useQuery({ queryKey: ['weather-correlation', hours], queryFn: () => fetchWeatherCorrelation(hours) });

export const useCapacityUtilization = () =>
  useQuery({ queryKey: ['capacity-utilization'], queryFn: fetchCapacityUtilization, refetchInterval: 60000 });

export const useModelPerformance = () =>
  useQuery({ queryKey: ['model-performance'], queryFn: fetchModelPerformance });

export const useRiskAlerts = (refreshInterval = 30000) =>
  useQuery({ queryKey: ['risk-alerts'], queryFn: fetchRiskAlerts, refetchInterval: refreshInterval });

export const useRiskSummary = () =>
  useQuery({ queryKey: ['risk-summary'], queryFn: fetchRiskSummary, refetchInterval: 30000 });

export const useRiskAnalysis = () =>
  useQuery({ queryKey: ['risk-analysis'], queryFn: fetchRiskAnalysis, refetchInterval: 60000 });

export const useTrainingStatus = (enabled = true) =>
  useQuery({ queryKey: ['training-status'], queryFn: getTrainingStatus, refetchInterval: enabled ? 3000 : false });

export const useModelComparison = () =>
  useQuery({ queryKey: ['model-comparison'], queryFn: getModelComparison });

export const usePredictions = (hours = 48, lat = 28.6139, lon = 77.209) =>
  useQuery({ queryKey: ['predictions', hours, lat, lon], queryFn: () => fetchPredictions(hours, lat, lon) });

export const usePredictHorizons = () =>
  useQuery({ queryKey: ['horizons'], queryFn: () => fetchPredictHorizons(), refetchInterval: 300000, retry: 1 });

export const useDataStatus = () =>
  useQuery({ queryKey: ['data-status'], queryFn: getDataStatus, refetchInterval: 5000 });

export const useConsumerBreakdown = () =>
  useQuery({ queryKey: ['consumer-breakdown'], queryFn: fetchConsumerBreakdown, refetchInterval: 120000 });

export const useLoadBalancing = () =>
  useQuery({ queryKey: ['load-balancing'], queryFn: fetchLoadBalancing, refetchInterval: 60000 });

export const useSolarPrediction = () =>
  useQuery({ queryKey: ['solar-prediction'], queryFn: fetchSolarPrediction, refetchInterval: 300000 });

export const useLiveSnapshot = () =>
  useQuery({ queryKey: ['live-snapshot'], queryFn: fetchLiveSnapshot, refetchInterval: 60000 });

export const useLiveHistory = (days = 7) =>
  useQuery({ queryKey: ['live-history', days], queryFn: () => fetchLiveHistory(days), refetchInterval: 60000 });
