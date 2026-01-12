import DivergenceChart from './components/DivergenceChart';

function App() {
  return (
    <div className="min-h-screen bg-[#050505] text-slate-100 font-mono p-6 md:p-16">
      <div className="max-w-7xl mx-auto">
        <header className="mb-14 border-b-2 border-slate-700 pb-10">
          <h1 className="text-5xl font-extrabold text-[#e0e0e0] uppercase tracking-tight drop-shadow-lg">
            Divergence Engine
          </h1>
          <p className="text-slate-300 mt-4 text-lg uppercase font-bold tracking-wider">
            Monetary Policy Sentiment Analysis // <span className="text-blue-400">Fed</span> vs. <span className="text-red-400">BoC</span>
          </p>
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

export default App;