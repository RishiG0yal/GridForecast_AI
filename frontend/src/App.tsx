import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import Dashboard from './pages/Dashboard';
import DemandForecast from './pages/DemandForecast';
import AreaAnalysis from './pages/AreaAnalysis';
import RiskAnalysis from './pages/RiskAnalysis';
import ModelComparison from './pages/ModelComparison';
import LoadBalancing from './pages/LoadBalancing';
import SolarPrediction from './pages/SolarPrediction';
import LiveData from './pages/LiveData';
import Settings from './pages/Settings';

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-5">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/live" element={<LiveData />} />
            <Route path="/demand" element={<DemandForecast />} />
            <Route path="/areas" element={<AreaAnalysis />} />
            <Route path="/risk" element={<RiskAnalysis />} />
            <Route path="/load-balancing" element={<LoadBalancing />} />
            <Route path="/solar" element={<SolarPrediction />} />
            <Route path="/models" element={<ModelComparison />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
