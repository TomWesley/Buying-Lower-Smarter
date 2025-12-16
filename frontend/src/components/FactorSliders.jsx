function FactorSliders({ weights, onChange, disabled = false, readOnly = false }) {
  const factors = [
    { key: 'industry', label: 'Industry (Tech/Healthcare)', description: 'Bonus for technology/healthcare companies' },
    { key: 'dividends', label: 'Low Dividend', description: 'Bonus for dividend yield < 1%' },
    { key: 'reit', label: 'Non-REIT', description: 'Bonus for non-REIT stocks' },
    { key: 'severity_of_loss', label: 'Loss Severity', description: 'Bonus for larger daily losses (>5%)' },
    { key: 'ranking', label: 'Ranking', description: 'Bonus for being the biggest loser (#1)' },
    { key: 'volume', label: 'High Volume', description: 'Bonus for volume > 30M' },
  ];

  const handleChange = (key, value) => {
    if (onChange && !readOnly) {
      onChange({ ...weights, [key]: value });
    }
  };

  const totalWeight = Object.values(weights).reduce((sum, w) => sum + w, 0);

  return (
    <div className="space-y-4">
      {factors.map((factor) => (
        <div key={factor.key}>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-300">{factor.label}</span>
            <span className="text-gray-400">{weights[factor.key] || 0}%</span>
          </div>
          {readOnly ? (
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{ width: `${weights[factor.key] || 0}%` }}
              />
            </div>
          ) : (
            <input
              type="range"
              min="0"
              max="50"
              value={weights[factor.key] || 0}
              onChange={(e) => handleChange(factor.key, parseInt(e.target.value))}
              className="w-full"
              disabled={disabled}
            />
          )}
          <div className="text-xs text-gray-500">{factor.description}</div>
        </div>
      ))}

      <div className="pt-2 border-t border-gray-700 flex justify-between text-sm">
        <span className="text-gray-400">Total Weight</span>
        <span className={totalWeight === 100 ? 'text-green-400' : 'text-yellow-400'}>
          {totalWeight}% {totalWeight !== 100 && '(should be 100%)'}
        </span>
      </div>
    </div>
  );
}

export default FactorSliders;
