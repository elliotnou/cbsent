import React, { useEffect, useState } from 'react';

const DivergenceChart = () => {
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/divergence')
      .then(res => res.json())
      .then(json => setData(json))
      .catch(err => setError(err.message));
  }, []);

  if ((error) || data.length === 0) return;

  return (
    <div style={{ 
      fontFamily: 'monospace', 
      padding:'13.5px', 
      background: 'white', 
      color: '#000', 
    }}>
      <h2 style={{margin: '0 0 10px 0'}}>TERMINAL TEST V0.1: SENTIMENT SPREAD</h2>

      <div style={{ display: 'flex', gap: '15px', marginBottom: '20px', fontSize: '12px' }}>
        <span>[ BLUE: FED ]</span>
        <span>[ RED: BOC ]</span>
        <span>[ GREEN: SPREAD ]</span>
      </div>

      <div style={{ 
        position: 'relative', 
        height: '300px', 
        borderBottom: '2px solid #000', 
        borderLeft: '2px solid #000',
        display: 'flex',
        alignItems: 'flex-end',
        padding: '0 10px'
      }}>

        <div style={{ 
          position: 'absolute', 
          top: '50%', 
          left: 0, 
          right: 0, 
          borderTop: '1px dashed #ccc',
          zIndex: 0
        }}></div>

        {data.map((point, i) => {
          const spread = (point.fed || 0) - (point.boc || 0);
          const barHeight = Math.abs(spread) * 150; 
          
          return (
            <div key={i} style={{ 
              flex: 1, 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center',
              position: 'relative',
              height: '100%'
            }}>
              <div style={{
                position: 'absolute',
                bottom: `${(point.fed * 150) + 150}px`,
                width: '4px',
                height: '4px',
                background: 'blue',
                borderRadius: '50%',
                zIndex: 3
              }}></div>

              <div style={{
                position: 'absolute',
                bottom: `${(point.boc * 150) + 150}px`,
                width: '4px',
                height: '4px',
                background: 'red',
                borderRadius: '50%',
                zIndex: 3
              }}></div>

              <div style={{
                position: 'absolute',
                bottom: spread > 0 ? '150px' : `${150 - barHeight}px`,
                width: '60%',
                height: `${barHeight}px`,
                background: spread > 0 ? 'green' : 'red',
                border: spread > 0 ? 'solid green' : 'solid red',
                zIndex: 1
              }}></div>
            </div>
          );
        })}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '5px', fontSize: '10px' }}>
        <span>{data[0]?.date}</span>
        <span>TIMELINE (DAILY)</span>
        <span>{data[data.length - 1]?.date}</span>
      </div>

      <div style={{ marginTop: '20px', fontSize: '12px', borderTop: '1px solid white', paddingTop: '10px' }}>
        <strong>LATEST SIGNAL:</strong> {
            ((data[data.length-1]?.fed || 0) - (data[data.length-1]?.boc || 0)) > 0 
            ? "FED_DOMINANT (BULLISH USD/CAD)" 
            : "BOC_DOMINANT (BEARISH USD/CAD)"
        }
      </div>
    </div>
  );
};

export default DivergenceChart;