import React from 'react';
import clsx from 'clsx';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon?: React.ReactNode;
  trend?: { value: number; label?: string };
  riskLevel?: string;
  loading?: boolean;
  subtitle?: string;
}

export default function StatCard({
  title, value, unit, icon, trend, riskLevel, loading, subtitle
}: StatCardProps) {
  const riskBorder: Record<string, string> = {
    normal: 'border-l-green-500',
    elevated: 'border-l-yellow-500',
    high: 'border-l-orange-500',
    critical: 'border-l-red-500',
    capacity_exceeded: 'border-l-purple-500',
  };

  if (loading) {
    return (
      <div className="card border-l-4 border-l-gray-700 animate-pulse">
        <div className="h-3 bg-gray-700 rounded w-24 mb-3" />
        <div className="h-8 bg-gray-700 rounded w-32 mb-2" />
        <div className="h-3 bg-gray-700 rounded w-20" />
      </div>
    );
  }

  return (
    <div className={clsx(
      'card border-l-4',
      riskLevel ? (riskBorder[riskLevel] || 'border-l-sky-500') : 'border-l-sky-500'
    )}>
      <div className="flex items-start justify-between">
        <p className="card-header">{title}</p>
        {icon && <span className="text-gray-500">{icon}</span>}
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="text-2xl font-bold text-white">{value ?? '—'}</span>
        {unit && <span className="text-sm text-gray-400">{unit}</span>}
      </div>
      {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
      {trend != null && (
        <div className={clsx(
          'flex items-center gap-1 text-xs mt-1',
          trend.value > 0 ? 'text-red-400' : trend.value < 0 ? 'text-green-400' : 'text-gray-400'
        )}>
          {trend.value > 0 ? <TrendingUp size={12} /> : trend.value < 0 ? <TrendingDown size={12} /> : <Minus size={12} />}
          <span>{Math.abs(trend.value).toFixed(1)}%{trend.label ? ` ${trend.label}` : ''}</span>
        </div>
      )}
    </div>
  );
}
