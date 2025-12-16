import { useState, useEffect } from 'react';
import { models } from '../api/client';
import { Save, Trash2, Plus } from 'lucide-react';
import FactorSliders from '../components/FactorSliders';

const DEFAULT_WEIGHTS = {
  industry: 15,
  dividends: 15,
  reit: 10,
  severity_of_loss: 30,
  ranking: 10,
  volume: 20,
};

function Models() {
  const [savedModels, setSavedModels] = useState([]);
  const [newModelName, setNewModelName] = useState('');
  const [newModelWeights, setNewModelWeights] = useState(DEFAULT_WEIGHTS);
  const [newModelThreshold, setNewModelThreshold] = useState(65);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);

  // Load saved models
  const loadModels = async () => {
    try {
      const res = await models.list();
      setSavedModels(res.data);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadModels();
  }, []);

  const saveModel = async () => {
    if (!newModelName.trim()) {
      setError('Please enter a model name');
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      await models.create(newModelName, newModelWeights, newModelThreshold);
      setNewModelName('');
      setNewModelWeights(DEFAULT_WEIGHTS);
      setNewModelThreshold(65);
      await loadModels();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const deleteModel = async (modelId) => {
    if (!confirm('Are you sure you want to delete this model?')) return;

    try {
      await models.delete(modelId);
      await loadModels();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Create New Model */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Plus className="w-5 h-5" />
          Create New Scoring Model
        </h2>
        <p className="text-gray-400 text-sm mb-6">
          Create and save scoring models with custom weights and thresholds.
          Use these models to run consistent analyses.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Model Name
              </label>
              <input
                type="text"
                value={newModelName}
                onChange={(e) => setNewModelName(e.target.value)}
                placeholder="e.g., High Volume Tech Focus"
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Confidence Threshold: {newModelThreshold}
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={newModelThreshold}
                onChange={(e) => setNewModelThreshold(parseInt(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>0 (All picks)</span>
                <span>100 (Most selective)</span>
              </div>
            </div>

            {error && (
              <div className="text-red-400 text-sm">{error}</div>
            )}

            <button
              onClick={saveModel}
              disabled={isSaving}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg font-medium transition-colors"
            >
              <Save className="w-4 h-4" />
              {isSaving ? 'Saving...' : 'Save Model'}
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Scoring Weights
            </label>
            <FactorSliders
              weights={newModelWeights}
              onChange={setNewModelWeights}
            />
          </div>
        </div>
      </div>

      {/* Saved Models */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Saved Models</h2>

        {savedModels.length === 0 ? (
          <p className="text-gray-400">No saved models yet. Create one above!</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {savedModels.map((model) => (
              <div key={model.id} className="bg-gray-700 rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-medium">{model.name}</h3>
                  <button
                    onClick={() => deleteModel(model.id)}
                    className="text-red-400 hover:text-red-300 p-1"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <div className="text-sm text-gray-400 mb-3">
                  Threshold: {model.threshold}
                </div>

                <div className="space-y-1 text-xs">
                  {Object.entries(model.weights).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-gray-400 capitalize">{key.replace(/_/g, ' ')}</span>
                      <span>{value}%</span>
                    </div>
                  ))}
                </div>

                {(model.avg_return !== null || model.win_rate !== null) && (
                  <div className="mt-3 pt-3 border-t border-gray-600 text-sm">
                    {model.avg_return !== null && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">Avg Return</span>
                        <span className={model.avg_return > 0 ? 'text-green-400' : 'text-red-400'}>
                          {model.avg_return}%
                        </span>
                      </div>
                    )}
                    {model.win_rate !== null && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">Win Rate</span>
                        <span>{model.win_rate}%</span>
                      </div>
                    )}
                  </div>
                )}

                <div className="mt-3 text-xs text-gray-500">
                  Created: {new Date(model.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Default Weights Reference */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Default Weights Reference</h2>
        <p className="text-gray-400 text-sm mb-4">
          These are the original weights derived from 2014-2019 training data.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {Object.entries(DEFAULT_WEIGHTS).map(([key, value]) => (
            <div key={key} className="bg-gray-700 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold">{value}%</div>
              <div className="text-xs text-gray-400 capitalize mt-1">
                {key.replace(/_/g, ' ')}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Models;
