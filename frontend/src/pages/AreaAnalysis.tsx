import React, { useState } from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, PieChart, Pie, Cell } from 'recharts';
import WeatherDemandChart from '../components/charts/WeatherDemandChart';
import { useAreaBreakdown, useWeatherCorrelation, useConsumerBreakdown } from '../hooks/useApi';
import { formatMW } from '../utils/formatters';
import clsx from 'clsx';

const CAT_COLORS: Record<string, string> = {
  residential: '#38bdf8', commercial: '#a78bfa', low_industrial: '#fb923c',
  medium_industrial: '#f59e0b', high_industrial: '#ef4444',
  hospital_24x7: '#34d399', others: '#94a3b8',
};

const DISCOM_COLORS: Record<string, string> = {
  BRPL: '#38bdf8', BYPL: '#a78bfa', NDPL: '#34d399', NDMC: '#f97316', MES: '#fbbf24'
};

export default function AreaAnalysis() {
  const { data: areaData } = useAreaBreakdown();
  const { data: weatherData } = useWeatherCorrelation(336);
  const { data: consumerData } = useConsumerBreakdown();
  const [selectedDiscom, setSelectedDiscom] = useState<string | null>(null);

  const discoms = consumerData?.discoms || [];
  const selected = selectedDiscom ? discoms.find((d: any) => d.discom === selectedDiscom) : null;

  const discomBarData = areaData?.areas?.map((a: any) => ({
    name: a.area.split('(')[0].trim(),
    demand_mw: a.demand_mw,
    pct: a.percentage,
    key: a.consumer_type,
  })) || [];

  const stackedData = discoms.map((d: any) => {
    const row: any = { name: d.discom };
    d.categories.forEach((c: any) => { row[c.key] = c.demand_mw; });
    return row;
  });

  const pieData = selected
    ? selected.categories.map((c: any) => ({
        name: c.category, value: c.pct, mw: c.demand_mw, key: c.key
      }))
    : [];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white">Area & Node Analysis</h1>
        <p className="text-sm text-gray-500 mt-0.5">DISCOM-wise demand, consumer category breakdown, and weather correlation</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {discomBarData.map((d: any) => (
          <div key={d.name} className="card text-center">
            <p className="text-xs text-gray-500 mb-1">{d.name}</p>
            <p className="text-lg font-bold" style={{ color: DISCOM_COLORS[d.key] || '#94a3b8' }}>{d.demand_mw.toFixed(0)} MW</p>
            <p className="text-xs text-gray-500">{d.pct.toFixed(1)}% of total</p>
          </div>
        ))}
      </div>

      <div className="card">
        <p className="card-header">DISCOM-wise Average Demand</p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={discomBarData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} />
            <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} unit=" MW" width={65} />
            <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, fontSize: 11 }} labelStyle={{ color: '#e5e7eb' }} />
            <Bar dataKey="demand_mw" name="Avg Demand (MW)" radius={[4, 4, 0, 0]}>
              {discomBarData.map((d: any, i: number) => (
                <Cell key={i} fill={DISCOM_COLORS[d.key] || '#94a3b8'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <p className="card-header mb-0">Consumer Category Breakdown</p>
          <div className="flex gap-2">
            {discoms.map((d: any) => (
              <button key={d.discom} onClick={() => setSelectedDiscom(selectedDiscom === d.discom ? null : d.discom)}
                className={clsx('px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors',
                  selectedDiscom === d.discom
                    ? 'text-gray-900 border-transparent'
                    : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-500'
                )}
                style={selectedDiscom === d.discom ? { background: DISCOM_COLORS[d.discom] } : {}}
              >{d.discom}</button>
            ))}
          </div>
        </div>

        {!selected ? (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={stackedData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} unit=" MW" width={65} />
              <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, fontSize: 11 }} labelStyle={{ color: '#e5e7eb' }} />
              <Legend iconSize={8} wrapperStyle={{ fontSize: 10 }} />
              {Object.entries(CAT_COLORS).map(([key, color]) => (
                <Bar key={key} dataKey={key} stackId="a" fill={color}
                  name={key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div>
              <p className="text-sm font-medium text-white mb-1">{selected.label}</p>
              <p className="text-xs text-gray-500 mb-3">Total avg demand: {selected.total_demand_mw.toFixed(1)} MW</p>
              <div className="space-y-2.5">
                {pieData.map((cat: any) => (
                  <div key={cat.key}>
                    <div className="flex justify-between text-xs mb-0.5">
                      <span className="text-gray-300">{cat.name}</span>
                      <span className="text-white">{cat.mw} MW ({cat.value}%)</span>
                    </div>
                    <div className="w-full bg-gray-800 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full" style={{ width: `${cat.value}%`, background: CAT_COLORS[cat.key] }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, value }) => `${value}%`} labelLine={false} fontSize={10}>
                  {pieData.map((cat: any, i: number) => (
                    <Cell key={i} fill={CAT_COLORS[cat.key]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => `${v}%`} contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="card">
        <p className="card-header">DISCOM Demand Summary Table</p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-gray-400">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left py-2 pr-4">DISCOM</th>
                <th className="text-right py-2 px-3">Avg Demand</th>
                <th className="text-right py-2 px-3">Share</th>
                <th className="text-right py-2 px-3">Residential</th>
                <th className="text-right py-2 px-3">Commercial</th>
                <th className="text-right py-2 px-3">Industrial</th>
                <th className="text-right py-2 pl-3">Hospital 24×7</th>
              </tr>
            </thead>
            <tbody>
              {discoms.map((d: any) => {
                const get = (key: string) => d.categories.find((c: any) => c.key === key);
                const res = get('residential'); const com = get('commercial');
                const ind = d.categories.filter((c: any) => c.key.includes('industrial'));
                const hos = get('hospital_24x7');
                const indMw = ind.reduce((s: number, c: any) => s + c.demand_mw, 0);
                return (
                  <tr key={d.discom} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-2 pr-4">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-sm" style={{ background: DISCOM_COLORS[d.discom] }} />
                        <span className="text-gray-200 font-medium">{d.discom}</span>
                      </div>
                    </td>
                    <td className="text-right py-2 px-3 text-white font-medium">{formatMW(d.total_demand_mw)}</td>
                    <td className="text-right py-2 px-3">{areaData?.areas?.find((a: any) => a.consumer_type === d.discom)?.percentage?.toFixed(1) || '—'}%</td>
                    <td className="text-right py-2 px-3 text-sky-400">{res ? `${res.demand_mw} MW` : '—'}</td>
                    <td className="text-right py-2 px-3 text-purple-400">{com ? `${com.demand_mw} MW` : '—'}</td>
                    <td className="text-right py-2 px-3 text-orange-400">{indMw > 0 ? `${indMw.toFixed(1)} MW` : '—'}</td>
                    <td className="text-right py-2 pl-3 text-green-400">{hos ? `${hos.demand_mw} MW` : '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <p className="card-header">Weather vs Demand (2 Weeks)</p>
        {weatherData?.data?.length > 0 ? (
          <WeatherDemandChart data={weatherData.data} />
        ) : (
          <div className="h-60 flex items-center justify-center text-gray-500 text-sm">No weather data</div>
        )}
      </div>
    </div>
  );
}
