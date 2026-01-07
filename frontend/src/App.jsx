import DivergenceChart from './components/DivergenceChart';

function App() {
  return (
    
    <div className="min-h-screen bg-black-950 p-8 text-white">
      <div className="max-w-6xl mx-auto">
        <header className="mb-12">
          <h1 className="text-4xl font-bold tracking-tight">
            Regime<span className="text-blue-500">Mapper</span>
          </h1>
          <p className="text-slate-400 mt-2 text-lg">
            Monetary Policy Sentiment: Federal Reserve vs. Bank of Canada
          </p>
        </header>

        <main className="bg-slate-900 rounded-2xl border border-slate-800 p-1">
          <DivergenceChart />
        </main>
      </div>
    </div>
  );
}

export default App;