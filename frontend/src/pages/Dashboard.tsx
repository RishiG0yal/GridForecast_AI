import React from 'react';
import { Zap, TrendingUp, Gauge, AlertTriangle } from 'lucide-react';
import StatCard from '../components/cards/StatCard';
import HorizonCards from '../components/cards/HorizonCards';
import DemandForecastChart from '../components/charts/DemandForecastChart';
import WeatherDemandChart from '../components/charts/WeatherDemandChart';
import ModelComparisonChart from '../components/charts/ModelComparisonChart';
import ConsumerBreakdownChart from '../components/charts/ConsumerBreakdownChart';
import RiskAlertBanner from '../components/risk/RiskAlertBanner';
import LiveDataPanel from '../components/live/LiveDataPanel';
import {
  useDashboardOverview, useDemandChart,
  useWeatherCorrelation, useModelPerformance, useRiskAlerts
} from '../hooks/useApi';

export default function Dashboard() {
  const { data: overview, isLoading: ovLoading } = useDashboardOverview();
  const { data: demandChart } = useDemandChart(72);
  const { data: weatherData } = useWeatherCorrelation(168);
  const { data: modelsData } = useModelPerformance();
  const { data: alertsData } = useRiskAlerts();
  const alerts = alertsData?.alerts || [];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white">System Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">Real-time Delhi electricity demand monitoring and forecasting</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Current Demand" value={overview?.current_demand_mw != null ? overview.current_demand_mw.toFixed(0) : '—'} unit="MW" icon={<Zap size={18} />} loading={ovLoading} riskLevel={overview?.risk_level} />
        <StatCard title="Peak Forecast (48h)" value={overview?.peak_forecast_mw != null ? overview.peak_forecast_mw.toFixed(0) : '—'} unit="MW" icon={<TrendingUp size={18} />} loading={ovLoading} />
        <StatCard title="Capacity Utilization" value={overview?.capacity_utilization_pct != null ? overview.capacity_utilization_pct.toFixed(1) : '—'} unit="%" icon={<Gauge size={18} />} loading={ovLoading} riskLevel={overview?.risk_level} />
        <StatCard title="Active Risk Alerts" value={overview?.active_alerts ?? '—'} icon={<AlertTriangle size={18} />} loading={ovLoading} riskLevel={alerts.length > 0 ? alerts[0]?.risk_level : 'normal'} subtitle={`Best model: ${overview?.best_model || '—'}`} />
      </div>

      {alerts.length > 0 && <RiskAlertBanner alerts={alerts} />}

      <HorizonCards />

      <div className="card">
        <p className="card-header">Actual vs Predicted Demand (MW)</p>
        {demandChart ? (
          <DemandForecastChart actual={demandChart.actual || []} predicted={demandChart.predicted || []} />
        ) : (
          <div className="h-[320px] flex items-center justify-center text-gray-500 text-sm">
            {ovLoading ? 'Loading...' : 'Training in background... will populate shortly'}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 card">
          <p className="card-header">Weather vs Demand Correlation</p>
          {weatherData?.data?.length > 0 ? (
            <WeatherDemandChart data={weatherData.data} />
          ) : (
            <div className="h-60 flex items-center justify-center text-gray-500 text-sm">No weather data</div>
          )}
        </div>
        <LiveDataPanel />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="card">
          <p className="card-header">Consumer Category Breakdown by DISCOM</p>
          <ConsumerBreakdownChart />
        </div>
        <div className="card">
          <p className="card-header">Model Performance Comparison</p>
          {modelsData?.models?.length > 0 ? (
            <ModelComparisonChart models={modelsData.models} bestModel={modelsData.best_model} />
          ) : (
            <div className="h-56 flex items-center justify-center text-gray-500 text-sm">Training models...</div>
          )}
        </div>
      </div>
    </div>
  );
}
