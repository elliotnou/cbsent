import React, { useEffect, useState, useMemo, Suspense, useRef } from 'react';
import {
  LineChart, Line, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, useGLTF } from '@react-three/drei';


const Model3D = () => {
  const { scene } = useGLTF('/cadpenny.glb');
  const modelRef = useRef();

  useFrame(() => {
    if (modelRef.current) {
      modelRef.current.rotation.y += 0.005;
    }
  });

  return <primitive ref={modelRef} object={scene} scale={1.5} />;
};

const Fallback3D = () => {
  return (
    <div className="w-full h-full flex items-center justify-center text-slate-600 text-xs">
      <div className="text-center">
        <div className="mb-1 text-[10px]">3D Model</div>
        <div className="text-[8px] text-slate-700">model.glb</div>
      </div>
    </div>
  );
};

const Model3DWrapper = () => {
  const [modelExists, setModelExists] = useState(null);

  useEffect(() => {
    fetch('/model.glb', { method:'HEAD'})
      .then(() => setModelExists(true))
      .catch(() => setModelExists(false));
  }, []);

  if (modelExists === null) {
    return <Fallback3D />;
  }

  if (modelExists === false) {
    return <Fallback3D />;
  }

  return (
    <Canvas
      camera={{ position: [0, 0, 38], fov: 50 }}
      onCreated={({ gl }) => {
        gl.setClearColor('#050505', 1);
      }}
      style={{ background: 'transparent' }}
    >
      <ambientLight intensity={1.2} />
      <directionalLight position={[10, 10, 5]} intensity={2} />
      <directionalLight position={[-10, -10, -5]} intensity={0.5} />
      <Suspense fallback={null}>
        <Model3D />
      </Suspense>
      <OrbitControls enableZoom={false} enablePan={false} />
    </Canvas>
  );
};

