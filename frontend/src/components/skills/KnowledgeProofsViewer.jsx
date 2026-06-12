import { useState, useEffect, useCallback } from 'react'

const API_BASE = 'http://127.0.0.1:8000'

const STEP_META = {
  data_extraction:   { emoji: '📥', color: '#38BDF8', bg: 'rgba(56,189,248,0.08)',  label: 'Data Extraction'   },
  rag_retrieval:     { emoji: '🧠', color: '#FBBF24', bg: 'rgba(251,191,36,0.08)',   label: 'RAG Retrieval'     },
  safety_check:      { emoji: '🛡️', color: '#F87171', bg: 'rgba(248,113,113,0.08)', label: 'Safety Check'      },
  action_dispatch:   { emoji: '⚙️', color: '#34D399', bg: 'rgba(52,211,153,0.08)',  label: 'Action Dispatch'   },
  human_intercept:   { emoji: '🚨', color: '#FB923C', bg: 'rgba(251,146,60,0.08)',  label: 'Human Intercept'   },
  initialization:    { emoji: '🚀', color: '#A78BFA', bg: 'rgba(167,139,250,0.08)', label: 'Initialization'    },
  awaiting_confirmation: { emoji: '⏳', color: '#94A3B8', bg: 'rgba(148,163,184,0.08)', label: 'Awaiting Confirmation' },
}

const getStepMeta = (step) => STEP_META[step] || { emoji: '📌', color: '#94A3B8', bg: 'rgba(148,163,184,0.08)', label: step }

function ChunkCard({ chunk, index }) {
  const [expanded, setExpanded] = useState(false)
  const preview = (chunk.content || '').slice(0, 160)
  return (
    <div style={{
      background: 'rgba(30,27,75,0.6)',
      border: '1px solid #312E81',
      borderRadius: 10,
      padding: '12px 14px',
      marginTop: index === 0 ? 0 : 8,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 16 }}>📄</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#E0E7FF' }}>
            {chunk.title || chunk.parent_path || `Chunk ${index + 1}`}
          </span>
        </div>
        <button
          onClick={() => setExpanded(e => !e)}
          style={{
            background: 'rgba(99,102,241,0.15)',
            border: '1px solid #4F46E5',
            borderRadius: 6,
            padding: '2px 10px',
            color: '#A5B4FC',
            fontSize: 11,
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >{expanded ? 'Hide' : 'View'}</button>
      </div>

      {chunk.tags?.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
          {chunk.tags.map(t => (
            <span key={t} style={{
              fontSize: 10, background: '#1E1B4B', border: '1px solid #3730A3',
              borderRadius: 4, padding: '1px 6px', color: '#A5B4FC'
            }}>#{t}</span>
          ))}
        </div>
      )}

      <p style={{ margin: '8px 0 0', fontSize: 12, color: '#94A3B8', lineHeight: 1.6 }}>
        {expanded ? chunk.content : `${preview}${chunk.content?.length > 160 ? '...' : ''}`}
      </p>
    </div>
  )
}

function TraceCard({ trace, index }) {
  const meta = getStepMeta(trace.step_name)
  const [open, setOpen] = useState(index === 0)
  const hasChunks = trace.retrieved_chunks?.length > 0
  const score = ((trace.classification_score || 0) * 100).toFixed(0)
  const time = trace.created_at ? new Date(trace.created_at).toLocaleTimeString() : ''

  return (
    <div style={{
      background: meta.bg,
      border: `1px solid ${meta.color}33`,
      borderRadius: 14,
      overflow: 'hidden',
      transition: 'box-shadow 0.2s',
    }}>
      {/* Header row */}
      <div
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 14,
          padding: '14px 18px', cursor: 'pointer',
          borderBottom: open ? `1px solid ${meta.color}22` : 'none',
        }}
      >
        {/* Step badge */}
        <div style={{
          background: `${meta.color}20`, border: `1px solid ${meta.color}55`,
          borderRadius: 8, padding: '6px 10px', fontSize: 20, flexShrink: 0,
        }}>{meta.emoji}</div>

        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 800, color: meta.color, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              Step {index + 1} — {meta.label}
            </span>
            {time && <span style={{ fontSize: 11, color: '#475569' }}>{time}</span>}
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
            {/* Confidence badge */}
            <span style={{
              fontSize: 11, background: 'rgba(52,211,153,0.1)', border: '1px solid #34D39944',
              borderRadius: 5, padding: '1px 7px', color: '#34D399', fontWeight: 600,
            }}>confidence {score}%</span>
            {/* Chunk count */}
            {hasChunks && (
              <span style={{
                fontSize: 11, background: 'rgba(251,191,36,0.1)', border: '1px solid #FBBF2444',
                borderRadius: 5, padding: '1px 7px', color: '#FBBF24', fontWeight: 600,
              }}>🧠 {trace.retrieved_chunks.length} knowledge source{trace.retrieved_chunks.length !== 1 ? 's' : ''}</span>
            )}
            {!hasChunks && (
              <span style={{
                fontSize: 11, background: 'rgba(100,116,139,0.1)', border: '1px solid #47556944',
                borderRadius: 5, padding: '1px 7px', color: '#64748B', fontWeight: 600,
              }}>no RAG retrieval</span>
            )}
          </div>
        </div>

        <span style={{ color: '#475569', fontSize: 18, flexShrink: 0 }}>{open ? '▲' : '▼'}</span>
      </div>

      {/* Expanded body */}
      {open && (
        <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Knowledge Sources */}
          {hasChunks && (
            <div>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10,
                fontSize: 12, fontWeight: 700, color: '#FBBF24', textTransform: 'uppercase', letterSpacing: 0.5,
              }}>
                <span>🧠</span> Expert Knowledge Retrieved
              </div>
              {trace.retrieved_chunks.map((chunk, ci) => (
                <ChunkCard key={chunk.chunk_id || ci} chunk={chunk} index={ci} />
              ))}
            </div>
          )}

          {/* Arrow connector */}
          {hasChunks && (
            <div style={{ textAlign: 'center', fontSize: 22, color: '#334155', lineHeight: 1 }}>↓</div>
          )}

          {/* AI Response Generated */}
          <div>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8,
              fontSize: 12, fontWeight: 700, color: meta.color, textTransform: 'uppercase', letterSpacing: 0.5,
            }}>
              <span>{meta.emoji}</span> Twin Response
            </div>
            <div style={{
              background: '#0F172A', border: `1px solid ${meta.color}33`,
              borderRadius: 10, padding: '12px 14px',
            }}>
              <p style={{ margin: 0, fontSize: 13, color: '#CBD5E1', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                {trace.response_generated || '—'}
              </p>
            </div>
          </div>

        </div>
      )}
    </div>
  )
}

