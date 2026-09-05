import React, { useState } from 'react';
import { useLoadBalancing } from '../hooks/useApi';
import { RefreshCw } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, Legend } from 'recharts';
import { getRiskColor, getRiskLabel, getRiskBgColor, getRiskDotColor, formatMW, formatPercent } from '../utils/formatters';
import clsx from 'clsx';



const RISK_FILL: Record<string, string> = {
  normal: '#16a34a', elevated: '#ca8a04', high: '#ea580c',
  critical: '#dc2626', capacity_exceeded: '#7c3aed', unknown: '#475569',
};

function UtilizationBar({ pct, risk }: { pct: number; risk: string }) {
  return (
    <div className="w-full bg-gray-800 rounded-full h-2.5 mt-1">
      <div
        className="h-2.5 rounded-full transition-all"
        style={{ width: `${Math.min(pct, 100)}%`, background: RISK_FILL[risk] || '#475569' }}
      />
    </div>
  );
}

export default function LoadBalancing() {
  const { data, isLoading, refetch } = useLoadBalancing();// original:
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Load Balancing Advisor</h1>
          <p className="text-sm text-gray-500 mt-0.5">DISCOM-wise demand, utilization and recommended actions</p>
        </div>
        <button onClick={() => refetch()} className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200">
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {data && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'System Load', value: formatMW(data.system_total_mw) },
            { label: 'Utilization', value: formatPercent(data.system_utilization_pct), color: getRiskColor(data.system_risk) },
            { label: 'DR Potential', value: formatMW(data.total_demand_response_mw) },
            { label: 'Interruptible', value: formatMW(data.total_interruptible_mw) },
          ].map(({ label, value, color }) => (
            <div key={label} className="card">
              <p className="card-header">{label}</p>
              <p className={clsx('text-xl font-bold', color || 'text-white')}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {data?.discoms && (
        <div className="card">
          <p className="card-header">DISCOM Load vs Capacity</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data.discoms.map((d: any) => ({
              name: d.discom,
              'Current Load': d.current_mw,
              'Available Reserve': Math.max(0, d.capacity_mw - d.current_mw),
              risk: d.risk_level,
            }))} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} unit=" MW" width={65} />
              <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, fontSize: 11 }} labelStyle={{ color: '#e5e7eb' }} />
              <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="Current Load" stackId="a" radius={[0, 0, 0, 0]}>
                {data.discoms.map((d: any, i: number) => (
                  <Cell key={i} fill={RISK_FILL[d.risk_level] || '#475569'} />
                ))}
              </Bar>
              <Bar dataKey="Available Reserve" stackId="a" fill="#1e3a5f" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {data?.discoms && (
        <div className="space-y-3">
          {data.discoms.map((d: any) => (
            <div key={d.discom} className={clsx('card border', getRiskBgColor(d.risk_level))}>
              <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpanded(expanded === d.discom ? null : d.discom)}
              >
                <div className="flex items-center gap-3">
                  <span className={clsx('w-2.5 h-2.5 rounded-full', getRiskDotColor(d.risk_level))} />
                  <div>
                    <p className="text-sm font-semibold text-white">{d.label}</p>
                    <p className="text-xs text-gray-400">
                      {formatMW(d.current_mw)} · {formatPercent(d.utilization_pct)} utilization
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs">
                  <div className="text-right hidden sm:block">
                    <p className="text-gray-400">DR Potential</p>
                    <p className="text-white font-medium">{formatMW(d.demand_response_potential_mw)}</p>
                  </div>
                  <div className="text-right hidden sm:block">
                    <p className="text-gray-400">Interruptible</p>
                    <p className="text-white font-medium">{formatMW(d.interruptible_load_mw)}</p>
                  </div>
                  <span className={clsx('px-2 py-0.5 rounded-full border text-xs font-medium', getRiskBgColor(d.risk_level), getRiskColor(d.risk_level))}>
                    {getRiskLabel(d.risk_level)}
                  </span>
                </div>
              </div>

              <UtilizationBar pct={d.utilization_pct} risk={d.risk_level} />

              {expanded === d.discom && (
                <div className="mt-3 pt-3 border-t border-gray-700 space-y-2">
                  <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Recommended Actions</p>
                  {d.actions.map((action: string, i: number) => (
                    <div key={i} className="flex items-start gap-2 text-xs">
                      <span className={clsx('mt-1 w-1.5 h-1.5 rounded-full shrink-0', getRiskDotColor(d.risk_level))} />
                      <span className="text-gray-300">{action}</span>
                    </div>
                  ))}
                  <div className="grid grid-cols-3 gap-3 mt-2 pt-2 border-t border-gray-800">
                    <div>
                      <p className="text-xs text-gray-500">Load Factor</p>
                      <p className="text-sm font-medium text-white">{d.load_factor}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Capacity</p>
                      <p className="text-sm font-medium text-white">{formatMW(d.capacity_mw)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Reserve</p>
                      <p className="text-sm font-medium text-green-400">{formatMW(Math.max(0, d.capacity_mw - d.current_mw))}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {data?.top_recommendations?.length > 0 && (
        <div className="card">
          <p className="card-header">Top Priority Actions Right Now</p>
          <div className="space-y-2">
            {data.top_recommendations.map((r: any, i: number) => (
              <div key={i} className="flex items-start gap-3 text-xs">
                <span className={clsx('mt-0.5 text-xs font-bold px-1.5 py-0.5 rounded shrink-0', getRiskBgColor(r.priority), getRiskColor(r.priority))}>
                  {r.discom}
                </span>
                <span className="text-gray-300">{r.action}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {isLoading && (
        <div className="card flex items-center justify-center h-48">
          <p className="text-gray-500 text-sm animate-pulse">Loading load balancing data...</p>
        </div>
      )}
    </div>
  );
}
