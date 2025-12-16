import { useState, useEffect } from 'react';
import { training, data } from '../api/client';
import { Play, Loader2, CheckCircle, XCircle, TrendingUp, TrendingDown, BarChart3, History, Trash2, Eye } from 'lucide-react';
import FactorSliders from '../components/FactorSliders';
import ResultsTable from '../components/ResultsTable';

function Training() {
  const [startDate, setStartDate] = useState('2014-01-01');
  const [endDate, setEndDate] = useState('2019-01-01');
  const [holdYears, setHoldYears] = useState([2, 5]);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [runId, setRunId] = useState(null);
  const [dateRange, setDateRange] = useState(null);
  const [previousRuns, setPreviousRuns] = useState([]);
  const [loadingRuns, setLoadingRuns] = useState(true);

  // Fetch available date range and previous runs on mount
  useEffect(() => {
    data.getDateRange().then((res) => {
      setDateRange(res.data);
    }).catch(console.error);

    fetchPreviousRuns();
  }, []);

  const fetchPreviousRuns = async () => {
    setLoadingRuns(true);
    try {
      const res = await training.listRuns();
      setPreviousRuns(res.data);
    } catch (err) {
      console.error('Failed to fetch previous runs:', err);
    } finally {
      setLoadingRuns(false);
    }
  };

  const startTraining = async () => {
    setIsRunning(true);
    setProgress(0);
    setMessage('Starting training...');
    setError(null);
    setResults(null);

    try {
      const response = await training.startRun(startDate, endDate, holdYears);
      const id = response.data.run_id;
      setRunId(id);

      // Poll for status
      const pollStatus = async () => {
        try {
          const statusRes = await training.getStatus(id);
          setProgress(statusRes.data.progress);
          setMessage(statusRes.data.message || '');

          if (statusRes.data.status === 'completed') {
            const resultsRes = await training.getResults(id);
            setResults(resultsRes.data);
            setIsRunning(false);
            fetchPreviousRuns(); // Refresh runs list
          } else if (statusRes.data.status === 'failed') {
            setError(statusRes.data.message || 'Training failed');
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

  const loadPreviousRun = async (id) => {
    setError(null);
    setMessage('Loading previous run...');
    try {
      const resultsRes = await training.getResults(id);
      setResults(resultsRes.data);
      setRunId(id);
      // Update hold years based on loaded data
      const loadedHoldYears = resultsRes.data.summary.hold_periods || [2, 5];
      setHoldYears(loadedHoldYears);
      setMessage('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load run');
    }
  };

  const deletePreviousRun = async (id) => {
    if (!confirm('Are you sure you want to delete this training run?')) return;
    try {
      await training.deleteRun(id);
      fetchPreviousRuns();
      // Clear results if we deleted the currently loaded run
      if (runId === id) {
        setResults(null);
        setRunId(null);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete run');
    }
  };

  return (
    <div className="space-y-6">
      {/* Configuration Panel */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Training Configuration</h2>
        <p className="text-gray-400 text-sm mb-6">
          Select a date range to analyze biggest losers and discover patterns.
          The training will identify which factors correlate with better returns.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Date Range */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              min={dateRange?.start_date}
              max={endDate}
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
              min={startDate}
              max={dateRange?.end_date}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
              disabled={isRunning}
            />
          </div>

          {/* Hold Period Selection */}
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
        </div>

        {/* Run Button */}
        <div className="mt-6 flex items-center gap-4">
          <button
            onClick={startTraining}
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
                Start Training
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
            <div className="flex items-center gap-2 text-green-400">
              <CheckCircle className="w-5 h-5" />
              Training complete!
            </div>
          )}
        </div>
      </div>

      {/* Previous Training Runs */}
      {previousRuns.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <History className="w-5 h-5" />
            Previous Training Runs
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-700 text-gray-300">
                <tr>
                  <th className="px-3 py-2 text-left">ID</th>
                  <th className="px-3 py-2 text-left">Date Range</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Picks</th>
                  <th className="px-3 py-2 text-left">Created</th>
                  <th className="px-3 py-2 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {previousRuns.map((run) => (
                  <tr
                    key={run.id}
                    className={`border-b border-gray-700 hover:bg-gray-700/50 ${
                      runId === run.id ? 'bg-blue-900/20' : ''
                    }`}
                  >
                    <td className="px-3 py-2 text-gray-400">#{run.id}</td>
                    <td className="px-3 py-2">
                      {run.start_date} to {run.end_date}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs ${
                          run.status === 'completed'
                            ? 'bg-green-500/20 text-green-400'
                            : run.status === 'failed'
                            ? 'bg-red-500/20 text-red-400'
                            : 'bg-yellow-500/20 text-yellow-400'
                        }`}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td className="px-3 py-2">{run.pick_count}</td>
                    <td className="px-3 py-2 text-gray-400">
                      {new Date(run.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-2">
                        {run.status === 'completed' && (
                          <button
                            onClick={() => loadPreviousRun(run.id)}
                            className="p-1.5 text-blue-400 hover:bg-blue-500/20 rounded"
                            title="Load results"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => deletePreviousRun(run.id)}
                          className="p-1.5 text-red-400 hover:bg-red-500/20 rounded"
                          title="Delete run"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {loadingRuns && previousRuns.length === 0 && (
        <div className="bg-gray-800 rounded-lg p-6 flex items-center justify-center">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          Loading previous runs...
        </div>
      )}

      {/* Results */}
      {results && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <SummaryCard
              title="Total Picks"
              value={results.summary.total_picks}
              subtitle={`${results.summary.total_trading_days} trading days`}
            />
            {holdYears.map((year) => {
              const analysis = results.analysis[`${year}y`];
              if (!analysis) return null;
              return (
                <SummaryCard
                  key={year}
                  title={`${year}Y Avg Return`}
                  value={`${analysis.avg_return}%`}
                  subtitle={`Win rate: ${analysis.win_rate}%`}
                  trend={analysis.avg_return > (analysis.spy_avg_return || 0) ? 'up' : 'down'}
                  comparison={analysis.spy_avg_return ? `SPY: ${analysis.spy_avg_return}%` : null}
                />
              );
            })}
          </div>

          {/* Factor Analysis */}
          {results.analysis['2y']?.factor_analysis && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Factor Analysis (2Y Returns)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(results.analysis['2y'].factor_analysis).map(([factor, data]) => (
                  <FactorCard key={factor} factor={factor} data={data} />
                ))}
              </div>
            </div>
          )}

          {/* Suggested Weights */}
          {results.analysis['2y']?.suggested_weights && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold mb-4">Suggested Weights (Based on 2Y Analysis)</h3>
              <FactorSliders
                weights={results.analysis['2y'].suggested_weights}
                readOnly
              />
            </div>
          )}

          {/* Results Table */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Training Data ({results.picks.length} picks)</h3>
            <ResultsTable picks={results.picks} holdYears={holdYears} />
          </div>
        </>
      )}
    </div>
  );
}

function SummaryCard({ title, value, subtitle, trend, comparison }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="text-sm text-gray-400">{title}</div>
      <div className="flex items-center gap-2 mt-1">
        <div className="text-2xl font-bold">{value}</div>
        {trend === 'up' && <TrendingUp className="w-5 h-5 text-green-400" />}
        {trend === 'down' && <TrendingDown className="w-5 h-5 text-red-400" />}
      </div>
      {subtitle && <div className="text-sm text-gray-400 mt-1">{subtitle}</div>}
      {comparison && (
        <div className="text-xs text-gray-500 mt-1">{comparison}</div>
      )}
    </div>
  );
}

function FactorCard({ factor, data }) {
  const formatFactor = (f) => {
    return f.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  };

  const isSignificant = data.significant;
  const correlation = data.correlation;

  return (
    <div className={`p-4 rounded-lg border ${isSignificant ? 'border-green-500/30 bg-green-500/5' : 'border-gray-600 bg-gray-700/30'}`}>
      <div className="font-medium">{formatFactor(factor)}</div>
      <div className="flex items-center gap-2 mt-2">
        <span className={`text-lg font-bold ${correlation > 0 ? 'text-green-400' : 'text-red-400'}`}>
          {correlation > 0 ? '+' : ''}{correlation}
        </span>
        {isSignificant && (
          <span className="text-xs px-2 py-0.5 bg-green-500/20 text-green-400 rounded">
            Significant
          </span>
        )}
      </div>
      <div className="text-xs text-gray-400 mt-1">p-value: {data.p_value}</div>
      {data.note && <div className="text-xs text-gray-500 mt-1">{data.note}</div>}
    </div>
  );
}

export default Training;
