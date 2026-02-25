import { useEffect, useState, useMemo } from 'react';
import {
  LineChart, Line, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts';

const STAT_DESCRIPTIONS = {
  'Current Divergence': 'Latest gap between Fed and BoC sentiment. Positive = Fed more hawkish.',
  'Mean Divergence': 'Average policy divergence over the selected time window.',
  'Volatility (σ)': 'Standard deviation of divergence — measures how much the gap fluctuates.',
  'Correlation': 'Pearson correlation between sentiment divergence and USD/CAD price movement.',
};

const ScoreBar = () => {
  return (
    <div className="card px-5 py-4">
      <div className="text-[11px] text-gray-500 font-medium uppercase tracking-wide mb-3">Score range</div>
      <div className="max-w-sm mx-auto">
        {/* The gradient bar */}
        <div className="h-2 bg-gradient-to-r from-rose-500/70 via-gray-600/60 to-emerald-500/70 score-bar" />

        {/* Labels row — each side is a wide hover zone */}
        <div className="flex text-[11px] mt-2.5" style={{ position: 'relative' }}>
          {/* Left half — Dovish hover zone */}
          <div className="flex-1 relative hover-zone" style={{ minHeight: 24 }}>
            <span className="text-rose-400/80 select-none">−1.0 Dovish</span>
            <div className="hover-tip hover-tip-left">
              <div className="card p-3">
                <p className="text-[11px] text-gray-400 leading-relaxed mb-2">
                  Accommodative stance — signals rate cuts, stimulus, or concern about weak growth.
                </p>
                <div className="p-2 bg-black/20 border-l-2 border-rose-500/40 rounded-sm">
                  <p className="text-[11px] text-gray-300 italic leading-relaxed">
                    "The Committee is prepared to adjust the stance of monetary policy as appropriate if risks emerge that could impede the attainment of our goals."
                  </p>
                </div>
              </div>
            </div>
          </div>

          <span className="text-gray-600 px-2">0</span>

          {/* Right half — Hawkish hover zone */}
          <div className="flex-1 relative text-right hover-zone" style={{ minHeight: 24 }}>
            <span className="text-emerald-400/80 select-none">+1.0 Hawkish</span>
            <div className="hover-tip hover-tip-right">
              <div className="card p-3">
                <p className="text-[11px] text-gray-400 leading-relaxed mb-2">
                  Restrictive stance — signals rate hikes, tightening, or concern about inflation.
                </p>
                <div className="p-2 bg-black/20 border-l-2 border-emerald-500/40 rounded-sm">
                  <p className="text-[11px] text-gray-300 italic leading-relaxed">
                    "Inflation remains significantly above our longer-run goal. We are strongly committed to returning inflation to our 2 percent objective."
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const DivergenceChart = () => {
  const [data, setData] = useState([]);
  const [usdcadData, setUsdcadData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('all');
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  const SentimentTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="chart-tooltip rounded-lg px-3 py-2.5 text-xs shadow-2xl">
        <p className="text-gray-400 mb-1.5 font-medium">{label}</p>
        {payload.map((entry, i) => {
          let color = '#999';
          if (entry.name === 'Fed') color = '#60a5fa';
          else if (entry.name === 'BoC') color = '#f87171';
          else if (entry.name === 'USD/CAD') color = '#4ade80';
          return (
            <p key={i} style={{ color }} className="my-0.5">
              {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(3) : entry.value}
            </p>
          );
        })}
      </div>
    );
  };

  const DivergenceTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const val = payload[0].value;
    const color = val > 0 ? '#34d399' : '#fb7185';
    return (
      <div className="chart-tooltip rounded-lg px-3 py-2.5 text-xs shadow-2xl max-w-[240px]">
        <p className="text-gray-400 mb-1.5 font-medium">{label}</p>
        <p style={{ color }} className="my-0.5">
          Divergence: {typeof val === 'number' ? val.toFixed(3) : val}
        </p>
        <p className="text-gray-500 text-[11px] leading-snug mt-1">
          {val > 0 ? 'Fed is more hawkish than BoC' : val < 0 ? 'BoC is more hawkish than Fed' : 'Equal sentiment'}
        </p>
      </div>
    );
  };

  useEffect(() => {
    const fetchSentiment = fetch(`${API_BASE_URL}/api/divergence`).then(r => r.json());
    const fetchFX = fetch(`${API_BASE_URL}/api/usdcad`).then(r => r.json());

    Promise.all([fetchSentiment, fetchFX])
      .then(([sentimentData, fxData]) => {
        const fedKeys = ['fed', 'federal reserve', 'us federal reserve', 'u.s. federal reserve', 'u.s. reserve', 'federal_reserve'];
        const bocKeys = ['boc', 'bank of canada', 'bank_of_canada', 'bankofcanada'];

        const mapped = (sentimentData || []).map(row => {
          let fedVal = 0, bocVal = 0;
          for (const k of fedKeys) if (row[k] !== undefined) { fedVal = Number(row[k]); break; }
          for (const k of bocKeys) if (row[k] !== undefined) { bocVal = Number(row[k]); break; }
          return {
            date: row.date,
            fed: Number(fedVal.toFixed(2)),
            boc: Number(bocVal.toFixed(2)),
            divergence: Number((fedVal - bocVal).toFixed(2))
          };
        }).filter(r => r.date);

        setData(mapped);
        setUsdcadData(fxData);
        setLoading(false);
      });
  }, []);

  const filteredData = useMemo(() => {
    if (timeRange === 'all') return data;
    const cutoff = new Date();
    if (timeRange === '90d') cutoff.setDate(cutoff.getDate() - 90);
    if (timeRange === '1y') cutoff.setFullYear(cutoff.getFullYear() - 1);
    if (timeRange === '3y') cutoff.setFullYear(cutoff.getFullYear() - 3);
    return data.filter(d => new Date(d.date) >= cutoff);
  }, [data, timeRange]);

  const filteredUSDCAD = useMemo(() => {
    if (timeRange === 'all') return usdcadData;
    const cutoff = new Date();
    if (timeRange === '90d') cutoff.setDate(cutoff.getDate() - 90);
    if (timeRange === '1y') cutoff.setFullYear(cutoff.getFullYear() - 1);
    if (timeRange === '3y') cutoff.setFullYear(cutoff.getFullYear() - 3);
    return usdcadData.filter(d => new Date(d.date) >= cutoff);
  }, [usdcadData, timeRange]);

  const mergedData = useMemo(() => {
    const fxSorted = [...filteredUSDCAD].sort((a, b) => new Date(a.date) - new Date(b.date));
    let lastFX = null, fxIdx = 0;
    return filteredData.map(d => {
      while (fxIdx < fxSorted.length && new Date(fxSorted[fxIdx].date) <= new Date(d.date)) {
        lastFX = fxSorted[fxIdx].price;
        fxIdx++;
      }
      return { ...d, usdcad_price: lastFX };
    });
  }, [filteredData, filteredUSDCAD]);

  const stats = useMemo(() => {
    if (filteredData.length === 0) return { current: 0, avg: 0, volatility: 0, correlation: 0, lagDays: 1 };
    const current = filteredData[filteredData.length - 1]?.divergence || 0;
    const avg = filteredData.reduce((sum, d) => sum + d.divergence, 0) / filteredData.length;
    const volatility = Math.sqrt(filteredData.reduce((sum, d) => sum + Math.pow(d.divergence - avg, 2), 0) / filteredData.length);

    const lagDays = 1;
    let correlation = 0;
    if (mergedData.length > lagDays + 10) {
      const divs = [], prices = [];
      for (let i = 0; i < mergedData.length - lagDays; i++) {
        const d = mergedData[i], fx = mergedData[i + lagDays];
        if (d.divergence != null && fx.usdcad_price != null) { divs.push(d.divergence); prices.push(fx.usdcad_price); }
      }
      if (divs.length > 10) {
        const mDiv = divs.reduce((a, b) => a + b, 0) / divs.length;
        const mPrice = prices.reduce((a, b) => a + b, 0) / prices.length;
        const num = divs.reduce((s, div, i) => s + (div - mDiv) * (prices[i] - mPrice), 0);
        const d1 = Math.sqrt(divs.reduce((s, v) => s + Math.pow(v - mDiv, 2), 0));
        const d2 = Math.sqrt(prices.reduce((s, v) => s + Math.pow(v - mPrice, 2), 0));
        correlation = num / (d1 * d2);
      }
    }
    return { current, avg, volatility, correlation, lagDays };
  }, [filteredData, mergedData]);

  if (loading) {
    return (
      <div className="space-y-5">
        <div className="card px-5 py-4 animate-skeleton">
          <div className="h-3 w-24 bg-gray-800/40 rounded mb-3" />
          <div className="h-2 max-w-sm mx-auto bg-gray-800/30 rounded-full" />
        </div>
        <div className="grid grid-cols-4 gap-3">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="card p-4 animate-skeleton" style={{ animationDelay: `${i * 0.1}s` }}>
              <div className="h-3 w-20 bg-gray-800/40 rounded mb-2" />
              <div className="h-6 w-16 bg-gray-800/30 rounded" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-4">
          {[1, 2].map(i => (
            <div key={i} className="card p-5 h-[520px] animate-skeleton" style={{ animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
      </div>
    );
  }

  const formatDate = (date) => {
    const d = new Date(date);
    return isNaN(d) ? date : `${d.getMonth() + 1}/${d.getFullYear()}`;
  };

  const statCards = [
    { label: 'Current Divergence', val: stats.current, color: stats.current > 0 ? 'text-emerald-400' : 'text-rose-400', sign: true },
    { label: 'Mean Divergence', val: stats.avg, color: 'text-blue-400', sign: true },
    { label: 'Volatility (σ)', val: stats.volatility, color: 'text-violet-400', sign: false },
    { label: `Correlation (${stats.lagDays}d lag)`, val: stats.correlation, color: 'text-amber-400', sign: false },
  ];

  return (
    <div className="space-y-5">
      {/* score guide */}
      <div className="animate-fade-in" style={{ position: 'relative', zIndex: 30 }}>
        <ScoreBar />
      </div>

      {/* time range */}
      <div className="flex gap-1.5 animate-fade-in stagger-1">
        {['all', '90d', '1y', '3y'].map(r => (
          <button
            key={r}
            onClick={() => setTimeRange(r)}
            className={`px-3 py-1 text-xs rounded-md transition-all duration-150 ${timeRange === r
              ? 'bg-white text-gray-900 font-medium shadow-sm'
              : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
              }`}
          >
            {r === 'all' ? 'All' : r.toUpperCase()}
          </button>
        ))}
      </div>

      {/* stat cards */}
      <div className="grid grid-cols-4 gap-3 animate-fade-in stagger-2" style={{ position: 'relative', zIndex: 20 }}>
        {statCards.map((s, i) => (
          <div
            key={i}
            className="relative card p-4 stat-card"
          >
            <p className="text-[11px] text-gray-500 mb-1.5 font-medium">{s.label}</p>
            <p className={`text-xl font-semibold tabular-nums tracking-tight ${s.color}`}>
              {s.sign && s.val > 0 ? '+' : ''}{Number(s.val).toFixed(3)}
            </p>

            <div className="stat-tip px-1">
              <div className="card p-2.5">
                <p className="text-[11px] text-gray-400 leading-relaxed">{STAT_DESCRIPTIONS[s.label] || STAT_DESCRIPTIONS[s.label.split('(')[0].trim()]}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* charts */}
      <div className="grid grid-cols-2 gap-4 animate-fade-in stagger-3" style={{ position: 'relative', zIndex: 1 }}>
        <div className="card p-5">
          <h2 className="text-[13px] font-medium text-gray-300 mb-5">Sentiment vs USD/CAD</h2>
          <div className="h-[460px] w-full">
            <ResponsiveContainer>
              <LineChart data={mergedData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e1e1e" vertical={false} />
                <XAxis
                  dataKey="date"
                  axisLine={{ stroke: '#2a2a2a' }}
                  tickLine={false}
                  tick={{ fontSize: 10, fill: '#555' }}
                  minTickGap={30}
                  tickFormatter={formatDate}
                />
                <YAxis yAxisId="left" domain={[-1, 1]} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#555' }} width={35} />
                <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#555' }} width={45} />
                <Legend
                  verticalAlign="top"
                  align="right"
                  iconType="line"
                  iconSize={10}
                  wrapperStyle={{ paddingBottom: '12px', fontSize: '11px' }}
                />
                <Tooltip content={<SentimentTooltip />} />
                <ReferenceLine y={0} yAxisId="left" stroke="#2a2a2a" strokeDasharray="3 3" />
                <Line yAxisId="left" name="Fed" type="stepAfter" dataKey="fed" stroke="#60a5fa" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                <Line yAxisId="left" name="BoC" type="stepAfter" dataKey="boc" stroke="#f87171" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                <Line yAxisId="right" name="USD/CAD" type="monotone" dataKey="usdcad_price" stroke="#4ade80" strokeWidth={1.5} dot={false} strokeOpacity={0.8} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card p-5">
          <h2 className="text-[13px] font-medium text-gray-300 mb-5">Divergence (Fed − BoC)</h2>
          <div className="h-[460px] w-full">
            <ResponsiveContainer>
              <BarChart data={filteredData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e1e1e" vertical={false} />
                <XAxis
                  dataKey="date"
                  axisLine={{ stroke: '#2a2a2a' }}
                  tickLine={false}
                  tick={{ fontSize: 10, fill: '#555' }}
                  minTickGap={30}
                  tickFormatter={formatDate}
                />
                <YAxis domain={[-1, 1]} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#555' }} width={35} />
                <Tooltip content={<DivergenceTooltip />} />
                <ReferenceLine y={0} stroke="#333" />
                <Bar dataKey="divergence" radius={[1, 1, 0, 0]} isAnimationActive={false}>
                  {filteredData.map((e, i) => (
                    <Cell key={i} fill={e.divergence > 0 ? '#34d399' : '#fb7185'} fillOpacity={0.75} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DivergenceChart;
