import React, { useState, useEffect } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  MarkerType,
  Position
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const API_BASE = 'http://127.0.0.1:8000';

// ── Node Styles ───────────────────────────────────────────────────────────────

const taskNodeStyle = {
  background: 'rgba(30, 41, 59, 0.98)',
  border: '2px solid #3B82F6',
  borderRadius: '12px',
  padding: '16px',
  color: '#F8FAFC',
  width: 200,
  boxShadow: '0 0 25px rgba(59, 130, 246, 0.5)',
  backdropFilter: 'blur(10px)',
};

const skillNodeStyle = {
  background: 'rgba(49, 46, 129, 0.98)',
  border: '2px solid #6366F1',
  borderRadius: '8px',
  padding: '12px',
  color: '#F8FAFC',
  width: 190,
  boxShadow: '0 4px 12px rgba(99,102,241,0.3)',
  backdropFilter: 'blur(10px)',
};

const knowledgeNodeStyle = {
  background: 'rgba(6, 78, 59, 0.95)',
  border: '1px solid #10B981',
  borderRadius: '8px',
  padding: '10px 12px',
  color: '#D1FAE5',
  width: 200,
  fontSize: '11px',
  boxShadow: '0 0 12px rgba(16,185,129,0.25)',
};

// ── Helper: Skill → Wrapper mapping ──────────────────────────────────────────
const getToolName = (title = '') => {
  const t = title.toLowerCase();
  if (t.includes('vital')) return 'ClinicalServicesWrapper.extract_vitals()';
  if (t.includes('symptom') || t.includes('profil')) return 'ClinicalServicesWrapper.extract_vitals()';
  if (t.includes('blood') || t.includes('risk') || t.includes('acs')) return 'ClinicalServicesWrapper.synthesize_report()';
  if (t.includes('escalat') || t.includes('dispatch') || t.includes('action')) return 'EmailServiceWrapper.send_communication()';
  return 'BaseWrapper.execute()';
};

// ── ReactFlow graph for one Task ──────────────────────────────────────────────
function TaskReactFlowGraph({ task, taskIdx, taskSkills, knowledgeChunks }) {
  const nodes = [];
  const edges = [];

  const CENTER_X = 420;
  const CENTER_Y = 260;
  const Y_SPACING = 130;

  // ── 1. Task Node (Centre) ────────────────────────────────────────────────
  nodes.push({
    id: `task-${task.id}`,
    position: { x: CENTER_X - 100, y: CENTER_Y - 50 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      label: (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 20, marginBottom: 4 }}>⚡</div>
          <div style={{ fontWeight: 800, fontSize: 13, color: '#38BDF8', textTransform: 'uppercase' }}>
            Task {taskIdx + 1}
          </div>
          <div style={{ fontSize: 14, marginTop: 4, fontWeight: 'bold' }}>{task.name}</div>
        </div>
      )
    },
    style: taskNodeStyle,
  });

  // ── 2. Skill Nodes (Right Side) ───────────────────────────────────────────
  const SKILL_X = CENTER_X + 270;
  const skillsStartY = CENTER_Y - ((taskSkills.length - 1) * Y_SPACING) / 2;

  taskSkills.forEach((skill, si) => {
    const sId = `skill-${task.id}-${si}`;
    const sY = skillsStartY + si * Y_SPACING;

    nodes.push({
      id: sId,
      position: { x: SKILL_X, y: sY - 40 },
      targetPosition: Position.Left,
      data: {
        label: (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <span>⚙️</span>
              <strong style={{ color: '#A5B4FC', fontSize: 11 }}>Skill (Execution Tool)</strong>
            </div>
            <div style={{ fontSize: 13, marginBottom: 6, fontWeight: 600 }}>{skill.title}</div>
            <div style={{
              background: 'rgba(0,0,0,0.35)', padding: '3px 6px', borderRadius: 4,
              fontSize: 9, color: '#93C5FD', fontFamily: 'monospace',
              border: '1px solid rgba(147,197,253,0.2)', wordBreak: 'break-all'
            }}>
              {getToolName(skill.title)}
            </div>
          </div>
        )
      },
      style: skillNodeStyle,
    });

    edges.push({
      id: `e-task-${sId}`,
      source: `task-${task.id}`,
      target: sId,
      animated: true,
      style: { stroke: '#6366F1', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#6366F1' },
    });
  });

  // ── 3. Knowledge Nodes (Left Side) — REAL chunks ─────────────────────────
  const KNOW_X = CENTER_X - 500;
  // Show up to 5 most relevant chunks per task to keep graph readable
  const chunksToShow = knowledgeChunks.slice(0, 5);
  const knowStartY = CENTER_Y - ((chunksToShow.length - 1) * Y_SPACING) / 2;

  chunksToShow.forEach((chunk, ki) => {
    const kId = `know-${task.id}-${ki}`;
    const kY = knowStartY + ki * Y_SPACING;

    // Truncate long titles / content for display
    const displayTitle = (chunk.title || chunk.parent_path || `Chunk ${ki + 1}`).slice(0, 50);
    const displayPreview = (chunk.content || '').slice(0, 90) + ((chunk.content || '').length > 90 ? '…' : '');
    const tags = (chunk.tags || []).slice(0, 3);

    nodes.push({
      id: kId,
      position: { x: KNOW_X, y: kY - 40 },
      sourcePosition: Position.Right,
      data: {
        label: (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
              <span>🧠</span>
              <strong style={{ color: '#34D399', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.3 }}>
                Expert Knowledge
              </strong>
            </div>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#A7F3D0', marginBottom: 4, lineHeight: 1.3 }}>
              {displayTitle}
            </div>
            {tags.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3, marginBottom: 4 }}>
                {tags.map(t => (
                  <span key={t} style={{
                    fontSize: 8, background: 'rgba(16,185,129,0.15)', border: '1px solid #059669',
                    borderRadius: 3, padding: '1px 4px', color: '#6EE7B7'
                  }}>#{t}</span>
                ))}
              </div>
            )}
            <div style={{ fontSize: 9, color: '#6EE7B7', lineHeight: 1.4, opacity: 0.8 }}>
              {displayPreview}
            </div>
          </div>
        )
      },
      style: knowledgeNodeStyle,
    });

    // Edge: Knowledge → Task (knowledge feeds into task)
    edges.push({
      id: `e-${kId}-task`,
      source: kId,
      target: `task-${task.id}`,
      animated: true,
      style: { stroke: '#10B981', strokeWidth: 1.5, strokeDasharray: '5,4' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#10B981' },
    });
  });

  // Graph height scales with content
  const graphHeight = Math.max(500, Math.max(taskSkills.length, chunksToShow.length) * 140 + 100);

  return (
    <div style={{
      width: '100%', height: graphHeight,
      background: '#020617', borderRadius: 12,
      border: '1px dashed #1E293B', overflow: 'hidden'
    }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        colorMode="dark"
        minZoom={0.15}
        nodesDraggable
      >
        <Background color="#1E293B" gap={20} />
        <Controls />
      </ReactFlow>
    </div>
  );
}

