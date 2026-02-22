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
      <div className="min-h-screen bg-[#111] text-gray-100 p-6 md:p-14">
        <div className="p-20 text-center text-gray-500 text-sm">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#111] text-gray-100 p-6 md:p-14">
      <div className="max-w-7xl mx-auto">
        <header className="mb-12 border-b border-gray-800 pb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white">Transcripts</h1>
              <p className="text-gray-400 mt-2 text-sm">Sentence-level sentiment breakdown</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowHelp(true)}
                className="px-4 py-1.5 text-xs font-medium border border-gray-700 text-gray-400 rounded hover:border-gray-500 hover:text-gray-200 transition-colors"
              >
                Help
              </button>
              <Link
                to="/"
                className="px-4 py-1.5 text-xs font-medium border border-gray-700 text-gray-400 rounded hover:border-gray-500 hover:text-gray-200 transition-colors"
              >
                ← Dashboard
              </Link>
            </div>
          </div>
        </header>

        <HelpModal showHelp={showHelp} setShowHelp={setShowHelp} />

        {/* bank filter */}
        <div className="flex gap-2 mb-8 border-b border-gray-800 pb-4">
          {['all', 'fed', 'boc'].map(bank => (
            <button
              key={bank}
              onClick={() => setFilterBank(bank)}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${filterBank === bank
                  ? 'bg-white text-black'
                  : 'border border-gray-800 text-gray-500 hover:border-gray-600 hover:text-gray-300'
                }`}
            >
              {bank === 'all' ? 'All Banks' : bank === 'fed' ? 'Federal Reserve' : 'Bank of Canada'}
            </button>
          ))}
        </div>

        <div className="mb-4 text-sm text-gray-500">
          {filtered.length} transcript{filtered.length !== 1 ? 's' : ''}
        </div>

        <div className="space-y-4">
          {filtered.length === 0 ? (
            <div className="text-center py-16 text-gray-600">
              <p>No transcripts found</p>
            </div>
          ) : (
            filtered.map((transcript) => (
              <div
                key={transcript.id}
                className="bg-[#1a1a1a] border border-gray-800 rounded-md hover:border-gray-700 transition-colors"
              >
                <div
                  className="p-5 cursor-pointer"
                  onClick={() => handleTranscriptClick(transcript.id)}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1.5">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded ${transcript.bank.toLowerCase().includes('fed')
                            ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                            : 'bg-red-500/10 text-red-400 border border-red-500/20'
                          }`}>
                          {transcript.bank}
                        </span>
                        <span className="text-gray-500 text-xs">
                          {new Date(transcript.date).toLocaleDateString('en-US', {
                            year: 'numeric', month: 'long', day: 'numeric'
                          })}
                        </span>
                      </div>
                      {transcript.title && (
                        <h3 className="text-sm font-medium text-gray-200">{transcript.title}</h3>
                      )}
                    </div>

                    <div className="text-right ml-4">
                      <div className="text-xs text-gray-500 mb-1">Sentiment</div>
                      <div className={`text-2xl font-semibold tabular-nums ${transcript.sentiment > 0 ? 'text-green-400'
                          : transcript.sentiment < 0 ? 'text-red-400'
                            : 'text-gray-400'
                        }`}>
                        {transcript.sentiment > 0 ? '+' : ''}{transcript.sentiment.toFixed(3)}
                      </div>
                      <div className="text-xs text-gray-600 mt-0.5">
                        {transcript.sentiment > 0.3 ? 'Hawkish' : transcript.sentiment < -0.3 ? 'Dovish' : 'Neutral'}
                      </div>
                    </div>

                    <div className="ml-3 text-gray-600 text-xl">
                      {expandedId === transcript.id ? '−' : '+'}
                    </div>
                  </div>

                  {expandedId !== transcript.id && transcript.excerpt && (
                    <div className="mt-3 p-3 bg-[#151515] border-l-2 border-gray-700 rounded-sm">
                      <p className="text-sm text-gray-400 leading-relaxed line-clamp-3">
                        {transcript.excerpt}
                      </p>
                    </div>
                  )}
                </div>

                {expandedId === transcript.id && (
                  <div className="border-t border-gray-800">
                    {loadingSentences[transcript.id] ? (
                      <div className="p-6 text-center text-gray-500 text-sm">Loading sentences...</div>
                    ) : sentences[transcript.id]?.length > 0 ? (
                      <div className="p-5 space-y-3 max-h-[600px] overflow-y-auto">
                        <div className="text-xs text-gray-500 mb-3">
                          {sentences[transcript.id].length} sentences
                        </div>
                        {sentences[transcript.id].map((sentence, idx) => (
                          <div
                            key={sentence.id}
                            className="bg-[#151515] border border-gray-800 p-3 rounded hover:border-gray-700 transition-colors"
                          >
                            <div className="mb-2">
                              <span className="text-gray-600 text-xs mr-2">#{idx + 1}</span>
                              <span className="text-gray-200 text-sm leading-relaxed">{sentence.text}</span>
                            </div>
                            <div className="flex gap-5 mb-2 text-xs">
                              <div>
                                <span className="text-gray-600">Score: </span>
                                <span className={`font-medium ${sentence.score > 0 ? 'text-green-400'
                                    : sentence.score < 0 ? 'text-red-400'
                                      : 'text-gray-400'
                                  }`}>
                                  {sentence.score > 0 ? '+' : ''}{sentence.score.toFixed(3)}
                                </span>
                              </div>
                              <div>
                                <span className="text-gray-600">Weight: </span>
                                <span className="text-gray-400">{sentence.impact.toFixed(2)}</span>
                              </div>
                              {sentence.topic && (
                                <div>
                                  <span className="text-gray-600">Topic: </span>
                                  <span className="text-gray-300">{sentence.topic}</span>
                                </div>
                              )}
                            </div>
                            {sentence.reasoning && (
                              <div className="mt-2 p-2 bg-[#111] border-l-2 border-gray-700 rounded-sm">
                                <p className="text-xs text-gray-500 leading-relaxed">{sentence.reasoning}</p>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-6 text-center text-gray-600 text-sm">No sentence data available</div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        <footer className="mt-20 pt-8 border-t border-gray-800 text-xs text-gray-500">
          <p>
            Data: <span className="text-gray-400">Federal Reserve</span> (federalreserve.gov), <span className="text-gray-400">Bank of Canada</span> (bankofcanada.ca)
          </p>
        </footer>
      </div>
    </div>
  );
};

export default TranscriptsPage;
