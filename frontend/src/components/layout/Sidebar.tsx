import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, TrendingUp, Map, AlertTriangle,
  Brain, Settings, Zap, ChevronLeft, ChevronRight,
  Radio, Scale, Sun
} from 'lucide-react';
import { useDataStatus } from '../../hooks/useApi';
import clsx from 'clsx';

const NAV = [
  { to: '/',               icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/live',           icon: Radio,            label: 'Live Delhi Data' },
  { to: '/demand',         icon: TrendingUp,       label: 'Demand Forecast' },
  { to: '/areas',          icon: Map,              label: 'Area Analysis' },
  { to: '/risk',           icon: AlertTriangle,    label: 'Risk Analysis' },
  { to: '/load-balancing', icon: Scale,            label: 'Load Balancing' },
  { to: '/solar',          icon: Sun,              label: 'Solar Prediction' },
  { to: '/models',         icon: Brain,            label: 'Models' },
  { to: '/settings',       icon: Settings,         label: 'Settings' },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { data: status } = useDataStatus();
  const apiOnline = !!status;

  return (
    <aside className={clsx(
      'flex flex-col bg-gray-900 border-r border-gray-800 transition-all duration-200',
      collapsed ? 'w-16' : 'w-56'
    )}>
      <div className="flex items-center justify-between px-3 py-4 border-b border-gray-800">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <Zap className="text-sky-400" size={20} />
            <span className="font-bold text-sky-400 text-sm">GridForecast AI</span>
          </div>
        )}
        {collapsed && <Zap className="text-sky-400 mx-auto" size={20} />}
        <button
          onClick={() => setCollapsed(c => !c)}
          className="text-gray-500 hover:text-gray-300 transition-colors ml-auto"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      <nav className="flex-1 py-3 space-y-0.5 px-2 overflow-y-auto">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => clsx(
              'flex items-center gap-3 px-2 py-2 rounded-lg text-sm font-medium transition-colors',
              isActive
                ? 'bg-sky-900/60 text-sky-300'
                : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
            )}
          >
            <Icon size={18} className="shrink-0" />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className={clsx(
        'flex items-center gap-2 px-3 py-3 border-t border-gray-800',
        collapsed && 'justify-center'
      )}>
        <span className={clsx(
          'inline-block w-2 h-2 rounded-full shrink-0',
          apiOnline ? 'bg-green-400' : 'bg-red-400'
        )} />
        {!collapsed && (
          <span className={clsx('text-xs', apiOnline ? 'text-green-400' : 'text-red-400')}>
            {apiOnline ? 'API Connected' : 'API Offline'}
          </span>
        )}
      </div>
    </aside>
  );
}
