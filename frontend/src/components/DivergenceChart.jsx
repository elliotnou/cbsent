import React, { useEffect, useState, useMemo } from 'react';
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

  useEffect(() => {
    
    const fetchSentiment = fetch(`${API_BASE_URL}/api/divergence`).then(res => res.json());
    const fetchUSDCAD = fetch(`${API_BASE_URL}/api/usdcad`).then(res => res.json());

    Promise.all([fetchSentiment, fetchUSDCAD])
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
    if (timeRange === '30d') cutoff.setDate(cutoff.getDate() - 30);
    if (timeRange === '90d') cutoff.setDate(cutoff.getDate() - 90);
    if (timeRange === '1y') cutoff.setFullYear(cutoff.getFullYear() - 1);
    return data.filter(d => new Date(d.date) >= cutoff);
  }, [data, timeRange]);

  const filteredUSDCAD = useMemo(() => {
    if (timeRange === 'all') return usdcadData;
    const cutoff = new Date();
    if (timeRange === '30d') cutoff.setDate(cutoff.getDate() - 30);
    if (timeRange === '90d') cutoff.setDate(cutoff.getDate() - 90);
    if (timeRange === '1y') cutoff.setFullYear(cutoff.getFullYear() - 1);
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
    if (filteredData.length === 0) return { current: 0, avg: 0, volatility: 0, forwardCorrelation: 0, lagDays: 1 };
    const current = filteredData[filteredData.length - 1]?.divergence || 0;
    const avg = filteredData.reduce((sum, d) => sum + d.divergence, 0) / filteredData.length;
    const volatility = Math.sqrt(filteredData.reduce((sum, d) => sum + Math.pow(d.divergence - avg, 2), 0) / filteredData.length);


    const lagDays = 1;
    let forwardCorrelation = 0;
    if (mergedData.length > lagDays + 10) {
      const divs = [], fxPrices = [];
      for (let i = 0; i < mergedData.length - lagDays; i++) {
        const d = mergedData[i], fx = mergedData[i + lagDays];
        if (d.divergence != null && fx.usdcad_price != null) { divs.push(d.divergence); fxPrices.push(fx.usdcad_price); }
      }
      if (divs.length > 10) {
        const mDiv = divs.reduce((a, b) => a + b, 0) / divs.length, mPrice = fxPrices.reduce((a, b) => a + b, 0) / fxPrices.length;
        const num = divs.reduce((s, div, i) => s + (div - mDiv) * (fxPrices[i] - mPrice), 0);
        const d1 = Math.sqrt(divs.reduce((s, v) => s + Math.pow(v - mDiv, 2), 0)), d2 = Math.sqrt(fxPrices.reduce((s, v) => s + Math.pow(v - mPrice, 2), 0));
        forwardCorrelation = num / (d1 * d2);
      }
    }
    return { current, avg, volatility, forwardCorrelation, lagDays };
  }, [filteredData, mergedData]);

  if (loading) return <div className="p-20 text-center animate-pulse tracking-widest text-slate-500 font-mono text-xl uppercase">INIT_SYSTEM_SEQ...</div>;

  return (
    <div className="space-y-10 font-mono">
      {/* Range Selectors */}
      <div className="flex gap-4 border-b border-slate-900 pb-6">
        {['all', '30d', '90d', '1y'].map(r => (
          <button 
            key={r} 
            onClick={() => setTimeRange(r)} 
            className={`px-4 py-1.5 text-[10px] font-bold border transition-all uppercase ${timeRange === r ? 'bg-[#fff] text-black border-[#fff]' : 'border-slate-800 text-slate-500 hover:border-slate-600'}`}
          >
            {r}
          </button>
        ))}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-6">
        {[{ label: 'Current DIvergence', val: stats.current, color: stats.current > 0 ? 'text-green-400' : 'text-red-400' },
          { label: 'Mean divergence', val: stats.avg, color: 'text-blue-400' },
          { label: 'Volatility', val: stats.volatility, color: 'text-purple-400' },
          { label: `Correlation.(${stats.lagDays}d)`, val: stats.forwardCorrelation, color: 'text-yellow-400' }
        ].map((s, i) => (
          <div key={i} className="border border-slate-900 p-6 bg-[#0d0d0d]">
            <p className="text-[13px] text-white uppercase font-black mb-3">{s.label}</p>
            <h3 className={`text-3xl font-bold tracking-tighter ${s.color}`}>
              {s.val > 0 && i < 2 ? '+' : ''}{Number(s.val).toFixed(3)}
            </h3>
          </div>
        ))}
      </div>

      {/* Main Analysis Windows */}
      <div className="grid grid-cols-2 gap-10">
        <div className="bg-[#0d0d0d] border border-slate-900 p-8">
          <h2 className="text-xs font-black uppercase tracking-[0.3em] text-[#fff] mb-8 border-l-2 border-blue-500 pl-4">Policy_Vs_USDCAD</h2>
          <div className="h-[500px] w-full">
            <ResponsiveContainer>
              <LineChart data={mergedData}>
                <CartesianGrid strokeDasharray="2 2" stroke="#444" vertical={false} strokeWidth={2} />
                <XAxis 
                  dataKey="date"
                  axisLine={{stroke:'#8d8d8d',strokeWidth:1}}
                  tickLine={{stroke:'#8d8d8d',strokeWidth:1}}
                  tick={{ fontSize: 14, fontWeight: 700, fill: '#8d8d8d' }}
                  minTickGap={20}
                  tickFormatter={date => {
                    const d = new Date(date);
                    return isNaN(d) ? date : `${d.getMonth()+1}/${d.getFullYear()}`;
                  }}
                />
                <YAxis yAxisId="left" domain={[-1, 1]} stroke="#8d8d8d" tick={{fontSize: 16, fontWeight: 700, fill: '#8d8d8d'}} />
                <YAxis yAxisId="right" orientation="right" stroke="#8d8d8d" tick={{fontSize: 16, fontWeight: 700, fill: '#8d8d8d'}} />
                
                <Legend 
                  verticalAlign="top" 
                  align="right"
                  iconType="rect"
                  wrapperStyle={{
                    paddingBottom: '20px',
                    textTransform: 'uppercase',
                    fontSize: '12px',
                    fontWeight: 700
                  }}
                />

                <Tooltip 
                  contentStyle={{ backgroundColor: '#181818', border: '2px solid #8d8d8d', fontSize: '14px', color: '#8d8d8d', fontWeight: 700 }} 
                  labelStyle={{ color: '#8d8d8d', fontWeight: 700 }} 
                  itemStyle={{ color: '#8d8d8d', fontWeight: 700 }}
                  formatter={(value) => typeof value === 'number'? value.toFixed(2) : value}
    
                />
                
                <ReferenceLine y={0} yAxisId="left" stroke="#8d8d8d" strokeWidth={1} />
                
                <Line yAxisId="left" name="FED_SENTIMENT" type="stepAfter" dataKey="fed" stroke="#3b82f6" strokeWidth={2} dot={false} />
                <Line yAxisId="left" name="BOC_SENTIMENT" type="stepAfter" dataKey="boc" stroke="#ef4444" strokeWidth={2} dot={false} />
                <Line yAxisId="right" name="USD_CAD_PRICE" type="monotone" dataKey="usdcad_price" stroke="#22c55e" strokeWidth={2} dot={false}  />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-[#0d0d0d] border border-slate-900 p-8">
          <h2 className="text-xs font-black uppercase tracking-[0.3em] text-[#fff] mb-8 border-l-2 border-slate-700 pl-4">Sentiment_Delta</h2>
          <div className="h-[500px] w-full">
            <ResponsiveContainer>
              <BarChart data={filteredData}>
                <CartesianGrid strokeDasharray="2 2" stroke="#444" vertical={false} strokeWidth={1} />
                <XAxis 
                  dataKey="date"
                  axisLine={{stroke:'#8d8d8d',strokeWidth:1}}
                  tickLine={{stroke:'#8d8d8d',strokeWidth:1}}
                  tick={{ fontSize: 14, fontWeight: 700, fill: '#8d8d8d' }}
                  minTickGap={20}
                  tickFormatter={date => {
                    const d = new Date(date);
                    return isNaN(d) ? date : `${d.getMonth()+1}/${d.getFullYear()}`;
                  }}
                />
                <YAxis domain={[-1, 1]} stroke="#8d8d8d" tick={{fontSize: 16, fontWeight: 700, fill: '#8d8d8d'}} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#181818', border: '2px solid #8d8d8d', fontSize: '14px', color: '#8d8d8d', fontWeight: 700 }} 
                  formatter={(value) => typeof value === 'number' ? value.toFixed(2) : value}
                  itemStyle={{ color: '#8d8d8d' }} 
                />
                <ReferenceLine y={0} stroke="#a7a7a7" strokeWidth={1} />
                <Bar dataKey="divergence">
                  {filteredData.map((e, i) => (
                    <Cell key={i} fill={e.divergence > 0 ? '#10b981' : '#f43f5e'} opacity={0.9} />
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