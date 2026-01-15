import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { useState } from 'react';
import DivergenceChart from './components/DivergenceChart';
import TranscriptsPage from './components/TranscriptsPage';
import HelpModal from './components/HelpModal';

function Dashboard() {
  const [showHelp, setShowHelp] = useState(false);

  return (
    <div className="min-h-screen bg-[#050505] text-slate-100 font-mono p-6 md:p-16">
      <div className="max-w-7xl mx-auto">
        <header className="mb-14 border-b-2 border-slate-700 pb-10">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-5xl font-extrabold text-[#e0e0e0] uppercase tracking-tight drop-shadow-lg transition-all duration-300 hover:text-white">
                FinSENT
              </h1>
              <p className="text-slate-300 mt-4 text-lg uppercase font-bold tracking-wider">
                Monetary Policy Sentiment Analysis // <span className="text-blue-400 glow-blue">Fed</span> vs. <span className="text-red-400 glow-red">BoC</span>
              </p>
            </div>
            <div className="flex gap-4">
              <button
                onClick={() => setShowHelp(true)}
                className="px-6 py-2 text-xs font-bold border border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200 transition-all duration-300 uppercase"
              >
                ? Help
              </button>
              <Link
                to="/transcripts"
                className="px-6 py-2 text-xs font-bold border border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200 transition-all duration-300 uppercase"
              >
                View Transcripts →
              </Link>
            </div>
          </div>
        </header>

        <HelpModal showHelp={showHelp} setShowHelp={setShowHelp} />


        <main>
          <DivergenceChart />
        </main>

        <footer className="mt-24 pt-10 border-t-2 border-slate-700 text-xs text-slate-400">
          <div className="space-y-3">
            <p className="uppercase tracking-widest font-bold">Data Sources</p>
            <p className="text-[10px] leading-relaxed normal-case font-normal tracking-normal">
              Press Releases: <span className="text-slate-300">Federal Reserve Monetary Policy Press Releases</span> (federalreserve.gov) and <span className="text-slate-300">Bank of Canada Press Releases</span> (bankofcanada.ca)
            </p>

          </div>
        </footer>
      </div>
    </div>
  );
}


function App(){
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