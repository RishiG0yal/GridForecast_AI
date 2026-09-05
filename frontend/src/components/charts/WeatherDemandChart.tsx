import React, { useState } from 'react';
import {
  ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend
} from 'recharts';
import { format } from 'date-fns';

interface WeatherDemandChartProps {
  data: Array<{
    timestamp: string;
    demand: number;
    temperature?: number;
    humidity?: number;
    solar_radiation?: number;
  }>;
}

export default function WeatherDemandChart({ data }: WeatherDemandChartProps) {
  const [showTemp, setShowTemp] = useState(true);
  const [showHumidity, setShowHumidity] = useState(false);
  const [showSolar, setShowSolar] = useState(false);

  const chartData = data.map(d => ({
    ...d,
    ts: (() => { try { return format(new Date(d.timestamp), 'dd/MM HH:mm'); } catch { return d.timestamp; } })(),
  }));

  return (
    <div>
      <div className="flex gap-2 mb-3">
        {[
          { key: 'showTemp', label: 'Temperature', state: showTemp, set: setShowTemp },
          { key: 'showHumidity', label: 'Humidity', state: showHumidity, set: setShowHumidity },
          { key: 'showSolar', label: 'Solar Radiation', state: showSolar, set: setShowSolar },
        ].map(({ label, state, set }) => (
          <button key={label} onClick={() => set(s => !s)}
            className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
              state ? 'bg-sky-700 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >{label}</button>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 30, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="ts" tick={{ fill: '#6b7280', fontSize: 10 }}
            interval={Math.floor(chartData.length / 8)} />
          <YAxis yAxisId="demand" tick={{ fill: '#6b7280', fontSize: 10 }} unit=" MW" width={65} />
          <YAxis yAxisId="weather" orientation="right" tick={{ fill: '#6b7280', fontSize: 10 }} width={50} />
          <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, fontSize: 11 }}
            labelStyle={{ color: '#e5e7eb' }} />
          <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
          <Area yAxisId="demand" dataKey="demand" fill="#1e3a5f" stroke="#38bdf8"
            strokeWidth={2} dot={false} name="Demand (MW)" />
          {showTemp && (
            <Line yAxisId="weather" dataKey="temperature" stroke="#f97316"
              strokeWidth={1.5} dot={false} name="Temperature (°C)" />
          )}
          {showHumidity && (
            <Line yAxisId="weather" dataKey="humidity" stroke="#a78bfa"
              strokeWidth={1.5} dot={false} name="Humidity (%)" />
          )}
          {showSolar && (
            <Line yAxisId="weather" dataKey="solar_radiation" stroke="#fbbf24"
              strokeWidth={1.5} dot={false} name="Solar (W/m²)" />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
