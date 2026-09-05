import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, Clock } from 'lucide-react';
import {
  ResponsiveContainer, ComposedChart, Line, Area, XAxis,
  YAxis, CartesianGrid, Tooltip, Legend
} from 'recharts';
import { format } from 'date-fns';
import client from '../api/client';
import { useDemandChart } from '../hooks/useApi';
import { formatDatetime, getRiskColor, getRiskLabel, getRiskBgColor } from '../utils/formatters';
import clsx from 'clsx';

const fetchHorizons = () => client.get('/api/predict/horizons').then(r => r.data);

const HORIZONS = [
  { key: 1,   label: '1 Hour',  short: '1H',  color: '#38bdf8' },
  { key: 2,   label: '2 Hours', short: '2H',  color: '#a78bfa' },
  { key: 24,  label: '24 Hours',short: '24H', color: '#f97316' },
  { key: 168, label: '7 Days',  short: '7D',  color: '#34d399' },
];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs space-y-1">
      <p className="text-gray-400 font-medium">{label}</p>
      {payload.map((p: any, i: number) => (
        <div key={i} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-gray-300">{p.name}:</span>
          <span className="text-white font-medium">{Number(p.value || 0).toFixed(0)} MW</span>
        </div>
      ))}
    </div>
  );
};

export default function DemandForecast() {
  const [selectedHours, setSelectedHours] = useState(24);
  const { data: horizonsData, isLoading: horizonLoading } = useQuery({
    queryKey: ['horizons'],
    queryFn: fetchHorizons,
    refetchInterval: 300000,
    retry: 1,
  });
  const { data: chartData } = useDemandChart(selectedHours);

  const selected = horizonsData?.horizons?.find((h: any) => h.hours === selectedHours)
    || horizonsData?.horizons?.[horizonsData.horizons.length - 1];

  const chartPoints = selected?.timestamps?.map((ts: string, i: number) => ({
    ts: (() => {
      try {
        const d = new Date(ts);
        return selectedHours <= 2
          ? format(d, 'HH:mm')
          : selectedHours <= 24
          ? format(d, 'HH:mm')
          : format(d, 'dd/MM HH:mm');
      } catch { return ts; }
    })(),
    predicted: selected.values[i],
    lower: selected.lower?.[i],
    upper: selected.upper?.[i],
  })) || [];

  const actualPoints = chartData?.actual?.slice(-selectedHours).map((d: any) => ({
    ts: (() => {
      try {
        const dt = new Date(d.timestamp);
        return selectedHours <= 2
          ? format(dt, 'HH:mm')
          : selectedHours <= 24
          ? format(dt, 'HH:mm')
          : format(dt, 'dd/MM HH:mm');
      } catch { return d.timestamp; }
    })(),
    actual: d.actual_demand,
  })) || [];

  const allTs = new Set([...actualPoints.map((p: any) => p.ts), ...chartPoints.map(p => p.ts)]);
  const merged = Array.from(allTs).sort().map(ts => ({
    ts,
    ...actualPoints.find((p: any) => p.ts === ts),
    ...chartPoints.find(p => p.ts === ts),
  }));

  const exportCSV = () => {
    if (!selected?.timestamps?.length) return;
    const rows = selected.timestamps.map((ts: string, i: number) =>
      `${ts},${selected.values[i]},${selected.lower?.[i] || ''},${selected.upper?.[i] || ''}`
    );
    const csv = 'timestamp,predicted_mw,lower_bound,upper_bound\n' + rows.join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = `delhi_demand_forecast_${selectedHours}h.csv`;
    a.click();
  };

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Demand Forecast</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {horizonsData?.model_used
              ? <>Model: <span className="text-sky-400">{horizonsData.model_used}</span> · Delhi Grid</>
              : 'Train models to generate forecasts'}
          </p>
        </div>
        <button onClick={exportCSV} disabled={!selected?.timestamps?.length}
          className="flex items-center gap-1.5 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-xs transition-colors disabled:opacity-40">
          <Download size={13} /> Export CSV
        </button>
      </div>

      <div className="flex gap-2">
        {HORIZONS.map(h => (
          <button
            key={h.key}
            onClick={() => setSelectedHours(h.key)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all border',
              selectedHours === h.key
                ? 'border-transparent text-gray-900'
                : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-500'
            )}
            style={selectedHours === h.key ? { background: h.color } : {}}
          >
            <Clock size={14} />
            <span>{h.label}</span>
          </button>
        ))}
      </div>

      {selected && (
        <div className={clsx(
          'rounded-xl border p-4 flex flex-wrap gap-6 items-center',
          getRiskBgColor(selected.risk_level)
        )}>
          <div>
            <p className="text-xs text-gray-400 mb-0.5">
              {selectedHours === 1 ? 'Next Hour' : selectedHours === 2 ? 'Next 2 Hours' : selectedHours === 24 ? 'Next 24 Hours' : 'Next 7 Days'} — Predicted
            </p>
            <p className="text-3xl font-bold text-white">{selected.next_value_mw?.toLocaleString('en-IN')} <span className="text-lg font-normal text-gray-400">MW</span></p>
          </div>
          <div className="h-10 w-px bg-gray-700" />
          <div>
            <p className="text-xs text-gray-400 mb-0.5">Peak</p>
            <p className="text-xl font-semibold text-white">{selected.peak_mw?.toLocaleString('en-IN')} MW</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-0.5">Average</p>
            <p className="text-xl font-semibold text-white">{selected.avg_mw?.toLocaleString('en-IN')} MW</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-0.5">Confidence Range</p>
            <p className="text-sm text-gray-300">{selected.lower_bound?.toLocaleString('en-IN')} – {selected.upper_bound?.toLocaleString('en-IN')} MW</p>
          </div>
          {selected.utilization_pct != null && (
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Grid Utilization</p>
              <p className={clsx('text-xl font-semibold', getRiskColor(selected.risk_level))}>
                {selected.utilization_pct}%
              </p>
            </div>
          )}
          <div className={clsx('ml-auto flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium', getRiskBgColor(selected.risk_level))}>
            <span className={clsx('w-2 h-2 rounded-full', selected.risk_level === 'normal' ? 'bg-green-400' : selected.risk_level === 'elevated' ? 'bg-yellow-400' : selected.risk_level === 'high' ? 'bg-orange-400' : 'bg-red-400')} />
            <span className={getRiskColor(selected.risk_level)}>{getRiskLabel(selected.risk_level)}</span>
          </div>
        </div>
      )}

      <div className="card">
        <p className="card-header">
          {HORIZONS.find(h => h.key === selectedHours)?.label} Forecast Chart
        </p>
        {merged.length > 0 ? (
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={merged} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="ts" tick={{ fill: '#6b7280', fontSize: 10 }}
                interval={Math.max(0, Math.floor(merged.length / 10))} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} unit=" MW" width={70} />
              <Tooltip content={<CustomTooltip />} />
              <Legend iconSize={10} wrapperStyle={{ fontSize: 12, color: '#9ca3af' }} />
              <Area dataKey="upper" fill="#1e3a5f" stroke="none" opacity={0.2} name="Upper Bound" legendType="none" />
              <Area dataKey="lower" fill="#1e3a5f" stroke="none" opacity={0} name="Lower Bound" legendType="none" />
              <Line dataKey="actual" stroke="#38bdf8" strokeWidth={2} dot={false} name="Actual" connectNulls />
              <Line dataKey="predicted" stroke={HORIZONS.find(h => h.key === selectedHours)?.color || '#f97316'}
                strokeWidth={2} strokeDasharray={selectedHours > 2 ? '6 3' : '0'}
                dot={false} name="Predicted" connectNulls />
            </ComposedChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[320px] flex items-center justify-center text-gray-500 text-sm">
            {horizonLoading ? 'Generating forecast...' : 'Train models first to see forecasts'}
          </div>
        )}
      </div>

      {selected?.timestamps?.length > 0 && (
        <div className="card">
          <p className="card-header">Hourly Breakdown</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-gray-400">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left py-2 pr-4">#</th>
                  <th className="text-left py-2 pr-4">Time</th>
                  <th className="text-right py-2 px-3">Predicted (MW)</th>
                  <th className="text-right py-2 px-3">Lower (MW)</th>
                  <th className="text-right py-2 pl-3">Upper (MW)</th>
                </tr>
              </thead>
              <tbody>
                {selected.timestamps.map((ts: string, i: number) => (
                  <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-1.5 pr-4 text-gray-600">{i + 1}</td>
                    <td className="py-1.5 pr-4 text-gray-300">{formatDatetime(ts)}</td>
                    <td className="text-right py-1.5 px-3 text-white font-medium">
                      {selected.values[i]?.toLocaleString('en-IN')}
                    </td>
                    <td className="text-right py-1.5 px-3 text-gray-500">
                      {selected.lower?.[i]?.toLocaleString('en-IN') || '—'}
                    </td>
                    <td className="text-right py-1.5 pl-3 text-gray-500">
                      {selected.upper?.[i]?.toLocaleString('en-IN') || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
