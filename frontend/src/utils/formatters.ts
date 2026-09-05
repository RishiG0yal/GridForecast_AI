export const formatMW = (v: number | null | undefined): string => {
  if (v == null) return '—';
  return `${v.toLocaleString('en-IN', { maximumFractionDigits: 1 })} MW`;
};

export const formatPercent = (v: number | null | undefined): string => {
  if (v == null) return '—';
  return `${v.toFixed(1)}%`;
};

export const formatDatetime = (iso: string | null | undefined): string => {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  });
};

export const getRiskColor = (level: string): string => {
  const map: Record<string, string> = {
    normal: 'text-green-400',
    elevated: 'text-yellow-400',
    high: 'text-orange-400',
    critical: 'text-red-400',
    capacity_exceeded: 'text-purple-400',
    unknown: 'text-gray-400',
  };
  return map[level?.toLowerCase()] || 'text-gray-400';
};

export const getRiskBgColor = (level: string): string => {
  const map: Record<string, string> = {
    normal: 'bg-green-900/30 border-green-700',
    elevated: 'bg-yellow-900/30 border-yellow-700',
    high: 'bg-orange-900/30 border-orange-700',
    critical: 'bg-red-900/30 border-red-700',
    capacity_exceeded: 'bg-purple-900/30 border-purple-700',
    unknown: 'bg-gray-900/30 border-gray-700',
  };
  return map[level?.toLowerCase()] || 'bg-gray-900/30 border-gray-700';
};

export const getRiskLabel = (level: string): string => {
  const map: Record<string, string> = {
    normal: 'Normal',
    elevated: 'Elevated',
    high: 'High',
    critical: 'Critical',
    capacity_exceeded: 'Capacity Exceeded',
    unknown: 'Unknown',
  };
  return map[level?.toLowerCase()] || 'Unknown';
};

export const getRiskDotColor = (level: string): string => {
  const map: Record<string, string> = {
    normal: 'bg-green-400',
    elevated: 'bg-yellow-400',
    high: 'bg-orange-400',
    critical: 'bg-red-400',
    capacity_exceeded: 'bg-purple-400',
    unknown: 'bg-gray-400',
  };
  return map[level?.toLowerCase()] || 'bg-gray-400';
};

export const getUtilizationColor = (pct: number): string => {
  if (pct >= 100) return '#7c3aed';
  if (pct >= 95) return '#dc2626';
  if (pct >= 85) return '#ea580c';
  if (pct >= 70) return '#ca8a04';
  return '#16a34a';
};
