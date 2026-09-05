import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, Tooltip
} from 'recharts';
import client from '../../api/client';
import { getRiskColor, getRiskBgColor, getRiskLabel, getRiskDotColor } from '../../utils/formatters';
import clsx from 'clsx';
import { format } from 'date-fns';

const fetchHorizons = () =>
  client.get('/api/predict/horizons').then(r => r.data);

const HORIZON_ICONS: Record<string, string> = {
  'Next 1 Hour': '1H',
  'Next 2 Hours': '2H',
  'Next 24 Hours': '24H',
  'Next 7 Days': '7D',
};

const HORIZON_COLORS: Record<string, string> = {
  'Next 1 Hour': '#38bdf8',
  'Next 2 Hours': '#a78bfa',
  'Next 24 Hours': '#f97316',
  'Next 7 Days': '#34d399',
};

function MiniSparkline({ values, color }: { values: number[]; color: string }) {
  const data = values.map((v, i) => ({ i, v }));
  return (
    <ResponsiveContainer width="100%" height={40}>
      <AreaChart data={data} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id={`grad-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#grad-${color.replace('#', '')})`}
          dot={false}
          isAnimationActive={false}
        />
        <Tooltip
          content={({ active, payload }) =>
            active && payload?.length ? (
              <div className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white">
                {Number(payload[0].value ?? 0).toFixed(0)} MW
              </div>
            ) : null
          }
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function HorizonCard({ horizon, color }: { horizon: any; color: string }) {
  const trend = horizon.end_value_mw - horizon.next_value_mw;
  const trendPct = horizon.next_value_mw > 0
    ? Math.abs(trend / horizon.next_value_mw * 100).toFixed(1)
    : '0';

  return (
    <div className={clsx(
      'card border-t-2 flex flex-col gap-2',
      `border-t-[${color}]`
    )} style={{ borderTopColor: color }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold px-2 py-0.5 rounded-full text-gray-900 font-mono"
            style={{ background: color }}>
            {HORIZON_ICONS[horizon.label] || horizon.label}
          </span>
          <span className="text-xs text-gray-400">{horizon.label}</span>
        </div>
        <div className={clsx(
          'flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border',
          getRiskBgColor(horizon.risk_level)
        )}>
          <span className={clsx('w-1.5 h-1.5 rounded-full', getRiskDotColor(horizon.risk_level))} />
          <span className={getRiskColor(horizon.risk_level)}>{getRiskLabel(horizon.risk_level)}</span>
        </div>
      </div>

      <div className="flex items-end justify-between">
        <div>
          <p className="text-2xl font-bold text-white">
            {horizon.next_value_mw?.toLocaleString('en-IN')}
            <span className="text-sm font-normal text-gray-400 ml-1">MW</span>
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            {horizon.hours === 1
              ? 'at next hour'
              : `avg ${horizon.avg_mw?.toLocaleString('en-IN')} MW`}
          </p>
        </div>
        <div className="text-right">
          <div className={clsx(
            'flex items-center gap-1 text-xs justify-end',
            trend > 0 ? 'text-red-400' : trend < 0 ? 'text-green-400' : 'text-gray-400'
          )}>
            {trend > 50 ? <TrendingUp size={12} /> :
              trend < -50 ? <TrendingDown size={12} /> :
              <Minus size={12} />}
            <span>{trendPct}%</span>
          </div>
          <p className="text-xs text-gray-600 mt-0.5">
            Peak: <span className="text-gray-300">{horizon.peak_mw?.toLocaleString('en-IN')} MW</span>
          </p>
          {horizon.utilization_pct != null && (
            <p className="text-xs text-gray-600">
              Util: <span className={getRiskColor(horizon.risk_level)}>{horizon.utilization_pct}%</span>
            </p>
          )}
        </div>
      </div>

      {horizon.values?.length > 1 && (
        <MiniSparkline values={horizon.values} color={color} />
      )}

      <div className="flex justify-between text-xs text-gray-600 mt-0.5">
        <span>Lower: {horizon.lower_bound?.toLocaleString('en-IN')} MW</span>
        <span>Upper: {horizon.upper_bound?.toLocaleString('en-IN')} MW</span>
      </div>
    </div>
  );
}

export default function HorizonCards() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['horizons'],
    queryFn: fetchHorizons,
    refetchInterval: 300000,
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[0, 1, 2, 3].map(i => (
          <div key={i} className="card animate-pulse">
            <div className="h-3 bg-gray-700 rounded w-16 mb-3" />
            <div className="h-8 bg-gray-700 rounded w-28 mb-2" />
            <div className="h-10 bg-gray-800 rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (error || !data?.horizons?.length) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {['1H', '2H', '24H', '7D'].map(label => (
          <div key={label} className="card border-t-2 border-t-gray-700 flex flex-col items-center justify-center py-6 gap-2">
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-gray-700 text-gray-400 font-mono">{label}</span>
            <p className="text-gray-600 text-xs text-center">Train models to see forecast</p>
          </div>
        ))}
      </div>
    );
  }

  const colors = Object.values(HORIZON_COLORS);

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="card-header mb-0">Demand Forecast Horizons</p>
        <p className="text-xs text-gray-500">
          Model: <span className="text-sky-400">{data.model_used}</span> ·{' '}
          {format(new Date(data.generated_at), 'HH:mm')} IST
        </p>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {data.horizons.map((h: any, i: number) => (
          <HorizonCard key={h.label} horizon={h} color={colors[i] || '#94a3b8'} />
        ))}
      </div>
    </div>
  );
}
