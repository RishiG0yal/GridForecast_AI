import React from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Cell } from 'recharts';
import { getRiskLabel } from '../../utils/formatters';

interface AreaUtil {
  area: string;
  available_mw: number;
  predicted_demand_mw: number;
  utilization_pct: number;
  risk_level: string;
}

interface Props { areas: AreaUtil[] }

const riskFill: Record<string, string> = {
  normal: '#16a34a', elevated: '#ca8a04', high: '#ea580c',
  critical: '#dc2626', capacity_exceeded: '#7c3aed', unknown: '#475569'
};

function GaugeCircle({ util, risk, area }: { util: number; risk: string; area: string }) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(util / 100, 1);
  const stroke = riskFill[risk] || '#475569';
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={88} height={88} viewBox="0 0 88 88">
        <circle cx={44} cy={44} r={r} fill="none" stroke="#1f2937" strokeWidth={10} />
        <circle cx={44} cy={44} r={r} fill="none" stroke={stroke} strokeWidth={10}
          strokeDasharray={circ} strokeDashoffset={circ * (1 - pct)}
          strokeLinecap="round" transform="rotate(-90 44 44)" />
        <text x={44} y={44} textAnchor="middle" dominantBaseline="central"
          fill="white" fontSize={13} fontWeight="bold">{util.toFixed(0)}%</text>
      </svg>
      <span className="text-xs text-gray-400 text-center leading-tight">{area.replace('_', ' ')}</span>
      <span className="text-xs font-medium" style={{ color: stroke }}>{getRiskLabel(risk)}</span>
    </div>
  );
}

export default function CapacityUtilizationChart({ areas }: Props) {
  return (
    <div>
      <div className="flex flex-wrap gap-4 justify-center mb-4">
        {areas.map(a => (
          <GaugeCircle key={a.area} util={a.utilization_pct} risk={a.risk_level} area={a.area} />
        ))}
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={areas.map(a => ({
          ...a,
          area: a.area.replace(/_/g, ' ').replace('Region', ''),
          surplus: Math.max(0, a.available_mw - a.predicted_demand_mw)
        }))} margin={{ top: 5, right: 10, bottom: 25, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="area" tick={{ fill: '#6b7280', fontSize: 10 }} angle={-15} textAnchor="end" />
          <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} unit=" MW" width={65} />
          <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, fontSize: 11 }}
            labelStyle={{ color: '#e5e7eb' }} />
          <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="predicted_demand_mw" name="Demand" radius={[2, 2, 0, 0]}>
            {areas.map((a, i) => <Cell key={i} fill={riskFill[a.risk_level] || '#475569'} />)}
          </Bar>
          <Bar dataKey="surplus" name="Available Surplus" fill="#1e3a5f" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
