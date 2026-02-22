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
        console.error('fetch transcripts failed:', err);
        setLoading(false);
      });
  }, []);

  const handleTranscriptClick = (id) => {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(id);
    if (!sentences[id]) {
      setLoadingSentences(prev => ({ ...prev, [id]: true }));
      fetch(`${API_BASE_URL}/api/transcripts/${id}/sentences`)
        .then(res => res.json())
        .then(data => {
          setSentences(prev => ({ ...prev, [id]: data }));
          setLoadingSentences(prev => ({ ...prev, [id]: false }));
        })
        .catch(err => {
          console.error('fetch sentences failed:', err);
          setLoadingSentences(prev => ({ ...prev, [id]: false }));
        });
    }
  };

  const filtered = transcripts.filter(t => {
    if (filterBank === 'all') return true;
    if (filterBank === 'fed') return t.bank.toLowerCase().includes('fed');
    if (filterBank === 'boc') return t.bank.toLowerCase().includes('boc') || t.bank.toLowerCase().includes('canada');
    return true;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0c0c0c] text-gray-100 flex items-center justify-center">
        <div className="text-sm text-gray-500">Loading transcripts...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0c0c0c] text-gray-100 p-6 md:p-12 lg:px-16">
      <div className="max-w-[1400px] mx-auto">
        <header className="mb-10 pb-6 border-b border-gray-800/60">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Transcripts</h1>
              <p className="text-gray-500 mt-1.5 text-[13px]">Sentence-level sentiment analysis</p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowHelp(true)}
                className="px-3.5 py-1.5 text-xs font-medium text-gray-500 rounded-md hover:text-gray-300 hover:bg-white/5 transition-all duration-150"
              >
                Help
              </button>
              <Link
                to="/"
                className="px-3.5 py-1.5 text-xs font-medium text-gray-500 rounded-md hover:text-gray-300 hover:bg-white/5 transition-all duration-150"
              >
                ← Dashboard
              </Link>
            </div>
          </div>
        </header>

        <HelpModal showHelp={showHelp} setShowHelp={setShowHelp} />

        {/* filter */}
        <div className="flex gap-1.5 mb-6">
          {['all', 'fed', 'boc'].map(bank => (
            <button
              key={bank}
              onClick={() => setFilterBank(bank)}
              className={`px-3 py-1 text-xs rounded-md transition-all duration-150 ${filterBank === bank
                  ? 'bg-white text-gray-900 font-medium shadow-sm'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                }`}
            >
              {bank === 'all' ? 'All' : bank === 'fed' ? 'Fed' : 'BoC'}
            </button>
          ))}
          <span className="ml-3 text-[11px] text-gray-600 self-center">{filtered.length} results</span>
        </div>

        <div className="space-y-3">
          {filtered.length === 0 ? (
            <div className="text-center py-16 text-gray-600 text-sm">No transcripts found</div>
          ) : (
            filtered.map((transcript) => (
              <div
                key={transcript.id}
                className="bg-[#141414] border border-gray-800/80 rounded-lg hover:border-gray-700/80 transition-colors"
              >
                <div
                  className="p-4 cursor-pointer select-none"
                  onClick={() => handleTranscriptClick(transcript.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2.5 mb-1">
                        <span className={`inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium rounded ${transcript.bank.toLowerCase().includes('fed')
                            ? 'bg-blue-500/10 text-blue-400'
                            : 'bg-red-500/10 text-red-400'
                          }`}>
                          {transcript.bank}
                        </span>
                        <span className="text-gray-600 text-[11px]">
                          {new Date(transcript.date).toLocaleDateString('en-US', {
                            year: 'numeric', month: 'short', day: 'numeric'
                          })}
                        </span>
                      </div>
                      {transcript.title && (
                        <h3 className="text-sm text-gray-300 truncate pr-4">{transcript.title}</h3>
                      )}
                    </div>

                    <div className="flex items-center gap-3 flex-shrink-0">
                      <div className="text-right">
                        <div className={`text-lg font-semibold tabular-nums ${transcript.sentiment > 0 ? 'text-emerald-400'
                            : transcript.sentiment < 0 ? 'text-rose-400'
                              : 'text-gray-500'
                          }`}>
                          {transcript.sentiment > 0 ? '+' : ''}{transcript.sentiment.toFixed(3)}
                        </div>
                        <div className="text-[10px] text-gray-600">
                          {transcript.sentiment > 0.3 ? 'Hawkish' : transcript.sentiment < -0.3 ? 'Dovish' : 'Neutral'}
                        </div>
                      </div>
                      <span className="text-gray-700 text-sm">
                        {expandedId === transcript.id ? '▾' : '▸'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* expanded sentence detail */}
                {expandedId === transcript.id && (
                  <div className="border-t border-gray-800/60">
                    {loadingSentences[transcript.id] ? (
                      <div className="p-5 text-center text-gray-500 text-xs">Loading sentences...</div>
                    ) : sentences[transcript.id]?.length > 0 ? (
                      <div className="p-4 space-y-2 max-h-[500px] overflow-y-auto">
                        <div className="text-[11px] text-gray-600 mb-2">{sentences[transcript.id].length} sentences</div>
                        {sentences[transcript.id].map((sentence, idx) => (
                          <div
                            key={sentence.id}
                            className="bg-[#0f0f0f] border border-gray-800/50 p-3 rounded-md"
                          >
                            <div className="mb-2">
                              <span className="text-gray-700 text-[10px] mr-1.5">{idx + 1}.</span>
                              <span className="text-gray-300 text-[13px] leading-relaxed">{sentence.text}</span>
                            </div>
                            <div className="flex items-center gap-4 text-[11px]">
                              <span>
                                <span className="text-gray-600">Score </span>
                                <span className={`font-medium ${sentence.score > 0 ? 'text-emerald-400'
                                    : sentence.score < 0 ? 'text-rose-400'
                                      : 'text-gray-500'
                                  }`}>
                                  {sentence.score > 0 ? '+' : ''}{sentence.score.toFixed(3)}
                                </span>
                              </span>
                              <span>
                                <span className="text-gray-600">Weight </span>
                                <span className="text-gray-400">{sentence.impact.toFixed(1)}</span>
                              </span>
                              {sentence.topic && (
                                <span className="text-gray-500">{sentence.topic}</span>
                              )}
                            </div>
                            {sentence.reasoning && (
                              <p className="mt-1.5 text-[11px] text-gray-600 leading-relaxed">{sentence.reasoning}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-5 text-center text-gray-600 text-xs">No sentence data</div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        <footer className="mt-16 pt-6 border-t border-gray-800/40 text-[11px] text-gray-600">
          Data from federalreserve.gov and bankofcanada.ca · Updated hourly
        </footer>
      </div>
    </div>
  );
};

export default TranscriptsPage;
