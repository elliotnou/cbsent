import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { useState } from 'react';
import DivergenceChart from './components/DivergenceChart';
import TranscriptsPage from './components/TranscriptsPage';
import HelpModal from './components/HelpModal';

function Dashboard() {
  const [showHelp, setShowHelp] = useState(false);

  return (
    <div className="min-h-screen bg-[#111] text-gray-100 p-6 md:p-14">
      <div className="max-w-7xl mx-auto">
        <header className="mb-12 border-b border-gray-800 pb-8">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-baseline gap-3">
                <h1 className="text-4xl font-bold tracking-tight text-white">
                  F<span className="lowercase">in</span>SENT
                </h1>
                <span className="text-xs text-gray-500 font-medium">v1.0</span>
              </div>
              <p className="text-gray-400 mt-3 text-sm">
                Monetary Policy Sentiment &mdash; <span className="text-blue-400">Fed</span> vs <span className="text-red-400">BoC</span>
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowHelp(true)}
                className="px-4 py-1.5 text-xs font-medium border border-gray-700 text-gray-400 rounded hover:border-gray-500 hover:text-gray-200 transition-colors"
              >
                Help
              </button>
              <Link
                to="/transcripts"
                className="px-4 py-1.5 text-xs font-medium border border-gray-700 text-gray-400 rounded hover:border-gray-500 hover:text-gray-200 transition-colors"
              >
                Transcripts
              </Link>
            </div>
          </div>
        </header>

        <HelpModal showHelp={showHelp} setShowHelp={setShowHelp} />

        <main>
          <DivergenceChart />
        </main>

        <footer className="mt-20 pt-8 border-t border-gray-800 text-xs text-gray-500">
          <p>
            Data: <span className="text-gray-400">Federal Reserve</span> (federalreserve.gov), <span className="text-gray-400">Bank of Canada</span> (bankofcanada.ca)
          </p>
        </footer>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/transcripts" element={<TranscriptsPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;