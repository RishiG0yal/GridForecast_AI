import React from 'react';
import {
  ResponsiveContainer, ComposedChart, Line, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ReferenceLine
} from 'recharts';
import { format } from 'date-fns';

interface DemandForecastChartProps {
  actual: Array<{ timestamp: string; actual_demand: number; gross_demand?: number }>;
  predicted: Array<{ timestamp: string; predicted_demand: number; lower_bound: number; upper_bound: number }>;
}

const fmt = (ts: string) => {
  try { return format(new Date(ts), 'dd/MM HH:mm'); } catch { return ts; }
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs space-y-1">
      <p className="text-gray-400 font-medium">{label}</p>
      {payload.map((p: any, i: number) => (
        <div key={i} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-gray-300">{p.name}:</span>
          <span className="text-white font-medium">{Number(p.value).toFixed(1)} MW</span>
        </div>
      ))}
    </div>
  );
};

export default function DemandForecastChart({ actual, predicted }: DemandForecastChartProps) {
  const nowStr = new Date().toISOString();

  const allData: any[] = [];
  const allTimestamps = new Set([
    ...actual.map(d => d.timestamp),
    ...predicted.map(d => d.timestamp),
  ]);

  const actualMap = Object.fromEntries(actual.map(d => [d.timestamp, d]));
  const predMap = Object.fromEntries(predicted.map(d => [d.timestamp, d]));

  Array.from(allTimestamps).sort().forEach(ts => {
    allData.push({
      timestamp: fmt(ts),
      raw_ts: ts,
      actual_demand: actualMap[ts]?.actual_demand,
      predicted_demand: predMap[ts]?.predicted_demand,
      lower_bound: predMap[ts]?.lower_bound,
      upper_bound: predMap[ts]?.upper_bound,
    });
  });

  const nowLabel = fmt(nowStr);

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={allData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis dataKey="timestamp" tick={{ fill: '#6b7280', fontSize: 11 }}
          interval={Math.floor(allData.length / 10)} />
        <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} unit=" MW"
          width={70} />
        <Tooltip content={<CustomTooltip />} />
        <Legend iconSize={10} wrapperStyle={{ fontSize: 12, color: '#9ca3af' }} />
        <ReferenceLine x={nowLabel} stroke="#6b7280" strokeDasharray="4 2"
          label={{ value: 'Now', fill: '#9ca3af', fontSize: 10 }} />
        <Area dataKey="upper_bound" fill="#1e40af" stroke="none" opacity={0.15} name="Upper Bound" />
        <Area dataKey="lower_bound" fill="#1e40af" stroke="none" opacity={0.0} name="Lower Bound" />
        <Line dataKey="actual_demand" stroke="#38bdf8" strokeWidth={2} dot={false} name="Actual Demand" />
        <Line dataKey="predicted_demand" stroke="#f97316" strokeWidth={2}
          strokeDasharray="6 3" dot={false} name="Predicted Demand" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
