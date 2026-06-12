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

// Custom node styles for ReactFlow
const taskNodeStyle = {
  background: 'rgba(30, 41, 59, 0.95)',
  border: '2px solid #3B82F6',
  borderRadius: '12px',
  padding: '16px',
  color: '#F8FAFC',
  width: 200,
  boxShadow: '0 0 25px rgba(59, 130, 246, 0.5)',
  backdropFilter: 'blur(10px)',
};

const skillNodeStyle = {
  background: 'rgba(49, 46, 129, 0.95)',
  border: '2px solid #6366F1',
  borderRadius: '8px',
  padding: '12px',
  color: '#F8FAFC',
  width: 180,
  boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
  backdropFilter: 'blur(10px)',
};

const knowledgeNodeStyle = {
  background: 'rgba(6, 78, 59, 0.9)',
  border: '1px solid #10B981',
  borderRadius: '6px',
  padding: '10px',
  color: '#E0E7FF',
  width: 160,
  fontSize: '12px',
  boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
};

// Sub-component to render the specific ReactFlow graph for a single Task
function TaskReactFlowGraph({ task, taskIdx, taskSkills, knowGroupsBySkill }) {
    
    const nodes = [];
    const edges = [];

    const CENTER_X = 500;
    const CENTER_Y = 250;

    // Flatten all knowledge for this task
    const allKnowledge = [];
    taskSkills.forEach(skill => {
        const kNodes = knowGroupsBySkill[skill.id || skill.node_id] || [];
        allKnowledge.push(...kNodes);
    });

    // Helper to map Skill Title to Backend Wrapper Function
    const getToolNameForSkill = (title) => {
        const lower = (title || "").toLowerCase();
        if (lower.includes('vital') || lower.includes('symptom') || lower.includes('profiling')) {
            return "ClinicalServicesWrapper.extract_vitals()";
        } else if (lower.includes('blood pressure') || lower.includes('fever') || lower.includes('acs') || lower.includes('risk')) {
            return "ClinicalServicesWrapper.synthesize_report()";
        } else if (lower.includes('escalation') || lower.includes('treatment') || lower.includes('dispatch') || lower.includes('action')) {
            return "EmailServiceWrapper.send_communication()";
        }
        return "BaseWrapper.execute()";
    };

    // 1. Task Node (Center)
    nodes.push({
        id: `task-${task.id}`,
        position: { x: CENTER_X - 100, y: CENTER_Y - 50 }, // -100 to center it since width is 200
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: {
            label: (
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '18px', marginBottom: '4px' }}>⚡</div>
                    <div style={{ fontWeight: 800, fontSize: '13px', color: '#38BDF8', textTransform: 'uppercase' }}>Task {taskIdx + 1}</div>
                    <div style={{ fontSize: '14px', marginTop: '4px', fontWeight: 'bold' }}>{task.name}</div>
                </div>
            )
        },
        style: taskNodeStyle,
    });

    // 2. Skill Nodes (Right Side)
    const SKILL_X = CENTER_X + 250;
    const Y_SPACING = 120;
    const skillsStartY = CENTER_Y - ((taskSkills.length - 1) * Y_SPACING) / 2;

    taskSkills.forEach((skill, sIndex) => {
        const sNodeId = `skill-${skill.node_id || skill.id || sIndex}`;
        const sY = skillsStartY + sIndex * Y_SPACING;
        
        nodes.push({
            id: sNodeId,
            position: { x: SKILL_X, y: sY - 30 }, 
            targetPosition: Position.Left,
            data: {
                label: (
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                            <span>⚙️</span>
                            <strong style={{ color: '#A5B4FC' }}>Skill (Execution Tool)</strong>
                        </div>
                        <div style={{ fontSize: '13px', marginBottom: '6px' }}>{skill.title}</div>
                        <div style={{ 
                            background: 'rgba(0,0,0,0.3)', 
                            padding: '4px 6px', 
                            borderRadius: '4px', 
                            fontSize: '9px', 
                            color: '#93C5FD',
                            fontFamily: 'monospace',
                            border: '1px solid rgba(147, 197, 253, 0.2)',
                            wordBreak: 'break-all'
                        }}>
                            {getToolNameForSkill(skill.title)}
                        </div>
                    </div>
                )
            },
            style: skillNodeStyle,
        });

        edges.push({
            id: `e-task-${sNodeId}`,
            source: `task-${task.id}`,
            target: sNodeId,
            animated: true,
            style: { stroke: '#6366F1', strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#6366F1' },
        });
    });

    // 3. Knowledge Nodes (Left Side)
    const KNOW_X = CENTER_X - 350;
    const knowStartY = CENTER_Y - ((allKnowledge.length - 1) * Y_SPACING) / 2;

    allKnowledge.forEach((know, kIndex) => {
        const kNodeId = `know-${know.node_id || know.id || Math.random()}`;
        const kY = knowStartY + kIndex * Y_SPACING;

        nodes.push({
            id: kNodeId,
            position: { x: KNOW_X, y: kY - 30 },
            sourcePosition: Position.Right,
            data: {
                label: (
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
                            <span>🧠</span>
                            <strong style={{ color: '#34D399', fontSize: '11px' }}>Knowledge (Source Rules)</strong>
                        </div>
                        <div style={{ fontSize: '11px' }}>{know.title}</div>
                    </div>
                )
            },
            style: knowledgeNodeStyle,
        });

        // Edge from Knowledge to Task (flows inwards)
        edges.push({
            id: `e-${kNodeId}-task`,
            source: kNodeId,
            target: `task-${task.id}`,
            animated: true,
            style: { stroke: '#10B981', strokeWidth: 1.5, strokeDasharray: '5,5' },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#10B981' },
        });
    });

    return (
        <div style={{ width: '100%', height: '500px', background: '#020617', borderRadius: '12px', border: '1px dashed #475569', overflow: 'hidden' }}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                fitView
                colorMode="dark"
                minZoom={0.2}
                nodesDraggable={true}
            >
                <Background color="#334155" gap={20} />
                <Controls />
            </ReactFlow>
        </div>
    );
}


