import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, CheckCircle, XCircle, Play, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { uploadLoadData, uploadCapacityData, startTraining } from '../api/endpoints';
import { useTrainingStatus, useDataStatus } from '../hooks/useApi';
import clsx from 'clsx';

const ALL_MODELS = [
  'LinearRegression', 'KNN', 'DecisionTree', 'RandomForest',
  'XGBoost', 'GradientBoosting', 'NaiveBayes', 'CNN', 'LSTM', 'HybridLSTMCNN', 'Prophet'
];

function DropZone({ label, accept, onFile, uploaded }: {
  label: string; accept: string; onFile: (f: File) => void; uploaded?: string
}) {
  const onDrop = useCallback((files: File[]) => { if (files[0]) onFile(files[0]); }, [onFile]);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'text/csv': ['.csv'], 'application/vnd.ms-excel': ['.xls', '.xlsx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] }, maxFiles: 1
  });
  return (
    <div {...getRootProps()} className={clsx(
      'border-2 border-dashed rounded-xl p-6 cursor-pointer transition-colors',
      isDragActive ? 'border-sky-500 bg-sky-900/20' : 'border-gray-700 hover:border-gray-500',
      uploaded && 'border-green-700 bg-green-900/10'
    )}>
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-2 text-center">
        {uploaded ? (
          <>
            <CheckCircle className="text-green-400" size={28} />
            <p className="text-green-400 text-sm font-medium">{uploaded}</p>
          </>
        ) : (
          <>
            <Upload className="text-gray-500" size={28} />
            <p className="text-sm text-gray-300 font-medium">{label}</p>
            <p className="text-xs text-gray-500">Drop CSV/Excel or click to browse</p>
          </>
        )}
      </div>
    </div>
  );
}

