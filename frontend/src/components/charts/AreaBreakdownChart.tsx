import React from 'react';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Cell, LabelList
} from 'recharts';

const DISCOM_COLORS: Record<string, string> = {
  BRPL: '#38bdf8',
  BYPL: '#a78bfa',
  NDPL: '#34d399',
  NDMC: '#f97316',
  MES:  '#fbbf24',
};

interface AreaItem {
  area: string;
  consumer_type: string;
  demand_mw: number;
  percentage: number;
}

interface AreaBreakdownChartProps {
  areas: AreaItem[];
  consumerTypes: string[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs space-y-1">
      <p className="text-white font-medium">{d.area}</p>
      <p className="text-gray-300">Avg Demand: <span className="text-white font-bold">{d.demand_mw.toFixed(1)} MW</span></p>
      <p className="text-gray-300">Share: <span className="text-white font-bold">{d.percentage.toFixed(1)}%</span></p>
    </div>
  );
};

export default function AreaBreakdownChart({ areas }: AreaBreakdownChartProps) {
  const sorted = [...areas].sort((a, b) => b.demand_mw - a.demand_mw);

  const getColor = (consumerType: string) => {
    const key = consumerType.toUpperCase();
    return DISCOM_COLORS[key] || '#94a3b8';
  };

  return (
    <div>
      <div className="flex flex-wrap gap-3 mb-4">
        {sorted.map(a => (
          <div key={a.area} className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm" style={{ background: getColor(a.consumer_type) }} />
            <span className="text-xs text-gray-400">{a.area.split('(')[0].trim()}</span>
          </div>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={sorted} margin={{ top: 15, right: 20, bottom: 40, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis
            dataKey="area"
            tick={{ fill: '#6b7280', fontSize: 9 }}
            angle={-20}
            textAnchor="end"
            interval={0}
            tickFormatter={(v) => v.split('(')[0].trim().replace('(South/West Delhi)', '').replace(' Delhi', '')}
          />
          <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} unit=" MW" width={65} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="demand_mw" radius={[4, 4, 0, 0]} name="Avg Demand">
            {sorted.map((entry, i) => (
              <Cell key={i} fill={getColor(entry.consumer_type)} />
            ))}
            <LabelList
              dataKey="percentage"
              position="top"
              formatter={(v: number) => `${v.toFixed(0)}%`}
              style={{ fontSize: 10, fill: '#9ca3af' }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-xs text-gray-400">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left py-1.5 pr-4">DISCOM / Area</th>
              <th className="text-right py-1.5 px-3">Avg Demand</th>
              <th className="text-right py-1.5 pl-3">Share</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((a, i) => (
              <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="py-1.5 pr-4 flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: getColor(a.consumer_type) }} />
                  <span className="text-gray-200">{a.area}</span>
                </td>
                <td className="text-right py-1.5 px-3 text-white font-medium">{a.demand_mw.toFixed(1)} MW</td>
                <td className="text-right py-1.5 pl-3 text-gray-400">{a.percentage.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
