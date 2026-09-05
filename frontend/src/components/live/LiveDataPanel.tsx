import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, Zap, Wind, Thermometer, Droplets } from 'lucide-react';
import client from '../../api/client';

import clsx from 'clsx';

const fetchLiveSnapshot = () => client.get('/api/live/snapshot').then(r => r.data);
const fetchLiveStatus = () => client.get('/api/live/status').then(r => r.data);

export default function LiveDataPanel() {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ['live-snapshot'],
    queryFn: fetchLiveSnapshot,
    refetchInterval: 60000,
  });
  const { data: status } = useQuery({
    queryKey: ['live-status'],
    queryFn: fetchLiveStatus,
    refetchInterval: 30000,
  });

  const scrapeNow = useMutation({
    mutationFn: () => client.post('/api/live/scrape-now'),
    onSuccess: () => setTimeout(() => qc.invalidateQueries({ queryKey: ['live-snapshot'] }), 8000),
  });

  const snap = data?.snapshot || {};
  const weather = data?.weather || {};
  const isLive = data?.is_live || status?.is_live;

  return (
    <div className="card border border-sky-900">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={clsx('w-2 h-2 rounded-full', isLive ? 'bg-green-400 animate-pulse' : 'bg-gray-500')} />
          <p className="card-header mb-0">Live Delhi Grid Data</p>
          {isLive && <span className="text-xs text-green-400 font-medium">LIVE</span>}
        </div>
        <button
          onClick={() => scrapeNow.mutate()}
          disabled={scrapeNow.isPending}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-200 transition-colors"
        >
          <RefreshCw size={12} className={scrapeNow.isPending ? 'animate-spin' : ''} />
          {scrapeNow.isPending ? 'Fetching...' : 'Refresh'}
        </button>
      </div>

      {snap.data_as_on && (
        <p className="text-xs text-gray-500 mb-3">
          Source: Delhi SLDC · As of {snap.data_as_on} IST
        </p>
      )}

      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-gray-800 rounded-lg p-2.5">
          <p className="text-xs text-gray-500 mb-0.5">Delhi Load</p>
          <p className="text-lg font-bold text-sky-400">
            {snap.delhi_load_mw ? `${snap.delhi_load_mw.toLocaleString('en-IN')} MW` : '—'}
          </p>
        </div>
        <div className="bg-gray-800 rounded-lg p-2.5">
          <p className="text-xs text-gray-500 mb-0.5">Grid Frequency</p>
          <p className={clsx('text-lg font-bold',
            snap.grid_frequency_hz >= 49.95 && snap.grid_frequency_hz <= 50.05 ? 'text-green-400' :
            snap.grid_frequency_hz ? 'text-orange-400' : 'text-gray-400'
          )}>
            {snap.grid_frequency_hz ? `${snap.grid_frequency_hz} Hz` : '—'}
          </p>
        </div>
        <div className="bg-gray-800 rounded-lg p-2.5">
          <p className="text-xs text-gray-500 mb-0.5">Scheduled Load</p>
          <p className="text-sm font-semibold text-white">
            {snap.scheduled_load_mw ? `${snap.scheduled_load_mw.toLocaleString('en-IN')} MW` : '—'}
          </p>
        </div>
        <div className="bg-gray-800 rounded-lg p-2.5">
          <p className="text-xs text-gray-500 mb-0.5">Total Generation</p>
          <p className="text-sm font-semibold text-white">
            {snap.total_generation_mw ? `${snap.total_generation_mw.toLocaleString('en-IN')} MW` : '—'}
          </p>
        </div>
      </div>

      {(snap.od_ud_mw != null) && (
        <div className={clsx(
          'flex items-center justify-between px-3 py-1.5 rounded-lg text-xs mb-3',
          snap.od_ud_mw > 0 ? 'bg-red-900/30 text-red-300' :
          snap.od_ud_mw < 0 ? 'bg-green-900/30 text-green-300' : 'bg-gray-800 text-gray-400'
        )}>
          <span>Over/Under Drawal</span>
          <span className="font-bold">{snap.od_ud_mw > 0 ? '+' : ''}{snap.od_ud_mw} MW</span>
        </div>
      )}

      {snap.peak_demand_today_mw && (
        <div className="flex items-center justify-between text-xs text-gray-400 mb-3">
          <span>Today's Peak</span>
          <span className="text-white font-medium">
            {snap.peak_demand_today_mw.toLocaleString('en-IN')} MW at {snap.peak_demand_today_time}
          </span>
        </div>
      )}

      {(weather.temperature != null) && (
        <div className="border-t border-gray-800 pt-3 mt-1">
          <p className="text-xs text-gray-500 mb-2">Delhi Weather (Open-Meteo Live)</p>
          <div className="flex gap-3 text-xs">
            <div className="flex items-center gap-1 text-orange-300">
              <Thermometer size={12} />
              <span>{weather.temperature}°C</span>
            </div>
            <div className="flex items-center gap-1 text-blue-300">
              <Droplets size={12} />
              <span>{weather.humidity}%</span>
            </div>
            <div className="flex items-center gap-1 text-gray-300">
              <Wind size={12} />
              <span>{weather.wind_speed} km/h</span>
            </div>
            {weather.solar_radiation != null && (
              <div className="flex items-center gap-1 text-yellow-300">
                <Zap size={12} />
                <span>{weather.solar_radiation} W/m²</span>
              </div>
            )}
          </div>
        </div>
      )}

      {!isLive && (
        <div className="mt-3 bg-yellow-900/20 border border-yellow-800 rounded-lg p-2.5 text-xs text-yellow-300">
          Live scraping starts automatically when backend runs. Data refreshes every 15 min.
        </div>
      )}

      <div className="mt-3 border-t border-gray-800 pt-2">
        <p className="text-xs text-gray-600">DISCOMs: BRPL (South/West) · BYPL (East/Central) · NDPL (North Delhi) · NDMC · MES</p>
      </div>
    </div>
  );
}
