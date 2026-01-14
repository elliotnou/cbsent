import { useEffect, useState } from 'react';
import React from 'react';
import { Link } from 'react-router-dom';

const TranscriptsPage = () => {
  const [transcripts, setTranscripts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterBank, setFilterBank] = useState('all');
  const [expandedId, setExpandedId] = useState(null);
  const [sentences, setSentences] = useState({});
  const [loadingSentences, setLoadingSentences] = useState({});
  const [showHelp, setShowHelp] = useState(false);
  const [expandedScoring, setExpandedScoring] = useState(false);
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (showHelp) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [showHelp]);

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
              <h1 className="text-5xl font-extrabold text-[#e0e0e0] uppercase tracking-tight drop-shadow-lg">
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

        {showHelp && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[100] flex items-center justify-center p-6 overflow-y-auto" onClick={() => setShowHelp(false)}>
            <div className="bg-gradient-to-br from-[#0d0d0d] to-[#1a1a1a] border-2 border-slate-700 max-w-3xl w-full max-h-[80vh] overflow-y-auto shadow-2xl relative" onClick={(e) => e.stopPropagation()}>
              <div className="sticky top-0 bg-gradient-to-r from-[#0d0d0d] to-[#1a1a1a] border-b-2 border-slate-700 p-6 flex items-center justify-between z-10">
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

                  <div className="space-y-4 text-sm">
                    <p className="leading-relaxed text-slate-300">
                      Each transcript is analyzed using a sophisticated AI-powered system that breaks down text into individual sentences, scores them, and aggregates results into a final transcript score.
                    </p>

                    <div className="space-y-3">
                      <div>
                        <span className="font-bold text-green-400">Hawkish (+1.0):</span> Signals tighter monetary policy, higher interest rates, and inflation control focus.
                      </div>
                      <div>
                        <span className="font-bold text-slate-300">Neutral (0.0):</span> Balanced stance with no clear bias toward raising or lowering interest rates.
                      </div>
                      <div>
                        <span className="font-bold text-red-400">Dovish (-1.0):</span> Indicates accommodative policy, lower interest rates, and growth stimulus.
                      </div>
                    </div>

                    <div className="mt-4 p-4 bg-slate-900/50 border-l-2 border-slate-700">
                      <span className="font-bold text-white">Divergence Score:</span> Calculated as Fed sentiment minus BoC sentiment. Positive values mean Fed is more hawkish than BoC, negative values indicate the opposite.
                    </div>

                    <button
                      onClick={() => setExpandedScoring(!expandedScoring)}
                      className="mt-4 w-full px-4 py-3 bg-gradient-to-r from-green-900/30 to-green-800/30 border border-green-700/50 hover:border-green-600 transition-all duration-300 text-left flex items-center justify-between group"
                    >
                      <span className="font-bold text-green-400 uppercase text-xs tracking-wider">Deep Dive: Scoring Methodology</span>
                      <span className="text-green-400 text-xl group-hover:scale-110 transition-transform">{expandedScoring ? '−' : '+'}</span>
                    </button>

                    {expandedScoring && (
                      <div className="mt-4 space-y-6 p-6 bg-black/40 border border-slate-800 animate-in fade-in duration-300">

                        <div>
                          <h4 className="font-black text-white uppercase text-sm mb-3 border-b border-slate-800 pb-2">1. Sentence-Level Analysis</h4>
                          <p className="text-slate-400 text-xs leading-relaxed mb-3">
                            Each sentence in a transcript is individually analyzed by GPT-4, which assigns:
                          </p>
                          <ul className="space-y-2 text-xs text-slate-400 ml-4">
                            <li className="flex items-start gap-2">
                              <span className="text-green-400 mt-0.5">▸</span>
                              <span><span className="font-bold text-white">Stance Score (-1.0 to +1.0):</span> Hawkish/dovish sentiment of the sentence</span>
                            </li>
                            <li className="flex items-start gap-2">
                              <span className="text-blue-400 mt-0.5">▸</span>
                              <span><span className="font-bold text-white">Impact Weight (0.0 to 1.0):</span> Importance and influence of the sentence</span>
                            </li>
                            <li className="flex items-start gap-2">
                              <span className="text-purple-400 mt-0.5">▸</span>
                              <span><span className="font-bold text-white">Topic Classification:</span> Interest rates, inflation, employment, growth, risk assessment, etc.</span>
                            </li>
                            <li className="flex items-start gap-2">
                              <span className="text-yellow-400 mt-0.5">▸</span>
                              <span><span className="font-bold text-white">Reasoning:</span> AI justification for the assigned scores</span>
                            </li>
                          </ul>
                        </div>

                        <div>
                          <h4 className="font-black text-white uppercase text-sm mb-3 border-b border-slate-800 pb-2">2. Impact Weight Assignment</h4>
                          <p className="text-slate-400 text-xs leading-relaxed mb-4">
                            GPT-4 assigns each sentence an impact weight (0.0 to 1.0) based on its topic category and relevance to monetary policy:
                          </p>

                          <div className="grid grid-cols-2 gap-3">
                            <div className="group relative bg-slate-900/50 border border-slate-800 p-3 hover:border-slate-600 transition-all cursor-help">
                              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-2 bg-slate-950 border border-slate-700 rounded text-[10px] text-slate-300 leading-relaxed opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-[5]">
                                Direct statements about interest rate decisions or forward guidance. Highest impact on overall policy stance.
                              </div>
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-bold text-white uppercase text-[10px]">Interest Rates & Inflation</span>
                                <span className="text-green-400 font-black text-sm">1.0</span>
                              </div>
                              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                                <div className="h-full bg-gradient-to-r from-green-600 to-green-400" style={{width: '100%'}}></div>
                              </div>
                            </div>

                            <div className="group relative bg-slate-900/50 border border-slate-800 p-3 hover:border-slate-600 transition-all cursor-help">
                              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-2 bg-slate-950 border border-slate-700 rounded text-[10px] text-slate-300 leading-relaxed opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-[5]">
                                Labor market conditions, unemployment rates, GDP growth, and economic expansion. Important for policy timing.
                              </div>
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-bold text-white uppercase text-[10px]">Employment & GDP Growth</span>
                                <span className="text-blue-400 font-black text-sm">0.7</span>
                              </div>
                              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                                <div className="h-full bg-gradient-to-r from-blue-600 to-blue-400" style={{width: '70%'}}></div>
                              </div>
                            </div>

                            <div className="group relative bg-slate-900/50 border border-slate-800 p-3 hover:border-slate-600 transition-all cursor-help">
                              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-2 bg-slate-950 border border-slate-700 rounded text-[10px] text-slate-300 leading-relaxed opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-[5]">
                                Financial stability concerns, global risks, and external factors. Secondary consideration for policy decisions.
                              </div>
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-bold text-white uppercase text-[10px]">Global Risks & External Factors</span>
                                <span className="text-purple-400 font-black text-sm">0.4</span>
                              </div>
                              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                                <div className="h-full bg-gradient-to-r from-purple-600 to-purple-400" style={{width: '40%'}}></div>
                              </div>
                            </div>

                            <div className="group relative bg-slate-900/50 border border-slate-800 p-3 hover:border-slate-600 transition-all cursor-help">
                              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-2 bg-slate-950 border border-slate-700 rounded text-[10px] text-slate-300 leading-relaxed opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-[5]">
                                General statements, procedural comments, or boilerplate content. No impact on policy interpretation.
                              </div>
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-bold text-white uppercase text-[10px]">Boilerplate</span>
                                <span className="text-slate-500 font-black text-sm">0.0</span>
                              </div>
                              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                                <div className="h-full bg-gradient-to-r from-slate-700 to-slate-500" style={{width: '0%'}}></div>
                              </div>
                            </div>
                          </div>
                        </div>

                        <div>
                          <h4 className="font-black text-white uppercase text-sm mb-3 border-b border-slate-800 pb-2">3. Weighted Aggregation Formula</h4>
                          <p className="text-slate-400 text-xs leading-relaxed mb-3">
                            The final transcript score is calculated using a weighted average:
                          </p>
                          <div className="p-4 bg-slate-950 border border-slate-800 rounded font-mono text-xs">
                            <div className="text-slate-300">
                              <span className="text-green-400">Transcript Score</span> = <span className="text-blue-400">Σ</span> (<span className="text-purple-400">Stance</span> × <span className="text-yellow-400">Impact</span>) / <span className="text-blue-400">Σ</span> (<span className="text-yellow-400">Impact</span>)
                            </div>
                            <div className="mt-3 text-[10px] text-slate-500">
                              Each sentence contributes proportionally to its impact weight, ensuring policy-critical statements dominate the score
                            </div>
                          </div>
                        </div>

                        <div>
                          <h4 className="font-black text-white uppercase text-sm mb-3 border-b border-slate-800 pb-2">4. Example Calculation</h4>
                          <div className="space-y-2 text-[11px]">
                            <div className="p-3 bg-slate-950 border-l-2 border-green-500">
                              <p className="text-slate-300 mb-2">"We are raising the policy rate by 25 basis points today."</p>
                              <div className="flex gap-4 text-[10px]">
                                <span className="text-green-400">Stance: +0.85</span>
                                <span className="text-blue-400">Impact: 1.0</span>
                                <span className="text-purple-400">Category: Interest Rates & Inflation</span>
                              </div>
                              <p className="text-slate-500 mt-1 text-[10px]">→ Weighted contribution: 0.85 × 1.0 = 0.85</p>
                            </div>

                            <div className="p-3 bg-slate-950 border-l-2 border-blue-500">
                              <p className="text-slate-300 mb-2">"Employment growth remains robust in most sectors."</p>
                              <div className="flex gap-4 text-[10px]">
                                <span className="text-green-400">Stance: +0.40</span>
                                <span className="text-blue-400">Impact: 0.7</span>
                                <span className="text-purple-400">Category: Employment & GDP Growth</span>
                              </div>
                              <p className="text-slate-500 mt-1 text-[10px]">→ Weighted contribution: 0.40 × 0.7 = 0.28</p>
                            </div>

                            <div className="p-3 bg-slate-950 border-l-2 border-slate-600">
                              <p className="text-slate-300 mb-2">"We will continue to monitor economic data closely."</p>
                              <div className="flex gap-4 text-[10px]">
                                <span className="text-green-400">Stance: 0.00</span>
                                <span className="text-blue-400">Impact: 0.0</span>
                                <span className="text-purple-400">Category: Boilerplate</span>
                              </div>
                              <p className="text-slate-500 mt-1 text-[10px]">→ Weighted contribution: 0.00 × 0.0 = 0.00</p>
                            </div>

                            <div className="p-3 bg-slate-900 border border-slate-700 mt-3">
                              <p className="text-white font-bold text-xs mb-1">Final Transcript Score:</p>
                              <p className="text-slate-300 text-[10px] font-mono">
                                (0.85 + 0.28 + 0.00) / (1.0 + 0.7 + 0.0) = 1.13 / 1.7 = <span className="text-green-400 font-bold">+0.665</span>
                              </p>
                            </div>
                          </div>
                        </div>

                        <div className="pt-4 border-t border-slate-800">
                          <p className="text-[10px] text-slate-500 italic">
                            This multi-layered approach ensures that policy-critical statements (like rate decisions) carry more weight than procedural or general comments, producing more accurate sentiment scores.
                          </p>
                        </div>
                      </div>
                    )}
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
                  <h3 className="text-lg font-black uppercase tracking-wider text-yellow-400 mb-3 border-l-2 border-yellow-500 pl-3">Data Sources & Attribution</h3>
                  <div className="space-y-3 text-sm">
                    <div>
                      <p className="font-bold text-white mb-1">Central Bank Transcripts:</p>
                      <p className="text-slate-400 leading-relaxed">
                        Official meeting transcripts and policy statements are sourced from the <span className="text-white">Federal Reserve Board of Governors</span> (federalreserve.gov) and the <span className="text-white">Bank of Canada</span> (bankofcanada.ca). All source materials are publicly available and used for educational and analytical purposes.
                      </p>
                    </div>
                    <div>
                      <p className="font-bold text-white mb-1">Analysis Methodology:</p>
                      <p className="text-slate-400 leading-relaxed">
                        Sentiment analysis powered by OpenAI GPT-4. Scores and interpretations are generated algorithmically and do not represent official positions of the Federal Reserve or Bank of Canada.
                      </p>
                    </div>
                    <div>
                      <p className="font-bold text-white mb-1">Exchange Rate Data:</p>
                      <p className="text-slate-400 leading-relaxed">
                        USD/CAD exchange rates provided by Alpha Vantage API.
                      </p>
                    </div>
                    <div>
                      <p className="font-bold text-white mb-1">Updates:</p>
                      <p className="text-slate-400 leading-relaxed">
                        Automated scraping and analysis runs hourly via GitHub Actions.
                      </p>
                    </div>
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

                <div className="pt-6 border-t border-slate-800 text-xs text-slate-500">
                  <p className="text-center mb-3">Built with React, FastAPI, PostgreSQL, and OpenAI GPT-4 • Deployed on Vercel and Render</p>
                  <p className="text-center text-[10px] leading-relaxed">
                    <span className="font-bold text-slate-400">Disclaimer:</span> This is an independent research project. FinSENT is not affiliated with, endorsed by, or representative of the Federal Reserve System or the Bank of Canada. All analysis and interpretations are solely those of this application.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

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
              Transcripts: <span className="text-slate-300">Federal Reserve Board of Governors</span> (federalreserve.gov) and <span className="text-slate-300">Bank of Canada</span> (bankofcanada.ca)
            </p>
            <p className="text-[10px] leading-relaxed normal-case font-normal tracking-normal opacity-70">
              This is an independent research project. FinSENT is not affiliated with, endorsed by, or representative of the Federal Reserve System or the Bank of Canada.
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default TranscriptsPage;
