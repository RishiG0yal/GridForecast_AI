import React from 'react';
import CapacityUtilizationChart from '../components/charts/CapacityUtilizationChart';
import RiskAlertBanner from '../components/risk/RiskAlertBanner';
import { useRiskAlerts, useRiskSummary, useCapacityUtilization } from '../hooks/useApi';
import { getRiskColor, getRiskLabel, getRiskBgColor, formatMW, formatPercent, formatDatetime } from '../utils/formatters';
import clsx from 'clsx';

export default function RiskAnalysis() {
  const { data: alertsData } = useRiskAlerts(15000);
  const { data: summary } = useRiskSummary();
  const { data: capData } = useCapacityUtilization();

  const alerts = alertsData?.alerts || [];
  const areas = capData?.areas || [];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white">Risk Analysis</h1>
        <p className="text-sm text-gray-500 mt-0.5">Grid capacity vs demand risk assessment</p>
      </div>

      {alerts.length > 0 && <RiskAlertBanner alerts={alerts} />}

      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'Peak Utilization', value: formatPercent(summary.peak_utilization_pct) },
            { label: 'Avg Utilization', value: formatPercent(summary.average_utilization_pct) },
            { label: 'Hours Capacity Exceeded', value: summary.hours_capacity_exceeded },
            { label: 'Hours Critical', value: summary.hours_critical },
          ].map(({ label, value }) => (
            <div key={label} className="card">
              <p className="card-header">{label}</p>
              <p className="text-xl font-bold text-white">{value}</p>
            </div>
          ))}
        </div>
      )}

      {summary?.counts_by_level && (
        <div className="card">
          <p className="card-header">Risk Distribution (48h Forecast)</p>
          <div className="flex flex-wrap gap-3">
            {Object.entries(summary.counts_by_level).map(([level, count]) => (
              <div key={level} className={clsx('flex items-center gap-2 px-3 py-2 rounded-lg border', getRiskBgColor(level))}>
                <span className={clsx('text-sm font-bold', getRiskColor(level))}>{count as number}</span>
                <span className="text-xs text-gray-400">{getRiskLabel(level)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {areas.length > 0 && (
        <div className="card">
          <p className="card-header">Capacity Utilization by Area</p>
          <CapacityUtilizationChart areas={areas} />
        </div>
      )}

      {alerts.length > 0 && (
        <div className="card">
          <p className="card-header">High-Risk Hours Detail</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-gray-400">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left py-2 pr-4">Time</th>
                  <th className="text-left py-2 pr-4">Area</th>
                  <th className="text-left py-2 pr-4">Risk Level</th>
                  <th className="text-right py-2 px-4">Demand</th>
                  <th className="text-right py-2 px-4">Capacity</th>
                  <th className="text-right py-2 pl-4">Utilization</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((a: any, i: number) => (
                  <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-1.5 pr-4">{formatDatetime(a.timestamp)}</td>
                    <td className="py-1.5 pr-4">{a.area}</td>
                    <td className="py-1.5 pr-4">
                      <span className={clsx('font-medium', getRiskColor(a.risk_level))}>
                        {getRiskLabel(a.risk_level)}
                      </span>
                    </td>
                    <td className="text-right py-1.5 px-4 text-white">{formatMW(a.predicted_demand)}</td>
                    <td className="text-right py-1.5 px-4">{formatMW(a.available_capacity)}</td>
                    <td className={clsx('text-right py-1.5 pl-4 font-medium', getRiskColor(a.risk_level))}>
                      {formatPercent(a.utilization_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!alerts.length && !summary && (
        <div className="card flex items-center justify-center h-48">
          <p className="text-gray-500 text-sm">Train models to generate risk analysis</p>
        </div>
      )}
    </div>
  );
}