export default function DataUpload() {
  const [loadFile, setLoadFile] = useState<string>('');
  const [capFile, setCapFile] = useState<string>('');
  const [selectedModels, setSelectedModels] = useState<string[]>(
    ['LinearRegression', 'RandomForest', 'XGBoost', 'GradientBoosting', 'Prophet']
  );
  const [isTraining, setIsTraining] = useState(false);
  const { data: status } = useTrainingStatus(isTraining);
  const { data: dataStatus } = useDataStatus();

  const handleLoadFile = async (file: File) => {
    const tid = toast.loading(`Uploading ${file.name}...`);
    try {
      const res = await uploadLoadData(file);
      setLoadFile(file.name);
      toast.success(`Loaded ${res.rows.toLocaleString()} rows`, { id: tid });
    } catch (e: any) {
      toast.error(`Upload failed: ${e.message}`, { id: tid });
    }
  };

  const handleCapFile = async (file: File) => {
    const tid = toast.loading(`Uploading ${file.name}...`);
    try {
      const res = await uploadCapacityData(file);
      setCapFile(file.name);
      toast.success(`Loaded ${res.plants} plants (${res.total_installed_mw.toFixed(0)} MW installed)`, { id: tid });
    } catch (e: any) {
      toast.error(`Upload failed: ${e.message}`, { id: tid });
    }
  };

  const toggleModel = (m: string) =>
    setSelectedModels(s => s.includes(m) ? s.filter(x => x !== m) : [...s, m]);

  const handleTrain = async () => {
    if (selectedModels.length === 0) {
      toast.error('Select at least one model'); return;
    }
    setIsTraining(true);
    try {
      await startTraining({ model_list: selectedModels });
      toast.success('Training started! This may take several minutes.');
    } catch (e: any) {
      setIsTraining(false);
      toast.error(`Failed to start training: ${e.message}`);
    }
  };

  const trainingDone = status?.status === 'completed' || status?.status === 'failed';
  if (trainingDone && isTraining) setIsTraining(false);

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-bold text-white">Data Upload & Training</h1>
        <p className="text-sm text-gray-500 mt-0.5">Upload your data files and train all ML models</p>
      </div>

      <div className="card">
        <p className="card-header">System Status</p>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Load Data', ok: dataStatus?.load_data_uploaded },
            { label: 'Capacity Data', ok: dataStatus?.capacity_data_uploaded },
            { label: 'Models Trained', ok: dataStatus?.models_trained },
          ].map(({ label, ok }) => (
            <div key={label} className={clsx(
              'flex items-center gap-2 p-2 rounded-lg text-sm',
              ok ? 'bg-green-900/20 text-green-400' : 'bg-gray-800 text-gray-500'
            )}>
              {ok ? <CheckCircle size={14} /> : <XCircle size={14} />}
              {label}
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <p className="card-header">Upload Data Files</p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-gray-400 mb-2 font-medium">Load Data (CSV/Excel)</p>
            <DropZone label="Upload Load/Demand Data" accept=".csv,.xlsx,.xls"
              onFile={handleLoadFile} uploaded={loadFile} />
            <p className="text-xs text-gray-600 mt-1">
              Expected columns: datetime, gross_demand_mw (or demand/load/mw),
              area, node, consumer_type, solar_generation_mw
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-2 font-medium">Capacity Data (CSV)</p>
            <DropZone label="Upload Capacity Data" accept=".csv"
              onFile={handleCapFile} uploaded={capFile} />
            <p className="text-xs text-gray-600 mt-1">
              Expected columns: plant_name, area, fuel_type, installed_mw, availability_factor
            </p>
          </div>
        </div>
      </div>

      <div className="card">
        <p className="card-header">Select Models to Train</p>
        <div className="flex flex-wrap gap-2">
          {ALL_MODELS.map(m => (
            <button key={m} onClick={() => toggleModel(m)}
              className={clsx(
                'px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors',
                selectedModels.includes(m)
                  ? 'bg-sky-700 border-sky-600 text-white'
                  : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-500'
              )}>{m}</button>
          ))}
        </div>
        <p className="text-xs text-gray-600 mt-2">
          CNN, LSTM, HybridLSTMCNN require TensorFlow. They will be skipped if not installed.
          If no load data uploaded, realistic synthetic Indian grid data will be auto-generated.
        </p>
      </div>

      {status && status.status !== 'idle' && (
        <div className="card">
          <p className="card-header">Training Progress</p>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300 capitalize">{status.status.replace('_', ' ')}</span>
              <span className="text-sm font-medium text-sky-400">{status.progress_pct}%</span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2">
              <div className="bg-sky-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${status.progress_pct}%` }} />
            </div>
            {status.current_model && (
              <p className="text-xs text-gray-400">
                Training: <span className="text-sky-300 font-medium">{status.current_model}</span>
              </p>
            )}
            {status.status === 'completed' && status.metrics && (
              <div className="mt-3">
                <p className="text-xs text-gray-400 mb-2">Results:</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-gray-400">
                    <thead>
                      <tr className="border-b border-gray-800">
                        <th className="text-left py-1">Model</th>
                        <th className="text-right py-1">RMSE</th>
                        <th className="text-right py-1">MAE</th>
                        <th className="text-right py-1">MAPE%</th>
                        <th className="text-right py-1">R²</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(status.metrics as any[]).slice(0, 5).map((m: any, i: number) => (
                        <tr key={m.model} className={`border-b border-gray-800/50 ${i === 0 ? 'text-sky-300' : ''}`}>
                          <td className="py-1">{i === 0 ? '★ ' : ''}{m.model}</td>
                          <td className="text-right py-1">{m.rmse?.toFixed(2)}</td>
                          <td className="text-right py-1">{m.mae?.toFixed(2)}</td>
                          <td className="text-right py-1">{m.mape?.toFixed(2)}</td>
                          <td className="text-right py-1">{m.r2?.toFixed(3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            {status.status === 'failed' && (
              <p className="text-xs text-red-400 mt-1">Error: {status.error}</p>
            )}
          </div>
        </div>
      )}

      <button onClick={handleTrain} disabled={isTraining}
        className={clsx(
          'flex items-center gap-2 px-6 py-3 rounded-xl font-medium text-sm transition-colors',
          isTraining
            ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
            : 'bg-sky-600 hover:bg-sky-500 text-white'
        )}>
        {isTraining ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
        {isTraining ? `Training... ${status?.progress_pct || 0}%` : 'Start Training All Models'}
      </button>
    </div>
  );
}
