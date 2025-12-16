import { useState } from 'react';
import { ChevronUp, ChevronDown, ArrowUpDown } from 'lucide-react';

function ResultsTable({ picks, holdYears = [2, 5] }) {
  const [sortField, setSortField] = useState('loser_date');
  const [sortDir, setSortDir] = useState('desc');
  const [page, setPage] = useState(0);
  const [filter, setFilter] = useState('');
  const pageSize = 50;

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  // Filter picks
  const filteredPicks = picks.filter((pick) => {
    if (!filter) return true;
    const searchLower = filter.toLowerCase();
    return (
      pick.ticker?.toLowerCase().includes(searchLower) ||
      pick.industry?.toLowerCase().includes(searchLower)
    );
  });

  // Sort picks
  const sortedPicks = [...filteredPicks].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];

    if (aVal === null || aVal === undefined) return 1;
    if (bVal === null || bVal === undefined) return -1;

    const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    return sortDir === 'asc' ? comparison : -comparison;
  });

  // Paginate
  const totalPages = Math.ceil(sortedPicks.length / pageSize);
  const displayedPicks = sortedPicks.slice(page * pageSize, (page + 1) * pageSize);

  const SortHeader = ({ field, children }) => (
    <th
      onClick={() => handleSort(field)}
      className="px-3 py-2 text-left cursor-pointer hover:bg-gray-600 select-none"
    >
      <div className="flex items-center gap-1">
        {children}
        {sortField === field ? (
          sortDir === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
        ) : (
          <ArrowUpDown className="w-3 h-3 opacity-30" />
        )}
      </div>
    </th>
  );

  return (
    <div>
      {/* Filter */}
      <div className="mb-4 flex items-center gap-4">
        <input
          type="text"
          placeholder="Filter by ticker or industry..."
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value);
            setPage(0);
          }}
          className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white w-64"
        />
        <span className="text-sm text-gray-400">
          Showing {displayedPicks.length} of {filteredPicks.length} picks
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-700 text-gray-300">
            <tr>
              <SortHeader field="loser_date">Loser Date</SortHeader>
              <SortHeader field="purchase_date">Buy Date</SortHeader>
              <SortHeader field="ticker">Ticker</SortHeader>
              <SortHeader field="daily_loss_pct">Loss %</SortHeader>
              <SortHeader field="ranking">Rank</SortHeader>
              <SortHeader field="industry">Industry</SortHeader>
              <SortHeader field="confidence_score">Score</SortHeader>
              {holdYears.includes(2) && <SortHeader field="return_2y">2Y Return</SortHeader>}
              {holdYears.includes(5) && <SortHeader field="return_5y">5Y Return</SortHeader>}
              {holdYears.includes(2) && <SortHeader field="spy_return_2y">SPY 2Y</SortHeader>}
            </tr>
          </thead>
          <tbody>
            {displayedPicks.map((pick, i) => (
              <tr
                key={`${pick.loser_date}-${pick.ticker}-${i}`}
                className="border-b border-gray-700 hover:bg-gray-700/50"
              >
                <td className="px-3 py-2 text-gray-400">{pick.loser_date}</td>
                <td className="px-3 py-2">{pick.purchase_date || '-'}</td>
                <td className="px-3 py-2 font-medium">{pick.ticker}</td>
                <td className="px-3 py-2 text-red-400">
                  {pick.daily_loss_pct?.toFixed(2)}%
                </td>
                <td className="px-3 py-2">#{pick.ranking}</td>
                <td className="px-3 py-2 text-gray-400 truncate max-w-[150px]">
                  {pick.industry}
                </td>
                <td className="px-3 py-2">
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    pick.confidence_score >= 65
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-gray-600 text-gray-400'
                  }`}>
                    {pick.confidence_score?.toFixed(0)}
                  </span>
                </td>
                {holdYears.includes(2) && (
                  <td className={`px-3 py-2 ${
                    pick.return_2y > 0 ? 'text-green-400' : pick.return_2y < 0 ? 'text-red-400' : ''
                  }`}>
                    {pick.return_2y !== null ? `${pick.return_2y.toFixed(1)}%` : '-'}
                  </td>
                )}
                {holdYears.includes(5) && (
                  <td className={`px-3 py-2 ${
                    pick.return_5y > 0 ? 'text-green-400' : pick.return_5y < 0 ? 'text-red-400' : ''
                  }`}>
                    {pick.return_5y !== null ? `${pick.return_5y.toFixed(1)}%` : '-'}
                  </td>
                )}
                {holdYears.includes(2) && (
                  <td className="px-3 py-2 text-gray-400">
                    {pick.spy_return_2y !== null ? `${pick.spy_return_2y.toFixed(1)}%` : '-'}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="px-3 py-1 bg-gray-700 rounded disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm text-gray-400">
            Page {page + 1} of {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
            disabled={page >= totalPages - 1}
            className="px-3 py-1 bg-gray-700 rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

export default ResultsTable;
