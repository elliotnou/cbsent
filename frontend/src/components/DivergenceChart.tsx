import { useEffect, useState, useMemo } from 'react';
import {
  LineChart, Line, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts';

const DivergenceChart = () => {
  const [data, setData] = useState([]);
  const [usdcadData, setUsdcadData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('all');
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  const SentimentTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{ backgroundColor: '#1a1a1a', border: '1px solid #444', padding: '10px', fontSize: '13px' }}>
        <p style={{ color: '#999', marginBottom: '6px' }}>{label}</p>
        {payload.map((entry, i) => {
          let color = '#999';
          if (entry.name === 'Fed Sentiment') color = '#3b82f6';
          else if (entry.name === 'BoC Sentiment') color = '#ef4444';
          else if (entry.name === 'USD/CAD') color = '#22c55e';
          return (
            <p key={i} style={{ color, margin: '3px 0' }}>
              {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
            </p>
          );
        })}
      </div>
    );
  };

  const DivergenceTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const val = payload[0].value;
    const color = val > 0 ? '#10b981' : '#f43f5e';
    return (
      <div style={{ backgroundColor: '#1a1a1a', border: '1px solid #444', padding: '10px', fontSize: '13px', maxWidth: '260px' }}>
        <p style={{ color: '#999', marginBottom: '6px' }}>{label}</p>
        <p style={{ color, margin: '3px 0' }}>
          Divergence: {typeof val === 'number' ? val.toFixed(2) : val}
        </p>
        <p style={{ color: '#888', fontSize: '11px', lineHeight: '1.4', margin: 0 }}>
          {val > 0
            ? 'Fed is more hawkish than BoC'
            : val < 0
              ? 'BoC is more hawkish than Fed'
              : 'Equal sentiment'}
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

  if (loading) return <div className="p-20 text-center text-gray-500 text-sm">Loading...</div>;

  const formatDate = (date) => {
    const d = new Date(date);
    return isNaN(d) ? date : `${d.getMonth() + 1}/${d.getFullYear()}`;
  };

  return (
    <div className="space-y-6">
      {/* score guide */}
      <div className="bg-[#1a1a1a] border border-gray-800 rounded-md px-4 py-3">
        <div className="text-xs text-gray-500 mb-2">Score guide</div>
        <div className="relative h-6 flex items-center">
          <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-1.5 bg-gradient-to-r from-red-500/60 via-gray-600 to-green-500/60 rounded-full"></div>
        </div>
        <div className="flex justify-between text-xs text-gray-500">
          <span className="text-red-400">-1.0 Dovish</span>
          <span>0 Neutral</span>
          <span className="text-green-400">+1.0 Hawkish</span>
        </div>
      </div>

      {/* time range buttons */}
      <div className="flex gap-2 border-b border-gray-800 pb-4">
        {['all', '90d', '1y', '3y'].map(r => (
          <button
            key={r}
            onClick={() => setTimeRange(r)}
            className={`px-3 py-1 text-xs font-medium rounded transition-colors ${timeRange === r
                ? 'bg-white text-black'
                : 'text-gray-500 hover:text-gray-300 border border-gray-800 hover:border-gray-600'
              }`}
          >
            {r === 'all' ? 'All' : r.toUpperCase()}
          </button>
        ))}
      </div>

      {/* stats cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Current Divergence', val: stats.current, color: stats.current > 0 ? 'text-green-400' : 'text-red-400' },
          { label: 'Mean Divergence', val: stats.avg, color: 'text-blue-400' },
          { label: 'Volatility (σ)', val: stats.volatility, color: 'text-purple-400' },
          { label: `Correlation (${stats.lagDays}d lag)`, val: stats.correlation, color: 'text-yellow-400' },
        ].map((s, i) => (
          <div key={i} className="border border-gray-800 rounded-md p-4 bg-[#1a1a1a]">
            <p className="text-xs text-gray-500 mb-2">{s.label}</p>
            <p className={`text-2xl font-semibold tabular-nums ${s.color}`}>
              {s.val > 0 && i < 2 ? '+' : ''}{Number(s.val).toFixed(3)}
            </p>
          </div>
        ))}
      </div>

      {/* charts */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-[#1a1a1a] border border-gray-800 rounded-md p-6">
          <h2 className="text-sm font-medium text-gray-300 mb-6">Policy Sentiment vs USD/CAD</h2>
          <div className="h-[480px] w-full">
            <ResponsiveContainer>
              <LineChart data={mergedData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                <XAxis
                  dataKey="date"
                  axisLine={{ stroke: '#555' }}
                  tickLine={{ stroke: '#555' }}
                  tick={{ fontSize: 11, fill: '#888' }}
                  minTickGap={20}
                  tickFormatter={formatDate}
                />
                <YAxis yAxisId="left" domain={[-1, 1]} stroke="#555" tick={{ fontSize: 11, fill: '#888' }} />
                <YAxis yAxisId="right" orientation="right" stroke="#555" tick={{ fontSize: 11, fill: '#888' }} />
                <Legend
                  verticalAlign="top"
                  align="right"
                  iconType="line"
                  wrapperStyle={{ paddingBottom: '16px', fontSize: '11px' }}
                />
                <Tooltip content={<SentimentTooltip />} />
                <ReferenceLine y={0} yAxisId="left" stroke="#555" />
                <Line yAxisId="left" name="Fed Sentiment" type="stepAfter" dataKey="fed" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
                <Line yAxisId="left" name="BoC Sentiment" type="stepAfter" dataKey="boc" stroke="#ef4444" strokeWidth={1.5} dot={false} />
                <Line yAxisId="right" name="USD/CAD" type="monotone" dataKey="usdcad_price" stroke="#22c55e" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-[#1a1a1a] border border-gray-800 rounded-md p-6">
          <h2 className="text-sm font-medium text-gray-300 mb-6">Sentiment Divergence (Fed − BoC)</h2>
          <div className="h-[480px] w-full">
            <ResponsiveContainer>
              <BarChart data={filteredData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                <XAxis
                  dataKey="date"
                  axisLine={{ stroke: '#555' }}
                  tickLine={{ stroke: '#555' }}
                  tick={{ fontSize: 11, fill: '#888' }}
                  minTickGap={20}
                  tickFormatter={formatDate}
                />
                <YAxis domain={[-1, 1]} stroke="#555" tick={{ fontSize: 11, fill: '#888' }} />
                <Tooltip content={<DivergenceTooltip />} />
                <ReferenceLine y={0} stroke="#666" />
                <Bar dataKey="divergence">
                  {filteredData.map((e, i) => (
                    <Cell key={i} fill={e.divergence > 0 ? '#10b981' : '#f43f5e'} opacity={0.85} />
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