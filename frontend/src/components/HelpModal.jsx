import { useState, useEffect } from 'react';

const HelpModal = ({ showHelp, setShowHelp }) => {
  const [expandedScoring, setExpandedScoring] = useState(false);

  // prevent body scroll when modal is open
  useEffect(() => {
    if (showHelp) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () =>{
      document.body.style.overflow = 'unset';
    };
  }, [showHelp]);

  if (!showHelp) return null;

  return (
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
                Each transcript is analyzed using an AI-powered system that breaks down text into individual sentences, scores them, and aggregates results into a final transcript score.
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
                      Each sentence in a transcript is individually analyzed by GPT-4o mini, which assigns:
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
                      GPT-4o mini assigns each sentence an impact weight (0.0 to 1.0) based on its topic category and relevance to monetary policy:
                    </p>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="group relative bg-slate-900/50 border border-slate-800 p-3 hover:border-slate-600 transition-all">
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

                      <div className="group relative bg-slate-900/50 border border-slate-800 p-3 hover:border-slate-600 transition-all">
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

                      <div className="group relative bg-slate-900/50 border border-slate-800 p-3 hover:border-slate-600 transition-all">
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

                      <div className="group relative bg-slate-900/50 border border-slate-800 p-3 hover:border-slate-600 transition-all">
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
                <p className="font-bold text-white mb-1">Press Releases:</p>
                <p className="text-slate-400 leading-relaxed">
                  Data is sourced from <span className="text-white">Federal Reserve Monetary Policy Press Releases</span> (federalreserve.gov) and <span className="text-white">Bank of Canada Press Releases</span> (bankofcanada.ca). All source materials are publicly available and used for educational and analytical purposes.
                </p>
              </div>
              <div>
                <p className="font-bold text-white mb-1">Analysis Methodology:</p>
                <p className="text-slate-400 leading-relaxed">
                  Sentiment analysis powered by OpenAI GPT-4o mini. Scores and interpretations are generated algorithmically and do not represent official positions of the Federal Reserve or Bank of Canada.
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
              <p><span className="font-bold text-white">Time Ranges:</span> Filter data by All, 90d, 1y, or 3y periods</p>
            </div>
          </section>

          <div className="pt-6 border-t border-slate-800 text-xs text-slate-500">
            <p className="text-center mb-3">Built with React, FastAPI, PostgreSQL, and OpenAI GPT-4o mini • Deployed on Vercel and Render</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HelpModal;