export default function TwinBrainAccordion() {
  const [loading, setLoading] = useState(true);
  const [rawFiles, setRawFiles] = useState({ skills: [], knowledge: [] });
  const [tasks, setTasks] = useState([]);
  
  // State for toggles
  const [isWorkflowExpanded, setIsWorkflowExpanded] = useState(true);
  const [expandedTaskIdx, setExpandedTaskIdx] = useState(null);

  const fetchGraphData = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/config/sync`);
      const json = await res.json();
      const files = json.files || [];

      const skills = files.filter(f => f.type === 'cot');
      const knowledge = files.filter(f => f.type === 'knowledge');

      const parsedTasks = [
          { id: 'step_1', name: 'Intake' },
          { id: 'step_2', name: 'Diagnosis Gate' },
          { id: 'step_3', name: 'Action Escalator' }
      ];

      setTasks(parsedTasks);
      setRawFiles({ skills, knowledge });
      
    } catch (err) {
      console.error("Failed to fetch graph data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraphData();
  }, []);

  const toggleTask = (idx) => {
    if (expandedTaskIdx === idx) {
        setExpandedTaskIdx(null); // Close if already open
    } else {
        setExpandedTaskIdx(idx); // Open this one
    }
  };

  if (loading) {
    return <div style={{ color: '#94A3B8', padding: '20px' }}>Loading Interactive Architecture...</div>;
  }

  // --- SEMANTIC MAPPING LOGIC ---
  const { skills, knowledge } = rawFiles;
  const skillGroups = Array.from({ length: tasks.length }, () => []);
  const knowGroupsBySkill = {};

  skills.forEach((skill) => {
      const title = (skill.title || "").toLowerCase();
      let assignedTaskIdx = 0; 

      if (title.includes('vital') || title.includes('symptom') || title.includes('profiling')) {
          assignedTaskIdx = 0;
      } else if (title.includes('blood pressure evaluation') || title.includes('fever') || title.includes('risk stratification') || title.includes('acs')) {
          assignedTaskIdx = 1;
      } else if (title.includes('escalation') || title.includes('treatment') || title.includes('dispatch') || title.includes('action')) {
          assignedTaskIdx = 2;
      } else {
          assignedTaskIdx = 1; 
      }
      skillGroups[assignedTaskIdx].push(skill);
      knowGroupsBySkill[skill.id || skill.node_id] = [];
  });

  knowledge.forEach((know) => {
      const title = (know.title || "").toLowerCase();
      let targetSkillId = null;

      const findSkillInAll = (keywords) => {
          const found = skills.find(s => keywords.some(k => (s.title || "").toLowerCase().includes(k)));
          return found ? (found.id || found.node_id) : null;
      };

      if (title.includes('blood pressure classification') || title.includes('temperature')) {
          targetSkillId = findSkillInAll(['vital', 'symptom']);
      } else if (title.includes('chest pain') || title.includes('risk factors') || title.includes('troponin') || title.includes('ecg')) {
          targetSkillId = findSkillInAll(['acs', 'risk stratification']);
      } else if (title.includes('refer') || title.includes('escalation') || title.includes('medication') || title.includes('therapy')) {
          targetSkillId = findSkillInAll(['escalation', 'treatment']);
      }

      if (targetSkillId && knowGroupsBySkill[targetSkillId]) {
          knowGroupsBySkill[targetSkillId].push(know);
      }
  });

  return (
    <div style={{ background: '#020617', borderRadius: '16px', border: '1px solid #1E293B', padding: '24px', color: '#F8FAFC' }}>
      
      {/* 1. Workflow Header */}
      <div 
        onClick={() => setIsWorkflowExpanded(!isWorkflowExpanded)}
        style={{ 
            background: 'rgba(30, 41, 59, 0.95)', 
            border: '2px solid #3B82F6', 
            borderRadius: '12px', 
            padding: '16px 24px', 
            cursor: 'pointer',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 0 15px rgba(59, 130, 246, 0.3)',
            transition: 'all 0.2s ease',
            marginBottom: '16px'
        }}
      >
        <div>
            <div style={{ fontSize: '12px', color: '#38BDF8', fontWeight: 800, textTransform: 'uppercase', marginBottom: '4px' }}>
                Core Workflow
            </div>
            <div style={{ fontSize: '18px', fontWeight: 'bold' }}>Cardiology Pre-Consultation</div>
        </div>
        <div style={{ fontSize: '24px', color: '#38BDF8', transform: isWorkflowExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.3s' }}>
            ▼
        </div>
      </div>

      {/* 2. Tasks Container */}
      {isWorkflowExpanded && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginLeft: '24px', borderLeft: '2px solid #334155', paddingLeft: '24px' }}>
              
              {tasks.map((task, idx) => {
                  const isTaskExpanded = expandedTaskIdx === idx;
                  const taskSkills = skillGroups[idx];

                  return (
                      <div key={task.id}>
                          {/* Task Card */}
                          <div 
                              onClick={() => toggleTask(idx)}
                              style={{ 
                                  background: isTaskExpanded ? 'rgba(59, 130, 246, 0.1)' : 'rgba(49, 46, 129, 0.4)', 
                                  border: isTaskExpanded ? '2px solid #60A5FA' : '1px solid #6366F1', 
                                  borderRadius: '10px', 
                                  padding: '14px 20px', 
                                  cursor: 'pointer',
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  transition: 'all 0.2s ease'
                              }}
                          >
                              <div>
                                  <div style={{ fontSize: '11px', color: '#A5B4FC', fontWeight: 800, textTransform: 'uppercase', marginBottom: '4px' }}>
                                      Task {idx + 1}
                                  </div>
                                  <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{task.name}</div>
                              </div>
                              <div style={{ color: '#A5B4FC', fontSize: '14px' }}>
                                  {isTaskExpanded ? 'Close Graph ▲' : 'View Graph ▼'}
                              </div>
                          </div>

                          {/* 3. React Flow Graph Container */}
                          {isTaskExpanded && (
                              <div style={{ marginTop: '16px', marginBottom: '16px' }}>
                                  <TaskReactFlowGraph 
                                      task={task} 
                                      taskIdx={idx} 
                                      taskSkills={taskSkills} 
                                      knowGroupsBySkill={knowGroupsBySkill} 
                                  />
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
