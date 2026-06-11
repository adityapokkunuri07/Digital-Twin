import React, { useState, useEffect, useRef } from 'react';
import { Send, User, Stethoscope, Clock, ShieldCheck, Activity, Calendar, FileText, CheckCircle2, Eye, EyeOff } from 'lucide-react';

const API_BASE = "http://127.0.0.1:8000/api";

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
  const [showPassword, setShowPassword] = useState(false);
  const [fullName, setFullName] = useState('');


  const [activeTab, setActiveTab] = useState('consultation');
  const [appointments, setAppointments] = useState([]);
  const [loadingAppointments, setLoadingAppointments] = useState(false);

  const fetchPatientAppointments = async () => {
    if (!patient?.id) return;
    setLoadingAppointments(true);
    try {
      const res = await fetch(`${API_BASE}/pre-consult/appointments/patient/${patient.id}`);
      const data = await res.json();
      setAppointments(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAppointments(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'appointments') {
      fetchPatientAppointments();
    }
  }, [activeTab, patient]);

  // 2. Session State
  const [sessionId, setSessionId] = useState(() => {
    return localStorage.getItem('dt_session_id') || null;
  });
  const [status, setStatus] = useState(null); // GATHERING, SYNTHESIZING, PENDING_REVIEW, ALIGNING, BOOKED
  const [turnCount, setTurnCount] = useState(0);
  const [confidence, setConfidence] = useState(0);

  // 3. Chat State
  const [chatLog, setChatLog] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);
  const isSendingRef = useRef(false);

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
    
    // Poll for status transitions and injected messages from doctor
    if (status === 'SYNTHESIZING' || status === 'SYNTHESIZING_PARTIAL' || status === 'PENDING_REVIEW' || status === 'ALIGNING') {
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/pre-consult/session/${sessionId}`);
          if (res.ok) {
            const data = await res.json();
            
            if (data.logs) {
              setChatLog(prev => {
                if (data.logs.length > prev.length) {
                  return data.logs.map(log => ({
                    sender: log.sender,
                    text: log.message_text
                  }));
                }
                return prev;
              });
            }

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

  // Hydrate session on load
  useEffect(() => {
    if (sessionId && chatLog.length === 0) {
      fetch(`${API_BASE}/pre-consult/session/${sessionId}`)
        .then(res => res.json())
        .then(data => {
          setStatus(data.session.status);
          setConfidence(data.session.current_confidence_score);
          setTurnCount(data.session.turn_count);
          if (data.logs && data.logs.length > 0) {
            const formattedLogs = data.logs.map(log => ({
              sender: log.sender,
              text: log.message_text
            }));
            setChatLog(formattedLogs);
          } else {
            // Fallback initial greeting if logs are empty somehow
            setChatLog([{ sender: 'AI_DOCTOR', text: "Hello! I am Dr. Sterling's AI assistant. To help the doctor prepare, could you briefly describe your symptoms today?" }]);
          }
          if (data.summary) {
            setSynthesisData(data.summary);
          }
        })
        .catch(err => {
          console.error("Failed to restore session", err);
        });
    }
  }, [sessionId]);

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
    localStorage.removeItem('dt_session_id');
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
      localStorage.setItem('dt_session_id', data.session_id);
      setStatus(data.status);
      setConfidence(data.current_confidence_score);
      setChatLog([{ sender: 'AI_DOCTOR', text: "Hello! I am Dr. Sterling's AI assistant. To help the doctor prepare, could you briefly describe your symptoms today?" }]);
    } catch (err) {
      console.error(err);
      alert("Failed to start session.");
    }
  };

  const sendMessage = async () => {
    if (!chatInput.trim() || !sessionId || isSendingRef.current) return;
    
    isSendingRef.current = true;
    const userMsg = chatInput;
    setChatInput('');
    setIsTyping(true);
    // Use functional state update to prevent any race conditions
    setChatLog(prev => [...prev, { sender: 'PATIENT', text: userMsg }]);

    try {
      const res = await fetch(`${API_BASE}/pre-consult/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: userMsg })
      });
      const data = await res.json();
      
      setIsTyping(false);
      isSendingRef.current = false;

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
      isSendingRef.current = false;
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
          patient_id: patient.id,
          doctor_id: DOCTOR_ID, 
          scheduled_time: scheduledTime 
        })
      });
      
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to book appointment");
      }
      
      setStatus('BOOKED');
      setBookingConfirmed(true);
    } catch (err) {
      console.error(err);
      alert(`Booking error: ${err.message}`);
    }
  };

  // ---------------------------------------------------------
  // RENDER HELPERS
  // ---------------------------------------------------------
  
  if (!patient) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: 'radial-gradient(circle at center, #1C1C1E 0%, #000 100%)' }}>
        <div className="glass-card" style={{ width: '420px', padding: '40px', borderRadius: '32px', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)' }}>
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <div className="animate-pulse-slow">
              <ShieldCheck size={56} style={{ color: 'var(--primary)', margin: '0 auto 16px' }} />
            </div>
            <h2 style={{ fontSize: '28px', margin: 0, fontFamily: 'var(--font-display)', fontWeight: 700, letterSpacing: '-0.5px' }}>Apple ID</h2>
            <p style={{ color: 'var(--text-secondary)', marginTop: '8px', fontSize: '15px' }}>Sign in to Pre-Consultation Portal</p>
          </div>
          
          <form onSubmit={handleAuth} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {authMode === 'register' && (
              <div className="input-group">
                <label className="input-label">Full Name</label>
                <input required type="text" className="form-input" style={{ borderRadius: '12px' }} value={fullName} onChange={e => setFullName(e.target.value)} />
              </div>
            )}
            <div className="input-group">
              <label className="input-label">Email</label>
              <input required type="email" className="form-input" style={{ borderRadius: '12px' }} value={email} onChange={e => setEmail(e.target.value)} />
            </div>
            <div className="input-group">
              <label className="input-label">Password</label>
              <div style={{ position: 'relative' }}>
                <input required type={showPassword ? "text" : "password"} className="form-input" style={{ borderRadius: '12px', paddingRight: '40px' }} value={password} onChange={e => setPassword(e.target.value)} />
                <button 
                  type="button" 
                  onClick={() => setShowPassword(!showPassword)}
                  style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 0, display: 'flex', alignItems: 'center' }}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '16px', padding: '12px', fontSize: '15px', borderRadius: '12px', fontWeight: 600 }}>
              {authMode === 'login' ? 'Continue' : 'Create Apple ID'}
            </button>
          </form>
          
          <div style={{ textAlign: 'center', marginTop: '24px', fontSize: '14px' }}>
            <span style={{ color: 'var(--text-muted)' }}>
              {authMode === 'login' ? "Don't have an Apple ID? " : "Already have an Apple ID? "}
            </span>
            <button 
              style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontWeight: 500, transition: 'opacity 0.2s' }}
              onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
              onMouseOver={(e) => e.target.style.opacity = '0.8'}
              onMouseOut={(e) => e.target.style.opacity = '1'}
            >
              {authMode === 'login' ? 'Create yours now.' : 'Sign in.'}
            </button>
          </div>
        </div>
      </div>
    );
  }


  return (
    <div className="app-container">
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ background: 'var(--primary)', color: 'white', padding: '8px', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Activity size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '18px', margin: 0, fontWeight: 700, fontFamily: 'var(--font-display)' }}>
              Patient Portal
            </h2>
          </div>
        </div>

        <nav className="sidebar-nav" style={{ flex: 1, padding: '0 16px' }}>
          <button
            className={`nav-link w-full ${activeTab === 'consultation' ? 'active' : ''}`}
            onClick={() => setActiveTab('consultation')}
          >
            <ShieldCheck size={18} style={{ color: activeTab === 'consultation' ? 'inherit' : 'var(--primary)' }} />
            <span>Consultation</span>
          </button>

          <button
            className={`nav-link w-full ${activeTab === 'appointments' ? 'active' : ''}`}
            onClick={() => setActiveTab('appointments')}
          >
            <Calendar size={18} style={{ color: activeTab === 'appointments' ? 'inherit' : 'var(--primary)' }} />
            <span>My Appointments</span>
          </button>

          <button
            className="nav-link w-full"
            onClick={logout}
            style={{ marginTop: '24px', color: 'var(--error)' }}
          >
            <User size={18} style={{ color: 'var(--error)' }} />
            <span>Log Out</span>
          </button>
        </nav>

        <div style={{ padding: '24px', fontSize: '13px', color: 'var(--text-muted)' }}>
          <div>Logged in as:</div>
          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{patient.name}</div>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="main-content">
        {activeTab === 'appointments' ? (
          <div>
            <h1 style={{ fontSize: '32px', fontFamily: 'var(--font-display)', marginBottom: '32px' }}>
              My Appointments
            </h1>
            {loadingAppointments ? (
              <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>Loading...</div>
            ) : appointments.length === 0 ? (
              <div className="glass-card" style={{ padding: '40px', textAlign: 'center', borderRadius: '24px' }}>
                <Calendar size={48} style={{ margin: '0 auto 16px', color: 'var(--text-muted)' }} />
                <h3 style={{ margin: '0 0 8px 0' }}>No Appointments</h3>
                <p style={{ margin: 0, color: 'var(--text-secondary)' }}>You have no booked appointments.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {appointments.map(appt => {
                  const date = new Date(appt.scheduled_time);
                  return (
                    <div key={appt.appointment_id} className="glass-card" style={{ padding: '24px', borderRadius: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                        <div style={{ background: 'rgba(50, 215, 75, 0.1)', padding: '16px', borderRadius: '16px', color: 'var(--success)' }}>
                          <Calendar size={28} />
                        </div>
                        <div>
                          <h3 style={{ margin: '0 0 4px 0', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            Dr. Sterling
                            <span style={{ fontSize: '12px', background: 'rgba(50, 215, 75, 0.15)', color: 'var(--success)', padding: '4px 8px', borderRadius: '12px', fontWeight: 600 }}>
                              CONFIRMED
                            </span>
                          </h3>
                          <div style={{ display: 'flex', gap: '16px', color: 'var(--text-secondary)', fontSize: '14px' }}>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <Clock size={14} />
                              {date.toLocaleDateString()} at {date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', gap: '32px', height: '100%' }}>
      
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
          </div>
        </div>

        {!sessionId ? (
          <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', borderRadius: '32px' }}>
            <div className="animate-pulse-ring" style={{ width: 80, height: 80, borderRadius: '50%', background: 'rgba(10, 132, 255, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '32px' }}>
              <Activity size={40} style={{ color: 'var(--primary)' }} />
            </div>
            <h2 style={{ marginBottom: '12px', fontSize: '24px', fontWeight: 600 }}>Begin Pre-Consultation</h2>
            <p style={{ color: 'var(--text-secondary)', textAlign: 'center', maxWidth: '380px', marginBottom: '40px', lineHeight: 1.6 }}>
              Our clinical AI will securely gather your vitals and symptoms to prepare for your appointment with Dr. Sterling.
            </p>
            <button className="btn btn-primary" onClick={startSession} style={{ padding: '14px 40px', fontSize: '16px', borderRadius: '24px', fontWeight: 600 }}>
              Start AI Intake
            </button>
          </div>
        ) : (
          <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', borderRadius: '32px', padding: 0 }}>
            
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
                      background: isSystem ? 'rgba(255, 69, 58, 0.1)' : (isPatient ? 'linear-gradient(180deg, #0A84FF 0%, #0060C0 100%)' : 'rgba(255, 255, 255, 0.08)'),
                      color: isSystem ? 'var(--error)' : (isPatient ? '#fff' : 'var(--text-primary)'),
                      fontSize: isSystem ? '12px' : '15px',
                      border: isSystem ? '1px solid rgba(255, 69, 58, 0.3)' : 'none',
                      fontFamily: isSystem ? 'monospace' : 'inherit',
                      boxShadow: isPatient ? '0 4px 10px rgba(0, 100, 255, 0.3), inset 0 1px 0 rgba(255,255,255,0.2)' : '0 1px 2px rgba(0,0,0,0.2)'
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
            <div style={{ padding: '16px 24px', borderTop: '1px solid rgba(255,255,255,0.05)', background: 'rgba(28, 28, 30, 0.6)', backdropFilter: 'blur(20px)' }}>
              {status === 'GATHERING' ? (
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                  <input 
                    className="form-input" 
                    style={{ flex: 1, borderRadius: '24px', padding: '14px 24px', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.1)', fontSize: '15px' }}
                    placeholder="iMessage..."
                    value={chatInput}
                    onChange={e => setChatInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && sendMessage()}
                  />
                  <button className="btn btn-primary" style={{ borderRadius: '50%', width: '40px', height: '40px', padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(180deg, var(--primary) 0%, #0060C0 100%)', boxShadow: '0 2px 8px rgba(0,100,255,0.4)' }} onClick={sendMessage}>
                    <Send size={16} style={{ marginLeft: '-2px' }} />
                  </button>
                </div>
              ) : (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px', padding: '16px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                  {status === 'SYNTHESIZING' || status === 'SYNTHESIZING_PARTIAL' ? (
                    <>
                      <div className="animate-spin-fast"><Activity size={24} style={{ color: 'var(--primary)' }} /></div>
                      AI is compiling your file...
                    </>
                  ) : status === 'PENDING_REVIEW' ? (
                    <>
                      <ShieldCheck size={28} style={{ color: 'var(--success)' }} />
                      <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>File Sent to Doctor</div>
                      <div style={{ maxWidth: '300px' }}>Your file is currently under review by Dr. Sterling. The booking portal will unlock once the review is complete.</div>
                    </>
                  ) : 'Chat session ended.'}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* RIGHT COLUMN: Doctor Review & Booking */}
      {sessionId && (
        <div style={{ width: '400px', display: 'flex', flexDirection: 'column', gap: '24px' }}>

          {/* Booking Interface (Unlocks at ALIGNING) */}
          {(status === 'ALIGNING' || status === 'BOOKED') && (
            <div className="glass-card" style={{ padding: '24px', borderRadius: '32px' }}>
              <h3 style={{ margin: '0 0 20px 0', display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-primary)', fontSize: '20px', fontWeight: 600 }}>
                <Calendar size={24} style={{ color: 'var(--primary)' }} /> Schedule
              </h3>
              
              {status === 'BOOKED' ? (
                <div style={{ textAlign: 'center', padding: '16px 0', animation: 'scaleUp 0.5s ease' }}>
                  <CheckCircle2 size={56} style={{ color: 'var(--success)', margin: '0 auto 16px', filter: 'drop-shadow(0 4px 12px rgba(50, 215, 75, 0.4))' }} />
                  <h4 style={{ margin: '0 0 8px 0', fontSize: '20px' }}>Booking Confirmed</h4>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '15px', margin: 0 }}>
                    Your appointment is set for {selectedDate} at {selectedTime}.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <div style={{ display: 'flex', gap: '16px' }}>
                    <div className="input-group" style={{ flex: 1, margin: 0 }}>
                      <label className="input-label" style={{ paddingLeft: '4px' }}>Date</label>
                      <input type="date" className="form-input" style={{ borderRadius: '16px' }} value={selectedDate} onChange={e => setSelectedDate(e.target.value)} />
                    </div>
                    <div className="input-group" style={{ flex: 1, margin: 0 }}>
                      <label className="input-label" style={{ paddingLeft: '4px' }}>Time</label>
                      <input type="time" className="form-input" style={{ borderRadius: '16px' }} value={selectedTime} onChange={e => setSelectedTime(e.target.value)} />
                    </div>
                  </div>
                  <button className="btn btn-primary" style={{ padding: '14px', borderRadius: '16px', fontWeight: 600, fontSize: '15px' }} onClick={bookAppointment}>
                    Confirm Booking
                  </button>
                </div>
              )}
            </div>
          )}
          
        </div>
      )}
          </div>
        )}
      </main>
    </div>
  );
}
