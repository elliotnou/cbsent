import { useState, useEffect } from 'react';

const HelpModal = ({ showHelp, setShowHelp }) => {
  const [showScoring, setShowScoring] = useState(false);

  useEffect(() => {
    document.body.style.overflow = showHelp ? 'hidden' : 'unset';
    return () => { document.body.style.overflow = 'unset'; };
  }, [showHelp]);

  if (!showHelp) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[100] flex items-center justify-center p-6" onClick={() => setShowHelp(false)}>
      <div className="bg-[#161616] border border-gray-700 max-w-3xl w-full max-h-[80vh] overflow-y-auto rounded-lg" onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 bg-[#161616] border-b border-gray-700 p-5 flex items-center justify-between z-10">
          <h2 className="text-xl font-semibold text-white">How it works</h2>
          <button onClick={() => setShowHelp(false)} className="text-gray-400 hover:text-white text-xl transition-colors">×</button>
        </div>

        <div className="p-6 space-y-8 text-gray-300 text-sm">

          <section>
            <h3 className="font-medium text-white mb-2">What is FinSENT?</h3>
            <p className="leading-relaxed">
              FinSENT tracks monetary policy sentiment from the Federal Reserve and Bank of Canada.
              It analyzes official transcripts using a fine-tuned DistilBERT model, quantifies policy stance
              on a hawkish–dovish spectrum, and visualizes divergence against USD/CAD exchange rates.
            </p>
          </section>

          <section>
            <h3 className="font-medium text-white mb-2">Scoring</h3>
            <div className="space-y-3">
              <p className="leading-relaxed">
                Each transcript is broken into individual sentences and scored by a DistilBERT model
                trained on central bank language. The model outputs:
              </p>
              <ul className="space-y-1.5 ml-4 text-gray-400">
                <li><span className="text-gray-200">Stance score</span> (−1.0 to +1.0) — hawkish vs dovish</li>
                <li><span className="text-gray-200">Topic</span> — Inflation, Growth, Employment, Guidance, or Boilerplate</li>
                <li><span className="text-gray-200">Impact weight</span> (0–1.0) — derived from topic relevance</li>
              </ul>

              <div className="mt-3 p-3 bg-[#111] border-l-2 border-gray-700 rounded-sm">
                <span className="text-gray-200">Divergence</span> = Fed sentiment − BoC sentiment. Positive means Fed is more hawkish.
              </div>

              <button
                onClick={() => setShowScoring(!showScoring)}
                className="mt-3 w-full px-3 py-2 bg-[#1a1a1a] border border-gray-700 rounded hover:border-gray-600 transition-colors text-left flex items-center justify-between"
              >
                <span className="text-xs text-gray-400">Scoring details</span>
                <span className="text-gray-500">{showScoring ? '−' : '+'}</span>
              </button>

              {showScoring && (
                <div className="mt-3 space-y-5 p-4 bg-[#111] border border-gray-800 rounded">
                  <div>
                    <h4 className="text-xs font-medium text-gray-300 mb-2">Impact weights by topic</h4>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {[
                        { topic: 'Inflation', weight: '1.0', desc: 'Direct rate/price signals' },
                        { topic: 'Guidance', weight: '1.0', desc: 'Forward-looking policy language' },
                        { topic: 'Employment', weight: '0.7', desc: 'Labour market conditions' },
                        { topic: 'Growth', weight: '0.7', desc: 'GDP and output indicators' },
                        { topic: 'Boilerplate', weight: '0.0', desc: 'Procedural or generic statements' },
                      ].map(({ topic, weight, desc }) => (
                        <div key={topic} className="bg-[#1a1a1a] border border-gray-800 p-2 rounded">
                          <div className="flex justify-between mb-0.5">
                            <span className="text-gray-300">{topic}</span>
                            <span className="text-gray-500">{weight}</span>
                          </div>
                          <p className="text-gray-600">{desc}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-xs font-medium text-gray-300 mb-2">Aggregation</h4>
                    <div className="p-2 bg-[#1a1a1a] border border-gray-800 rounded text-xs font-mono text-gray-400">
                      transcript_score = Σ(stance × weight) / Σ(weight)
                    </div>
                  </div>

                  <div>
                    <h4 className="text-xs font-medium text-gray-300 mb-2">Example</h4>
                    <div className="space-y-1.5 text-xs text-gray-400">
                      <div className="p-2 bg-[#1a1a1a] border-l-2 border-green-800 rounded-sm">
                        <p className="text-gray-300 mb-1">"We are raising the policy rate by 25 basis points."</p>
                        <p>Score: +0.85 · Weight: 1.0 · Inflation</p>
                      </div>
                      <div className="p-2 bg-[#1a1a1a] border-l-2 border-blue-800 rounded-sm">
                        <p className="text-gray-300 mb-1">"Employment growth remains robust."</p>
                        <p>Score: +0.40 · Weight: 0.7 · Employment</p>
                      </div>
                      <div className="p-2 bg-[#1a1a1a] border-l-2 border-gray-700 rounded-sm">
                        <p className="text-gray-300 mb-1">"We will continue to monitor data closely."</p>
                        <p>Score: 0.00 · Weight: 0.0 · Boilerplate</p>
                      </div>
                      <div className="p-2 bg-[#1a1a1a] border border-gray-700 rounded mt-2">
                        <p className="text-gray-300">Result: (0.85 + 0.28) / (1.0 + 0.7) = <span className="text-green-400">+0.665</span></p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>

          <section>
            <h3 className="font-medium text-white mb-2">Metrics</h3>
            <div className="space-y-2 text-gray-400">
              <p><span className="text-gray-200">Current Divergence</span> — latest Fed − BoC gap</p>
              <p><span className="text-gray-200">Mean Divergence</span> — average over selected period</p>
              <p><span className="text-gray-200">Volatility</span> — std. deviation of divergence</p>
              <p><span className="text-gray-200">Correlation</span> — relationship between divergence and USD/CAD</p>
            </div>
          </section>

          <section>
            <h3 className="font-medium text-white mb-2">Data sources</h3>
            <div className="space-y-2 text-gray-400">
              <p>
                Transcripts from <span className="text-gray-300">Federal Reserve</span> (federalreserve.gov) and
                <span className="text-gray-300"> Bank of Canada</span> (bankofcanada.ca).
                Sentiment scored by a fine-tuned DistilBERT model. Exchange rate data via yfinance.
                Pipeline runs hourly via GitHub Actions.
              </p>
            </div>
          </section>

          <div className="pt-4 border-t border-gray-800 text-xs text-gray-600 text-center">
            Built with React, FastAPI, PostgreSQL, PyTorch, and DistilBERT
          </div>
        </div>
      </div>
    </div>
  );
};

export default HelpModal;
