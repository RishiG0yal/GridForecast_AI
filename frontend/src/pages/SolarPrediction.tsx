import React from 'react';
import { useSolarPrediction } from '../hooks/useApi';
import { Sun, Zap, Home, TrendingDown } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { formatMW, formatPercent } from '../utils/formatters';
import clsx from 'clsx';



export default function SolarPrediction() {
  const { data, isLoading } = useSolarPrediction();// original:

  const sys = data?.system_summary;
  const weather = data?.weather_conditions;

  const chartData = data?.areas?.map((a: any) => ({
    name: a.discom,
    'Gross Demand': a.avg_demand_mw,
    'Solar Generation': a.current_solar_generation_mw,
    'Residual (Grid)': a.residual_demand_mw,
  })) || [];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Sun size={22} className="text-yellow-400" />
          Solar Power Prediction
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Area-wise rooftop solar generation, units needed and residual grid demand
        </p>
      </div>

      {weather && (
        <div className="flex items-center gap-4 px-4 py-2.5 bg-yellow-900/20 border border-yellow-800 rounded-xl text-xs text-yellow-300">
          <Sun size={14} />
          <span>Solar radiation: <strong>{weather.solar_radiation_wm2} W/m²</strong></span>
          <span>Cloud cover: <strong>{weather.cloud_cover_pct}%</strong></span>
          <span className="text-gray-500 ml-auto">Live from Open-Meteo</span>
        </div>
      )}

      {sys && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'Total Demand', value: formatMW(sys.total_demand_mw), icon: <Zap size={16} />, color: 'text-sky-400' },
            { label: 'Solar Generation', value: formatMW(sys.total_solar_generation_mw), icon: <Sun size={16} />, color: 'text-yellow-400' },
            { label: 'Solar Coverage', value: formatPercent(sys.solar_coverage_pct), icon: <TrendingDown size={16} />, color: 'text-green-400' },
            { label: 'Residual (needs grid)', value: formatMW(sys.total_residual_demand_mw), icon: <Home size={16} />, color: 'text-orange-400' },
          ].map(({ label, value, icon, color }) => (
            <div key={label} className="card">
              <div className="flex items-center gap-2 mb-1">
                <span className={color}>{icon}</span>
                <p className="card-header mb-0">{label}</p>
              </div>
              <p className={clsx('text-xl font-bold', color)}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {sys && (
        <div className="card">
          <p className="card-header">Rooftop Solar Potential</p>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex-1 bg-gray-800 rounded-full h-4 overflow-hidden">
              <div
                className="h-4 bg-yellow-500 rounded-full transition-all flex items-center justify-end pr-2"
                style={{ width: `${Math.min(sys.solar_coverage_pct, 100)}%` }}
              >
                <span className="text-xs font-bold text-gray-900">{sys.solar_coverage_pct}%</span>
              </div>
            </div>
            <span className="text-xs text-gray-400 shrink-0">
              {formatMW(sys.total_solar_generation_mw)} of {formatMW(sys.total_demand_mw)}
            </span>
          </div>
          <div className="flex gap-6 mt-3 text-xs text-gray-400">
            <div>Total potential: <span className="text-yellow-400 font-medium">{formatMW(sys.total_rooftop_potential_mw)}</span></div>
            <div>Currently generating: <span className="text-green-400 font-medium">{formatMW(sys.total_solar_generation_mw)}</span></div>
            <div>Still needs grid: <span className="text-orange-400 font-medium">{formatMW(sys.total_residual_demand_mw)}</span></div>
          </div>
        </div>
      )}

      {chartData.length > 0 && (
        <div className="card">
          <p className="card-header">Demand vs Solar vs Residual by DISCOM</p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} unit=" MW" width={65} />
              <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, fontSize: 11 }} labelStyle={{ color: '#e5e7eb' }} />
              <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="Solar Generation" fill="#fbbf24" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Residual (Grid)" fill="#f97316" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {data?.areas && (
        <div className="card">
          <p className="card-header">DISCOM-wise Solar Breakdown</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-gray-400">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left py-2 pr-3">DISCOM</th>
                  <th className="text-right py-2 px-2">Avg Demand</th>
                  <th className="text-right py-2 px-2">Solar Potential</th>
                  <th className="text-right py-2 px-2">Current Gen</th>
                  <th className="text-right py-2 px-2">Coverage</th>
                  <th className="text-right py-2 px-2">Residual</th>
                  <th className="text-right py-2 px-2">Units/Rooftop/Day</th>
                  <th className="text-right py-2 pl-2">Extra Rooftops Needed</th>
                </tr>
              </thead>
              <tbody>
                {data.areas.map((a: any) => (
                  <tr key={a.discom} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-2 pr-3">
                      <div className="font-medium text-gray-200">{a.discom}</div>
                      <div className="text-gray-600 text-xs">{a.area_sqkm} km²</div>
                    </td>
                    <td className="text-right py-2 px-2 text-white">{formatMW(a.avg_demand_mw)}</td>
                    <td className="text-right py-2 px-2 text-yellow-400">{formatMW(a.rooftop_solar_potential_mw)}</td>
                    <td className="text-right py-2 px-2 text-green-400">{formatMW(a.current_solar_generation_mw)}</td>
                    <td className="text-right py-2 px-2">
                      <span className={clsx('font-medium', a.solar_coverage_pct >= 10 ? 'text-green-400' : 'text-orange-400')}>
                        {formatPercent(a.solar_coverage_pct)}
                      </span>
                    </td>
                    <td className="text-right py-2 px-2 text-orange-400">{formatMW(a.residual_demand_mw)}</td>
                    <td className="text-right py-2 px-2">{a.avg_units_per_rooftop_per_day} kWh</td>
                    <td className="text-right py-2 pl-2 text-sky-400">{a.additional_rooftops_needed.toLocaleString('en-IN')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data?.assumptions && (
        <div className="card">
          <p className="card-header">Calculation Assumptions</p>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-xs text-gray-400">
            <div>Panel efficiency: <span className="text-white">{data.assumptions.panel_efficiency_pct}%</span></div>
            <div>Performance ratio: <span className="text-white">{data.assumptions.performance_ratio}</span></div>
            <div>Avg rooftop size: <span className="text-white">{data.assumptions.avg_rooftop_size_kw} kW</span></div>
            <div>Peak sun hours: <span className="text-white">{data.assumptions.peak_sun_hours} hrs/day</span></div>
          </div>
        </div>
      )}

      {isLoading && (
        <div className="card flex items-center justify-center h-48">
          <p className="text-gray-500 text-sm animate-pulse">Calculating solar predictions...</p>
        </div>
      )}
    </div>
  );
}
