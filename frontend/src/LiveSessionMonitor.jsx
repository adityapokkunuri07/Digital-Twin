import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Activity, Eye, MessageSquare, Send, Radio, User, Bot, RefreshCw, AlertTriangle } from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

export default function LiveSessionMonitor() {
  const [activeSessions, setActiveSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [sessionDetails, setSessionDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [doctorMessage, setDoctorMessage] = useState('');
  const [sendingMsg, setSendingMsg] = useState(false);
  const chatEndRef = useRef(null);

  // Poll active sessions every 5 seconds
  useEffect(() => {
    fetchActiveSessions();
    const interval = setInterval(fetchActiveSessions, 5000);
    return () => clearInterval(interval);
  }, []);

  // Poll selected session details every 3 seconds
  useEffect(() => {
    if (!selectedSessionId) return;
    fetchSessionDetails(selectedSessionId);
    const interval = setInterval(() => fetchSessionDetails(selectedSessionId), 3000);
    return () => clearInterval(interval);
  }, [selectedSessionId]);

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [sessionDetails?.logs]);

  const fetchActiveSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/pre-consult/queue/active`);
      if (res.ok) {
        const data = await res.json();
        setActiveSessions(data);
      }
    } catch (err) {
      console.error("Failed to fetch active sessions", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSessionDetails = async (sessionId) => {
    try {
      const res = await fetch(`${API_BASE}/pre-consult/session/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setSessionDetails(data);
      }
    } catch (err) {
      console.error("Failed to fetch session details", err);
    } finally {
      setDetailsLoading(false);
    }
  };

  const selectSession = (session) => {
    setSelectedSessionId(session.session_id);
    setSessionDetails(null);
    setDetailsLoading(true);
    setDoctorMessage('');
  };

  const sendDirectMessage = async () => {
    if (!selectedSessionId || !doctorMessage.trim()) return;
    setSendingMsg(true);

    try {
      const res = await fetch(`${API_BASE}/session/${selectedSessionId}/doctor-inject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: doctorMessage })
      });

      if (res.ok) {
        setDoctorMessage('');
        // Immediately refresh to show the injected message
        await fetchSessionDetails(selectedSessionId);
      } else {
        alert("Failed to send message.");
      }
    } catch (err) {
      console.error("Failed to inject message", err);
      alert("Failed to send message.");
    } finally {
      setSendingMsg(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'GATHERING':
      case 'awaiting_user_input':
      case 'probing': return 'var(--success)';
      case 'SYNTHESIZING':
      case 'processing_synthesis': return 'var(--warning)';
      case 'SYNTHESIZING_PARTIAL':
      case 'processing_partial_synthesis': return 'var(--error)';
      default: return 'var(--text-muted)';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'GATHERING':
      case 'awaiting_user_input':
      case 'probing': return 'Gathering';
      case 'SYNTHESIZING':
      case 'processing_synthesis': return 'Synthesizing';
      case 'SYNTHESIZING_PARTIAL':
      case 'processing_partial_synthesis': return 'Partial Synth';
      default: return status;
    }
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    try {
      const d = new Date(timestamp);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch { return ''; }
  };

  if (loading) {
    return (
      <div style={{ padding: '60px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
        <RefreshCw size={24} className="animate-spin-fast" style={{ color: 'var(--primary)' }} />
        <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Loading active sessions...</span>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: '24px', minHeight: '70vh' }}>

      {/* ─── LEFT: Active Sessions List ─── */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3 style={{ fontSize: '16px', display: 'flex', alignItems: 'center', gap: '10px', margin: 0 }}>
            <Radio size={18} style={{ color: 'var(--success)' }} className="animate-pulse-slow" />
            Live Sessions
          </h3>
          <span className="badge badge-info" style={{ fontSize: '11px' }}>
            {activeSessions.length} active
          </span>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {activeSessions.length === 0 ? (
            <div style={{
              color: 'var(--text-muted)', textAlign: 'center', padding: '60px 16px',
              fontSize: '13px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px',
              flex: 1, justifyContent: 'center'
            }}>
              <Eye size={28} style={{ opacity: 0.3 }} />
              No active patient sessions.
              <br />
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Sessions will appear here when a patient starts a consultation.
              </span>
            </div>
          ) : (
            activeSessions.map(session => {
              const isSelected = selectedSessionId === session.session_id;
              return (
                <div
                  key={session.session_id}
                  onClick={() => selectSession(session)}
                  style={{
                    padding: '14px 16px',
                    background: isSelected ? 'rgba(10, 132, 255, 0.12)' : 'rgba(255,255,255,0.03)',
                    border: isSelected ? '1px solid var(--primary)' : '1px solid var(--border-light)',
                    borderRadius: '14px',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <strong style={{ fontSize: '14px' }}>
                      {session.patients?.full_name || `Patient ${session.session_id?.slice(0, 6)}`}
                    </strong>
                    <span style={{
                      fontSize: '10px', fontWeight: 600, textTransform: 'uppercase',
                      padding: '2px 8px', borderRadius: '8px', letterSpacing: '0.04em',
                      color: getStatusColor(session.status),
                      background: `color-mix(in srgb, ${getStatusColor(session.status)} 12%, transparent)`
                    }}>
                      {getStatusLabel(session.status)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-secondary)' }}>
                    <span>{session.patients?.email || '—'}</span>
                    <span>Turn {session.turn_count || 0}</span>
                  </div>
                  <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div style={{
                      flex: 1, height: '3px', borderRadius: '2px', background: 'rgba(255,255,255,0.06)', overflow: 'hidden'
                    }}>
                      <div style={{
                        height: '100%', borderRadius: '2px',
                        width: `${Math.min((session.current_confidence_score || 0) * 100, 100)}%`,
                        background: `linear-gradient(90deg, var(--primary), var(--secondary))`,
                        transition: 'width 0.5s ease'
                      }} />
                    </div>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}>
                      {((session.current_confidence_score || 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* ─── RIGHT: Live Chat Transcript ─── */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: 0 }}>
        {!selectedSessionId ? (
          <div style={{
            flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            color: 'var(--text-muted)', gap: '12px', padding: '40px'
          }}>
            <MessageSquare size={36} style={{ opacity: 0.2 }} />
            <span style={{ fontSize: '14px' }}>Select a session to monitor the live conversation.</span>
          </div>
        ) : detailsLoading && !sessionDetails ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <RefreshCw size={24} className="animate-spin-fast" style={{ color: 'var(--primary)' }} />
          </div>
        ) : (
          <>
            {/* Chat Header */}
            <div style={{
              padding: '16px 24px', borderBottom: '1px solid var(--border-light)',
              background: 'rgba(255,255,255,0.02)', display: 'flex', alignItems: 'center', justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{
                  width: '36px', height: '36px', borderRadius: '50%',
                  background: 'linear-gradient(135deg, var(--primary), var(--secondary))',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#FFF', fontSize: '14px', fontWeight: 700
                }}>
                  {(sessionDetails?.session?.patients?.full_name || 'P')[0]}
                </div>
                <div>
                  <div style={{ fontSize: '15px', fontWeight: 600 }}>
                    {sessionDetails?.session?.patients?.full_name || `Session ${selectedSessionId?.slice(0, 8)}`}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {sessionDetails?.session?.patients?.email || selectedSessionId}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                {sessionDetails?.session?.status && (
                  <span style={{
                    fontSize: '11px', fontWeight: 600, textTransform: 'uppercase',
                    padding: '4px 12px', borderRadius: '8px',
                    color: getStatusColor(sessionDetails.session.status),
                    background: `color-mix(in srgb, ${getStatusColor(sessionDetails.session.status)} 12%, transparent)`,
                    display: 'flex', alignItems: 'center', gap: '6px'
                  }}>
                    <span style={{
                      width: '6px', height: '6px', borderRadius: '50%',
                      background: getStatusColor(sessionDetails.session.status),
                      animation: 'pulse 2s infinite'
                    }} />
                    {getStatusLabel(sessionDetails.session.status)}
                  </span>
                )}
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Conf: {((sessionDetails?.session?.current_confidence_score || 0) * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Telemetry Strip */}
            {sessionDetails?.session?.current_extracted_entities &&
              Object.keys(sessionDetails.session.current_extracted_entities).length > 0 && (
                <div style={{
                  padding: '10px 24px', borderBottom: '1px solid var(--border-light)',
                  background: 'rgba(191, 90, 242, 0.04)', display: 'flex', alignItems: 'center', gap: '8px',
                  overflowX: 'auto'
                }}>
                  <span style={{ fontSize: '11px', color: 'var(--secondary)', fontWeight: 600, textTransform: 'uppercase', flexShrink: 0, letterSpacing: '0.05em' }}>
                    Extracted:
                  </span>
                  {Object.entries(sessionDetails.session.current_extracted_entities).map(([key, val]) => (
                    <span key={key} style={{
                      fontSize: '11px', padding: '3px 10px', borderRadius: '6px',
                      background: 'rgba(191, 90, 242, 0.1)', color: 'var(--secondary)',
                      border: '1px solid rgba(191, 90, 242, 0.15)', whiteSpace: 'nowrap'
                    }}>
                      {key}: <strong>{typeof val === 'object' ? JSON.stringify(val) : String(val)}</strong>
                    </span>
                  ))}
                </div>
              )}

            {/* Chat Messages */}
            <div style={{
              flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '12px',
              background: 'rgba(0,0,0,0.15)'
            }}>
              {sessionDetails?.logs && sessionDetails.logs.length > 0 ? (
                sessionDetails.logs.map((log, i) => {
                  const isPatient = log.sender === 'PATIENT';
                  const isDoctorDirect = log.message_text?.startsWith('DIRECT MESSAGE FROM DOCTOR:');
                  return (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        justifyContent: isPatient ? 'flex-end' : 'flex-start',
                        animation: 'fadeInUp 0.3s ease'
                      }}
                    >
                      <div style={{
                        maxWidth: '70%', display: 'flex', flexDirection: 'column', gap: '4px',
                        alignItems: isPatient ? 'flex-end' : 'flex-start'
                      }}>
                        <div style={{
                          display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px',
                          color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.03em'
                        }}>
                          {isPatient ? (
                            <><span>Patient</span><User size={12} /></>
                          ) : isDoctorDirect ? (
                            <><AlertTriangle size={12} style={{ color: 'var(--warning)' }} /><span style={{ color: 'var(--warning)' }}>Doctor Override</span></>
                          ) : (
                            <><Bot size={12} /><span>AI Twin</span></>
                          )}
                        </div>
                        <div style={{
                          padding: '12px 16px',
                          borderRadius: isPatient ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                          fontSize: '14px', lineHeight: '1.55',
                          background: isPatient
                            ? 'var(--primary)'
                            : isDoctorDirect
                              ? 'rgba(255, 159, 10, 0.12)'
                              : 'rgba(255,255,255,0.06)',
                          color: isPatient ? '#FFF' : 'var(--text-primary)',
                          border: isDoctorDirect ? '1px solid rgba(255, 159, 10, 0.25)' : '1px solid transparent',
                          boxShadow: '0 1px 3px rgba(0,0,0,0.15)'
                        }}>
                          {isDoctorDirect
                            ? log.message_text.replace('DIRECT MESSAGE FROM DOCTOR: ', '')
                            : log.message_text}
                        </div>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                          {formatTime(log.created_at)}
                        </span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                  Waiting for patient interaction...
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Doctor Injection Input */}
            <div style={{
              padding: '16px 24px', borderTop: '1px solid var(--border-light)',
              background: 'rgba(0,0,0,0.1)', display: 'flex', gap: '12px', alignItems: 'center'
            }}>
              <div style={{
                width: '8px', height: '8px', borderRadius: '50%',
                background: 'var(--warning)', flexShrink: 0, boxShadow: '0 0 8px rgba(255, 159, 10, 0.4)'
              }} />
              <input
                className="form-input"
                style={{
                  flex: 1, borderRadius: '9999px', padding: '12px 20px', fontSize: '14px',
                  background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255, 159, 10, 0.2)'
                }}
                placeholder="Inject a message directly to the patient (bypasses AI)..."
                value={doctorMessage}
                onChange={e => setDoctorMessage(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendDirectMessage()}
              />
              <button
                className="btn btn-primary"
                onClick={sendDirectMessage}
                disabled={sendingMsg || !doctorMessage.trim()}
                style={{
                  borderRadius: '50%', width: '44px', height: '44px', padding: 0,
                  background: 'linear-gradient(135deg, var(--warning), #FF6F00)',
                  border: 'none', flexShrink: 0
                }}
              >
                {sendingMsg ? (
                  <RefreshCw size={16} className="animate-spin-fast" />
                ) : (
                  <Send size={16} />
                )}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
