import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { useState } from 'react';
import DivergenceChart from './components/DivergenceChart';
import TranscriptsPage from './components/TranscriptsPage';
import HelpModal from './components/HelpModal';

function Dashboard() {
  const [showHelp, setShowHelp] = useState(false);

  return (
    <div className="min-h-screen bg-[#0c0c0c] text-gray-100 p-6 md:p-12 lg:px-16">
      <div className="max-w-[1400px] mx-auto">
        <header className="mb-10 pb-6 border-b border-gray-800/60">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-baseline gap-2.5">
                <h1 className="text-3xl font-bold tracking-tight text-white">
                  F<span className="lowercase">in</span>SENT
                </h1>
                <span className="text-[11px] text-gray-600 font-medium">v1.0</span>
              </div>
              <p className="text-gray-500 mt-2 text-[13px]">
                Monetary policy sentiment — <span className="text-blue-400/90">Fed</span> vs <span className="text-red-400/90">BoC</span>
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowHelp(true)}
                className="px-3.5 py-1.5 text-xs font-medium text-gray-500 rounded-md hover:text-gray-300 hover:bg-white/5 transition-all duration-150"
              >
                Help
              </button>
              <Link
                to="/transcripts"
                className="px-3.5 py-1.5 text-xs font-medium text-gray-500 rounded-md hover:text-gray-300 hover:bg-white/5 transition-all duration-150"
              >
                Transcripts →
              </Link>
            </div>
          </div>
        </header>

        <HelpModal showHelp={showHelp} setShowHelp={setShowHelp} />

        <main>
          <DivergenceChart />
        </main>

        <footer className="mt-16 pt-6 border-t border-gray-800/40 text-[11px] text-gray-600">
          Data from federalreserve.gov and bankofcanada.ca · Updated hourly
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