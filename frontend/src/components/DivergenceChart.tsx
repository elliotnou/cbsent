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

const DivergenceChart = () => {
  const [data, setData] = useState([]);
  const [usdcadData, setUsdcadData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('all');
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  const SentimentTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-[#161616] border border-gray-700/60 rounded px-3 py-2.5 text-xs shadow-lg">
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
      <div className="bg-[#161616] border border-gray-700/60 rounded px-3 py-2.5 text-xs shadow-lg max-w-[240px]">
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
      <div className="flex items-center justify-center py-24">
        <div className="text-sm text-gray-500">Loading data...</div>
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
      <div className="bg-[#141414] border border-gray-800/80 rounded-lg px-5 py-3">
        <div className="text-[11px] text-gray-500 mb-2 font-medium uppercase tracking-wide">Score range</div>
        <div className="relative h-5 flex items-center">
          <div className="absolute inset-x-0 h-1 bg-gradient-to-r from-rose-500/50 via-gray-700 to-emerald-500/50 rounded-full"></div>
        </div>
        <div className="flex justify-between text-[11px] text-gray-500 mt-1">
          <span className="text-rose-400/80">−1.0 Dovish</span>
          <span>0 Neutral</span>
          <span className="text-emerald-400/80">+1.0 Hawkish</span>
        </div>
      </div>

      {/* time range */}
      <div className="flex gap-1.5">
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
      <div className="grid grid-cols-4 gap-3">
        {statCards.map((s, i) => (
          <div
            key={i}
            className="relative bg-[#141414] border border-gray-800/80 rounded-lg p-4 hover:border-gray-700 transition-colors cursor-default group"
          >
            <p className="text-[11px] text-gray-500 mb-1.5 font-medium">{s.label}</p>
            <p className={`text-xl font-semibold tabular-nums tracking-tight ${s.color}`}>
              {s.sign && s.val > 0 ? '+' : ''}{Number(s.val).toFixed(3)}
            </p>

            <div className="absolute left-0 right-0 -bottom-1 translate-y-full z-50 px-1 hidden group-hover:block">
              <div className="bg-[#1a1a1a] border border-gray-700 rounded-md p-2.5 shadow-xl">
                <p className="text-[11px] text-gray-400 leading-relaxed">{STAT_DESCRIPTIONS[s.label] || STAT_DESCRIPTIONS[s.label.split('(')[0].trim()]}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* charts */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-[#141414] border border-gray-800/80 rounded-lg p-5">
          <h2 className="text-[13px] font-medium text-gray-300 mb-5">Sentiment vs USD/CAD</h2>
          <div className="h-[460px] w-full">
            <ResponsiveContainer>
              <LineChart data={mergedData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                <XAxis
                  dataKey="date"
                  axisLine={{ stroke: '#333' }}
                  tickLine={false}
                  tick={{ fontSize: 10, fill: '#666' }}
                  minTickGap={30}
                  tickFormatter={formatDate}
                />
                <YAxis yAxisId="left" domain={[-1, 1]} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#666' }} width={35} />
                <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#666' }} width={45} />
                <Legend
                  verticalAlign="top"
                  align="right"
                  iconType="line"
                  iconSize={10}
                  wrapperStyle={{ paddingBottom: '12px', fontSize: '11px' }}
                />
                <Tooltip content={<SentimentTooltip />} />
                <ReferenceLine y={0} yAxisId="left" stroke="#333" strokeDasharray="3 3" />
                <Line yAxisId="left" name="Fed" type="stepAfter" dataKey="fed" stroke="#60a5fa" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                <Line yAxisId="left" name="BoC" type="stepAfter" dataKey="boc" stroke="#f87171" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                <Line yAxisId="right" name="USD/CAD" type="monotone" dataKey="usdcad_price" stroke="#4ade80" strokeWidth={1.5} dot={false} strokeOpacity={0.8} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-[#141414] border border-gray-800/80 rounded-lg p-5">
          <h2 className="text-[13px] font-medium text-gray-300 mb-5">Divergence (Fed − BoC)</h2>
          <div className="h-[460px] w-full">
            <ResponsiveContainer>
              <BarChart data={filteredData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                <XAxis
                  dataKey="date"
                  axisLine={{ stroke: '#333' }}
                  tickLine={false}
                  tick={{ fontSize: 10, fill: '#666' }}
                  minTickGap={30}
                  tickFormatter={formatDate}
                />
                <YAxis domain={[-1, 1]} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#666' }} width={35} />
                <Tooltip content={<DivergenceTooltip />} />
                <ReferenceLine y={0} stroke="#444" />
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