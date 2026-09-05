import React from 'react';

export default function Settings() {
  return (
    <div className="space-y-5 max-w-xl">
      <div>
        <h1 className="text-xl font-bold text-white">Settings</h1>
        <p className="text-sm text-gray-500 mt-0.5">System configuration</p>
      </div>

      <div className="card space-y-4">
        <p className="card-header">Grid Configuration</p>
        {[
          { label: 'Default Location (Latitude)', placeholder: '28.6139' },
          { label: 'Default Location (Longitude)', placeholder: '77.2090' },
          { label: 'Default Grid Capacity (MW)', placeholder: '10000' },
          { label: 'Forecast Horizon (Hours)', placeholder: '48' },
        ].map(({ label, placeholder }) => (
          <div key={label}>
            <label className="block text-xs text-gray-400 mb-1">{label}</label>
            <input type="text" defaultValue={placeholder}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white
                focus:outline-none focus:border-sky-600 transition-colors" />
          </div>
        ))}
      </div>

      <div className="card">
        <p className="card-header">Data Sources</p>
        <div className="space-y-3 text-sm text-gray-400">
          <div className="flex items-start gap-2">
            <span className="text-green-400 mt-0.5">✓</span>
            <div>
              <p className="text-white">Open-Meteo (Weather)</p>
              <p className="text-xs">Free API — no key required. archive-api.open-meteo.com</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-sky-400 mt-0.5">→</span>
            <div>
              <p className="text-white">POSOCO / NLDC</p>
              <p className="text-xs">Download from <a href="https://posoco.in/reports/" target="_blank"
                className="text-sky-400 underline" rel="noreferrer">posoco.in/reports/</a> and upload via Data Upload page</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-sky-400 mt-0.5">→</span>
            <div>
              <p className="text-white">State SLDC Reports</p>
              <p className="text-xs">Download from respective state load dispatch center websites</p>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <p className="card-header">Risk Thresholds</p>
        <div className="space-y-2 text-xs text-gray-400">
          {[
            { level: 'Normal', range: '< 70%', color: 'bg-green-500' },
            { level: 'Elevated', range: '70–85%', color: 'bg-yellow-500' },
            { level: 'High', range: '85–95%', color: 'bg-orange-500' },
            { level: 'Critical', range: '95–100%', color: 'bg-red-500' },
            { level: 'Capacity Exceeded', range: '> 100%', color: 'bg-purple-500' },
          ].map(({ level, range, color }) => (
            <div key={level} className="flex items-center gap-3">
              <span className={`w-3 h-3 rounded-full ${color}`} />
              <span className="text-white w-36">{level}</span>
              <span>{range} utilization</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
