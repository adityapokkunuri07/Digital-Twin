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
                Digital Twin Brain & Blueprint Assembly Module
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="fade-up">
          <div className="bg-[#1E293B] rounded-xl border border-[#334155] p-6 shadow-lg mb-8">
            <TwinBrainAccordion />
            <div style={{ paddingTop: 32 }}>
               <h3 style={{ fontSize: 14, color: '#94A3B8', marginBottom: 16 }}>Execution Event Log</h3>
               <KnowledgeProofsViewer />
            </div>
          </div>
        </div>

      </main>
    </div>
  )
}