// ── Main TwinBrainAccordion ───────────────────────────────────────────────────
export default function TwinBrainAccordion() {
  const [loading, setLoading]         = useState(true);
  const [skills, setSkills]           = useState([]);
  const [knowledge, setKnowledge]     = useState([]);   // raw file list from sync
  const [chunks, setChunks]           = useState([]);   // actual knowledge chunks
  const [tasks]                       = useState([
    { id: 'step_1', name: 'Intake' },
    { id: 'step_2', name: 'Diagnosis Gate' },
    { id: 'step_3', name: 'Action Escalator' },
  ]);
  const [isWorkflowExpanded, setIsWorkflowExpanded] = useState(true);
  const [expandedTaskIdx, setExpandedTaskIdx]       = useState(null);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        // 1. Fetch skill (cot) and knowledge file list
        const syncRes  = await fetch(`${API_BASE}/api/config/sync`);
        const syncJson = await syncRes.json();
        const files = syncJson.files || [];
        setSkills(files.filter(f => f.type === 'cot'));
        setKnowledge(files.filter(f => f.type === 'knowledge'));

        // 2. Try to fetch actual knowledge chunks for real content
        // Use the session's config_id from localStorage if available
        const configId = localStorage.getItem('dt_config_id') || syncJson.config_id;
        if (configId) {
          try {
            const chunkRes  = await fetch(`${API_BASE}/api/config/${configId}/knowledge-chunks`);
            if (chunkRes.ok) {
              const chunkJson = await chunkRes.json();
              setChunks(chunkJson.chunks || chunkJson || []);
            }
          } catch (_) {
            // silently fall back to file list
          }
        }

        // 3. Fallback: build chunk-like objects from the knowledge file list
        if (chunks.length === 0) {
          const fallbackChunks = files
            .filter(f => f.type === 'knowledge')
            .map(f => ({
              chunk_id: f.id || f.path,
              title: f.title || f.path?.split('/').pop() || f.path,
              content: f.description || f.summary || '',
              tags: f.tags || [],
              parent_path: f.path || '',
            }));
          setChunks(fallbackChunks);
        }
      } catch (err) {
        console.error('TwinBrainAccordion fetch failed:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Skill-to-Task mapping ─────────────────────────────────────────────────
  const skillGroups = Array.from({ length: tasks.length }, () => []);
  skills.forEach(skill => {
    const t = (skill.title || '').toLowerCase();
    if (t.includes('vital') || t.includes('symptom') || t.includes('profil')) {
      skillGroups[0].push(skill);
    } else if (t.includes('blood') || t.includes('fever') || t.includes('risk') || t.includes('acs')) {
      skillGroups[1].push(skill);
    } else if (t.includes('escalat') || t.includes('dispatch') || t.includes('action') || t.includes('treatment')) {
      skillGroups[2].push(skill);
    } else {
      // Assign unmatched skills round-robin across tasks
      const minIdx = skillGroups.reduce((mi, g, i) => g.length < skillGroups[mi].length ? i : mi, 0);
      skillGroups[minIdx].push(skill);
    }
  });

  // ── Knowledge-to-Task mapping ─────────────────────────────────────────────
  // All tasks draw from the same expert knowledge base; distribute chunks evenly
  const chunkGroups = Array.from({ length: tasks.length }, () => []);
  chunks.forEach((chunk, ci) => {
    chunkGroups[ci % tasks.length].push(chunk);
  });

  if (loading) {
    return (
      <div style={{ color: '#94A3B8', padding: 20, textAlign: 'center' }}>
        Loading Twin Brain Architecture…
      </div>
    );
  }

  return (
    <div style={{ background: '#020617', borderRadius: 16, border: '1px solid #1E293B', padding: 24, color: '#F8FAFC' }}>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 20, marginBottom: 20, flexWrap: 'wrap' }}>
        {[
          { color: '#10B981', emoji: '🧠', label: 'Expert Knowledge (RAG Chunks)' },
          { color: '#3B82F6', emoji: '⚡', label: 'Task Node' },
          { color: '#6366F1', emoji: '⚙️', label: 'Skill / Execution Tool' },
        ].map(item => (
          <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12 }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: item.color }} />
            <span style={{ color: '#94A3B8' }}>{item.emoji} {item.label}</span>
          </div>
        ))}
        <div style={{ marginLeft: 'auto', fontSize: 12, color: '#334155' }}>
          {chunks.length} knowledge chunk{chunks.length !== 1 ? 's' : ''} · {skills.length} skill{skills.length !== 1 ? 's' : ''} loaded
        </div>
      </div>

      {/* Workflow Header */}
      <div
        onClick={() => setIsWorkflowExpanded(e => !e)}
        style={{
          background: 'rgba(30,41,59,0.95)', border: '2px solid #3B82F6',
          borderRadius: 12, padding: '16px 24px', cursor: 'pointer',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          boxShadow: '0 0 15px rgba(59,130,246,0.3)', marginBottom: 16,
          transition: 'all 0.2s',
        }}
      >
        <div>
          <div style={{ fontSize: 11, color: '#38BDF8', fontWeight: 800, textTransform: 'uppercase', marginBottom: 4 }}>
            Core Workflow
          </div>
          <div style={{ fontSize: 18, fontWeight: 'bold' }}>
            {knowledge[0]?.title || 'Expert Knowledge'} Pre-Consultation
          </div>
        </div>
        <div style={{ fontSize: 22, color: '#38BDF8', transform: isWorkflowExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.3s' }}>▼</div>
      </div>

      {/* Tasks */}
      {isWorkflowExpanded && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginLeft: 24, borderLeft: '2px solid #1E293B', paddingLeft: 24 }}>
          {tasks.map((task, idx) => {
            const isExpanded = expandedTaskIdx === idx;
            const taskSkills = skillGroups[idx];
            const taskChunks = chunkGroups[idx];

            return (
              <div key={task.id}>
                {/* Task accordion header */}
                <div
                  onClick={() => setExpandedTaskIdx(isExpanded ? null : idx)}
                  style={{
                    background: isExpanded ? 'rgba(59,130,246,0.1)' : 'rgba(49,46,129,0.4)',
                    border: isExpanded ? '2px solid #60A5FA' : '1px solid #6366F1',
                    borderRadius: 10, padding: '14px 20px', cursor: 'pointer',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    transition: 'all 0.2s',
                  }}
                >
                  <div>
                    <div style={{ fontSize: 10, color: '#A5B4FC', fontWeight: 800, textTransform: 'uppercase', marginBottom: 3 }}>
                      Task {idx + 1}
                    </div>
                    <div style={{ fontSize: 16, fontWeight: 'bold' }}>{task.name}</div>
                    <div style={{ fontSize: 11, color: '#64748B', marginTop: 2 }}>
                      {taskSkills.length} skill{taskSkills.length !== 1 ? 's' : ''} · {taskChunks.length} knowledge source{taskChunks.length !== 1 ? 's' : ''}
                    </div>
                  </div>
                  <div style={{ color: '#A5B4FC', fontSize: 13, fontWeight: 600 }}>
                    {isExpanded ? 'Close Graph ▲' : 'View Graph ▼'}
                  </div>
                </div>

                {/* ReactFlow Graph */}
                {isExpanded && (
                  <div style={{ marginTop: 12, marginBottom: 12 }}>
                    {taskChunks.length === 0 && taskSkills.length === 0 ? (
                      <div style={{
                        padding: 32, background: '#0F172A', borderRadius: 10, textAlign: 'center',
                        color: '#475569', border: '1px dashed #1E293B', fontSize: 13
                      }}>
                        No knowledge or skills loaded yet. Upload an expert document in the Configuration tab to populate this graph.
                      </div>
                    ) : (
                      <TaskReactFlowGraph
                        task={task}
                        taskIdx={idx}
                        taskSkills={taskSkills}
                        knowledgeChunks={taskChunks}
                      />
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
