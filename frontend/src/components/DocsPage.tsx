import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft, Sun, Moon, BookOpen, Workflow, Globe, Brain,
  Calculator, Lightbulb, BarChart3, Wrench, MessageSquare,
} from 'lucide-react';

const DocsPage = () => {
  const [light, setLight] = useState(() => document.documentElement.classList.contains('light'));
  const toggleTheme = () => {
    setLight(p => { document.documentElement.classList.toggle('light', !p); return !p; });
  };

  return (
    <div className="min-h-screen theme-bg theme-text">
      {/* Top nav */}
      <div className="px-6 md:px-12 lg:px-16 pt-6 pb-4">
        <div className="max-w-[900px] mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-[13px] theme-muted hover:theme-heading transition-colors">
            <ArrowLeft size={14} />
            Back to Dashboard
          </Link>
          <button
            onClick={toggleTheme}
            className="p-2 theme-muted rounded-lg hover:theme-heading hover:bg-white/5 transition-all duration-150"
            title={light ? 'Dark mode' : 'Light mode'}
          >
            {light ? <Moon size={16} /> : <Sun size={16} />}
          </button>
        </div>
      </div>

      <div className="px-6 md:px-12 lg:px-16 pb-24">
        <div className="max-w-[900px] mx-auto">

          {/* Hero */}
          <div className="mb-16 animate-fade-in">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-semibold tracking-wide uppercase rounded-md bg-blue-500/10 text-blue-400 mb-5">
              <BookOpen size={12} />
              System Documentation
            </span>
            <h1 className="text-4xl font-bold theme-heading tracking-tight mb-4">
              How FinSENT Works
            </h1>
            <p className="text-[15px] text-gray-400 leading-relaxed max-w-[700px]">
              FinSENT scores Federal Reserve and Bank of Canada monetary policy sentiment using a fine-tuned DistilBERT model trained on central bank transcripts. Here's exactly how every piece fits together.
            </p>
          </div>

          {/* Pipeline overview */}
          <section className="mb-14 animate-fade-in stagger-1">
            <div className="card p-6 md:p-8">
              <div className="flex items-center gap-2.5 mb-4">
                <Workflow size={18} className="text-blue-400" />
                <h2 className="text-lg font-semibold text-blue-400">The Pipeline</h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                {[
                  { step: '1', label: 'Scrape', desc: 'Pull new transcripts from Fed & BoC', color: 'text-rose-400', bg: 'bg-rose-500/8' },
                  { step: '2', label: 'Split', desc: 'Break into individual sentences', color: 'text-amber-400', bg: 'bg-amber-500/8' },
                  { step: '3', label: 'Score', desc: 'Run each through DistilBERT', color: 'text-emerald-400', bg: 'bg-emerald-500/8' },
                  { step: '4', label: 'Aggregate', desc: 'Weighted average → transcript score', color: 'text-blue-400', bg: 'bg-blue-500/8' },
                ].map(s => (
                  <div key={s.step} className={`${s.bg} rounded-lg p-4`}>
                    <span className={`text-[11px] font-bold ${s.color} uppercase tracking-wider`}>Step {s.step}</span>
                    <p className={`text-[15px] font-semibold ${s.color} mt-1`}>{s.label}</p>
                    <p className="text-[12px] text-gray-500 mt-1 leading-relaxed">{s.desc}</p>
                  </div>
                ))}
              </div>
              <p className="text-[12px] text-gray-600 mt-4">Pipeline runs hourly via GitHub Actions. New transcripts are automatically detected and scored.</p>
            </div>
          </section>

          {/* Scraping */}
          <section className="mb-14 animate-fade-in stagger-2">
            <div className="card p-6 md:p-8">
              <div className="flex items-center gap-2.5 mb-4">
                <Globe size={18} className="text-rose-400" />
                <h2 className="text-lg font-semibold text-rose-400">Data Collection</h2>
              </div>
              <p className="text-[13px] text-gray-400 leading-relaxed mb-5">
                Two specialized scrapers pull monetary policy transcripts from their respective central bank websites.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="rounded-lg p-4 bg-blue-500/5 border border-blue-500/10">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium rounded bg-blue-500/15 text-blue-400">Fed</span>
                    <span className="text-[11px] text-gray-600">federalreserve.gov</span>
                  </div>
                  <p className="text-[12px] text-gray-400 leading-relaxed mb-3">
                    Pulls from the Fed's JSON press release feed. Targets FOMC statements and economic projections. Handles both HTML pages and PDF documents.
                  </p>
                  <div className="docs-code">
                    <span className="text-gray-600">source</span> = <span className="text-blue-400">"/json/ne-press.json"</span><br/>
                    <span className="text-gray-600">filter</span> = <span className="text-amber-400">"statement"</span> | <span className="text-amber-400">"projections"</span>
                  </div>
                </div>

                <div className="rounded-lg p-4 bg-red-500/5 border border-red-500/10">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium rounded bg-red-500/15 text-red-400">BoC</span>
                    <span className="text-[11px] text-gray-600">bankofcanada.ca</span>
                  </div>
                  <p className="text-[12px] text-gray-400 leading-relaxed mb-3">
                    Scrapes press releases page for interest rate decisions and monetary policy reports. Extracts article content with HTML parsing via BeautifulSoup.
                  </p>
                  <div className="docs-code">
                    <span className="text-gray-600">filter</span> = <span className="text-amber-400">"interest rate"</span> | <span className="text-amber-400">"monetary policy"</span> | <span className="text-amber-400">"policy rate"</span>
                  </div>
                </div>
              </div>
              <p className="text-[12px] text-gray-600 mt-4">
                Both scrapers skip URLs already in the database (dedup by URL). Text is cleaned of Unicode artifacts, control characters, and formatting noise before storage.
              </p>
            </div>
          </section>

          {/* Model */}
          <section className="mb-14 animate-fade-in stagger-3">
            <div className="card p-6 md:p-8">
              <div className="flex items-center gap-2.5 mb-4">
                <Brain size={18} className="text-violet-400" />
                <h2 className="text-lg font-semibold text-violet-400">The Model</h2>
              </div>
              <p className="text-[13px] text-gray-400 leading-relaxed mb-5">
                A multi-task <span className="text-violet-400 font-medium">DistilBERT</span> model fine-tuned specifically on central bank language. It was distilled from GPT-4o-mini labels — the larger model scored thousands of sentences first, then DistilBERT learned to replicate those judgments at 100× speed.
              </p>

              <div className="docs-code mb-5">
                <span className="text-gray-500">// Architecture</span><br/>
                <span className="text-violet-400">backbone</span> = <span className="text-emerald-400">DistilBERT</span>-base-uncased (66M params)<br/>
                <span className="text-violet-400">head_1</span>{'  '}= Regression → <span className="text-amber-400">stance_score</span> ∈ [-1, +1] via tanh<br/>
                <span className="text-violet-400">head_2</span>{'  '}= Classification → <span className="text-amber-400">topic</span> (5 classes)<br/><br/>
                <span className="text-gray-500">// Training</span><br/>
                <span className="text-gray-600">loss</span>{'    '}= <span className="text-rose-400">MSE</span>(score) + <span className="text-rose-400">CrossEntropy</span>(topic)<br/>
                <span className="text-gray-600">optim</span>{'   '}= AdamW, lr=<span className="text-blue-400">2e-5</span>, epochs=<span className="text-blue-400">10</span><br/>
                <span className="text-gray-600">seq_len</span> = <span className="text-blue-400">128</span> tokens
              </div>

              <p className="text-[13px] text-gray-400 leading-relaxed mb-4">
                Both heads share the <span className="text-gray-300">[CLS]</span> token representation from the DistilBERT backbone. Each passes through a dropout → linear (768→128) → ReLU → dropout → linear projection.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="rounded-lg p-4 bg-violet-500/5 border border-violet-500/10">
                  <p className="text-[11px] font-semibold text-violet-400 uppercase tracking-wider mb-1">Stance Head</p>
                  <p className="text-[12px] text-gray-400 leading-relaxed">
                    Outputs a single float in [−1, +1]. Negative = dovish (rate cuts, stimulus). Positive = hawkish (rate hikes, tightening). Near zero = neutral.
                  </p>
                </div>
                <div className="rounded-lg p-4 bg-violet-500/5 border border-violet-500/10">
                  <p className="text-[11px] font-semibold text-violet-400 uppercase tracking-wider mb-1">Topic Head</p>
                  <p className="text-[12px] text-gray-400 leading-relaxed">
                    Classifies into one of 5 economic topics. The topic determines the sentence's impact weight in the final aggregation.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Scoring formula */}
          <section className="mb-14 animate-fade-in stagger-4">
            <div className="card p-6 md:p-8">
              <div className="flex items-center gap-2.5 mb-4">
                <Calculator size={18} className="text-amber-400" />
                <h2 className="text-lg font-semibold text-amber-400">The Scoring</h2>
              </div>

              <div className="docs-code mb-5">
                <span className="text-gray-500">// Per-sentence output</span><br/>
                <span className="text-amber-400">stance_score</span> = model.score_head(sentence){'  '}<span className="text-gray-600">// -1.0 to +1.0</span><br/>
                <span className="text-amber-400">topic</span>{'       '}= model.topic_head(sentence){'  '}<span className="text-gray-600">// 5-class</span><br/>
                <span className="text-amber-400">weight</span>{'      '}= TOPIC_TO_WEIGHT[topic]{'     '}<span className="text-gray-600">// 0.0 to 1.0</span><br/><br/>
                <span className="text-gray-500">// Transcript aggregation</span><br/>
                <span className="text-emerald-400">transcript_score</span> = Σ(stance × weight) / Σ(weight)
              </div>

              <div className="mb-5">
                <h3 className="text-[12px] font-semibold text-gray-300 uppercase tracking-wider mb-3">Impact Weights by Topic</h3>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                  {[
                    { topic: 'Inflation', weight: 1.0, color: 'text-rose-400', bg: 'bg-rose-500/8' },
                    { topic: 'Guidance', weight: 1.0, color: 'text-blue-400', bg: 'bg-blue-500/8' },
                    { topic: 'Employment', weight: 0.7, color: 'text-amber-400', bg: 'bg-amber-500/8' },
                    { topic: 'Growth', weight: 0.7, color: 'text-emerald-400', bg: 'bg-emerald-500/8' },
                    { topic: 'Boilerplate', weight: 0.0, color: 'text-gray-500', bg: 'bg-gray-500/8' },
                  ].map(t => (
                    <div key={t.topic} className={`${t.bg} rounded-lg p-3 text-center`}>
                      <p className={`text-[13px] font-semibold ${t.color}`}>{t.topic}</p>
                      <p className="text-[18px] font-bold text-gray-300 tabular-nums mt-0.5">{t.weight.toFixed(1)}</p>
                    </div>
                  ))}
                </div>
              </div>

              <p className="text-[12px] text-gray-500 leading-relaxed">
                Higher weight is given to Inflation and Guidance because they most directly signal rate decisions. Boilerplate sentences (procedural, generic language) are excluded entirely.
              </p>
            </div>
          </section>

          {/* Worked example */}
          <section className="mb-14 animate-fade-in">
            <div className="card p-6 md:p-8">
              <div className="flex items-center gap-2.5 mb-4">
                <Lightbulb size={18} className="text-emerald-400" />
                <h2 className="text-lg font-semibold text-emerald-400">Worked Example</h2>
              </div>
              <p className="text-[13px] text-gray-400 leading-relaxed mb-5">
                Three sentences from a transcript scored individually, then aggregated:
              </p>
              <div className="space-y-2 mb-5">
                <div className="rounded-lg p-3.5 bg-emerald-500/5 border-l-2 border-emerald-500/40">
                  <p className="text-[13px] text-gray-300 mb-1.5">"We are raising the policy rate by 25 basis points."</p>
                  <div className="flex gap-4 text-[11px]">
                    <span>Score: <span className="text-emerald-400 font-medium">+0.850</span></span>
                    <span>Topic: <span className="text-rose-400">Inflation</span></span>
                    <span>Weight: <span className="text-gray-300">1.0</span></span>
                  </div>
                </div>
                <div className="rounded-lg p-3.5 bg-blue-500/5 border-l-2 border-blue-500/40">
                  <p className="text-[13px] text-gray-300 mb-1.5">"Employment growth remains robust across sectors."</p>
                  <div className="flex gap-4 text-[11px]">
                    <span>Score: <span className="text-emerald-400 font-medium">+0.400</span></span>
                    <span>Topic: <span className="text-amber-400">Employment</span></span>
                    <span>Weight: <span className="text-gray-300">0.7</span></span>
                  </div>
                </div>
                <div className="rounded-lg p-3.5 bg-gray-500/5 border-l-2 border-gray-500/30">
                  <p className="text-[13px] text-gray-300 mb-1.5">"We will continue to monitor incoming data closely."</p>
                  <div className="flex gap-4 text-[11px]">
                    <span>Score: <span className="text-gray-500 font-medium">+0.000</span></span>
                    <span>Topic: <span className="text-gray-500">Boilerplate</span></span>
                    <span>Weight: <span className="text-gray-500">0.0</span></span>
                  </div>
                </div>
              </div>
              <div className="docs-code">
                <span className="text-gray-500">// Aggregation (boilerplate excluded)</span><br/>
                <span className="text-gray-400">result</span> = (<span className="text-emerald-400">0.850</span> × <span className="text-gray-300">1.0</span> + <span className="text-emerald-400">0.400</span> × <span className="text-gray-300">0.7</span>) / (<span className="text-gray-300">1.0</span> + <span className="text-gray-300">0.7</span>)<br/>
                {'       '}= <span className="text-emerald-400 font-semibold">+0.665</span> <span className="text-gray-600">→ Hawkish</span>
              </div>
            </div>
          </section>

          {/* Divergence */}
          <section className="mb-14 animate-fade-in">
            <div className="card p-6 md:p-8">
              <div className="flex items-center gap-2.5 mb-4">
                <BarChart3 size={18} className="text-cyan-400" />
                <h2 className="text-lg font-semibold text-cyan-400">Divergence & Metrics</h2>
              </div>
              <div className="docs-code mb-5">
                <span className="text-cyan-400">divergence</span> = Fed_score − BoC_score
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
                <div>
                  <p className="text-[12px] text-gray-300 font-medium mb-1">Positive divergence</p>
                  <p className="text-[12px] text-gray-500 leading-relaxed">Fed is more hawkish than BoC — suggests tighter US monetary policy relative to Canada. Historically associated with USD strength.</p>
                </div>
                <div>
                  <p className="text-[12px] text-gray-300 font-medium mb-1">Negative divergence</p>
                  <p className="text-[12px] text-gray-500 leading-relaxed">BoC is more hawkish than Fed — tighter Canadian policy. Can correlate with CAD strength (lower USD/CAD).</p>
                </div>
              </div>

              <h3 className="text-[12px] font-semibold text-gray-300 uppercase tracking-wider mb-3">Dashboard Metrics</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {[
                  { metric: 'Current Divergence', desc: 'Latest gap between Fed and BoC sentiment scores.', color: 'text-emerald-400' },
                  { metric: 'Mean Divergence', desc: 'Average policy divergence over the selected time window.', color: 'text-blue-400' },
                  { metric: 'Volatility (σ)', desc: 'Standard deviation — how much the divergence fluctuates.', color: 'text-violet-400' },
                  { metric: 'Correlation', desc: 'Pearson correlation between divergence and USD/CAD price movement.', color: 'text-amber-400' },
                ].map(m => (
                  <div key={m.metric} className="rounded-lg p-3 bg-white/[0.02] border border-white/[0.04]">
                    <p className={`text-[12px] font-medium ${m.color}`}>{m.metric}</p>
                    <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed">{m.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* Chatbot / Policy Analyst */}
          <section className="mb-14 animate-fade-in">
            <div className="card p-6 md:p-8">
              <div className="flex items-center gap-2.5 mb-4">
                <MessageSquare size={18} className="text-blue-400" />
                <h2 className="text-lg font-semibold text-blue-400">Policy Analyst Chatbot</h2>
              </div>
              <p className="text-[13px] text-gray-400 leading-relaxed mb-5">
                An AI-powered conversational interface that lets you query the FinSENT database in natural language. Powered by <span className="text-blue-400 font-medium">GPT-4o-mini</span> with tool-use — the model decides which database queries to run, executes them, and synthesizes the results into a coherent answer.
              </p>

              <div className="docs-code mb-5">
                <span className="text-gray-500">// Agent loop (max 5 iterations)</span><br/>
                <span className="text-blue-400">user_message</span> → GPT-4o-mini<br/>
                {'  '}→ decides which <span className="text-amber-400">tools</span> to call<br/>
                {'  '}→ executes SQL via tool functions<br/>
                {'  '}→ feeds results back to model<br/>
                {'  '}→ repeat until final <span className="text-emerald-400">answer</span>
              </div>

              <div className="mb-5">
                <h3 className="text-[12px] font-semibold text-gray-300 uppercase tracking-wider mb-3">Available Tools</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {[
                    { name: 'get_sentiment_summary', desc: 'Average stance scores by date for a specific bank. Shows sentiment evolution over time.', color: 'text-emerald-400' },
                    { name: 'get_transcripts', desc: 'List transcripts with aggregate scores. Filter by bank and date range.', color: 'text-blue-400' },
                    { name: 'get_transcript_sentences', desc: 'Full sentence-level breakdown for a transcript. Drill into why it scored that way.', color: 'text-violet-400' },
                    { name: 'search_sentences', desc: 'Keyword search across all sentences with optional bank and topic filters.', color: 'text-amber-400' },
                    { name: 'get_divergence', desc: 'Fed-vs-BoC sentiment divergence over time with per-date scores.', color: 'text-rose-400' },
                  ].map(t => (
                    <div key={t.name} className="rounded-lg p-3 bg-white/[0.02] border border-white/[0.04]">
                      <p className={`text-[12px] font-mono font-medium ${t.color}`}>{t.name}</p>
                      <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed">{t.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              <p className="text-[12px] text-gray-500 leading-relaxed">
                The chatbot never guesses — it always queries your database first, then responds with precise scores (3 decimal places). Tool calls are shown as tags beneath each response so you can see exactly what data was accessed.
              </p>
            </div>
          </section>

          {/* Tech stack */}
          <section className="mb-14 animate-fade-in">
            <div className="card p-6 md:p-8">
              <div className="flex items-center gap-2.5 mb-4">
                <Wrench size={18} className="text-gray-300" />
                <h2 className="text-lg font-semibold text-gray-300">Tech Stack</h2>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { name: 'React + Vite', role: 'Frontend', color: 'text-blue-400' },
                  { name: 'FastAPI', role: 'API Server', color: 'text-emerald-400' },
                  { name: 'PostgreSQL', role: 'Database (Neon)', color: 'text-violet-400' },
                  { name: 'PyTorch', role: 'Model Training', color: 'text-rose-400' },
                  { name: 'DistilBERT', role: 'NLP Backbone', color: 'text-amber-400' },
                  { name: 'GPT-4o-mini', role: 'Label Distillation', color: 'text-cyan-400' },
                  { name: 'Recharts', role: 'Visualizations', color: 'text-pink-400' },
                  { name: 'GitHub Actions', role: 'CI/CD + Scraping', color: 'text-gray-400' },
                ].map(t => (
                  <div key={t.name} className="rounded-lg p-3 bg-white/[0.02] border border-white/[0.04]">
                    <p className={`text-[12px] font-medium ${t.color}`}>{t.name}</p>
                    <p className="text-[11px] text-gray-600 mt-0.5">{t.role}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* Footer */}
          <div className="text-center text-[11px] text-gray-600 pt-4 animate-fade-in">
            Data from federalreserve.gov and bankofcanada.ca · Model distilled from GPT-4o-mini labels · Updated hourly
          </div>

        </div>
      </div>
    </div>
  );
};

export default DocsPage;