const DivergenceChart = () => {
  const [data, setData] = useState([]);
  const [usdcadData, setUsdcadData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('all');
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ backgroundColor: '#181818', border: '2px solid #8d8d8d', padding: '10px', fontSize: '14px', fontWeight: 700 }}>
          <p style={{ color: '#8d8d8d', marginBottom: '8px' }}>{label}</p>
          {payload.map((entry, index) => {
            let color = '#8d8d8d';
            if (entry.name === 'FED_SENTIMENT') color = '#3b82f6';
            else if (entry.name === 'BOC_SENTIMENT') color = '#ef4444';
            else if (entry.name === 'USD_CAD_PRICE') color = '#22c55e';

            return (
              <p key={index} style={{ color, margin: '4px 0' }}>
                {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
              </p>
            );
          })}
        </div>
      );
    }
    return null;
  };

  const DivergenceTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const value = payload[0].value;
      const color = value > 0 ? '#10b981' : '#f43f5e';

      return (
        <div style={{ backgroundColor: '#181818', border: '2px solid #8d8d8d', padding: '12px', fontSize: '14px', fontWeight: 700, maxWidth: '280px' }}>
          <p style={{ color: '#8d8d8d', marginBottom: '8px' }}>{label}</p>
          <p style={{ color, margin: '4px 0', marginBottom: '8px' }}>
            Divergence: {typeof value === 'number' ? value.toFixed(2) : value}
          </p>
          <p style={{ color: '#a0a0a0', fontSize: '11px', lineHeight: '1.4', margin: '0' }}>
            {value > 0
              ? 'Positive: Fed is more hawkish than BoC (Fed - BoC > 0)'
              : value < 0
              ? 'Negative: BoC is more hawkish than Fed (Fed - BoC < 0)'
              : 'Zero: Both central banks have equal sentiment'}
          </p>
        </div>
      );
    }
    return null;
  };

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
    <div className="space-y-8 font-mono">
      <style>{`
        * {
          outline: none !important;
        }
        *:focus {
          outline: none !important;
        }
      `}</style>
      <div className="flex items-center gap-8">
        <div className="flex-1">
          <div className="relative bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700 rounded px-4 py-3 hover:border-slate-600 transition-all duration-300 shadow-lg">
            <div className="text-xs text-slate-400 mb-2 uppercase tracking-wide">Score Guide:</div>
            <div className="relative h-8 flex items-center">
              <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-2 bg-gradient-to-r from-red-500/70 via-slate-600 to-green-500/70 rounded-full shadow-inner"></div>
              <div className="absolute left-0 top-0 bottom-0 w-1/3 group flex items-center">
                <span className="absolute bottom-full left-0 mb-2 w-64 p-2 bg-slate-900 border border-slate-700 rounded text-[10px] text-slate-300 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
                  Dovish: Favors lower interest rates and accommodative monetary policy to stimulate economic growth and employment
                </span>
              </div>
              <div className="absolute left-1/3 top-0 bottom-0 w-1/3 group flex items-center">
                <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-2 bg-slate-900 border border-slate-700 rounded text-[10px] text-slate-300 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
                  Neutral: Balanced stance with no clear bias toward raising or lowering interest rates
                </span>
              </div>
              <div className="absolute right-0 top-0 bottom-0 w-1/3 group flex items-center">
                <span className="absolute bottom-full right-0 mb-2 w-64 p-2 bg-slate-900 border border-slate-700 rounded text-[10px] text-slate-300 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
                  Hawkish: Favors higher interest rates and restrictive monetary policy to control inflation
                </span>
              </div>
            </div>
            <div className="flex justify-between text-xs text-slate-400">
              <span className="text-red-400">-1.0 Dovish</span>
              <span className="text-slate-300">0 Neutral</span>
              <span className="text-green-400">1.0 Hawkish</span>
            </div>
          </div>
        </div>

        <div className="w-40 h-28">
          <Model3DWrapper />
        </div>
      </div>

      <div className="flex gap-4 border-b border-slate-900 pb-5">
        {['all','90d','1y','3y'].map(r => (
          <button
            key={r}
            onClick={() => setTimeRange(r)}
            className={`px-4 py-1.5 text-[10px] font-bold border transition-all duration-300 uppercase ${timeRange === r ? 'bg-[#fff] text-black border-[#fff] shadow-lg scale-105' : 'border-slate-800 text-slate-500 hover:border-slate-600 hover:text-slate-300 hover:scale-105'}`}
          >
            {r}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-4 gap-6">
        {[
          {
            label: 'Current DIvergence',
            val: stats.current,
            color: stats.current > 0 ? 'text-green-400' : 'text-red-400',
            glow: stats.current > 0 ? 'glow-green' : 'glow-red',
            tooltip: 'The most recent difference between Fed and BoC sentiment scores. Positive means Fed is more hawkish than BoC.'
          },
          {
            label: 'Mean divergence',
            val: stats.avg,
            color: 'text-blue-400',
            glow: 'glow-blue',
            tooltip: 'Average divergence over the selected time period. Shows the typical policy stance difference between the two central banks.'
          },
          {
            label: 'Volatility',
            val: stats.volatility,
            color: 'text-purple-400',
            glow: '',
            tooltip: 'Standard deviation of the divergence. Higher values indicate more fluctuation in policy stance differences.'
          },
          {
            label: `Correlation.(${stats.lagDays}d)`,
            val: stats.forwardCorrelation,
            color: 'text-yellow-400',
            glow: '',
            tooltip: `Correlation between policy divergence and USD/CAD price ${stats.lagDays} day later. Measures predictive relationship between central bank sentiment and currency movement.`
          }
        ].map((s, i) => (
          <div key={i} className="relative border border-slate-900 p-6 bg-gradient-to-br from-[#0d0d0d] to-[#1a1a1a] hover:border-slate-700 hover:card-glow hover:scale-[1.02] transition-all duration-300 group">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-full mb-2 w-72 p-3 bg-slate-900 border border-slate-700 rounded text-[11px] text-slate-300 leading-relaxed opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-20 pointer-events-none">
              {s.tooltip}
            </div>
            <p className="text-[13px] text-slate-400 uppercase font-black mb-3 group-hover:text-white transition-colors">{s.label}</p>
            <h3 className={`text-3xl font-bold tracking-tighter ${s.color} ${s.glow} ${i === 0 ? 'pulse-glow' : ''}`}>
              {s.val > 0 && i < 2 ? '+' : ''}{Number(s.val).toFixed(3)}
            </h3>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-10">
        <div className="bg-gradient-to-br from-[#0d0d0d] to-[#1a1a1a] border border-slate-900 p-8 hover:border-slate-600 hover:shadow-2xl transition-all duration-500 group">
          <h2 className="text-xs font-black uppercase tracking-[0.3em] text-[#fff] mb-8 border-l-2 border-blue-500 pl-4 group-hover:border-blue-400 transition-colors">Policy_Vs_USDCAD</h2>
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

                <Tooltip content={<CustomTooltip />} />
                
                <ReferenceLine y={0} yAxisId="left" stroke="#8d8d8d" strokeWidth={1} />
                
                <Line yAxisId="left" name="FED_SENTIMENT" type="stepAfter" dataKey="fed" stroke="#3b82f6" strokeWidth={2} dot={false} />
                <Line yAxisId="left" name="BOC_SENTIMENT" type="stepAfter" dataKey="boc" stroke="#ef4444" strokeWidth={2} dot={false} />
                <Line yAxisId="right" name="USD_CAD_PRICE" type="monotone" dataKey="usdcad_price" stroke="#22c55e" strokeWidth={2} dot={false}  />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-gradient-to-br from-[#0d0d0d] to-[#1a1a1a] border border-slate-900 p-8 hover:border-slate-600 hover:shadow-2xl transition-all duration-500 group">
          <h2 className="text-xs font-black uppercase tracking-[0.3em] text-[#fff] mb-8 border-l-2 border-slate-700 pl-4 group-hover:border-slate-500 transition-colors">Sentiment_Delta</h2>
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
                <Tooltip content={<DivergenceTooltip />} />
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