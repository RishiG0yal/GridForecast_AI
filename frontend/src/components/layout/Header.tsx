import React, { useState, useEffect } from 'react';
import { RefreshCw, Clock } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useDashboardOverview } from '../../hooks/useApi';
import { getRiskLabel, getRiskBgColor, getRiskColor } from '../../utils/formatters';
import clsx from 'clsx';

export default function Header() {
  const [now, setNow] = useState(new Date());
  const queryClient = useQueryClient();
  const { data: overview } = useDashboardOverview();

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const riskLevel = overview?.risk_level || 'unknown';

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800">
      <div className="flex items-center gap-2 text-gray-400 text-sm">
        <Clock size={14} />
        <span>{now.toLocaleString('en-IN', {
          weekday: 'short', day: '2-digit', month: 'short', year: 'numeric',
          hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
        })}</span>
      </div>

      <div className="flex items-center gap-4">
        <div className={clsx(
          'flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-medium',
          getRiskBgColor(riskLevel)
        )}>
          <span className={clsx('w-2 h-2 rounded-full', riskLevel === 'normal' ? 'bg-green-400' :
            riskLevel === 'elevated' ? 'bg-yellow-400' : riskLevel === 'high' ? 'bg-orange-400' :
            riskLevel === 'critical' ? 'bg-red-400 animate-pulse' :
            riskLevel === 'capacity_exceeded' ? 'bg-purple-400 animate-pulse' : 'bg-gray-400')} />
          <span className={getRiskColor(riskLevel)}>{getRiskLabel(riskLevel)}</span>
        </div>

        <button
          onClick={() => queryClient.invalidateQueries()}
          className="flex items-center gap-1.5 text-gray-400 hover:text-gray-200 text-xs transition-colors"
        >
          <RefreshCw size={13} />
          <span>Refresh</span>
        </button>
      </div>
    </header>
  );
}