export default function KnowledgeProofsViewer() {
  const [traces, setTraces] = useState([])
  const [loading, setLoading] = useState(true)
  const [sessionId, setSessionId] = useState(null)
  const [inputId, setInputId] = useState('')
  const [error, setError] = useState(null)

  // Auto-detect session ID from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('dt_session_id')
    if (stored) {
      setSessionId(stored)
      setInputId(stored)
    }
  }, [])

  const fetchTraces = useCallback(async (sid) => {
    if (!sid) return
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/workflows/session-traces/${sid}`)
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || 'Failed')
      setTraces(json.traces || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  // Auto-poll every 4 seconds when session is known
  useEffect(() => {
    if (!sessionId) { setLoading(false); return }
    fetchTraces(sessionId)
    const interval = setInterval(() => fetchTraces(sessionId), 4000)
    return () => clearInterval(interval)
  }, [sessionId, fetchTraces])

  const handleLoad = () => {
    if (!inputId.trim()) return
    setLoading(true)
    setSessionId(inputId.trim())
    localStorage.setItem('dt_session_id', inputId.trim())
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Session picker */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        background: '#0F172A', border: '1px solid #1E293B',
        borderRadius: 10, padding: '10px 14px',
      }}>
        <span style={{ fontSize: 13, color: '#64748B', whiteSpace: 'nowrap' }}>Session ID:</span>
        <input
          value={inputId}
          onChange={e => setInputId(e.target.value)}
          placeholder="Paste session ID to load traces…"
          style={{
            flex: 1, background: 'transparent', border: 'none', outline: 'none',
            color: '#F8FAFC', fontSize: 13, fontFamily: 'monospace',
          }}
          onKeyDown={e => e.key === 'Enter' && handleLoad()}
        />
        <button
          onClick={handleLoad}
          style={{
            background: 'rgba(99,102,241,0.2)', border: '1px solid #4F46E5',
            borderRadius: 6, padding: '4px 14px', color: '#A5B4FC',
            fontSize: 12, cursor: 'pointer', fontWeight: 700,
          }}
        >Load</button>
        <button
          onClick={() => fetchTraces(sessionId)}
          title="Refresh"
          style={{
            background: 'rgba(52,211,153,0.1)', border: '1px solid #34D39944',
            borderRadius: 6, padding: '4px 10px', color: '#34D399',
            fontSize: 14, cursor: 'pointer',
          }}
        >↻</button>
      </div>

      {/* Status */}
      {!sessionId && (
        <div style={{ padding: 20, textAlign: 'center', color: '#475569', fontSize: 13 }}>
          No active session detected. Start a pre-consultation chat and traces will appear here automatically.
        </div>
      )}

      {sessionId && loading && (
        <div style={{ padding: 20, textAlign: 'center', color: '#94A3B8', fontSize: 13 }}>
          Loading execution traces…
        </div>
      )}

      {error && (
        <div style={{ padding: 12, background: 'rgba(248,113,113,0.08)', border: '1px solid #F87171', borderRadius: 8, color: '#F87171', fontSize: 13 }}>
          ⚠️ {error}
        </div>
      )}

      {sessionId && !loading && traces.length === 0 && !error && (
        <div style={{ padding: 20, textAlign: 'center', color: '#475569', fontSize: 13 }}>
          No execution traces yet for this session. Send a message in the chat to generate traces.
        </div>
      )}

      {/* Trace cards */}
      {traces.map((trace, i) => (
        <TraceCard key={trace.trace_id || i} trace={trace} index={i} />
      ))}

      {traces.length > 0 && (
        <div style={{ fontSize: 11, color: '#334155', textAlign: 'center', paddingTop: 4 }}>
          Auto-refreshes every 4 seconds · {traces.length} step{traces.length !== 1 ? 's' : ''} recorded
        </div>
      )}
    </div>
  )
}
