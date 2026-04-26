import React, { useEffect, useState } from 'react';
import { getFirestore, collection, query, orderBy, limit, onSnapshot } from 'firebase/firestore';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export interface DoctorDashboardProps {
  sessionId: string;
}

export const DoctorDashboard = ({ sessionId }: DoctorDashboardProps) => {
  const [data, setData] = useState<any[]>([]);
  const [patients, setPatients] = useState<{id: string, name: string}[]>([
    { id: sessionId, name: 'Current Patient' }
  ]);

  useEffect(() => {
    const db = getFirestore();
    const eventsRef = collection(db, `sessions/${sessionId}/events`);
    
    // Subscribe to the most recent 100 events uploaded by the parent relay
    const q = query(eventsRef, orderBy('timestamp', 'desc'), limit(100));

    const unsubscribe = onSnapshot(q, (snapshot: any) => {
      const liveData: any[] = [];
      snapshot.forEach((doc: any) => {
        liveData.push({ id: doc.id, ...doc.data() });
      });
      // Firestore sorts DESC so we get the newest. Reverse it to chronologically map Left -> Right on chart
      setData(liveData.reverse());
    });

    return () => unsubscribe();
  }, [sessionId]);

  const latestEvent = data.length > 0 ? data[data.length - 1] : null;

  return (
    <div style={{ padding: 24, fontFamily: 'system-ui, -apple-system, sans-serif', maxWidth: 1200, margin: '0 auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, color: '#1f2937' }}>Neonatal Telemetry Monitor</h2>
        
        {latestEvent && latestEvent.alert_state === 'EMERGENCY' ? (
          <div style={{ backgroundColor: '#fee2e2', color: '#ef4444', padding: '10px 20px', borderRadius: 8, fontWeight: 'bold', border: '1px solid #ef4444' }}>
            ⚠️ EMERGENCY ALERT ACTIVE
          </div>
        ) : (
          <div style={{ color: '#10b981', fontWeight: 'bold' }}>
            {latestEvent ? '● Receiving Data' : '○ Awaiting Connection'}
          </div>
        )}
      </header>

      {/* Live Chart Container */}
      <div style={{ width: '100%', height: 450, backgroundColor: '#ffffff', padding: 24, borderRadius: 12, boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', marginBottom: 24 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
            
            <XAxis 
              dataKey="timestamp" 
              tickFormatter={(tick: any) => new Date(tick).toLocaleTimeString()} 
              stroke="#9ca3af"
              tick={{ fontSize: 12 }}
            />
            
            {/* Left Y-Axis for Heart Rate */}
            <YAxis 
              yAxisId="left" 
              domain={[60, 200]} 
              stroke="#ef4444"
              tick={{ fontSize: 12 }}
            />
            
            {/* Right Y-Axis for Respiratory Rate */}
            <YAxis 
              yAxisId="right" 
              orientation="right" 
              domain={[10, 80]} 
              stroke="#3b82f6"
              tick={{ fontSize: 12 }}
            />
            
            <Tooltip 
              labelFormatter={(label: any) => new Date(label).toLocaleString()}
              contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' }}
            />
            <Legend wrapperStyle={{ paddingTop: 20 }} />
            
            <Line 
              yAxisId="left" 
              type="monotone" 
              dataKey="hr_bpm" 
              stroke="#ef4444" 
              name="Heart Rate (BPM)" 
              strokeWidth={3} 
              dot={false} 
              isAnimationActive={false}
            />
            
            <Line 
              yAxisId="right" 
              type="monotone" 
              dataKey="rr_bpm" 
              stroke="#3b82f6" 
              name="Resp Rate (B/min)" 
              strokeWidth={3} 
              dot={false} 
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Latest Snapshot Table */}
      <div style={{ backgroundColor: '#ffffff', padding: 24, borderRadius: 12, boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}>
        <h3 style={{ margin: '0 0 16px 0', color: '#374151' }}>Latest Vital Snapshot</h3>
        
        {latestEvent ? (
           <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: 14 }}>
             <thead>
               <tr style={{ borderBottom: '2px solid #e5e7eb', color: '#6b7280' }}>
                 <th style={{ padding: 12 }}>Time</th>
                 <th style={{ padding: 12 }}>Heart Rate</th>
                 <th style={{ padding: 12 }}>Respiratory Rate</th>
                 <th style={{ padding: 12 }}>Status</th>
                 <th style={{ padding: 12 }}>Device ID</th>
                 <th style={{ padding: 12 }}>Confidence (HR / RR)</th>
               </tr>
             </thead>
             <tbody>
               <tr>
                 <td style={{ padding: 12, fontWeight: '500' }}>{new Date(latestEvent.timestamp).toLocaleTimeString()}</td>
                 <td style={{ padding: 12, color: '#ef4444', fontWeight: 'bold' }}>{latestEvent.hr_bpm} BPM</td>
                 <td style={{ padding: 12, color: '#3b82f6', fontWeight: 'bold' }}>{latestEvent.rr_bpm} B/min</td>
                 <td style={{ padding: 12 }}>
                    <span style={{ 
                      padding: '4px 8px', 
                      borderRadius: 4, 
                      fontWeight: 'bold',
                      backgroundColor: latestEvent.alert_state === 'EMERGENCY' ? '#fee2e2' : latestEvent.alert_state === 'CAUTION' ? '#fef3c7' : '#d1fae5',
                      color: latestEvent.alert_state === 'EMERGENCY' ? '#ef4444' : latestEvent.alert_state === 'CAUTION' ? '#d97706' : '#10b981'
                    }}>
                      {latestEvent.alert_state}
                    </span>
                 </td>
                 <td style={{ padding: 12, color: '#6b7280' }}>{latestEvent.device_id}</td>
                 <td style={{ padding: 12, color: '#6b7280' }}>{Math.round(latestEvent.hr_confidence * 100)}% / {Math.round(latestEvent.rr_confidence * 100)}%</td>
               </tr>
             </tbody>
           </table>
        ) : (
          <p style={{ color: '#9ca3af', margin: 0 }}>Awaiting incoming telemetry from patient device...</p>
        )}
      </div>
    </div>
  );
};
