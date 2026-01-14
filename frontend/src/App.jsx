import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import DivergenceChart from './components/DivergenceChart';
import TranscriptsPage from './components/TranscriptsPage';

function Dashboard() {
  return (
    <div className="min-h-screen bg-[#050505] text-slate-100 font-mono p-6 md:p-16">
      <div className="max-w-7xl mx-auto">
        <header className="mb-14 border-b-2 border-slate-700 pb-10">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-5xl font-extrabold text-[#e0e0e0] uppercase tracking-tight drop-shadow-lg">
                FinSENT
              </h1>
              <p className="text-slate-300 mt-4 text-lg uppercase font-bold tracking-wider">
                Monetary Policy Sentiment Analysis // <span className="text-blue-400">Fed</span> vs. <span className="text-red-400">BoC</span>
              </p>
            </div>
            <Link
              to="/transcripts"
              className="px-6 py-2 text-xs font-bold border border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200 transition-all uppercase"
            >
              View Transcripts →
            </Link>
          </div>
        </header>

        <main>
          <DivergenceChart />
        </main>

        <footer className="mt-24 pt-10 border-t-2 border-slate-700 text-xs text-slate-400 uppercase tracking-widest font-bold">
          Source: Central Bank Transcripts
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