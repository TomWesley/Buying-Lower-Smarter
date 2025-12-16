import { useState, useEffect } from 'react';
import { analysis, models } from '../api/client';
import { Play, Loader2, CheckCircle, XCircle, Download, TrendingUp, TrendingDown } from 'lucide-react';
import FactorSliders from '../components/FactorSliders';
import ResultsTable from '../components/ResultsTable';

const DEFAULT_WEIGHTS = {
  industry: 15,
  dividends: 15,
  reit: 10,
  severity_of_loss: 30,
  ranking: 10,
  volume: 20,
};

function Analysis() {
  const [startDate, setStartDate] = useState('2000-01-01');
  const [endDate, setEndDate] = useState('2020-12-31');
  const [holdYears, setHoldYears] = useState([2, 5]);
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [threshold, setThreshold] = useState(65);
  const [savedModels, setSavedModels] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [runId, setRunId] = useState(null);

  // Load saved models
  useEffect(() => {
    models.list().then((res) => {
      setSavedModels(res.data);
    }).catch(console.error);
  }, []);

  const loadModel = (modelId) => {
    if (!modelId) {
      setWeights(DEFAULT_WEIGHTS);
      setThreshold(65);
      setSelectedModelId(null);
      return;
    }

    const model = savedModels.find((m) => m.id === parseInt(modelId));
    if (model) {
      setWeights(model.weights);
      setThreshold(model.threshold);
      setSelectedModelId(model.id);
    }
  };

  const startAnalysis = async () => {
    setIsRunning(true);
    setProgress(0);
    setMessage('Starting analysis...');
    setError(null);
    setResults(null);

    try {
      const response = await analysis.startRun(
        startDate,
        endDate,
        holdYears,
        weights,
        threshold,
        selectedModelId
      );
      const id = response.data.run_id;
      setRunId(id);

      // Poll for status
      const pollStatus = async () => {
        try {
          const statusRes = await analysis.getStatus(id);
          setProgress(statusRes.data.progress);
          setMessage(statusRes.data.message || '');

          if (statusRes.data.status === 'completed') {
            const resultsRes = await analysis.getResults(id);
            setResults(resultsRes.data);
            setIsRunning(false);
          } else if (statusRes.data.status === 'failed') {
            setError(statusRes.data.message || 'Analysis failed');
            setIsRunning(false);
          } else {
            setTimeout(pollStatus, 1000);
          }
        } catch (err) {
          setError(err.message);
          setIsRunning(false);
        }
      };

      pollStatus();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      setIsRunning(false);
    }
  };

  const toggleHoldYear = (year) => {
    if (holdYears.includes(year)) {
      if (holdYears.length > 1) {
        setHoldYears(holdYears.filter((y) => y !== year));
      }
    } else {
      setHoldYears([...holdYears, year].sort());
    }
  };

  return (
    <div className="space-y-6">
      {/* Configuration Panel */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Analysis Configuration</h2>
        <p className="text-gray-400 text-sm mb-6">
          Run a full backtest with your scoring model. Configure weights and threshold,
          then analyze historical performance vs SPY.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column: Date & Model */}
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Start Date
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                  disabled={isRunning}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  End Date
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                  disabled={isRunning}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Hold Periods
              </label>
              <div className="flex gap-2">
                {[2, 5].map((year) => (
                  <button
                    key={year}
                    onClick={() => toggleHoldYear(year)}
                    disabled={isRunning}
                    className={`px-4 py-2 rounded-lg transition-colors ${
                      holdYears.includes(year)
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {year} Years
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Load Saved Model
              </label>
              <select
                value={selectedModelId || ''}
                onChange={(e) => loadModel(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                disabled={isRunning}
              >
                <option value="">Custom Weights</option>
                {savedModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} (threshold: {model.threshold})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Confidence Threshold: {threshold}
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={threshold}
                onChange={(e) => setThreshold(parseInt(e.target.value))}
                className="w-full"
                disabled={isRunning}
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>0 (All picks)</span>
                <span>100 (Most selective)</span>
              </div>
            </div>
          </div>

          {/* Right Column: Weights */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Scoring Weights
            </label>
            <FactorSliders
              weights={weights}
              onChange={setWeights}
              disabled={isRunning}
            />
          </div>
        </div>

        {/* Run Button */}
        <div className="mt-6 flex items-center gap-4">
          <button
            onClick={startAnalysis}
            disabled={isRunning}
            className="flex items-center gap-2 px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 rounded-lg font-medium transition-colors"
          >
            {isRunning ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                Run Analysis
              </>
            )}
          </button>

          {isRunning && (
            <div className="flex-1">
              <div className="flex justify-between text-sm text-gray-400 mb-1">
                <span>{message}</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 text-red-400">
              <XCircle className="w-5 h-5" />
              {error}
            </div>
          )}

          {results && !isRunning && (
            <>
              <div className="flex items-center gap-2 text-green-400">
                <CheckCircle className="w-5 h-5" />
                Analysis complete!
              </div>
              <a
                href={analysis.exportCsv(runId)}
                className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
              >
                <Download className="w-4 h-4" />
                Export CSV
              </a>
            </>
          )}
        </div>
      </div>

      {/* Results */}
      {results && (
        <>
          {/* Summary Comparison */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Filtered Results */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-400" />
                Filtered Picks (Score &ge; {threshold})
              </h3>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-400">Total Picks</span>
                  <span className="font-bold">{results.summary.filtered_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Filter Rate</span>
                  <span>{results.summary.filter_rate}% of all picks</span>
                </div>
                {holdYears.map((year) => {
                  const stats = results.summary[`${year}y_filtered`];
                  if (!stats) return null;
                  return (
                    <div key={year} className="border-t border-gray-700 pt-4">
                      <div className="font-medium mb-2">{year}-Year Returns</div>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-400">Avg Return</span>
                          <span className={stats.avg_return > 0 ? 'text-green-400' : 'text-red-400'}>
                            {stats.avg_return}%
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Win Rate</span>
                          <span>{stats.win_rate}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">SPY Avg</span>
                          <span>{stats.spy_avg}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Outperformance</span>
                          <span className={stats.avg_return > stats.spy_avg ? 'text-green-400' : 'text-red-400'}>
                            {(stats.avg_return - stats.spy_avg).toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* All Results (No Filter) */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <TrendingDown className="w-5 h-5 text-gray-400" />
                All Picks (No Filter)
              </h3>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-400">Total Picks</span>
                  <span className="font-bold">{results.summary.total_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Trading Days</span>
                  <span>{results.summary.total_trading_days}</span>
                </div>
                {holdYears.map((year) => {
                  const stats = results.summary[`${year}y_all`];
                  if (!stats) return null;
                  return (
                    <div key={year} className="border-t border-gray-700 pt-4">
                      <div className="font-medium mb-2">{year}-Year Returns</div>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-400">Avg Return</span>
                          <span className={stats.avg_return > 0 ? 'text-green-400' : 'text-red-400'}>
                            {stats.avg_return}%
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Win Rate</span>
                          <span>{stats.win_rate}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">SPY Avg</span>
                          <span>{stats.spy_avg}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Outperformance</span>
                          <span className={stats.avg_return > stats.spy_avg ? 'text-green-400' : 'text-red-400'}>
                            {(stats.avg_return - stats.spy_avg).toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Results Table */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">
              Filtered Results ({results.filtered_picks.length} picks)
            </h3>
            <ResultsTable picks={results.filtered_picks} holdYears={holdYears} />
          </div>
        </>
      )}
    </div>
  );
}

export default Analysis;
