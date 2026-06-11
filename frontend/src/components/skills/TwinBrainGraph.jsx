import React, { useState, useEffect, useCallback } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const API_BASE = 'http://127.0.0.1:8000';

// Custom node styles
const workflowNodeStyle = {
  background: 'rgba(30, 41, 59, 0.95)',
  border: '2px solid #3B82F6',
  borderRadius: '12px',
  padding: '16px',
  color: '#F8FAFC',
  width: 250,
  boxShadow: '0 0 15px rgba(59, 130, 246, 0.4)',
  backdropFilter: 'blur(10px)',
};

const taskNodeStyle = {
  background: 'rgba(49, 46, 129, 0.95)',
  border: '2px solid #6366F1',
  borderRadius: '8px',
  padding: '12px',
  color: '#F8FAFC',
  width: 200,
  boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
  backdropFilter: 'blur(10px)',
};

export default function TwinBrainGraph() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [loading, setLoading] = useState(true);

  const onNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const fetchGraphData = async () => {
    try {
      // Hardcoded tasks matching the workflow
      const parsedTasks = [
          { id: 'step_1', name: 'Intake' },
          { id: 'step_2', name: 'Diagnosis Gate' },
          { id: 'step_3', name: 'Action Escalator' }
      ];

      const newNodes = [];
      const newEdges = [];

      // ── Tree Layout Dimensions ──
      const Y_WORKFLOW = 100;
      const Y_TASK = 300;
      const WORKFLOW_X = 400; // Center
      const TASK_SPACING_X = 250;

      // 1. Build Workflow Root Node
      newNodes.push({
          id: 'workflow-root',
          position: { x: WORKFLOW_X, y: Y_WORKFLOW },
          data: {
              label: (
                  <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '20px', marginBottom: '4px' }}>⚙️</div>
                      <div style={{ fontWeight: 800, fontSize: '15px', color: '#38BDF8', textTransform: 'uppercase' }}>Core Workflow</div>
                      <div style={{ fontSize: '14px', marginTop: '4px' }}>Cardiology Pre-Consultation</div>
                  </div>
              )
          },
          style: workflowNodeStyle,
      });

      // 2. Build Task Nodes
      const startX = WORKFLOW_X - ((parsedTasks.length - 1) * TASK_SPACING_X) / 2;

      parsedTasks.forEach((t, i) => {
          const x = startX + (i * TASK_SPACING_X);
          const taskId = `task-${t.id}`;
          
          newNodes.push({
              id: taskId,
              position: { x, y: Y_TASK },
              data: {
                  label: (
                      <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: '18px', marginBottom: '4px' }}>⚡</div>
                          <div style={{ fontWeight: 800, fontSize: '13px', color: '#A5B4FC', textTransform: 'uppercase' }}>Task {i + 1}</div>
                          <div style={{ fontSize: '14px', marginTop: '4px', fontWeight: 'bold' }}>{t.name}</div>
                      </div>
                  )
              },
              style: taskNodeStyle,
          });

          // Edge: Workflow -> Task
          newEdges.push({
              id: `e-root-${taskId}`,
              source: 'workflow-root',
              target: taskId,
              animated: true,
              style: { stroke: '#6366F1', strokeWidth: 2 },
              markerEnd: { type: MarkerType.ArrowClosed, color: '#6366F1' },
          });
      });

      setNodes(newNodes);
      setEdges(newEdges);
      
    } catch (err) {
      console.error("Failed to fetch graph data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraphData();
  }, []);

  if (loading) {
    return <div style={{ color: '#94A3B8', padding: '20px' }}>Loading Interactive Graph...</div>;
  }

  return (
    <div style={{ width: '100%', height: '600px', background: '#020617', borderRadius: '16px', border: '1px solid #1E293B', overflow: 'hidden' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        colorMode="dark"
        minZoom={0.2}
      >
        <Background color="#334155" gap={20} />
        <Controls />
      </ReactFlow>
    </div>
  );
}
