import { useState, useEffect } from 'react'

const API_BASE = 'http://127.0.0.1:8000'

export default function KnowledgeProofsViewer() {
  const [data, setData] = useState({ rules: [], blueprints: [] })
  const [loading, setLoading] = useState(true)

  const fetchProofs = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/workflows/knowledge-proofs`)
      const json = await res.json()
      setData({ rules: json.rules || [], blueprints: json.blueprints || [] })
    } catch (err) {
      console.error("Failed to fetch proofs", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProofs()
    const interval = setInterval(fetchProofs, 3000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return <p style={{ color: '#94A3B8', fontSize: 13 }}>Loading Knowledge Engine Proofs...</p>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
      
      {data.rules.length === 0 ? (
         <div style={{ padding: 16, background: '#0F172A', borderRadius: 8, fontSize: 13, color: '#94A3B8', border: '1px solid #1E293B' }}>No rules found. Try ingesting a transcript first.</div>
      ) : data.rules.map((rule, idx) => (
        <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            {/* PHASE 1: Task Context */}
            <div style={{ flex: 1, background: '#0F172A', border: '1px solid #1E293B', borderRadius: '12px', padding: '20px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <span style={{ fontSize: '18px' }}>⚡</span>
                    <h4 style={{ color: '#38BDF8', margin: 0, fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 800 }}>Task Triggered</h4>
                </div>
                <p style={{ margin: 0, fontWeight: 700, fontSize: '16px', color: '#F8FAFC' }}>{rule.task_boundary}</p>
                <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#94A3B8' }}>Execution Step: {rule.execution_order}</p>
            </div>

            <div style={{ color: '#334155', fontSize: '28px', fontWeight: 300 }}>→</div>

            {/* PHASE 2: Knowledge Source */}
            <div style={{ flex: 1.5, background: '#1E1B4B', border: '1px solid #312E81', borderRadius: '12px', padding: '20px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <span style={{ fontSize: '18px' }}>🧠</span>
                    <h4 style={{ color: '#FBBF24', margin: 0, fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 800 }}>Expert Knowledge Retrieved</h4>
                </div>
                
                {/* Source Label */}
                <div style={{ background: '#3730A3', padding: '6px 12px', borderRadius: '6px', display: 'inline-block', marginBottom: '12px' }}>
                    <span style={{ fontSize: '11px', color: '#E0E7FF', fontWeight: 600 }}>📄 Source: Expert Knowledge Base (DNA)</span>
                </div>
                
                <p style={{ margin: 0, fontWeight: 600, fontSize: '15px', color: '#F8FAFC', lineHeight: '1.5' }}>"{rule.rule_text}"</p>
            </div>

            <div style={{ color: '#334155', fontSize: '28px', fontWeight: 300 }}>→</div>

            {/* PHASE 3: AI Execution */}
            <div style={{ flex: 1, background: '#064E3B', border: '1px solid #065F46', borderRadius: '12px', padding: '20px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <span style={{ fontSize: '18px' }}>⚙️</span>
                    <h4 style={{ color: '#34D399', margin: 0, fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 800 }}>Skill Selected</h4>
                </div>
                <div style={{ background: '#022C22', padding: '8px 12px', borderRadius: '8px', border: '1px dashed #059669', marginTop: '12px' }}>
                    <p style={{ margin: 0, fontWeight: 700, fontFamily: 'monospace', fontSize: '12px', color: '#6EE7B7', wordBreak: 'break-all' }}>
                        {rule.required_action}
                    </p>
                </div>
            </div>
        </div>
      ))}
      
      {/* Raw Blueprint Fallback for Debugging */}
      <div style={{ marginTop: '32px', borderTop: '2px solid #334155', paddingTop: '24px' }}>
          <details>
              <summary style={{ fontSize: '13px', color: '#94A3B8', cursor: 'pointer', fontWeight: 600 }}>View Raw Assembled Blueprint Payload</summary>
              {data.blueprints.map((bp, idx) => (
                  <pre key={idx} style={{ background: '#0F172A', color: '#818CF8', padding: '16px', borderRadius: '8px', fontSize: '12px', marginTop: '12px', overflow: 'auto', border: '1px solid #1E293B' }}>
                      {JSON.stringify(bp.payload_template, null, 2)}
                  </pre>
              ))}
          </details>
      </div>
      
    </div>
  )
}
