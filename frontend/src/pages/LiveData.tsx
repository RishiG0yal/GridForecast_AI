import React from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Radio, Database, Loader2 } from 'lucide-react';
import client from '../api/client';
import LiveDataPanel from '../components/live/LiveDataPanel';
import toast from 'react-hot-toast';

const fetchHistory = (days: number) =>
  client.get('/api/live/history', { params: { days } }).then(r => r.data);

export default function LiveData() {
  const { data: history } = useQuery({
    queryKey: ['live-history'],
    queryFn: () => fetchHistory(3),
    refetchInterval: 60000,
  });

  const buildDataset = useMutation({
    mutationFn: () => client.post('/api/live/build-dataset', null, { params: { days: 365 } }),
    onSuccess: () => toast.success('Building 365-day Delhi dataset with real weather. Check back in ~2 min.'),
    onError: () => toast.error('Build failed'),
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Radio size={20} className="text-green-400 animate-pulse" />
          Live Delhi Grid Data
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Real-time data from Delhi SLDC · Weather from Open-Meteo API
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <LiveDataPanel />

        <div className="card">
          <p className="card-header">Data Sources</p>
          <div className="space-y-3 text-sm">
            {[
              {
                name: 'Delhi SLDC (Live)',
                url: 'https://www.delhisldc.org',
                data: 'Delhi total load, BRPL/BYPL/NDPL/NDMC/MES demand, grid frequency, scheduled vs actual, OD/UD, peak demand',
                freq: 'Every 15 minutes (auto-scraped)',
                status: 'live',
              },
              {
                name: 'Open-Meteo (Live Weather)',
                url: 'https://open-meteo.com',
                data: 'Temperature, humidity, solar radiation, wind speed, cloud cover for Delhi (28.61°N, 77.21°E)',
                freq: 'Every 10 minutes',
                status: 'live',
              },
            ].map(src => (
              <div key={src.name} className="bg-gray-800 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`w-2 h-2 rounded-full ${src.status === 'live' ? 'bg-green-400' : 'bg-gray-500'}`} />
                  <span className="font-medium text-white text-xs">{src.name}</span>
                  <a href={src.url} target="_blank" rel="noreferrer"
                    className="text-sky-400 text-xs underline ml-auto">{src.url}</a>
                </div>
                <p className="text-xs text-gray-400 mb-0.5">{src.data}</p>
                <p className="text-xs text-gray-600">Refresh: {src.freq}</p>
              </div>
            ))}
          </div>

          <div className="mt-4 border-t border-gray-800 pt-4">
            <p className="text-xs text-gray-400 mb-3 font-medium">Build Full Training Dataset</p>
            <p className="text-xs text-gray-500 mb-3">
              Downloads 365 days of real Delhi weather + generates calibrated load profile
              (matching actual Delhi demand patterns: 5,000–8,748 MW range).
              After building, go to Upload Data → Train to get accurate predictions.
            </p>
            <button
              onClick={() => buildDataset.mutate()}
              disabled={buildDataset.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-sky-700 hover:bg-sky-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              {buildDataset.isPending ? <Loader2 size={14} className="animate-spin" /> : <Database size={14} />}
              Build Delhi Dataset (365 days)
            </button>
          </div>
        </div>
      </div>

      {history?.data?.length > 0 && (
        <div className="card">
          <p className="card-header">Recent SLDC Scrape History ({history.total_records} records)</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-gray-400">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left py-2 pr-4">Time</th>
                  <th className="text-right py-2 px-3">Delhi Load (MW)</th>
                  <th className="text-right py-2 px-3">Scheduled (MW)</th>
                  <th className="text-right py-2 px-3">Generation (MW)</th>
                  <th className="text-right py-2 px-3">Frequency (Hz)</th>
                  <th className="text-right py-2 pl-3">OD/UD (MW)</th>
                </tr>
              </thead>
              <tbody>
                {history.data.slice(-20).reverse().map((r: any, i: number) => (
                  <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-1.5 pr-4">{r.datetime}</td>
                    <td className="text-right py-1.5 px-3 text-white font-medium">
                      {r.gross_demand_mw ? r.gross_demand_mw.toLocaleString('en-IN') : '—'}
                    </td>
                    <td className="text-right py-1.5 px-3">
                      {r.scheduled_load_mw ? r.scheduled_load_mw.toLocaleString('en-IN') : '—'}
                    </td>
                    <td className="text-right py-1.5 px-3">
                      {r.generation_mw ? r.generation_mw.toLocaleString('en-IN') : '—'}
                    </td>
                    <td className={`text-right py-1.5 px-3 ${r.grid_frequency_hz >= 49.95 && r.grid_frequency_hz <= 50.05 ? 'text-green-400' : r.grid_frequency_hz ? 'text-orange-400' : ''}`}>
                      {r.grid_frequency_hz || '—'}
                    </td>
                    <td className={`text-right py-1.5 pl-3 ${r.od_ud_mw > 0 ? 'text-red-400' : r.od_ud_mw < 0 ? 'text-green-400' : ''}`}>
                      {r.od_ud_mw != null ? (r.od_ud_mw > 0 ? '+' : '') + r.od_ud_mw : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
