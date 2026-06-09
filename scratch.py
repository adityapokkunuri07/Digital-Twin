import re

with open("frontend/src/PreConsultation.jsx", "r", encoding="utf-8") as f:
    content = f.read()

# Add activeTab and appointments state
state_injection = """
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
"""
content = content.replace("  // 2. Session State", state_injection + "\n  // 2. Session State")

# Replace return logic
main_render_start = content.find("  return (\n    <div style={{ padding: '0px 20px', maxWidth: '1200px', margin: '0 auto', display: 'flex', gap: '32px', height: 'calc(100vh - 100px)' }}>")

new_render = """
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
"""

old_render_end = content[main_render_start:].replace(
    "  return (\n    <div style={{ padding: '0px 20px', maxWidth: '1200px', margin: '0 auto', display: 'flex', gap: '32px', height: 'calc(100vh - 100px)' }}>",
    "          <div style={{ display: 'flex', gap: '32px', height: '100%' }}>"
)
old_render_end = old_render_end.replace(
    "            <button className=\"btn btn-secondary\" onClick={logout} style={{ padding: '6px 12px', fontSize: '12px' }}>Log Out</button>\n          </div>",
    "          </div>"
)

content = content[:main_render_start] + new_render + old_render_end
content = content.replace("    </div>\n  );\n}", "          </div>\n        )}\n      </main>\n    </div>\n  );\n}")

with open("frontend/src/PreConsultation.jsx", "w", encoding="utf-8") as f:
    f.write(content)
