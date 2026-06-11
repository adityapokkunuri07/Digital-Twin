import React, { useState, useEffect } from 'react';
import { Calendar, User, Clock, CheckCircle2, ChevronRight, AlertCircle, X, FileText, Activity, MessageSquare } from 'lucide-react';

const API_BASE = "http://127.0.0.1:8000/api";

export default function DoctorAppointments() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAppt, setSelectedAppt] = useState(null);
  const [sessionDetails, setSessionDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  const fetchAppointments = async () => {
    try {
      const res = await fetch(`${API_BASE}/pre-consult/appointments/all`);
      const data = await res.json();
      setAppointments(data);
    } catch (err) {
      console.error("Failed to fetch appointments", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
    const interval = setInterval(fetchAppointments, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleViewDetails = async (appt) => {
    setSelectedAppt(appt);
    setLoadingDetails(true);
    setSessionDetails(null);
    try {
      const res = await fetch(`${API_BASE}/pre-consult/session/${appt.session_id}`);
      const data = await res.json();
      setSessionDetails(data);
    } catch (err) {
      console.error("Failed to fetch session details", err);
    } finally {
      setLoadingDetails(false);
    }
  };

  return (
    <div style={{ padding: '40px', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ marginBottom: '32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '32px', margin: '0 0 8px 0', fontFamily: 'var(--font-display)', fontWeight: 700, letterSpacing: '-0.5px' }}>
            Master Schedule
          </h1>
          <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '15px' }}>
            All booked appointments across the clinic.
          </p>
        </div>
      </header>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
          <div className="animate-pulse-slow">
            <Calendar size={48} style={{ margin: '0 auto 16px' }} />
          </div>
          Loading schedule...
        </div>
      ) : appointments.length === 0 ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '60px', borderRadius: '24px' }}>
          <AlertCircle size={48} style={{ color: 'var(--text-muted)', margin: '0 auto 16px' }} />
          <h3 style={{ margin: '0 0 8px 0', fontSize: '20px' }}>No Appointments</h3>
          <p style={{ color: 'var(--text-secondary)', margin: 0 }}>No patients have scheduled an appointment yet.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {appointments.map((appt) => {
            const date = new Date(appt.scheduled_time);
            return (
              <div key={appt.appointment_id} className="glass-card list-item" style={{ padding: '24px', borderRadius: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                  <div style={{ background: 'rgba(50, 215, 75, 0.1)', padding: '16px', borderRadius: '16px', color: 'var(--success)' }}>
                    <Calendar size={28} />
                  </div>
                  <div>
                    <h3 style={{ margin: '0 0 4px 0', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {appt.patients?.full_name || 'Unknown Patient'}
                      {appt.status === 'BOOKED' || appt.status === 'SCHEDULED' ? (
                        <span style={{ fontSize: '12px', background: 'rgba(50, 215, 75, 0.15)', color: 'var(--success)', padding: '4px 8px', borderRadius: '12px', fontWeight: 600 }}>
                          CONFIRMED
                        </span>
                      ) : null}
                    </h3>
                    <div style={{ display: 'flex', gap: '16px', color: 'var(--text-secondary)', fontSize: '14px' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={14} />
                        {date.toLocaleDateString()} at {date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <User size={14} />
                        {appt.patients?.email || 'No email'}
                      </span>
                    </div>
                  </div>
                </div>
                
                <button 
                  className="btn btn-secondary" 
                  onClick={() => handleViewDetails(appt)}
                  style={{ padding: '12px 24px', borderRadius: '100px', display: 'flex', alignItems: 'center', gap: '8px' }}
                >
                  View Details <ChevronRight size={16} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* VIEW DETAILS MODAL */}
      {selectedAppt && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          padding: '24px'
        }}>
          <div className="glass-card" style={{
            width: '100%', maxWidth: '800px', maxHeight: '90vh',
            display: 'flex', flexDirection: 'column',
            padding: 0, overflow: 'hidden', borderRadius: '24px'
          }}>
            {/* Modal Header */}
            <div style={{
              padding: '24px', borderBottom: '1px solid rgba(255,255,255,0.1)',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center'
            }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '24px' }}>Appointment Details</h2>
                <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                  {selectedAppt.patients?.full_name || 'Unknown Patient'} • {new Date(selectedAppt.scheduled_time).toLocaleString()}
                </p>
              </div>
              <button onClick={() => setSelectedAppt(null)} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '8px' }}>
                <X size={24} />
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {loadingDetails ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  <div className="animate-pulse-slow">
                    <Activity size={32} style={{ margin: '0 auto 16px' }} />
                  </div>
                  Loading clinical context...
                </div>
              ) : sessionDetails ? (
                <>
                  <section>
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '18px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', marginBottom: '16px' }}>
                      <Activity size={20} style={{ color: 'var(--primary)' }} /> Clinical Summary
                    </h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                      <div className="glass-card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
                        <h4 style={{ margin: '0 0 12px 0', color: 'var(--text-secondary)' }}>Symptom Entities</h4>
                        {sessionDetails.summary?.structured_clinical_data ? (
                          <ul style={{ margin: 0, paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {Object.entries(sessionDetails.summary.structured_clinical_data).map(([k, v]) => (
                              <li key={k}><strong style={{ color: 'var(--text-primary)' }}>{k}:</strong> {v}</li>
                            ))}
                          </ul>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>No structured data available.</span>
                        )}
                      </div>
                      <div className="glass-card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
                        <h4 style={{ margin: '0 0 12px 0', color: 'var(--text-secondary)' }}>Session Meta</h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <div><strong>Status:</strong> <span style={{ color: 'var(--success)' }}>{sessionDetails.session.status}</span></div>
                          <div><strong>Confidence:</strong> {(sessionDetails.session.current_confidence_score * 100).toFixed(0)}%</div>
                          <div><strong>Turns:</strong> {sessionDetails.session.turn_count}</div>
                        </div>
                      </div>
                    </div>
                  </section>

                  {sessionDetails.summary?.doctor_review_notes && (
                    <section>
                      <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '18px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', marginBottom: '16px' }}>
                        <FileText size={20} style={{ color: 'var(--primary)' }} /> Doctor Review Notes
                      </h3>
                      <div className="glass-card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
                        <p style={{ margin: 0, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                          {sessionDetails.summary.doctor_review_notes}
                        </p>
                      </div>
                    </section>
                  )}

                  <section>
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '18px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', marginBottom: '16px' }}>
                      <MessageSquare size={20} style={{ color: 'var(--primary)' }} /> AI Intake Transcript
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {sessionDetails.logs?.map((log) => (
                        <div key={log.log_id} style={{
                          padding: '12px 16px', borderRadius: '16px',
                          background: log.sender === 'PATIENT' ? 'rgba(10, 132, 255, 0.15)' : 'rgba(255,255,255,0.05)',
                          alignSelf: log.sender === 'PATIENT' ? 'flex-end' : 'flex-start',
                          maxWidth: '85%'
                        }}>
                          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            {log.sender.replace('_', ' ')}
                          </div>
                          <div style={{ lineHeight: 1.5 }}>{log.message_text}</div>
                        </div>
                      ))}
                    </div>
                  </section>
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--error)' }}>
                  Failed to load session details.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
