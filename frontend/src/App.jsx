import { useState } from 'react';
import Training from './pages/Training';
import Analysis from './pages/Analysis';
import Models from './pages/Models';
import { TrendingDown, FlaskConical, LineChart, Settings } from 'lucide-react';

function App() {
  const [currentPage, setCurrentPage] = useState('training');

  const navItems = [
    { id: 'training', label: 'Training', icon: FlaskConical },
    { id: 'analysis', label: 'Analysis', icon: LineChart },
    { id: 'models', label: 'Models', icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <TrendingDown className="w-8 h-8 text-red-500" />
              <div>
                <h1 className="text-xl font-bold">Biggest Losers Analysis</h1>
                <p className="text-sm text-gray-400">S&P 500 Daily Losers Strategy Backtester</p>
              </div>
            </div>
            <nav className="flex gap-2">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setCurrentPage(item.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                    currentPage === item.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </button>
              ))}
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {currentPage === 'training' && <Training />}
        {currentPage === 'analysis' && <Analysis />}
        {currentPage === 'models' && <Models />}
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 border-t border-gray-700 mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-4 text-center text-gray-400 text-sm">
          Stock Analysis Tool - Historical S&P 500 biggest losers strategy backtesting
        </div>
      </footer>
    </div>
  );
}

export default App;
