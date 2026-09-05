import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import client from '../../api/client';
import clsx from 'clsx';

const fetchBreakdown = () => client.get('/api/areas/consumer-breakdown').then(r => r.data);

const CAT_COLORS: Record<string, string> = {
  residential:       '#38bdf8',
  commercial:        '#a78bfa',
  low_industrial:    '#fb923c',
  medium_industrial: '#f59e0b',
  high_industrial:   '#ef4444',
  hospital_24x7:     '#34d399',
  others:            '#94a3b8',
};

const CAT_LABELS: Record<string, string> = {
  residential:       'Residential',
  commercial:        'Commercial',
  low_industrial:    'Low Industrial',
  medium_industrial: 'Medium Industrial',
  high_industrial:   'High Industrial',
  hospital_24x7:     'Hospital / 24×7',
  others:            'Others',
};

export default function ConsumerBreakdownChart() {
  const { data, isLoading } = useQuery({
    queryKey: ['consumer-breakdown'],
    queryFn: fetchBreakdown,
    refetchInterval: 120000,
  });
  const [selectedDiscom, setSelectedDiscom] = useState<string | null>(null);

  if (isLoading) return <div className="h-64 flex items-center justify-center text-gray-500 text-sm animate-pulse">Loading...</div>;
  if (!data?.discoms?.length) return <div className="h-64 flex items-center justify-center text-gray-500 text-sm">No data</div>;

  const discoms = data.discoms;
  const selected = selectedDiscom ? discoms.find((d: any) => d.discom === selectedDiscom) : null;

  const stackedData = discoms.map((d: any) => {
    const row: any = { name: d.discom, total: d.total_demand_mw };
    d.categories.forEach((c: any) => { row[c.key] = c.demand_mw; });
    return row;
  });

  const pieData = selected
    ? selected.categories.map((c: any) => ({ name: CAT_LABELS[c.key] || c.key, value: c.pct, mw: c.demand_mw, key: c.key }))
    : [];

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-3">
        {discoms.map((d: any) => (
          <button key={d.discom} onClick={() => setSelectedDiscom(selectedDiscom === d.discom ? null : d.discom)}
            className={clsx('px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors',
              selectedDiscom === d.discom
                ? 'bg-sky-700 border-sky-600 text-white'
                : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-500'
            )}>{d.discom}</button>
        ))}
        {selectedDiscom && <button onClick={() => setSelectedDiscom(null)} className="px-2.5 py-1 rounded-lg text-xs text-gray-500 hover:text-gray-300">× Clear</button>}
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
              <Bar key={key} dataKey={key} stackId="a" fill={color} name={CAT_LABELS[key]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div>
          <p className="text-xs text-gray-400 mb-3 font-medium">{selected.label} — {selected.total_demand_mw.toFixed(1)} MW avg</p>
          <div className="space-y-2">
            {pieData.map((cat: any) => (
              <div key={cat.key} className="flex items-center gap-3">
                <span className="w-3 h-3 rounded-sm shrink-0" style={{ background: CAT_COLORS[cat.key] }} />
                <span className="text-xs text-gray-300 w-36">{cat.name}</span>
                <div className="flex-1 bg-gray-800 rounded-full h-2">
                  <div className="h-2 rounded-full" style={{ width: `${cat.value}%`, background: CAT_COLORS[cat.key] }} />
                </div>
                <span className="text-xs text-gray-400 w-10 text-right">{cat.value}%</span>
                <span className="text-xs text-white w-16 text-right">{cat.mw} MW</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
