import React, { useState } from 'react';
import { AlertTriangle, X, ChevronDown, ChevronUp } from 'lucide-react';
import { getRiskBgColor, getRiskColor, getRiskLabel, formatDatetime, formatMW, formatPercent } from '../../utils/formatters';
import clsx from 'clsx';

interface Alert {
  timestamp: string;
  risk_level: string;
  predicted_demand: number;
  available_capacity: number;
  utilization_pct: number;
  area: string;
  message: string;
  recommendations: string[];
}

interface Props { alerts: Alert[] }

export default function RiskAlertBanner({ alerts }: Props) {
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  if (!alerts?.length) return null;
  const visible = alerts.filter((_, i) => !dismissed.has(i));
  if (!visible.length) return null;

  return (
    <div className="space-y-2 mb-4 animate-slide-in">
      {visible.map((alert, i) => (
        <div key={i} className={clsx(
          'rounded-lg border p-3',
          getRiskBgColor(alert.risk_level)
        )}>
          <div className="flex items-start gap-3">
            <AlertTriangle size={16} className={clsx('shrink-0 mt-0.5', getRiskColor(alert.risk_level))} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className={clsx('text-xs font-bold uppercase', getRiskColor(alert.risk_level))}>
                    {getRiskLabel(alert.risk_level)}
                  </span>
                  <span className="text-xs text-gray-400">• {alert.area} • {formatDatetime(alert.timestamp)}</span>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => {
                    const s = new Set(expanded);
                    s.has(i) ? s.delete(i) : s.add(i);
                    setExpanded(s);
                  }} className="text-gray-500 hover:text-gray-300">
                    {expanded.has(i) ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                  <button onClick={() => setDismissed(s => new Set([...s, i]))}
                    className="text-gray-500 hover:text-gray-300">
                    <X size={14} />
                  </button>
                </div>
              </div>
              <p className="text-xs text-gray-300 mt-0.5">{alert.message}</p>
              <div className="flex gap-4 mt-1">
                <span className="text-xs text-gray-400">Demand: <span className="text-white">{formatMW(alert.predicted_demand)}</span></span>
                <span className="text-xs text-gray-400">Capacity: <span className="text-white">{formatMW(alert.available_capacity)}</span></span>
                <span className="text-xs text-gray-400">Utilization: <span className={getRiskColor(alert.risk_level)}>{formatPercent(alert.utilization_pct)}</span></span>
              </div>
              {expanded.has(i) && alert.recommendations?.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {alert.recommendations.map((r, j) => (
                    <li key={j} className="text-xs text-gray-300 flex items-start gap-1.5">
                      <span className={clsx('mt-1 w-1.5 h-1.5 rounded-full shrink-0', getRiskColor(alert.risk_level).replace('text-', 'bg-'))} />
                      {r}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
