import React from 'react';
import ModelComparisonChart from '../components/charts/ModelComparisonChart';
import { useModelComparison } from '../hooks/useApi';
import { Trophy } from 'lucide-react';

export default function ModelComparison() {
  const { data, isLoading } = useModelComparison();

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white">Model Comparison</h1>
        <p className="text-sm text-gray-500 mt-0.5">Performance metrics across all trained algorithms</p>
      </div>

      {data?.best_model && (
        <div className="card border-l-4 border-l-yellow-500">
          <div className="flex items-center gap-3">
            <Trophy className="text-yellow-400" size={24} />
            <div>
              <p className="text-sm text-gray-400">Best Performing Model</p>
              <p className="text-xl font-bold text-yellow-400">{data.best_model}</p>
            </div>
            {data.models?.length > 0 && (() => {
              const best = data.models.find((m: any) => m.model === data.best_model);
              if (!best) return null;
              return (
                <div className="ml-auto flex gap-6">
                  {[['RMSE', best.rmse], ['MAE', best.mae], ['MAPE', best.mape + '%'], ['R²', best.r2]].map(([k, v]) => (
                    <div key={String(k)} className="text-center">
                      <p className="text-xs text-gray-500">{k}</p>
                      <p className="text-sm font-bold text-white">{typeof v === 'number' ? v.toFixed(3) : v}</p>
                    </div>
                  ))}
                </div>
              );
            })()}
          </div>
        </div>
      )}

      <div className="card">
        <p className="card-header">Algorithm Performance Comparison</p>
        {isLoading ? (
          <div className="h-64 flex items-center justify-center text-gray-500 text-sm animate-pulse">Loading...</div>
        ) : data?.models?.length > 0 ? (
          <ModelComparisonChart models={data.models} bestModel={data.best_model} />
        ) : (
          <div className="h-64 flex items-center justify-center text-gray-500 text-sm">
            No trained models yet — go to Upload Data to start training
          </div>
        )}
      </div>
    </div>
  );
}
