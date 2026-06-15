import React, { useState, useEffect } from 'react';
import { Activity, ShieldCheck, Stethoscope, FileText, CheckCircle2 } from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

export default function DoctorEscalationQueue() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSession, setSelectedSession] = useState(null);
  const [sessionDetails, setSessionDetails] = useState(null);
  const [escalationContext, setEscalationContext] = useState(null);
  const [doctorNotes, setDoctorNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchQueue();
    // Poll every 10 seconds for new escalations
    const interval = setInterval(fetchQueue, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchQueue = async () => {
    try {
      const res = await fetch(`${API_BASE}/pre-consult/queue`);
      if (res.ok) {
        const data = await res.json();
        setQueue(data);
      }
    } catch (err) {
      console.error("Failed to fetch queue", err);
    } finally {
      setLoading(false);
    }
  };

  const selectSession = async (session) => {
    setSelectedSession(session);
    setSessionDetails(null);
    setEscalationContext(null);
    setDoctorNotes('');
    
    try {
      const [resDetails, resContext] = await Promise.all([
        fetch(`${API_BASE}/pre-consult/session/${session.session_id}`),
        fetch(`${API_BASE}/pre-consult/session/${session.session_id}/escalation-context`)
      ]);
      if (resDetails.ok) {
        setSessionDetails(await resDetails.json());
      }
      if (resContext.ok) {
        setEscalationContext(await resContext.json());
      }
    } catch (err) {
      console.error("Failed to fetch session details or context", err);
    }
  };

  const submitDoctorReview = async () => {
    if (!selectedSession) return;
    setSubmitting(true);
    
    try {
      const res = await fetch(`${API_BASE}/pre-consult/session/${selectedSession.session_id}/align-release`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (res.ok) {
        // Success: Remove from queue and clear selection
        setQueue(prev => prev.filter(s => s.session_id !== selectedSession.session_id));
        setSelectedSession(null);
        alert("Session aligned and released successfully. Workflow advanced.");
      } else {
        alert("Failed to align and release session.");
      }
    } catch (err) {
      console.error("Align & Release failed", err);
      alert("Failed to align and release");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="animate-spin-fast" style={{ padding: '40px', textAlign: 'center' }}><Activity size={24} style={{ color: 'var(--primary)' }} /></div>;
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
      
      {/* QUEUE LIST */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <h3 style={{ fontSize: '18px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ShieldCheck size={20} style={{ color: 'var(--error)' }} /> Requires Immediate Review
        </h3>
        
        {queue.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 0', fontSize: '14px' }}>
            No patients currently require escalation review.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {queue.map(session => (
              <div 
                key={session.session_id} 
                onClick={() => selectSession(session)}
                style={{ 
                  padding: '16px', 
                  background: selectedSession?.session_id === session.session_id ? 'rgba(10, 132, 255, 0.1)' : 'rgba(255,255,255,0.03)', 
                  border: selectedSession?.session_id === session.session_id ? '1px solid var(--primary)' : '1px solid var(--border-light)', 
                  borderRadius: '12px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <strong style={{ fontSize: '15px' }}>{session.patients?.full_name || 'Unknown Patient'}</strong>
                  <span style={{ fontSize: '12px', color: 'var(--error)', background: 'rgba(255, 55, 95, 0.1)', padding: '2px 8px', borderRadius: '8px' }}>
                    ESCALATED
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: 'var(--text-secondary)' }}>
                  <span>{session.patients?.email}</span>
                  <span>Conf: {(session.current_confidence_score * 100).toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* DOCTOR REVIEW PANEL */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <h3 style={{ fontSize: '18px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Stethoscope size={20} style={{ color: 'var(--secondary)' }} /> Handoff Telemetry & Alignment
        </h3>

        {!selectedSession ? (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 0', fontSize: '14px', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            Select a patient from the queue to review their clinical summary.
          </div>
        ) : !sessionDetails ? (
           <div className="animate-spin-fast" style={{ padding: '40px', textAlign: 'center', flex: 1 }}><Activity size={24} style={{ color: 'var(--primary)' }} /></div>
        ) : (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div style={{ background: '#1E1E1E', padding: '16px', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.05)', boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.5)', overflowY: 'auto', maxHeight: '200px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '16px' }}>
                  <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#FF5F56' }}/>
                  <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#FFBD2E' }}/>
                  <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#27C93F' }}/>
                  <span style={{ marginLeft: '10px', fontSize: '12px', color: 'var(--text-muted)', fontFamily: '"SF Mono", "Menlo", monospace' }}>patient_data.json</span>
                </div>
                <pre style={{ margin: 0, fontSize: '13px', color: '#5AC8FA', whiteSpace: 'pre-wrap', fontFamily: '"SF Mono", "Menlo", monospace', lineHeight: 1.5 }}>
                  {JSON.stringify(escalationContext?.patient_data || sessionDetails.summary?.structured_clinical_data || {}, null, 2)}
                </pre>
              </div>

              <div style={{ background: '#1E1E1E', padding: '16px', borderRadius: '16px', border: '1px solid rgba(255, 69, 58, 0.2)', boxShadow: 'inset 0 2px 10px rgba(255,0,0,0.1)', overflowY: 'auto', maxHeight: '200px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '16px' }}>
                  <ShieldCheck size={14} style={{ color: 'var(--error)' }} />
                  <span style={{ fontSize: '12px', color: 'var(--error)', fontFamily: '"SF Mono", "Menlo", monospace' }}>threshold_rules.json</span>
                </div>
                <pre style={{ margin: 0, fontSize: '13px', color: '#FF9F0A', whiteSpace: 'pre-wrap', fontFamily: '"SF Mono", "Menlo", monospace', lineHeight: 1.5 }}>
                  {JSON.stringify(escalationContext?.thresholds || [], null, 2)}
                </pre>
              </div>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto', maxHeight: '200px', padding: '12px', background: 'rgba(0,0,0,0.2)', borderRadius: '16px' }}>
              <h5 style={{ margin: '0 0 8px 0', fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Interaction History</h5>
              {sessionDetails.logs && sessionDetails.logs.length > 0 ? sessionDetails.logs.map((log, i) => (
                <div key={i} style={{ padding: '10px', borderRadius: '12px', background: log.sender === 'PATIENT' ? 'rgba(10, 132, 255, 0.1)' : 'rgba(255,255,255,0.05)', borderLeft: log.sender === 'PATIENT' ? '3px solid var(--primary)' : '3px solid var(--secondary)' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase' }}>{log.sender}</div>
                  <div style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{log.message_text}</div>
                </div>
              )) : (
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center', padding: '20px' }}>No interaction logs available.</div>
              )}
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: 'auto' }}>
              <h5 style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>PHYSICIAN OVERRIDE / NOTES</h5>
              <textarea 
                className="form-input" 
                style={{ minHeight: '100px', fontSize: '14px', borderRadius: '16px', background: 'rgba(0,0,0,0.3)' }} 
                placeholder="Enter clinical alignment notes here..."
                value={doctorNotes}
                onChange={e => setDoctorNotes(e.target.value)}
              />
              <button 
                className="btn btn-secondary" 
                onClick={submitDoctorReview} 
                disabled={submitting}
                style={{ padding: '14px', borderRadius: '16px', fontWeight: 600, fontSize: '15px' }}
              >
                {submitting ? 'Processing...' : 'Align & Release for Booking'}
              </button>
            </div>
          </>
        )}
      </div>
      
    </div>
  );
}
