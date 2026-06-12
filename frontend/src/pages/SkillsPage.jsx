import KnowledgeProofsViewer from '../components/skills/KnowledgeProofsViewer'
import TwinBrainAccordion from '../components/skills/TwinBrainAccordion'

export default function SkillsPage() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#0F172A', color: '#F8FAFC' }}>
      <main style={{ flex: 1, padding: '32px 36px', overflow: 'auto' }}>

        {/* Header */}
        <div className="fade-up" style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <h1 style={{ fontSize: 24, fontWeight: 700, color: '#F8FAFC' }}>Twin Brain</h1>
              <p style={{ color: '#94A3B8', fontSize: 13.5, marginTop: 4 }}>
                Digital Twin Brain — Workflow Architecture &amp; Knowledge Traceability
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="fade-up">
          <div style={{ background: '#1E293B', borderRadius: 12, border: '1px solid #334155', padding: 24, marginBottom: 8 }}>
            <TwinBrainAccordion />
          </div>

          <div style={{ background: '#1E293B', borderRadius: 12, border: '1px solid #334155', padding: 24, marginTop: 16 }}>
            <div style={{ marginBottom: 18 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#F8FAFC', margin: '0 0 4px 0', display: 'flex', alignItems: 'center', gap: 8 }}>
                🔍 Knowledge Traceability — Session Execution Log
              </h3>
              <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>
                Every step the Twin took, which knowledge chunks it retrieved, and the response it generated — live, per session.
              </p>
            </div>
            <KnowledgeProofsViewer />
          </div>
        </div>

      </main>
    </div>
  )
}
