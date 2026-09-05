import React, { useState } from 'react';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Cell
} from 'recharts';

interface ModelComparisonChartProps {
  models: Array<{ model: string; mae: number; rmse: number; mape: number; r2: number }>;
  bestModel?: string;
}

const METRICS = ['rmse', 'mae', 'mape', 'r2'] as const;

export default function ModelComparisonChart({ models, bestModel }: ModelComparisonChartProps) {
  const [metric, setMetric] = useState<typeof METRICS[number]>('rmse');

  const sorted = [...models].sort((a, b) =>
    metric === 'r2' ? b[metric] - a[metric] : a[metric] - b[metric]
  );

  return (
    <div>
      <div className="flex gap-2 mb-3">
        {METRICS.map(m => (
          <button key={m} onClick={() => setMetric(m)}
            className={`px-2 py-1 rounded text-xs font-medium uppercase transition-colors ${
              metric === m ? 'bg-sky-700 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}>{m}</button>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={sorted} margin={{ top: 5, right: 10, bottom: 30, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="model" tick={{ fill: '#6b7280', fontSize: 10 }} angle={-25} textAnchor="end" />
          <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} />
          <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, fontSize: 11 }}
            labelStyle={{ color: '#e5e7eb' }} />
          <Bar dataKey={metric} radius={[3, 3, 0, 0]}>
            {sorted.map((entry, i) => (
              <Cell key={i} fill={entry.model === bestModel ? '#38bdf8' : '#334155'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-xs text-gray-400">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left py-1.5 pr-3">Model</th>
              <th className="text-right py-1.5 px-2">RMSE</th>
              <th className="text-right py-1.5 px-2">MAE</th>
              <th className="text-right py-1.5 px-2">MAPE%</th>
              <th className="text-right py-1.5 pl-2">R²</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((m, i) => (
              <tr key={m.model} className={`border-b border-gray-800/50 ${m.model === bestModel ? 'text-sky-300' : ''}`}>
                <td className="py-1.5 pr-3 font-medium flex items-center gap-1">
                  {i === 0 && <span className="text-yellow-400">★</span>} {m.model}
                </td>
                <td className="text-right px-2">{m.rmse?.toFixed(2)}</td>
                <td className="text-right px-2">{m.mae?.toFixed(2)}</td>
                <td className="text-right px-2">{m.mape?.toFixed(2)}</td>
                <td className="text-right pl-2">{m.r2?.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
