import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { useState } from 'react';
import DivergenceChart from './components/DivergenceChart';
import TranscriptsPage from './components/TranscriptsPage';

function Dashboard() {
  const [showHelp, setShowHelp] = useState(false);
  const [expandedScoring, setExpandedScoring] = useState(false);

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

        {showHelp && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={() => setShowHelp(false)}>
            <div className="bg-gradient-to-br from-[#0d0d0d] to-[#1a1a1a] border-2 border-slate-700 max-w-3xl w-full max-h-[80vh] overflow-y-auto shadow-2xl" onClick={(e) => e.stopPropagation()}>
              <div className="sticky top-0 bg-gradient-to-r from-[#0d0d0d] to-[#1a1a1a] border-b-2 border-slate-700 p-6 flex items-center justify-between">
                <h2 className="text-2xl font-black uppercase tracking-wider text-white">Help & Information</h2>
                <button
                  onClick={() => setShowHelp(false)}
                  className="text-slate-400 hover:text-white text-2xl font-bold transition-colors"
                >
                  ×
                </button>
              </div>

              <div className="p-8 space-y-8 text-slate-300">
                <section>
                  <h3 className="text-lg font-black uppercase tracking-wider text-blue-400 mb-3 border-l-2 border-blue-500 pl-3">What is FinSENT?</h3>
                  <p className="leading-relaxed text-sm">
                    FinSENT is a real-time sentiment analysis platform that tracks and compares monetary policy stances between the Federal Reserve (Fed) and the Bank of Canada (BoC). By analyzing official transcripts using AI, we quantify policy divergence and explore its relationship with USD/CAD exchange rates.
                  </p>
                </section>

                <section>
                  <h3 className="text-lg font-black uppercase tracking-wider text-green-400 mb-3 border-l-2 border-green-500 pl-3">How Scoring Works</h3>
                  <div className="space-y-3 text-sm">
                    <div>
                      <span className="font-bold text-green-400">Hawkish (+1.0):</span> Signals tighter monetary policy, higher interest rates, and inflation control focus.
                    </div>
                    <div>
                      <span className="font-bold text-slate-300">Neutral (0.0):</span> Balanced stance with no clear directional bias in policy.
                    </div>
                    <div>
                      <span className="font-bold text-red-400">Dovish (-1.0):</span> Indicates accommodative policy, lower interest rates, and growth stimulus.
                    </div>
                    <div className="mt-4 p-4 bg-slate-900/50 border-l-2 border-slate-700">
                      <span className="font-bold text-white">Divergence Score:</span> Calculated as Fed sentiment minus BoC sentiment. Positive values mean Fed is more hawkish than BoC, negative values indicate the opposite.
                    </div>
                  </div>
                </section>

                <section>
                  <h3 className="text-lg font-black uppercase tracking-wider text-purple-400 mb-3 border-l-2 border-purple-500 pl-3">Key Metrics Explained</h3>
                  <div className="space-y-4 text-sm">
                    <div>
                      <span className="font-bold text-white uppercase text-xs">Current Divergence:</span>
                      <p className="text-slate-400 mt-1">The latest difference between Fed and BoC sentiment. Shows real-time policy stance gap.</p>
                    </div>
                    <div>
                      <span className="font-bold text-white uppercase text-xs">Mean Divergence:</span>
                      <p className="text-slate-400 mt-1">Average divergence over the selected period. Reveals historical policy relationship trends.</p>
                    </div>
                    <div>
                      <span className="font-bold text-white uppercase text-xs">Volatility:</span>
                      <p className="text-slate-400 mt-1">Measures fluctuation in policy stance differences. Higher values indicate unstable divergence.</p>
                    </div>
                    <div>
                      <span className="font-bold text-white uppercase text-xs">Correlation:</span>
                      <p className="text-slate-400 mt-1">Statistical relationship between divergence and USD/CAD price movements. Values near +1 or -1 indicate strong predictive power.</p>
                    </div>
                  </div>
                </section>

                <section>
                  <h3 className="text-lg font-black uppercase tracking-wider text-yellow-400 mb-3 border-l-2 border-yellow-500 pl-3">Data & Methodology</h3>
                  <div className="space-y-2 text-sm">
                    <p><span className="font-bold text-white">Source:</span> Official FOMC and BoC meeting transcripts</p>
                    <p><span className="font-bold text-white">Analysis:</span> AI-powered sentence-level sentiment scoring using OpenAI GPT-4</p>
                    <p><span className="font-bold text-white">Updates:</span> Automated scraping and analysis runs hourly via GitHub Actions</p>
                    <p><span className="font-bold text-white">FX Data:</span> USD/CAD exchange rates from Alpha Vantage API</p>
                  </div>
                </section>

                <section>
                  <h3 className="text-lg font-black uppercase tracking-wider text-red-400 mb-3 border-l-2 border-red-500 pl-3">Navigation</h3>
                  <div className="space-y-2 text-sm">
                    <p><span className="font-bold text-white">Dashboard:</span> View policy divergence charts, statistics, and currency correlation</p>
                    <p><span className="font-bold text-white">Transcripts:</span> Browse full transcript archive with sentence-by-sentence analysis</p>
                    <p><span className="font-bold text-white">Time Ranges:</span> Filter data by All, 30d, 90d, or 1y periods</p>
                  </div>
                </section>

                <div className="pt-6 border-t border-slate-800 text-xs text-slate-500 text-center">
                  Built with React, FastAPI, PostgreSQL, and OpenAI GPT-4 • Deployed on Vercel and Render
                </div>
              </div>
            </div>
          </div>
        )}


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