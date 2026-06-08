import React, { useState, useEffect, useRef } from 'react';
import { Send, User, Stethoscope, Clock, ShieldCheck, Activity, Calendar, FileText, CheckCircle2 } from 'lucide-react';

const API_BASE = "http://localhost:8000/api/v1";

export default function PreConsultation() {
  // 1. Auth State
  const [patient, setPatient] = useState(() => {
    try {
      const saved = localStorage.getItem('dt_patient');
      return saved ? JSON.parse(saved) : null;
    } catch { return null; }
  });
  
  const [authMode, setAuthMode] = useState('login'); // login | register
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');

  // 2. Session State
  const [sessionId, setSessionId] = useState(null);
  const [status, setStatus] = useState(null); // GATHERING, SYNTHESIZING, PENDING_REVIEW, ALIGNING, BOOKED
  const [turnCount, setTurnCount] = useState(0);
  const [confidence, setConfidence] = useState(0);

  // 3. Chat State
  const [chatLog, setChatLog] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);

  // 4. Doctor Review State
  const [synthesisData, setSynthesisData] = useState(null);
  const [doctorNotes, setDoctorNotes] = useState('');

  // 5. Booking State
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedTime, setSelectedTime] = useState('');
  const [bookingConfirmed, setBookingConfirmed] = useState(false);

  // Hardcoded config/doctor IDs for simulation
  const CONFIG_ID = "11111111-1111-1111-1111-111111111111";
  const DOCTOR_ID = "22222222-2222-2222-2222-222222222222";

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatLog]);

  // Polling loop for status changes
  useEffect(() => {
    if (!sessionId) return;
    
    // Only poll when we expect a state transition from the backend
    if (status === 'SYNTHESIZING' || status === 'SYNTHESIZING_PARTIAL') {
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/pre-consult/session/${sessionId}`);
          if (res.ok) {
            const data = await res.json();
            if (data.session.status !== status) {
              setStatus(data.session.status);
              if (data.summary) {
                setSynthesisData(data.summary);
              }
            }
          }
        } catch (err) {
          console.error("Polling error", err);
        }
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [sessionId, status]);

  const handleAuth = async (e) => {
    e.preventDefault();
    const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register';
    const payload = authMode === 'login' 
      ? { email, password } 
      : { email, password, full_name: fullName };

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Authentication failed");
      
      const newPatient = { id: data.patient_id, name: data.full_name, email: data.email };
      setPatient(newPatient);
      localStorage.setItem('dt_patient', JSON.stringify(newPatient));
    } catch (err) {
      alert(err.message);
    }
  };

  const logout = () => {
    setPatient(null);
    setSessionId(null);
    setStatus(null);
    setChatLog([]);
    localStorage.removeItem('dt_patient');
  };

  const startSession = async () => {
    try {
      const res = await fetch(`${API_BASE}/pre-consult/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ patient_id: patient.id, config_id: CONFIG_ID })
      });
      const data = await res.json();
      setSessionId(data.session_id);
      setStatus(data.status);
      setConfidence(data.current_confidence_score);
      setChatLog([{ sender: 'AI_DOCTOR', text: "Hello! I am Dr. Sterling's AI assistant. To help the doctor prepare, could you briefly describe your symptoms today?" }]);
    } catch (err) {
      console.error(err);
      alert("Failed to start session.");
    }
  };

  const sendMessage = async () => {
    if (!chatInput.trim() || !sessionId) return;
    
    const userMsg = chatInput;
    setChatLog(prev => [...prev, { sender: 'PATIENT', text: userMsg }]);
    setChatInput('');
    setIsTyping(true);

    try {
      const res = await fetch(`${API_BASE}/pre-consult/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: userMsg })
      });
      const data = await res.json();
      
      setIsTyping(false);

      if (data.alert) {
        setChatLog(prev => [...prev, { sender: 'SYSTEM', text: data.alert }]);
        // Fast-forward state to trigger polling
        setStatus('SYNTHESIZING_PARTIAL');
      } else if (data.response) {
        setChatLog(prev => [...prev, { sender: 'AI_DOCTOR', text: data.response }]);
        // Fetch current state to see if we reached threshold
        const stateRes = await fetch(`${API_BASE}/pre-consult/session/${sessionId}`);
        const stateData = await stateRes.json();
        setStatus(stateData.session.status);
        setConfidence(stateData.session.current_confidence_score);
        setTurnCount(stateData.session.turn_count);
      }
    } catch (err) {
      setIsTyping(false);
      console.error(err);
    }
  };

  const submitDoctorReview = async () => {
    try {
      const res = await fetch(`${API_BASE}/pre-consult/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, doctor_review_notes: doctorNotes })
      });
      const data = await res.json();
      setStatus(data.status); // Should move to ALIGNING
    } catch (err) {
      console.error(err);
    }
  };

  const bookAppointment = async () => {
    if (!selectedDate || !selectedTime) return alert("Please select a date and time");
    
    try {
      // Create an ISO string for the backend
      const scheduledTime = new Date(`${selectedDate}T${selectedTime}:00Z`).toISOString();
      const res = await fetch(`${API_BASE}/pre-consult/book?patient_id=${patient.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          session_id: sessionId, 
          doctor_id: DOCTOR_ID, 
          scheduled_time: scheduledTime 
        })
      });
      const data = await res.json();
      setStatus('BOOKED');
      setBookingConfirmed(true);
    } catch (err) {
      console.error(err);
    }
  };

  // ---------------------------------------------------------
  // RENDER HELPERS
  // ---------------------------------------------------------
  
  if (!patient) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
        <div className="glass-card" style={{ width: '400px', padding: '32px' }}>
          <div style={{ textAlign: 'center', marginBottom: '24px' }}>
            <ShieldCheck size={48} style={{ color: 'var(--primary)', margin: '0 auto 16px' }} />
            <h2 style={{ fontSize: '24px', margin: 0, fontFamily: 'var(--font-display)' }}>Patient Portal</h2>
            <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>Secure Pre-Consultation Access</p>
          </div>
          
          <form onSubmit={handleAuth} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {authMode === 'register' && (
              <div className="input-group">
                <label className="input-label">Full Name</label>
                <input required type="text" className="form-input" value={fullName} onChange={e => setFullName(e.target.value)} />
              </div>
            )}
            <div className="input-group">
              <label className="input-label">Email</label>
              <input required type="email" className="form-input" value={email} onChange={e => setEmail(e.target.value)} />
            </div>
            <div className="input-group">
              <label className="input-label">Password</label>
              <input required type="password" className="form-input" value={password} onChange={e => setPassword(e.target.value)} />
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '8px' }}>
              {authMode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
          
          <div style={{ textAlign: 'center', marginTop: '24px', fontSize: '13px' }}>
            <span style={{ color: 'var(--text-muted)' }}>
              {authMode === 'login' ? "Don't have an account? " : "Already have an account? "}
            </span>
            <button 
              style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontWeight: 600 }}
              onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
            >
              {authMode === 'login' ? 'Register here' : 'Sign in'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '0px 20px', maxWidth: '1200px', margin: '0 auto', display: 'flex', gap: '32px', height: 'calc(100vh - 100px)' }}>
      
      {/* LEFT COLUMN: Patient Chat / Booking */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div className="glass-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '18px', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <User size={20} /> {patient.name}
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>ID: {patient.id.substring(0,8)}...</span>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <span className={`badge ${status ? 'badge-primary' : 'badge-warning'}`}>
              {status || 'READY'}
            </span>
            <button className="btn btn-secondary" onClick={logout} style={{ padding: '6px 12px', fontSize: '12px' }}>Log Out</button>
          </div>
        </div>

        {!sessionId ? (
          <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
            <Activity size={64} style={{ color: 'var(--primary)', opacity: 0.5, marginBottom: '24px' }} />
            <h2 style={{ marginBottom: '12px' }}>Begin Pre-Consultation</h2>
            <p style={{ color: 'var(--text-secondary)', textAlign: 'center', maxWidth: '400px', marginBottom: '32px' }}>
              Our AI assistant will ask you a few questions to gather your vitals and symptoms before you meet with Dr. Sterling.
            </p>
            <button className="btn btn-primary" onClick={startSession} style={{ padding: '12px 32px', fontSize: '16px' }}>
              Start AI Intake
            </button>
          </div>
        ) : (
          <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            
            {/* Chat History */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {chatLog.map((msg, idx) => {
                const isPatient = msg.sender === 'PATIENT';
                const isSystem = msg.sender === 'SYSTEM';
                return (
                  <div key={idx} style={{ 
                    display: 'flex', 
                    justifyContent: isSystem ? 'center' : (isPatient ? 'flex-end' : 'flex-start') 
                  }}>
                    <div style={{
                      maxWidth: '80%',
                      padding: isSystem ? '8px 16px' : '12px 16px',
                      borderRadius: isSystem ? '16px' : '20px',
                      borderBottomRightRadius: isPatient ? '4px' : '20px',
                      borderBottomLeftRadius: (!isPatient && !isSystem) ? '4px' : '20px',
                      background: isSystem ? 'rgba(255, 69, 58, 0.1)' : (isPatient ? 'var(--primary)' : 'rgba(255, 255, 255, 0.05)'),
                      color: isSystem ? 'var(--error)' : (isPatient ? '#fff' : 'var(--text-primary)'),
                      fontSize: isSystem ? '12px' : '14px',
                      border: isSystem ? '1px solid rgba(255, 69, 58, 0.3)' : '1px solid rgba(255, 255, 255, 0.1)',
                      fontFamily: isSystem ? 'monospace' : 'inherit'
                    }}>
                      {msg.text}
                    </div>
                  </div>
                );
              })}
              {isTyping && (
                <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                  <div style={{ padding: '12px 16px', borderRadius: '20px', background: 'rgba(255, 255, 255, 0.05)' }}>
                    <span style={{ opacity: 0.5 }}>Dr. Sterling's AI is typing...</span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Chat Input Area (Disabled if not GATHERING) */}
            <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border-light)', background: 'rgba(0,0,0,0.2)' }}>
              {status === 'GATHERING' ? (
                <div style={{ display: 'flex', gap: '12px' }}>
                  <input 
                    className="form-input" 
                    style={{ flex: 1, borderRadius: '24px', padding: '12px 20px' }}
                    placeholder="Type your symptoms..."
                    value={chatInput}
                    onChange={e => setChatInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && sendMessage()}
                  />
                  <button className="btn btn-primary" style={{ borderRadius: '50%', width: '48px', height: '48px', padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={sendMessage}>
                    <Send size={18} />
                  </button>
                </div>
              ) : (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px', padding: '8px 0' }}>
                  {status === 'SYNTHESIZING' || status === 'SYNTHESIZING_PARTIAL' ? 'AI is compiling your file...' : 'Chat session ended.'}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* RIGHT COLUMN: Doctor Review & Booking */}
      {sessionId && (
        <div style={{ width: '400px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Status Tracker */}
          <div className="glass-card" style={{ padding: '24px' }}>
            <h4 style={{ margin: '0 0 16px 0', fontSize: '14px', color: 'var(--text-secondary)' }}>AI Handoff Telemetry</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Confidence Score</span>
                <span style={{ fontWeight: 600, color: confidence > 0.8 ? 'var(--success)' : 'var(--primary)' }}>
                  {(confidence * 100).toFixed(1)}%
                </span>
              </div>
              <div style={{ width: '100%', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px' }}>
                <div style={{ width: `${Math.min(100, confidence * 100)}%`, height: '100%', background: 'var(--primary)', borderRadius: '2px', transition: 'width 0.3s ease' }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Interaction Turns</span>
                <span>{turnCount} / 10</span>
              </div>
            </div>
          </div>

          {/* Doctor Review Dashboard (Simulated View) */}
          <div className="glass-card" style={{ padding: '24px', flex: 1, display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--secondary)' }}>
              <Stethoscope size={20} /> Doctor Review Terminal
            </h3>
            
            {status === 'GATHERING' || status === 'SYNTHESIZING' || status === 'SYNTHESIZING_PARTIAL' ? (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center' }}>
                <FileText size={32} style={{ opacity: 0.3, marginBottom: '12px' }} />
                Waiting for AI Synthesis to complete...<br/>
                (Status: {status})
              </div>
            ) : synthesisData ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '12px', border: '1px solid var(--border-light)' }}>
                  <h5 style={{ margin: '0 0 8px 0', fontSize: '12px', color: 'var(--text-muted)' }}>EXTRACTED CLINICAL DATA</h5>
                  <pre style={{ margin: 0, fontSize: '11px', color: 'var(--success)', whiteSpace: 'pre-wrap' }}>
                    {JSON.stringify(synthesisData.structured_clinical_data, null, 2)}
                  </pre>
                </div>
                
                {status === 'PENDING_REVIEW' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <h5 style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)' }}>PHYSICIAN OVERRIDE / NOTES</h5>
                    <textarea 
                      className="form-input" 
                      style={{ minHeight: '80px', fontSize: '13px' }} 
                      placeholder="Enter clinical alignment notes here..."
                      value={doctorNotes}
                      onChange={e => setDoctorNotes(e.target.value)}
                    />
                    <button className="btn btn-secondary" onClick={submitDoctorReview} style={{ borderColor: 'var(--secondary)', color: 'var(--secondary)' }}>
                      Align & Release for Booking
                    </button>
                  </div>
                )}
                
                {status === 'ALIGNING' || status === 'BOOKED' ? (
                  <div style={{ padding: '12px', borderRadius: '8px', background: 'rgba(50, 215, 75, 0.1)', color: 'var(--success)', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <CheckCircle2 size={16} /> Doctor Review Complete
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          {/* Booking Interface (Unlocks at ALIGNING) */}
          {(status === 'ALIGNING' || status === 'BOOKED') && (
            <div className="glass-card" style={{ padding: '24px' }}>
              <h3 style={{ margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)' }}>
                <Calendar size={20} /> Schedule Appointment
              </h3>
              
              {status === 'BOOKED' ? (
                <div style={{ textAlign: 'center', padding: '16px 0' }}>
                  <CheckCircle2 size={48} style={{ color: 'var(--success)', margin: '0 auto 12px' }} />
                  <h4 style={{ margin: '0 0 8px 0' }}>Booking Confirmed</h4>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '13px', margin: 0 }}>
                    Your appointment is set for {selectedDate} at {selectedTime}.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ display: 'flex', gap: '12px' }}>
                    <div className="input-group" style={{ flex: 1 }}>
                      <label className="input-label">Date</label>
                      <input type="date" className="form-input" value={selectedDate} onChange={e => setSelectedDate(e.target.value)} />
                    </div>
                    <div className="input-group" style={{ flex: 1 }}>
                      <label className="input-label">Time</label>
                      <input type="time" className="form-input" value={selectedTime} onChange={e => setSelectedTime(e.target.value)} />
                    </div>
                  </div>
                  <button className="btn btn-primary" onClick={bookAppointment}>
                    Confirm Booking
                  </button>
                </div>
              )}
            </div>
          )}
          
        </div>
      )}
    </div>
  );
}
