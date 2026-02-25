import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { HelpCircle, MessageSquare, FileText, Sun, Moon } from 'lucide-react';
import DivergenceChart from './components/DivergenceChart';
import TranscriptsPage from './components/TranscriptsPage';
import ChatPage from './components/ChatPage';
import HelpModal from './components/HelpModal';

function useTheme() {
  const [light, setLight] = useState(() => document.documentElement.classList.contains('light'));
  useEffect(() => {
    document.documentElement.classList.toggle('light', light);
  }, [light]);
  return [light, () => setLight(p => !p)] as const;
}

function Dashboard() {
  const [showHelp, setShowHelp] = useState(false);
  const [light, toggleTheme] = useTheme();

  return (
    <div className="min-h-screen theme-bg theme-text p-6 md:p-12 lg:px-16">
      <div className="max-w-[1400px] mx-auto">
        <header className="mb-10 pb-6 border-b theme-border animate-fade-in">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-[22px] font-semibold tracking-tight theme-heading">
                fin<span className="text-blue-400">SENT</span>
              </span>
              <span className="hidden sm:inline text-[11px] theme-muted font-normal tracking-wide">Monetary policy sentiment</span>
            </div>
            <div className="flex gap-1">
              <button
                onClick={toggleTheme}
                className="p-2 theme-muted rounded-lg hover:theme-heading hover:bg-white/5 transition-all duration-150"
                title={light ? 'Dark mode' : 'Light mode'}
              >
                {light ? <Moon size={16} /> : <Sun size={16} />}
              </button>
              <button
                onClick={() => setShowHelp(true)}
                className="p-2 theme-muted rounded-lg hover:theme-heading hover:bg-white/5 transition-all duration-150"
                title="Help"
              >
                <HelpCircle size={16} />
              </button>
              <Link
                to="/chat"
                className="p-2 theme-muted rounded-lg hover:theme-heading hover:bg-white/5 transition-all duration-150"
                title="Policy Analyst"
              >
                <MessageSquare size={16} />
              </Link>
              <Link
                to="/transcripts"
                className="p-2 theme-muted rounded-lg hover:theme-heading hover:bg-white/5 transition-all duration-150"
                title="Transcripts"
              >
                <FileText size={16} />
              </Link>
            </div>
          </div>
        </header>

        <HelpModal showHelp={showHelp} setShowHelp={setShowHelp} />

        <main className="animate-fade-in stagger-1">
          <DivergenceChart />
        </main>

        <footer className="mt-16 pt-6 border-t border-gray-800/40 text-[11px] text-gray-600 animate-fade-in stagger-4">
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
        <Route path="/chat" element={<ChatPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
