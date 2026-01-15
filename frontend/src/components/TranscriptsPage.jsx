import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import HelpModal from './HelpModal';

const TranscriptsPage = () => {
  const [transcripts, setTranscripts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterBank, setFilterBank] = useState('all');
  const [expandedId, setExpandedId] = useState(null);
  const [sentences, setSentences] = useState({});
  const [loadingSentences, setLoadingSentences] = useState({});
  const [showHelp, setShowHelp] = useState(false);
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/transcripts`)
      .then(res => res.json())
      .then(data => {
        setTranscripts(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch transcripts:', err);
        setLoading(false);
      });
  }, []);

  const handleTranscriptClick = (transcriptId) => {
    if (expandedId === transcriptId) {
      setExpandedId(null);
      return;
    }

    setExpandedId(transcriptId);

    if (!sentences[transcriptId]) {
      setLoadingSentences(prev => ({ ...prev, [transcriptId]: true }));
      fetch(`${API_BASE_URL}/api/transcripts/${transcriptId}/sentences`)
        .then(res => res.json())
        .then(data => {
          setSentences(prev => ({ ...prev, [transcriptId]: data }));
          setLoadingSentences(prev => ({ ...prev, [transcriptId]: false }));
        })
        .catch(err => {
          console.error('Failed to fetch sentences:', err);
          setLoadingSentences(prev => ({ ...prev, [transcriptId]: false }));
        });
    }
  };

  const filteredTranscripts = transcripts.filter(t => {
    if (filterBank === 'all') return true;
    if (filterBank === 'fed') return t.bank.toLowerCase().includes('fed');
    if (filterBank === 'boc') return t.bank.toLowerCase().includes('boc') || t.bank.toLowerCase().includes('canada');
    return true;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-[#050505] text-slate-100 font-mono p-6 md:p-16">
        <div className="p-20 text-center animate-pulse tracking-widest text-slate-500 text-xl uppercase">
          LOADING_TRANSCRIPTS...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505] text-slate-100 font-mono p-6 md:p-16">
      <style>{`
        * {
          outline: none !important;
        }
        *:focus {
          outline: none !important;
        }
      `}</style>

      <div className="max-w-7xl mx-auto">
        <header className="mb-14 border-b-2 border-slate-700 pb-10">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-5xl font-extrabold uppercase tracking-tight bg-gradient-to-r from-blue-400 via-white to-red-400 bg-clip-text text-transparent" style={{ textShadow: '0 0 40px rgba(59, 130, 246, 0.3), 0 0 40px rgba(239, 68, 68, 0.3)' }}>
                Transcripts
              </h1>
              <p className="text-slate-300 mt-4 text-lg uppercase font-bold tracking-wider">
                Central Bank Sentiment Analysis Archive
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
                to="/"
                className="px-6 py-2 text-xs font-bold border border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200 transition-all duration-300 uppercase"
              >
                ← Back to Dashboard
              </Link>
            </div>
          </div>
        </header>

        <HelpModal showHelp={showHelp} setShowHelp={setShowHelp} />

        <div className="flex gap-4 mb-10 border-b border-slate-900 pb-5">
          {['all', 'fed', 'boc'].map(bank => (
            <button
              key={bank}
              onClick={() => setFilterBank(bank)}
              className={`px-4 py-1.5 text-[10px] font-bold border transition-all duration-300 uppercase ${
                filterBank === bank
                  ? 'bg-[#fff] text-black border-[#fff] shadow-lg scale-105'
                  : 'border-slate-800 text-slate-500 hover:border-slate-600 hover:text-slate-300 hover:scale-105'
              }`}
            >
              {bank === 'all' ? 'All Banks' : bank === 'fed' ? 'Federal Reserve' : 'Bank of Canada'}
            </button>
          ))}
        </div>

        <div className="mb-6 text-sm text-slate-500 uppercase tracking-wide">
          Showing {filteredTranscripts.length} transcript{filteredTranscripts.length !== 1 ? 's' : ''}
        </div>
        <div className="space-y-6">
          {filteredTranscripts.length === 0 ? (
            <div className="text-center py-20 text-slate-600">
              <p className="text-lg uppercase tracking-wide">No transcripts found</p>
            </div>
          ) : (
            filteredTranscripts.map((transcript, idx) => (
              <div
                key={idx}
                className="bg-gradient-to-br from-[#0d0d0d] to-[#1a1a1a] border border-slate-900 hover:border-slate-700 hover:card-glow hover:scale-[1.01] transition-all duration-300"
              >
                <div
                  className="p-6 cursor-pointer"
                  onClick={() => handleTranscriptClick(transcript.id)}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className={`px-3 py-1 text-xs font-black uppercase ${
                          transcript.bank.toLowerCase().includes('fed')
                            ? 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                            : 'bg-red-500/10 text-red-400 border border-red-500/30'
                        }`}>
                          {transcript.bank}
                        </span>
                        <span className="text-slate-500 text-xs uppercase tracking-wide">
                          {new Date(transcript.date).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                          })}
                        </span>
                      </div>
                      {transcript.title && (
                        <h3 className="text-lg font-bold text-slate-200 uppercase tracking-tight">
                          {transcript.title}
                        </h3>
                      )}
                    </div>

                    <div className="text-right ml-4">
                      <div className="text-xs text-slate-500 uppercase mb-1">Sentiment</div>
                      <div className={`text-3xl font-bold ${
                        transcript.sentiment > 0
                          ? 'text-green-400 glow-green'
                          : transcript.sentiment < 0
                          ? 'text-red-400 glow-red'
                          : 'text-slate-400'
                      }`}>
                        {transcript.sentiment > 0 ? '+' : ''}{transcript.sentiment.toFixed(3)}
                      </div>
                      <div className="text-xs text-slate-600 uppercase mt-1">
                        {transcript.sentiment > 0.3 ? 'Hawkish' : transcript.sentiment < -0.3 ? 'Dovish' : 'Neutral'}
                      </div>
                    </div>

                    <div className="ml-4 text-slate-500">
                      <span className="text-2xl">
                        {expandedId === transcript.id ? '−' : '+'}
                      </span>
                    </div>
                  </div>

                  {expandedId !== transcript.id && transcript.excerpt && (
                    <div className="mt-4 p-4 bg-slate-900/30 border-l-2 border-slate-700">
                      <div className="text-xs text-slate-500 uppercase mb-2">Excerpt</div>
                      <p className="text-sm text-slate-300 leading-relaxed line-clamp-4">
                        {transcript.excerpt}
                      </p>
                    </div>
                  )}
                </div>

                {expandedId === transcript.id && (
                  <div className="border-t border-slate-800 bg-black/30">
                    {loadingSentences[transcript.id] ? (
                      <div className="p-8 text-center text-slate-500 text-sm uppercase tracking-wide">
                        Loading sentence analysis...
                      </div>
                    ) : sentences[transcript.id] && sentences[transcript.id].length > 0 ? (
                      <div className="p-6 space-y-4 max-h-[600px] overflow-y-auto">
                        <div className="text-xs text-slate-500 uppercase mb-4 font-bold tracking-wider">
                          Sentence-by-Sentence Analysis ({sentences[transcript.id].length} sentences)
                        </div>
                        {sentences[transcript.id].map((sentence, idx) => (
                          <div
                            key={sentence.id}
                            className="bg-slate-900/40 border border-slate-800 p-4 rounded hover:border-slate-700 transition-all duration-300"
                          >
                            <div className="mb-3">
                              <span className="text-slate-600 text-xs mr-2">#{idx + 1}</span>
                              <span className="text-slate-200 text-sm leading-relaxed">
                                {sentence.text}
                              </span>
                            </div>

                            <div className="flex gap-6 mb-3">
                              <div>
                                <span className="text-[10px] text-slate-600 uppercase">Stance Score:</span>
                                <span className={`ml-2 text-sm font-bold ${
                                  sentence.score > 0
                                    ? 'text-green-400'
                                    : sentence.score < 0
                                    ? 'text-red-400'
                                    : 'text-slate-400'
                                }`}>
                                  {sentence.score > 0 ? '+' : ''}{sentence.score.toFixed(3)}
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-600 uppercase">Impact Weight:</span>
                                <span className="ml-2 text-sm font-bold text-slate-400">
                                  {sentence.impact.toFixed(3)}
                                </span>
                              </div>
                              {sentence.topic && (
                                <div>
                                  <span className="text-[10px] text-slate-600 uppercase">Topic:</span>
                                  <span className="ml-2 text-sm text-slate-300">
                                    {sentence.topic}
                                  </span>
                                </div>
                              )}
                            </div>

                            {sentence.reasoning && (
                              <div className="mt-3 p-3 bg-slate-950/50 border-l-2 border-slate-700">
                                <div className="text-[10px] text-slate-600 uppercase mb-1">AI Justification:</div>
                                <p className="text-xs text-slate-400 leading-relaxed">
                                  {sentence.reasoning}
                                </p>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-8 text-center text-slate-600 text-sm uppercase tracking-wide">
                        No sentence analysis available
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

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
};

export default TranscriptsPage;
