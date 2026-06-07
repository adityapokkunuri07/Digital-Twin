import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Activity, Layers, UserCheck, FileText, FolderOpen, Send, 
  ShieldAlert, RefreshCw, CheckCircle2, AlertTriangle,
  Play, RotateCcw, Sparkles, Search, Eye, Trash2,
  ChevronDown, ChevronRight, Folder, File,
  ZoomIn, ZoomOut, Maximize2
} from 'lucide-react';
import PreConsultation from './PreConsultation';

const API_BASE = "http://localhost:8000/api";
const DOCTOR_ID = "4a8f39b6-89d1-4db8-bbbe-d9616e00b8e2";

const buildFileTree = (files) => {
  const root = { name: 'root', children: [], isFolder: true };
  
  files.forEach(file => {
    let path = file.path;
    // Explode dot-notation for knowledge chunks
    if (path.startsWith('knowledge/')) {
       let subPath = path.substring(10);
       if (subPath.endsWith('.md')) {
          subPath = subPath.substring(0, subPath.length - 3);
          const parts = subPath.split('.');
          parts[parts.length - 1] += '.md';
          path = 'knowledge/' + parts.join('/');
       }
    }
    
    const parts = path.split('/');
    let currentLevel = root.children;
    
    parts.forEach((part, index) => {
      let existing = currentLevel.find(item => item.name === part);
      
      if (index === parts.length - 1) {
        if (!existing) {
          currentLevel.push({ name: part, isFile: true, fileData: file });
        } else {
          existing.isFile = true;
          existing.fileData = file;
        }
      } else {
        if (!existing) {
          existing = { name: part, isFolder: true, children: [], isOpen: true };
          currentLevel.push(existing);
        } else if (!existing.children) {
          existing.isFolder = true;
          existing.children = [];
          existing.isOpen = true;
        }
        currentLevel = existing.children;
      }
    });
  });
  
  return root.children;
};

const FileTreeNode = ({ node, level, selectedFile, onSelect, onUnlearnSelect }) => {
  const [isOpen, setIsOpen] = useState(node.isOpen);
  const paddingLeft = level * 16 + 10;

  if (node.isFile) {
    const file = node.fileData;
    const isSelected = selectedFile?.path === file.path;
    return (
      <div 
        onClick={() => {
          onSelect(file);
          if (file.node_id) onUnlearnSelect(file.node_id);
        }}
        style={{ 
          display: 'flex', alignItems: 'center', gap: '6px', 
          padding: `6px 10px 6px ${paddingLeft}px`,
          cursor: 'pointer',
          background: isSelected ? 'rgba(255,255,255,0.08)' : 'transparent',
          borderLeft: isSelected ? '2px solid var(--primary)' : '2px solid transparent',
          color: file.quarantine_status ? 'var(--error)' : 'var(--text-primary)',
          borderRadius: '4px',
          margin: '2px 0'
        }}
      >
        <File size={14} style={{ color: file.quarantine_status ? 'var(--error)' : 'var(--primary)', flexShrink: 0 }} />
        <span style={{ fontSize: '12px', fontFamily: 'monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {node.name}
        </span>
      </div>
    );
  }

  return (
    <div>
      <div 
        onClick={() => setIsOpen(!isOpen)}
        style={{ 
          display: 'flex', alignItems: 'center', gap: '6px', 
          padding: `6px 10px 6px ${paddingLeft - 4}px`,
          cursor: 'pointer',
          color: 'var(--text-secondary)',
          borderRadius: '4px'
        }}
      >
        {isOpen ? <ChevronDown size={14} style={{ flexShrink: 0 }} /> : <ChevronRight size={14} style={{ flexShrink: 0 }} />}
        <Folder size={14} style={{ color: 'var(--text-secondary)', flexShrink: 0 }} />
        <span style={{ fontSize: '13px', fontWeight: 500 }}>
          {node.name}
        </span>
      </div>
      {isOpen && (
        <div>
          {node.children.map((child, i) => (
            <FileTreeNode 
              key={i} 
              node={child} 
              level={level + 1} 
              selectedFile={selectedFile}
              onSelect={onSelect}
              onUnlearnSelect={onUnlearnSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════
// Graphical Tree View — Obsidian Mapping visual node graph
// ═══════════════════════════════════════════════════════════════

const NODE_WIDTH = 200;
const NODE_HEIGHT = 42;
const LEVEL_GAP = 110;
const SIBLING_GAP = 40;

// Curated color palette — one per depth layer (cycles if deeper)
const LAYER_COLORS = [
  { bg: 'rgba(191, 90, 242, 0.22)', border: 'rgba(191, 90, 242, 0.5)',  accent: '#BF5AF2', edge: 'rgba(191, 90, 242, 0.35)' },  // Purple  — L0
  { bg: 'rgba(10, 132, 255, 0.18)', border: 'rgba(10, 132, 255, 0.45)', accent: '#0A84FF', edge: 'rgba(10, 132, 255, 0.30)' },  // Blue    — L1
  { bg: 'rgba(50, 215, 75, 0.15)',  border: 'rgba(50, 215, 75, 0.40)',  accent: '#32D74B', edge: 'rgba(50, 215, 75, 0.28)' },   // Green   — L2
  { bg: 'rgba(255, 159, 10, 0.16)', border: 'rgba(255, 159, 10, 0.42)', accent: '#FF9F0A', edge: 'rgba(255, 159, 10, 0.30)' },  // Orange  — L3
  { bg: 'rgba(255, 55, 95, 0.15)',  border: 'rgba(255, 55, 95, 0.40)',  accent: '#FF375F', edge: 'rgba(255, 55, 95, 0.28)' },   // Pink    — L4
  { bg: 'rgba(90, 200, 250, 0.15)', border: 'rgba(90, 200, 250, 0.40)', accent: '#5AC8FA', edge: 'rgba(90, 200, 250, 0.28)' },  // Cyan    — L5
];

const getLayerColor = (depth) => LAYER_COLORS[depth % LAYER_COLORS.length];

/**
 * Recursively compute layout positions for each node in the tree.
 * Returns a flat array of { node, x, y, parentX, parentY, depth } for rendering.
 */
const computeTreeLayout = (nodes) => {
  const positioned = [];

  // Measure subtree widths first (recursive)
  const measureWidth = (node) => {
    if (!node.children || node.children.length === 0) {
      node._width = NODE_WIDTH;
      return NODE_WIDTH;
    }
    let totalChildWidth = 0;
    node.children.forEach(child => {
      totalChildWidth += measureWidth(child);
    });
    totalChildWidth += (node.children.length - 1) * SIBLING_GAP;
    node._width = Math.max(NODE_WIDTH, totalChildWidth);
    return node._width;
  };

  // Position nodes recursively — now tracks depth
  const positionNode = (node, x, y, parentX, parentY, depth) => {
    positioned.push({ node, x, y, parentX, parentY, depth });

    if (node.children && node.children.length > 0) {
      const childY = y + NODE_HEIGHT + LEVEL_GAP;
      let startX = x - node._width / 2;

      node.children.forEach(child => {
        const childCenterX = startX + child._width / 2;
        positionNode(child, childCenterX, childY, x, y + NODE_HEIGHT / 2, depth + 1);
        startX += child._width + SIBLING_GAP;
      });
    }
  };

  // Create a synthetic root if there are multiple top-level nodes
  if (nodes.length === 0) return { positioned: [], totalWidth: 0, totalHeight: 0 };

  let rootNode;
  if (nodes.length === 1) {
    rootNode = nodes[0];
  } else {
    rootNode = { name: 'Vault', isFolder: true, children: nodes, _syntheticRoot: true };
  }

  measureWidth(rootNode);
  const totalWidth = rootNode._width + 80; // padding
  positionNode(rootNode, totalWidth / 2, 20, null, null, 0);

  // Calculate total height
  let maxY = 0;
  positioned.forEach(p => { if (p.y > maxY) maxY = p.y; });
  const totalHeight = maxY + NODE_HEIGHT + 60;

  return { positioned, totalWidth, totalHeight };
};

const ZOOM_MIN = 0.3;
const ZOOM_MAX = 1.5;
const ZOOM_STEP = 0.15;

const GraphicalTreeView = ({ files, selectedFile, onSelect, onUnlearnSelect }) => {
  const [zoom, setZoom] = useState(0.75);
  const containerRef = useRef(null);
  const treeData = buildFileTree(files);
  const { positioned, totalWidth, totalHeight } = computeTreeLayout(treeData);

  const handleZoomIn = useCallback(() => setZoom(z => Math.min(ZOOM_MAX, +(z + ZOOM_STEP).toFixed(2))), []);
  const handleZoomOut = useCallback(() => setZoom(z => Math.max(ZOOM_MIN, +(z - ZOOM_STEP).toFixed(2))), []);
  const handleFitToView = useCallback(() => {
    if (!containerRef.current || totalWidth === 0) return;
    const container = containerRef.current;
    const scaleX = (container.clientWidth - 32) / totalWidth;
    const scaleY = (container.clientHeight - 32) / totalHeight;
    const fitScale = Math.min(scaleX, scaleY, 1.0);
    setZoom(Math.max(ZOOM_MIN, +(fitScale).toFixed(2)));
  }, [totalWidth, totalHeight]);

  // Mouse wheel zoom
  const handleWheel = useCallback((e) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
      setZoom(z => Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, +(z + delta).toFixed(2))));
    }
  }, []);

  if (files.length === 0) {
    return (
      <div style={{ 
        color: 'var(--text-muted)', padding: '60px 20px', textAlign: 'center', fontSize: '13px',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', height: '100%', justifyContent: 'center'
      }}>
        <FolderOpen size={32} style={{ opacity: 0.3 }} />
        No sync triggers recorded. Save configs, finalize onboarding, or ingest documents.
      </div>
    );
  }

  const scaledWidth = totalWidth * zoom;
  const scaledHeight = totalHeight * zoom;

  return (
    <div style={{ position: 'relative', height: '600px' }}>
      {/* Zoom Controls */}
      <div className="graph-zoom-controls">
        <button className="graph-zoom-btn" onClick={handleZoomIn} title="Zoom In">
          <ZoomIn size={16} />
        </button>
        <span className="graph-zoom-label">{Math.round(zoom * 100)}%</span>
        <button className="graph-zoom-btn" onClick={handleZoomOut} title="Zoom Out">
          <ZoomOut size={16} />
        </button>
        <div className="graph-zoom-divider" />
        <button className="graph-zoom-btn" onClick={handleFitToView} title="Fit to View">
          <Maximize2 size={16} />
        </button>
      </div>

      {/* Scrollable container */}
      <div
        ref={containerRef}
        className="graph-tree-container"
        style={{ height: '100%' }}
        onWheel={handleWheel}
      >
        <div
          className="graph-tree-canvas"
          style={{
            width: scaledWidth + 'px',
            height: scaledHeight + 'px',
            minWidth: scaledWidth > 0 ? scaledWidth + 'px' : '100%',
          }}
        >
          {/* Scaled inner layer */}
          <div style={{
            width: totalWidth + 'px',
            height: totalHeight + 'px',
            transform: `scale(${zoom})`,
            transformOrigin: 'top left',
          }}>
            {/* SVG Edges — colored per child depth */}
            <svg className="graph-tree-edges" width={totalWidth} height={totalHeight}>
              {positioned.map((p, i) => {
                if (p.parentX === null) return null;
                const layerColor = getLayerColor(p.depth);
                const x1 = p.parentX;
                const y1 = p.parentY + NODE_HEIGHT / 2 + 4;
                const x2 = p.x;
                const y2 = p.y - 2;
                const midY = (y1 + y2) / 2;
                return (
                  <path
                    key={`edge-${i}`}
                    d={`M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}`}
                    style={{ stroke: layerColor.edge, strokeWidth: 2 }}
                  />
                );
              })}
            </svg>

            {/* Nodes — colored per depth layer */}
            {positioned.map((p, i) => {
              const { node, x, y, depth } = p;
              const layerColor = getLayerColor(depth);
              const isFolder = node.isFolder && !node._syntheticRoot;
              const isRoot = i === 0;
              const isFile = node.isFile;
              const fileData = node.fileData;
              const isSelected = isFile && selectedFile && selectedFile.path === fileData?.path;
              const isQuarantined = isFile && fileData?.quarantine_status;

              let className = 'graph-node';
              if (isSelected) className += ' graph-node--selected';
              if (isQuarantined) className += ' graph-node--quarantined';

              const handleClick = () => {
                if (isFile && fileData) {
                  onSelect(fileData);
                  if (fileData.node_id) onUnlearnSelect(fileData.node_id);
                }
              };

              const nodeStyle = {
                left: x + 'px',
                top: y + 'px',
                background: isQuarantined ? 'rgba(255, 69, 58, 0.08)' : layerColor.bg,
                borderColor: isSelected ? 'var(--primary)' : (isQuarantined ? 'rgba(255, 69, 58, 0.4)' : layerColor.border),
                borderStyle: isFolder && !isRoot ? 'dashed' : 'solid',
              };

              const iconColor = isQuarantined ? 'var(--error)' : layerColor.accent;

              return (
                <div
                  key={i}
                  className={className}
                  style={nodeStyle}
                  onClick={handleClick}
                  title={isFile ? fileData?.path : node.name}
                >
                  {isFolder || isRoot ? (
                    <Folder size={16} style={{ color: iconColor, flexShrink: 0 }} />
                  ) : (
                    <File size={16} style={{ color: iconColor, flexShrink: 0 }} />
                  )}
                  <span className="graph-node__label" style={{ color: layerColor.accent }}>{node.name}</span>
                  {isFile && fileData?.type && (
                    <span className="graph-node__badge" style={{ background: layerColor.bg, color: layerColor.accent, borderColor: layerColor.border }}>
                      {fileData.type}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

const buildChunkTree = (chunks) => {
  const root = { name: 'root', children: [], isFolder: true };
  
  chunks.forEach(chunk => {
    let path = chunk.current_path || chunk.title.toLowerCase().replace(/\s+/g, '_');
    const parts = path.split('.');
    let currentLevel = root.children;
    
    parts.forEach((part, index) => {
      let existing = currentLevel.find(item => item.name === part);
      
      if (index === parts.length - 1) {
        if (!existing) {
          currentLevel.push({ name: part, isChunk: true, chunkData: chunk });
        } else {
          existing.isChunk = true;
          existing.chunkData = chunk;
        }
      } else {
        if (!existing) {
          existing = { name: part, isFolder: true, children: [], isOpen: true };
          currentLevel.push(existing);
        } else if (!existing.children) {
          existing.isFolder = true;
          existing.children = [];
          existing.isOpen = true;
        }
        currentLevel = existing.children;
      }
    });
  });
  
  return root.children;
};

const ChunkTreeNode = ({ node, level }) => {
  const [isOpen, setIsOpen] = useState(true);
  const paddingLeft = level * 16;
  const chunk = node.chunkData;
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div style={{ marginLeft: paddingLeft + 'px', marginBottom: node.isFolder ? '0' : '12px' }}>
      {(node.isFolder || hasChildren) && (
        <div 
          onClick={() => setIsOpen(!isOpen)}
          style={{ 
            display: 'flex', alignItems: 'center', gap: '8px', 
            padding: '8px 12px', cursor: 'pointer', color: 'var(--text-primary)',
            borderRadius: '8px', marginBottom: '8px', background: 'rgba(255,255,255,0.03)',
            border: '1px solid var(--border-light)'
          }}
        >
          {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <Folder size={16} style={{ color: 'var(--primary)' }} />
          <span style={{ fontSize: '14px', fontWeight: 600, fontFamily: 'monospace' }}>
            {node.name}
          </span>
        </div>
      )}

      {(!node.isFolder || isOpen) && (
        <div style={{ marginLeft: (node.isFolder || hasChildren) ? '24px' : '0px' }}>
          {node.isChunk && chunk && (
            <div style={{ 
              marginBottom: '12px', padding: '16px', background: 'rgba(255,255,255,0.02)',
              border: '1px solid var(--border-light)', borderRadius: '12px', fontSize: '13px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <FileText size={16} style={{ color: 'var(--primary)' }} />
                <h4 style={{ margin: 0, fontSize: '15px', color: 'var(--text-primary)' }}>{chunk.title}</h4>
              </div>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: '1.5' }}>{chunk.content}</p>
              
              {chunk.tags && chunk.tags.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
                  {chunk.tags.map((t, i) => <span key={i} className="badge badge-info" style={{ fontSize: '10px', padding: '4px 8px' }}>{t}</span>)}
                </div>
              )}
              
              {chunk.synthetic_questions && chunk.synthetic_questions.length > 0 && (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: '6px' }}>
                  <strong style={{ color: 'var(--secondary)' }}>Q:</strong> {chunk.synthetic_questions[0]}
                </div>
              )}
            </div>
          )}

          {hasChildren && node.children.map((child, i) => (
            <ChunkTreeNode key={i} node={child} level={0} />
          ))}
        </div>
      )}
    </div>
  );
};

export default function App() {
  // --- localStorage helpers ---
  const loadState = (key, fallback) => {
    try {
      const saved = localStorage.getItem(`dt_${key}`);
      return saved !== null ? JSON.parse(saved) : fallback;
    } catch { return fallback; }
  };
  const saveState = (key, value) => {
    try { localStorage.setItem(`dt_${key}`, JSON.stringify(value)); } catch {}
  };

  const [activeTab, setActiveTab] = useState(() => {
    // 1. First check URL path
    const path = window.location.pathname.replace('/', '').toLowerCase();
    const routeMap = {
      'workflow': 'workflow',
      'onboarding': 'onboarding',
      'rag-ingestion': 'rag',
      'obsidian-mapping': 'obsidian',
      'pre-consult': 'pre-consult'
    };
    if (routeMap[path]) return routeMap[path];
    
    // 2. Fallback to localStorage or default
    return loadState('activeTab', 'workflow');
  });

  // Sync activeTab to URL and localStorage
  useEffect(() => {
    const tabToRoute = {
      'workflow': 'workflow',
      'onboarding': 'onboarding',
      'rag': 'rag-ingestion',
      'obsidian': 'obsidian-mapping',
      'pre-consult': 'pre-consult'
    };
    const newPath = `/${tabToRoute[activeTab] || 'workflow'}`;
    if (window.location.pathname !== newPath) {
      window.history.pushState({ tab: activeTab }, '', newPath);
    }
    saveState('activeTab', activeTab);
  }, [activeTab]);

  // Handle browser back/forward buttons
  useEffect(() => {
    const handlePopState = (e) => {
      if (e.state && e.state.tab) {
        setActiveTab(e.state.tab);
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);
  
  // --- Global State ---
  const [configId, setConfigId] = useState(() => loadState('configId', '11111111-1111-1111-1111-111111111111'));
  const [activeVersion, setActiveVersion] = useState(() => loadState('activeVersion', '1.0.0'));
  const [isFeasible, setIsFeasible] = useState(() => loadState('isFeasible', true));
  const [validationErrors, setValidationErrors] = useState(() => loadState('validationErrors', []));
  const [apiStatus, setApiStatus] = useState('offline'); // always re-probe on load

  // --- Workflow Configurator State ---
  const [steps, setSteps] = useState(() => loadState('steps', [
    { id: "step_1", name: "Intake", inputs: [], outputs: ["symptoms", "temperature"], dependencies: [] },
    { id: "step_2", name: "Diagnosis Gate", inputs: ["symptoms", "temperature"], outputs: ["is_severe", "diagnosis_summary"], dependencies: ["step_1"] },
    { id: "step_3", name: "Action Escalator", inputs: ["is_severe", "diagnosis_summary"], outputs: ["escalation_done"], dependencies: ["step_2"] }
  ]));
  const [autopilot, setAutopilot] = useState(() => loadState('autopilot', true));
  const [newStep, setNewStep] = useState({ name: '', inputs: '', outputs: '', dependencies: '' });

  // --- Onboarding Journalist State ---
  const [transcript, setTranscript] = useState(() => loadState('transcript',
    "Dr. Sterling: Initial intake gathers vitals including blood pressure and temperature. " +
    "Then, we evaluate if patient complains of chest tightness. " +
    "If temperature is >= 103, we escalate to emergency. " +
    "Action plans involve scheduling immediate checkups or dispatching medical alerts."
  ));
  const [saturationScore, setSaturationScore] = useState(() => loadState('saturationScore', 0.45));
  const [isSaturationSatisfied, setIsSaturationSatisfied] = useState(() => loadState('isSaturationSatisfied', false));
  const [nextPrompt, setNextPrompt] = useState(() => loadState('nextPrompt', "Explain how you evaluate blood pressure limits?"));
  const [chatLog, setChatLog] = useState(() => loadState('chatLog', [
    { sender: 'journalist', text: "Welcome Dr. Sterling. Please explain your standard clinical intake routine?" },
    { sender: 'expert', text: "Dr. Sterling: Initial intake gathers vitals including blood pressure and temperature. Then, we evaluate if patient complains of chest tightness." }
  ]));
  const [chatInput, setChatInput] = useState('');
  const [cotNodes, setCotNodes] = useState(() => loadState('cotNodes', []));
  const [cotEdges, setCotEdges] = useState(() => loadState('cotEdges', []));

  // --- Ingestion State ---
  const [rawText, setRawText] = useState(() => loadState('rawText',
    "# Clinical Triage Guidelines\n\n" +
    "This document covers the cardiac intake and evaluation procedures.\n\n" +
    "## Intake Protocol\n\n" +
    "Collect patient complains and vitals. Core variables include temperature and chest tightness. Vitals must be checked immediately.\n\n" +
    "## Evaluation Standards\n\n" +
    "Assess results. If temperature exceeds 103, trigger emergency alarms. If chest pain is checked, halt immediately.\n\n" +
    "## Treatment Action\n\n" +
    "Escalate critical cases to physicians or schedule routine followups."
  ));
  const [ingestedChunks, setIngestedChunks] = useState(() => loadState('ingestedChunks', []));
  const [ingesting, setIngesting] = useState(false);

  // --- Obsidian & Unlearning State ---
  const [obsidianFiles, setObsidianFiles] = useState(() => loadState('obsidianFiles', []));
  const [selectedObsidianFile, setSelectedObsidianFile] = useState(() => loadState('selectedObsidianFile', null));
  const [unlearnNodeInput, setUnlearnNodeInput] = useState(() => loadState('unlearnNodeInput', ''));
  const [unlearnRationale, setUnlearnRationale] = useState(() => loadState('unlearnRationale', 'Guidelines changed due to updated AHA recommendations.'));
  const [unlearnStep, setUnlearnStep] = useState(0); // 0 = default, 1 = confirm 1, 2 = confirm 2, 3 = confirm 3
  const [unlearnTargetNode, setUnlearnTargetNode] = useState(null);

  // --- Query Sandbox State ---
  const [sessionId, setSessionId] = useState(() => loadState('sessionId', null));
  const [userQuery, setUserQuery] = useState(() => loadState('userQuery', "My temperature is 104 and my chest feels tight"));
  const [sandboxLog, setSandboxLog] = useState(() => loadState('sandboxLog', []));
  const [activeSessionState, setActiveSessionState] = useState(() => loadState('activeSessionState', null));
  const [loadingSandbox, setLoadingSandbox] = useState(false);

  // --- Persist state to localStorage on change ---
  useEffect(() => {
    saveState('activeTab', activeTab);
    saveState('configId', configId);
    saveState('activeVersion', activeVersion);
    saveState('isFeasible', isFeasible);
    saveState('validationErrors', validationErrors);
    saveState('steps', steps);
    saveState('autopilot', autopilot);
    saveState('transcript', transcript);
    saveState('saturationScore', saturationScore);
    saveState('isSaturationSatisfied', isSaturationSatisfied);
    saveState('nextPrompt', nextPrompt);
    saveState('chatLog', chatLog);
    saveState('cotNodes', cotNodes);
    saveState('cotEdges', cotEdges);
    saveState('rawText', rawText);
    saveState('ingestedChunks', ingestedChunks);
    saveState('obsidianFiles', obsidianFiles);
    saveState('selectedObsidianFile', selectedObsidianFile);
    saveState('unlearnNodeInput', unlearnNodeInput);
    saveState('unlearnRationale', unlearnRationale);
    saveState('sessionId', sessionId);
    saveState('userQuery', userQuery);
    saveState('sandboxLog', sandboxLog);
    saveState('activeSessionState', activeSessionState);
  }, [activeTab, configId, activeVersion, isFeasible, validationErrors, steps, autopilot,
      transcript, saturationScore, isSaturationSatisfied, nextPrompt, chatLog, cotNodes, cotEdges,
      rawText, ingestedChunks, obsidianFiles, selectedObsidianFile, unlearnNodeInput, unlearnRationale,
      sessionId, userQuery, sandboxLog, activeSessionState]);

  // --- Probe Backend Status on Load ---
  useEffect(() => {
    checkBackend();
  }, []);

  const checkBackend = async () => {
    try {
      const res = await fetch("http://localhost:8000/");
      if (res.ok) {
        setApiStatus('online');
      } else {
        setApiStatus('offline');
      }
    } catch {
      setApiStatus('offline');
    }
  };

  // --- API Handlers ---
  const handleValidateConfig = async (currentSteps = steps) => {
    const payload = {
      workflow_config: { steps: currentSteps }
    };
    
    if (apiStatus === 'online') {
      try {
        const res = await fetch(`${API_BASE}/config/validate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        setIsFeasible(data.is_feasible);
        setValidationErrors(data.errors);
        return data;
      } catch (err) {
        console.error("Validation error", err);
      }
    }

    // Local Fallback validation check
    const errors = [];
    const stepIds = currentSteps.map(s => s.id);
    const resolvedVars = new Set();
    
    // Cycle check (simple sequential checking)
    let cycle = false;
    currentSteps.forEach(s => {
      s.dependencies.forEach(d => {
        if (!stepIds.includes(d)) {
          errors.push(`Validation Error: Step '${s.name}' depends on non-existent step ID '${d}'.`);
        }
      });
    });

    // Variable satisfaction
    currentSteps.forEach(s => {
      s.inputs.forEach(inp => {
        if (!resolvedVars.has(inp)) {
          errors.push(`Validation Error: Step '${s.name}' requires variable '${inp}' which has not been outputted yet.`);
        }
      });
      s.outputs.forEach(out => resolvedVars.add(out));
    });

    const feasible = errors.length === 0;
    setIsFeasible(feasible);
    setValidationErrors(errors);
    return { is_feasible: feasible, errors };
  };

  const handleSaveConfig = async () => {
    const payload = {
      config_id: configId,
      doctor_id: DOCTOR_ID,
      workflow_config: { steps, autopilot },
      active_version: activeVersion
    };

    if (apiStatus === 'online') {
      try {
        const res = await fetch(`${API_BASE}/config/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        setIsFeasible(data.is_feasible);
        setValidationErrors(data.errors);
        
        // Log to synced files
        setObsidianFiles(prev => [
          {
            path: `configs/config_${configId}.md`,
            type: 'config',
            node_id: crypto.randomUUID(),
            title: `Workflow Config ${activeVersion}`,
            content: `Configuration for Dr. Sterling.\nNodes: ${steps.length}`,
            tags: ["config", "workflow"]
          },
          ...prev.filter(f => !f.path.includes(configId))
        ]);
        alert("Configuration saved & exported to Obsidian Vault!");
        return;
      } catch (err) {
        console.error("Save config error", err);
      }
    }

    // Mock response
    const check = await handleValidateConfig();
    setObsidianFiles(prev => [{
      path: `configs/config_${configId}.md`,
      type: 'config',
      node_id: crypto.randomUUID(),
      title: `Workflow Config ${activeVersion}`,
      content: `Configuration for Dr. Sterling.\nNodes: ${steps.length}`,
      tags: ["config", "workflow"]
    }, ...prev.filter(f => !f.path.includes(configId))]);
    alert(`[MOCK DB] Config saved! Feasibility: ${check.is_feasible ? 'SUCCESS' : 'FAILED'}`);
  };

  const handleSendChat = async () => {
    if (!chatInput.trim()) return;
    const newTranscript = transcript + "\nDr. Sterling: " + chatInput;
    setTranscript(newTranscript);
    
    const userMsg = { sender: 'expert', text: chatInput };
    setChatLog(prev => [...prev, userMsg]);
    setChatInput('');

    if (apiStatus === 'online') {
      try {
        const res = await fetch(`${API_BASE}/onboarding/interview`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ transcript: newTranscript })
        });
        const data = await res.json();
        setSaturationScore(data.saturation_score);
        setIsSaturationSatisfied(data.is_satisfied);
        setNextPrompt(data.next_prompt);
        setChatLog(prev => [...prev, { sender: 'journalist', text: data.next_prompt }]);
        return;
      } catch (err) {
        console.error("Chat interview error", err);
      }
    }

    // Local Fallback simulation
    const nextSaturation = Math.min(1.0, saturationScore + 0.15);
    setSaturationScore(nextSaturation);
    const satisfied = nextSaturation >= 0.90;
    setIsSaturationSatisfied(satisfied);
    const prompts = [
      "Can you describe what vital metrics triggers physician notification?",
      "Excellent. Tell me about standard dosage recommendations for minor cases?",
      "Onboarding saturation complete. Graph structure is ready to compile."
    ];
    const next = satisfied ? prompts[2] : prompts[Math.floor(Math.random() * 2)];
    setNextPrompt(next);
    setChatLog(prev => [...prev, { sender: 'journalist', text: next }]);
  };

  const handleFinalizeOnboarding = async () => {
    if (apiStatus === 'online') {
      try {
        const res = await fetch(`${API_BASE}/onboarding/finalize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ config_id: configId, transcript })
        });
        const data = await res.json();
        alert(`Onboarding finalized! Nodes: ${data.nodes_count}, Edges: ${data.edges_count}`);
        
        // Load files list
        const cotFiles = [
          { path: "cot_nodes/node_intake.md", type: "cot", node_id: crypto.randomUUID(), title: "Intake CoT", content: "Collect vitals...", tags: ["onboarding"] },
          { path: "cot_nodes/node_evaluation.md", type: "cot", node_id: crypto.randomUUID(), title: "Evaluation CoT", content: "Check parameters...", tags: ["onboarding"] },
          { path: "cot_nodes/node_action.md", type: "cot", node_id: crypto.randomUUID(), title: "Action CoT", content: "Trigger escalation...", tags: ["onboarding"] }
        ];
        setObsidianFiles(prev => [...cotFiles, ...prev]);
        return;
      } catch (err) {
        alert("Failed to finalize: Saturation score must be >= 0.90");
        return;
      }
    }

    // Mock onboarding nodes
    const cotFiles = [
      { path: "cot_nodes/node_intake.md", type: "cot", node_id: crypto.randomUUID(), title: "Intake CoT", content: "Collect vitals...", tags: ["onboarding"] },
      { path: "cot_nodes/node_evaluation.md", type: "cot", node_id: crypto.randomUUID(), title: "Evaluation CoT", content: "Check parameters...", tags: ["onboarding"] },
      { path: "cot_nodes/node_action.md", type: "cot", node_id: crypto.randomUUID(), title: "Action CoT", content: "Trigger escalation...", tags: ["onboarding"] }
    ];
    setObsidianFiles(prev => [...cotFiles, ...prev]);
    alert("[MOCK ONBOARDING] CoT nodes and edges written to database and Obsidian Vault!");
  };

  const handleIngest = async () => {
    setIngesting(true);
    if (apiStatus === 'online') {
      try {
        const res = await fetch(`${API_BASE}/config/ingest`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ config_id: configId, raw_text: rawText })
        });
        const data = await res.json();
        
        if (!res.ok) {
          console.error("Server error:", data.detail || data);
          alert("Ingestion failed: " + (data.detail || "Server Error"));
          setIngesting(false);
          return;
        }

        setIngestedChunks(data.chunks);
        
        const newFiles = data.chunks.map(c => ({
          path: `knowledge/${c.current_path || c.title.toLowerCase().replace(/\s+/g, '_')}.md`,
          type: 'knowledge',
          node_id: c.chunk_id || crypto.randomUUID(),
          parent_id: c.parent_path || "",
          title: c.title,
          content: c.content,
          tags: c.tags || [],
          chain_of_thought: (c.synthetic_questions && c.synthetic_questions.length > 0) ? c.synthetic_questions[0] : "",
          quarantine_status: false,
          unlearning_rationale: ""
        }));
        
        setObsidianFiles(prev => {
          const filtered = prev.filter(f => !f.path.startsWith('knowledge/'));
          return [...newFiles, ...filtered];
        });

        setIngesting(false);
        return;
      } catch (err) {
        console.error("Ingestion failed", err);
        alert("Failed to connect to backend for ingestion.");
        setIngesting(false);
      }
    }

    // Mock Parser Stage A & B
    setTimeout(() => {
      const parsed = [
        { title: "Overview", content: "Cardiac intake and evaluation procedures.", parent_path: "overview", tags: ["cardiac"], synthetic_questions: ["What does this cover?"] },
        { title: "Intake Protocol", content: "Collect symptoms and vitals (temp, chest tightness).", parent_path: "overview.intake", tags: ["vitals", "intake"], synthetic_questions: ["What metrics are collected?"] },
        { title: "Evaluation Standards", content: "If temp > 103, alert emergency. If chest pain, halt.", parent_path: "overview.evaluation", tags: ["evaluation", "anomaly"], synthetic_questions: ["What triggers emergency?"] },
        { title: "Treatment Action", content: "Schedule routine checks or trigger dispatcher.", parent_path: "overview.action", tags: ["treatment", "dispatcher"], synthetic_questions: ["What is the final action?"] }
      ];
      setIngestedChunks(parsed);
      setIngesting(false);
      alert("[MOCK RAG] Document ingested, split, enriched, and stored in vector DB!");
    }, 1000);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIngesting(true);
    const formData = new FormData();
    formData.append('config_id', configId);
    formData.append('file', file);

    if (apiStatus === 'online') {
      try {
        const res = await fetch(`${API_BASE}/config/upload`, {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        
        if (!res.ok) {
          console.error("Upload error:", data.detail || data);
          alert("Upload failed: " + (data.detail || "Server Error"));
          setIngesting(false);
          return;
        }

        setIngestedChunks(data.chunks);
        if (data.raw_text) {
          setRawText(data.raw_text);
        }
        
        const newFiles = data.chunks.map(c => ({
          path: `knowledge/${c.current_path || c.title.toLowerCase().replace(/\s+/g, '_')}.md`,
          type: 'knowledge',
          node_id: c.chunk_id || crypto.randomUUID(),
          parent_id: c.parent_path || "",
          title: c.title,
          content: c.content,
          tags: c.tags || [],
          chain_of_thought: (c.synthetic_questions && c.synthetic_questions.length > 0) ? c.synthetic_questions[0] : "",
          quarantine_status: false,
          unlearning_rationale: ""
        }));
        
        setObsidianFiles(prev => {
          const filtered = prev.filter(f => !f.path.startsWith('knowledge/'));
          return [...newFiles, ...filtered];
        });

        setIngesting(false);
        return;
      } catch (err) {
        console.error("Upload failed", err);
        alert("Failed to connect to backend for upload.");
        setIngesting(false);
      }
    } else {
       alert("API Offline. Mock mode only supports manual text pasting.");
       setIngesting(false);
    }
  };

  const handleStartUnlearn = () => {
    if (!unlearnNodeInput.trim()) return;
    const targetNode = obsidianFiles.find(f => f.node_id === unlearnNodeInput || f.path.includes(unlearnNodeInput));
    if (!targetNode) {
      setUnlearnStep(-1); // -1 for error
      return;
    }
    setUnlearnTargetNode(targetNode);
    setUnlearnStep(1);
  };

  const handleConfirmStep = () => {
    if (unlearnStep < 3) {
      setUnlearnStep(prev => prev + 1);
    } else {
      executeUnlearn();
    }
  };

  const handleCancelUnlearn = () => {
    setUnlearnStep(0);
    setUnlearnTargetNode(null);
  };

  const executeUnlearn = async () => {
    const payload = {
      node_ids: [unlearnNodeInput],
      rationale: unlearnRationale
    };
    
    const updateLocalState = () => {
      // Completely remove the node from the graphical tree dynamically
      setObsidianFiles(prev => prev.filter(f => f.node_id !== unlearnNodeInput && !f.path.includes(unlearnNodeInput)));
      if (selectedObsidianFile && (selectedObsidianFile.node_id === unlearnNodeInput || selectedObsidianFile.path.includes(unlearnNodeInput))) {
        setSelectedObsidianFile(null);
      }
      setUnlearnNodeInput('');
      setUnlearnStep(4); // 4 for success
      setTimeout(() => setUnlearnStep(0), 3000);
    };

    if (apiStatus === 'online') {
      try {
        const res = await fetch(`${API_BASE}/config/${configId}/unlearn`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        await res.json();
        updateLocalState();
      } catch (err) {
        console.error(err);
        setUnlearnStep(-2); // -2 for backend error
        setTimeout(() => setUnlearnStep(0), 3000);
      }
    } else {
      updateLocalState();
    }
  };

  // --- Runtime Query sandbox ---
  const handleInitiateSession = async () => {
    const cid = configId || uuid4();
    if (apiStatus === 'online') {
      try {
        const res = await fetch(`${API_BASE}/session/initiate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ conversation_id: uuid4(), config_id: cid })
        });
        const data = await res.json();
        setSessionId(data.session_id);
        setActiveSessionState(data);
        setSandboxLog([{ node: 'init', msg: 'Session initialized. Ready for user query.' }]);
        return;
      } catch (err) {
        console.error(err);
      }
    }

    // Mock init
    const sid = "f39d89b1-e28a-4934-8da8-bc389a9f24e9";
    setSessionId(sid);
    setActiveSessionState({
      session_id: sid,
      current_node: "start",
      is_paused: false,
      requires_review: false,
      gathered_data: {}
    });
    setSandboxLog([{ node: 'init', msg: 'Session initialized. Ready for user query.' }]);
  };

  const handleRunQuery = async () => {
    if (!sessionId) {
      alert("Please initiate session first!");
      return;
    }
    setLoadingSandbox(true);

    if (apiStatus === 'online') {
      try {
        const res = await fetch(`${API_BASE}/session/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId, query: userQuery })
        });
        const data = await res.json();
        setActiveSessionState(data);
        setSandboxLog(prev => [
          ...prev, 
          { node: data.current_node, msg: `User: "${userQuery}" -> Twin: "${data.output_message}"` }
        ]);
        setLoadingSandbox(false);
        return;
      } catch (err) {
        console.error(err);
        setLoadingSandbox(false);
      }
    }

    // Mock LangGraph Execution Flow
    setTimeout(() => {
      const q = userQuery.toLowerCase();
      let nextNode = "data_gathering";
      let msg = "";
      let paused = false;
      let review = false;
      let extracted = {};

      if (q.includes("temp") || q.includes("temperature")) {
        extracted = { ...activeSessionState.gathered_data, temperature: 104.0 };
      }
      if (q.includes("chest") || q.includes("pain") || q.includes("tight")) {
        extracted = { ...extracted, chest_pain: true };
      }

      if (extracted.temperature >= 103.0 || extracted.chest_pain) {
        nextNode = "human_intercept";
        paused = true;
        review = true;
        msg = "CRITICAL HUMAN INTERCEPT: Severe symptoms detected (extreme fever / cardiac tightness). Circuit breaker triggered. Twin frozen.";
      } else {
        nextNode = "action_dispatch";
        msg = "Clinical guidelines verified. Vitals stable. Action dispatched: scheduling routine follow-up.";
      }

      const updated = {
        ...activeSessionState,
        current_node: nextNode,
        is_paused: paused,
        requires_review: review,
        gathered_data: extracted,
        output_message: msg
      };

      setActiveSessionState(updated);
      setSandboxLog(prev => [
        ...prev,
        { node: nextNode, msg: `User: "${userQuery}" -> Twin: "${msg}"` }
      ]);
      setLoadingSandbox(false);
    }, 1200);
  };

  // --- Dynamic Layout UI Helpers ---
  const addWorkflowStep = () => {
    if (!newStep.name) return;
    const inputs = newStep.inputs.split(',').map(x => x.trim()).filter(Boolean);
    const outputs = newStep.outputs.split(',').map(x => x.trim()).filter(Boolean);
    const deps = newStep.dependencies.split(',').map(x => x.trim()).filter(Boolean);
    const sid = `step_${uuid4().slice(0,4)}`;
    
    const updated = [...steps, { id: sid, name: newStep.name, inputs, outputs, dependencies: deps }];
    setSteps(updated);
    setNewStep({ name: '', inputs: '', outputs: '', dependencies: '' });
    handleValidateConfig(updated);
  };

  const deleteStep = (id) => {
    const updated = steps.filter(s => s.id !== id);
    setSteps(updated);
    handleValidateConfig(updated);
  };

  const generateMarkdown = (file) => {
    if (!file) return "";
    return `---
node_id: "${file.node_id}"
parent_id: "${file.parent_id || 'root'}"
sync_status: "verified"
chain_of_thought: |
  "${file.chain_of_thought || ''}"
tags: [${(file.tags || []).join(', ')}]
quarantine_status: ${file.quarantine_status || false}
${file.quarantine_status ? `unlearning_rationale: "${file.unlearning_rationale}"\ndeprecated_at: "${new Date().toISOString()}"\n` : ''}---

# ${file.title || 'Untitled Node'}
${file.content || ''}
`;
  };

  return (
    <div className="app-container">
      {/* LEFT SIDEBAR */}
      <aside className="sidebar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '32px' }}>
          <Activity size={24} style={{ color: 'var(--secondary)' }} className="animate-pulse-slow" />
          <h2 style={{ fontSize: '20px', fontFamily: 'var(--font-display)', fontWeight: 800 }}>
            AGENTIC TWIN
          </h2>
        </div>

        <div className="glass-card" style={{ padding: '16px', marginBottom: '24px', fontSize: '13px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <span style={{ height: '8px', width: '8px', borderRadius: '50%', backgroundColor: apiStatus === 'online' ? 'var(--success)' : 'var(--warning)' }}></span>
            <span style={{ fontWeight: 600 }}>API Endpoint: {apiStatus.toUpperCase()}</span>
          </div>
          <p style={{ color: 'var(--text-muted)' }}>Active Config: {configId.slice(0, 8)}...</p>
        </div>

        <nav style={{ flex: 1 }}>
          <button 
            className={`nav-link w-full ${activeTab === 'workflow' ? 'active' : ''}`}
            onClick={() => setActiveTab('workflow')}
          >
            <Layers size={18} />
            <span>Workflow Config</span>
          </button>
          
          <button 
            className={`nav-link w-full ${activeTab === 'onboarding' ? 'active' : ''}`}
            onClick={() => setActiveTab('onboarding')}
          >
            <UserCheck size={18} />
            <span>Onboarding Expert</span>
          </button>

          <button 
            className={`nav-link w-full ${activeTab === 'ingestion' ? 'active' : ''}`}
            onClick={() => setActiveTab('ingestion')}
          >
            <FileText size={18} />
            <span>RAG Ingestion Hub</span>
          </button>

          <button 
            className={`nav-link w-full ${activeTab === 'obsidian' ? 'active' : ''}`}
            onClick={() => setActiveTab('obsidian')}
          >
            <FolderOpen size={18} />
            <span>Obsidian Mapping</span>
          </button>

          <button 
            className={`nav-link w-full ${activeTab === 'pre-consult' ? 'active' : ''}`}
            onClick={() => setActiveTab('pre-consult')}
          >
            <ShieldAlert size={18} />
            <span>Pre-Consultation</span>
          </button>
        </nav>

        <div style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center' }}>
          Digital Twin Engine v1.0.0
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="main-content">
        <h1 style={{ fontSize: '32px', fontFamily: 'var(--font-display)', marginBottom: '32px' }}>
          Expert Proxy Control Plane
        </h1>

        {/* WORKFLOW BUILDER TAB */}
        {activeTab === 'workflow' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Feasibility State Banner */}
            <div className="glass-card" style={{ 
              borderColor: isFeasible ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)',
              background: isFeasible ? 'rgba(16,185,129,0.05)' : 'rgba(239,68,68,0.05)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyItems: 'center', gap: '12px' }}>
                {isFeasible ? (
                  <CheckCircle2 size={24} style={{ color: 'var(--success)' }} />
                ) : (
                  <AlertTriangle size={24} style={{ color: 'var(--error)' }} />
                )}
                <div>
                  <h3 style={{ fontSize: '18px', fontWeight: 600 }}>
                    Feasibility Compiler Check: {isFeasible ? 'VALID GRAPH' : 'INVALID COMPILATION'}
                  </h3>
                  {isFeasible ? (
                    <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                      All variable propagation sequences satisfied. No circular dependencies found.
                    </p>
                  ) : (
                    <ul style={{ color: 'var(--error)', fontSize: '13px', marginTop: '6px', paddingLeft: '20px' }}>
                      {validationErrors.map((err, i) => <li key={i}>{err}</li>)}
                    </ul>
                  )}
                </div>
              </div>
            </div>

            {/* Config Builder Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px' }}>
              <div className="glass-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
                  <h3 style={{ fontSize: '18px' }}>Workflow Steps Layout</h3>
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Auto-pilot</label>
                    <input 
                      type="checkbox" 
                      checked={autopilot} 
                      onChange={() => setAutopilot(!autopilot)} 
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {steps.map((step, idx) => (
                    <div key={step.id} style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      padding: '16px',
                      background: 'rgba(255,255,255,0.02)',
                      border: '1px solid var(--border-light)',
                      borderRadius: '8px'
                    }}>
                      <div>
                        <h4 style={{ fontWeight: 600 }}>{idx + 1}. {step.name}</h4>
                        <div style={{ display: 'flex', gap: '16px', fontSize: '12px', marginTop: '6px', color: 'var(--text-secondary)' }}>
                          <span><strong>Inputs:</strong> {step.inputs.join(', ') || 'None'}</span>
                          <span><strong>Outputs:</strong> {step.outputs.join(', ') || 'None'}</span>
                          <span><strong>Depends:</strong> {step.dependencies.join(', ') || 'None'}</span>
                        </div>
                      </div>
                      <button 
                        onClick={() => deleteStep(step.id)}
                        style={{ background: 'transparent', border: 'none', color: 'var(--error)', cursor: 'pointer' }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Add step Panel */}
              <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h3 style={{ fontSize: '18px' }}>Add Step</h3>
                <div className="input-group">
                  <span className="input-label">Step Name</span>
                  <input 
                    className="form-input" 
                    placeholder="e.g. Dose Check" 
                    value={newStep.name} 
                    onChange={e => setNewStep({...newStep, name: e.target.value})}
                  />
                </div>
                <div className="input-group">
                  <span className="input-label">Inputs (comma separated)</span>
                  <input 
                    className="form-input" 
                    placeholder="e.g. diagnosis_summary" 
                    value={newStep.inputs} 
                    onChange={e => setNewStep({...newStep, inputs: e.target.value})}
                  />
                </div>
                <div className="input-group">
                  <span className="input-label">Outputs (comma separated)</span>
                  <input 
                    className="form-input" 
                    placeholder="e.g. final_dose" 
                    value={newStep.outputs} 
                    onChange={e => setNewStep({...newStep, outputs: e.target.value})}
                  />
                </div>
                <div className="input-group">
                  <span className="input-label">Dependencies (step IDs)</span>
                  <input 
                    className="form-input" 
                    placeholder="e.g. step_2" 
                    value={newStep.dependencies} 
                    onChange={e => setNewStep({...newStep, dependencies: e.target.value})}
                  />
                </div>
                <button className="btn btn-primary" onClick={addWorkflowStep}>
                  Add Step
                </button>
                <button className="btn btn-accent" onClick={handleSaveConfig} style={{ marginTop: '12px' }}>
                  Save Config & Compile
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ONBOARDING JOURNALIST TAB */}
        {activeTab === 'onboarding' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px' }}>
            <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '520px' }}>
              <h3 style={{ fontSize: '18px', marginBottom: '16px' }}>Journalist Interview Terminal</h3>
              
              {/* Chat display */}
              <div style={{ flex: 1, overflowY: 'auto', border: '1px solid var(--border-light)', borderRadius: '8px', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px', background: 'rgba(0,0,0,0.2)' }}>
                {chatLog.map((c, i) => (
                  <div key={i} style={{ 
                    alignSelf: c.sender === 'journalist' ? 'flex-start' : 'flex-end',
                    background: c.sender === 'journalist' ? 'var(--bg-tertiary)' : 'var(--primary)',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    maxWidth: '80%',
                    fontSize: '14px'
                  }}>
                    <strong style={{ display: 'block', fontSize: '11px', opacity: 0.8, marginBottom: '2px' }}>
                      {c.sender === 'journalist' ? 'AI Journalist' : 'Dr. Avery Sterling'}
                    </strong>
                    {c.text}
                  </div>
                ))}
              </div>

              {/* Chat Input */}
              <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                <input 
                  className="form-input" 
                  style={{ flex: 1 }}
                  placeholder="Answer the question to train your twin..."
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSendChat()}
                />
                <button className="btn btn-primary" onClick={handleSendChat}>
                  <Send size={16} />
                </button>
              </div>
            </div>

            {/* Saturation Side Panel */}
            <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyItems: 'space-between', gap: '24px' }}>
              <div>
                <h3 style={{ fontSize: '18px', marginBottom: '16px' }}>Knowledge Saturation</h3>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', marginBottom: '8px' }}>
                  <span>Expert Saturation:</span>
                  <span style={{ fontWeight: 700 }}>{(saturationScore * 100).toFixed(0)}%</span>
                </div>
                
                {/* Progress bar */}
                <div style={{ height: '12px', width: '100%', background: 'var(--bg-tertiary)', borderRadius: '6px', overflow: 'hidden', marginBottom: '12px' }}>
                  <div style={{ 
                    height: '100%', 
                    width: `${saturationScore * 100}%`, 
                    background: 'linear-gradient(90deg, var(--primary), var(--secondary))',
                    transition: 'width 0.4s ease'
                  }}></div>
                </div>
                
                <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Target Saturation limit is <strong>90%</strong> to ensure zero-hallucination epistemic fencing bounds are complete.
                </p>
              </div>

              <div>
                <button 
                  className={`btn w-full ${isSaturationSatisfied ? 'btn-primary' : 'btn-secondary'}`}
                  disabled={!isSaturationSatisfied}
                  onClick={handleFinalizeOnboarding}
                >
                  Finalize CoT Graph
                </button>
              </div>
            </div>
          </div>
        )}

        {/* INGESTION HUB TAB */}
        {activeTab === 'ingestion' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px' }}>
            <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <h3 style={{ fontSize: '18px' }}>Ingestion Console</h3>
              
              {/* Drag and Drop Zone */}
              <div 
                className="upload-zone"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    handleFileUpload({ target: { files: [e.dataTransfer.files[0]] } });
                  }
                }}
              >
                <FolderOpen size={32} style={{ color: 'var(--primary)', marginBottom: '12px' }} />
                <h4 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '4px' }}>Drag & Drop clinical guidelines here</h4>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>Supports PDF, TXT, MD</p>
                
                <label className="btn btn-secondary" style={{ cursor: 'pointer' }}>
                  Browse Files
                  <input type="file" accept=".pdf,.txt,.md" style={{ display: 'none' }} onChange={handleFileUpload} disabled={ingesting} />
                </label>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', margin: '4px 0' }}>
                <div style={{ flex: 1, height: '1px', background: 'var(--border-light)' }}></div>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>OR PASTE TEXT</span>
                <div style={{ flex: 1, height: '1px', background: 'var(--border-light)' }}></div>
              </div>

              <textarea 
                className="form-input"
                style={{ flex: 1, minHeight: '180px', fontFamily: 'monospace', fontSize: '13px', resize: 'vertical' }}
                value={rawText}
                onChange={e => setRawText(e.target.value)}
              />
              <button className="btn btn-primary" onClick={handleIngest} disabled={ingesting}>
                {ingesting ? (
                  <>
                    <RefreshCw size={16} className="animate-spin-fast" />
                    Ingesting & Generating Vectors...
                  </>
                ) : (
                  "Run Parser Pipeline"
                )}
              </button>
            </div>

            {/* Ingested output preview */}
            <div className="glass-card" style={{ overflowY: 'auto', maxHeight: '520px' }}>
              <h3 style={{ fontSize: '18px', marginBottom: '16px' }}>Extracted Nodes</h3>
              {ingestedChunks.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 0' }}>
                  No guidelines ingested yet.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  {buildChunkTree(ingestedChunks).map((node, idx) => (
                    <ChunkTreeNode key={idx} node={node} level={0} />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* OBSIDIAN AUDIT MAPPING TAB */}
        {activeTab === 'obsidian' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 400px', gap: '24px' }}>
            {/* Graphical Tree View */}
            <div className="glass-card" style={{ padding: '0', overflow: 'hidden' }}>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-light)', background: 'rgba(0,0,0,0.15)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Sparkles size={18} style={{ color: 'var(--secondary)' }} />
                <h3 style={{ fontSize: '16px', margin: 0, fontWeight: 600 }}>Knowledge Graph</h3>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: 'auto' }}>
                  {obsidianFiles.length} node{obsidianFiles.length !== 1 ? 's' : ''}
                </span>
              </div>
              <GraphicalTreeView
                files={obsidianFiles}
                selectedFile={selectedObsidianFile}
                onSelect={(file) => setSelectedObsidianFile(file)}
                onUnlearnSelect={(id) => setUnlearnNodeInput(id)}
              />
            </div>

            {/* Right Column: Markdown Preview + Retract Knowledge stacked */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {/* Markdown Viewer */}
              <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', padding: '0', overflow: 'hidden', flex: 1, minHeight: '320px' }}>
                <div style={{ padding: '16px', borderBottom: '1px solid var(--border-light)', background: 'rgba(0,0,0,0.2)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Eye size={16} style={{ color: 'var(--primary)' }} />
                  <h3 style={{ fontSize: '14px', margin: 0, fontFamily: 'monospace' }}>
                    {selectedObsidianFile ? selectedObsidianFile.path : 'Select a node'}
                  </h3>
                </div>
                <div style={{ 
                  flex: 1, 
                  padding: '20px', 
                  overflowY: 'auto', 
                  fontFamily: 'monospace', 
                  fontSize: '13px', 
                  lineHeight: '1.6',
                  background: selectedObsidianFile?.quarantine_status ? 'rgba(255,50,50,0.02)' : 'transparent'
                }}>
                  {selectedObsidianFile ? (
                    <pre style={{ whiteSpace: 'pre-wrap', margin: 0, wordWrap: 'break-word' }}>
                      <span style={{ color: 'var(--text-muted)' }}>
                        {(() => {
                          const md = generateMarkdown(selectedObsidianFile);
                          const parts = md.split('\n---');
                          return parts[0] + '\n---';
                        })()}
                      </span>
                      <span style={{ color: 'var(--text-primary)' }}>
                        {(() => {
                          const md = generateMarkdown(selectedObsidianFile);
                          const parts = md.split('\n---');
                          return parts.slice(1).join('\n---');
                        })()}
                      </span>
                    </pre>
                  ) : (
                    <div style={{ color: 'var(--text-muted)', display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', textAlign: 'center', fontSize: '13px' }}>
                      Click a node in the Knowledge Graph to view its projected SSOT state.
                    </div>
                  )}
                </div>
              </div>

              {/* Mom-Child Unlearning panel */}
              <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h3 style={{ fontSize: '18px', color: 'var(--error)' }}>Retract Knowledge</h3>
                
                {unlearnStep === 0 && (
                  <>
                    <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      Mom-and-Child Unlearning Protocol: Nullifies embedding vector in the SSOT database to disable semantic retrieve paths, while keeping YAML audit logs intact.
                    </p>
                    <div className="input-group">
                      <span className="input-label">Target Node ID</span>
                      <input 
                        className="form-input" 
                        placeholder="UUID" 
                        value={unlearnNodeInput}
                        onChange={e => setUnlearnNodeInput(e.target.value)}
                      />
                    </div>
                    <div className="input-group">
                      <span className="input-label">Retraction Rationale</span>
                      <textarea 
                        className="form-input" 
                        style={{ minHeight: '80px' }}
                        value={unlearnRationale}
                        onChange={e => setUnlearnRationale(e.target.value)}
                      />
                    </div>
                    <button className="btn btn-primary" style={{ backgroundColor: 'var(--error)' }} onClick={handleStartUnlearn}>
                      Retract Node
                    </button>
                  </>
                )}

                {unlearnStep === -1 && (
                  <>
                    <p style={{ color: 'var(--error)' }}>Node not found in current graph. Please select a valid node.</p>
                    <button className="btn btn-secondary" onClick={handleCancelUnlearn}>Try Again</button>
                  </>
                )}

                {unlearnStep === -2 && (
                  <>
                    <p style={{ color: 'var(--error)' }}>Failed to connect to backend for unlearning.</p>
                    <button className="btn btn-secondary" onClick={handleCancelUnlearn}>Dismiss</button>
                  </>
                )}

                {unlearnStep === 4 && (
                  <>
                    <p style={{ color: 'var(--success)' }}>✔ Mom-and-Child Unlearning complete. Vector tombstoned and node removed from graph!</p>
                  </>
                )}

                {unlearnStep > 0 && unlearnStep < 4 && (
                  <div style={{ background: 'rgba(255,50,50,0.1)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,50,50,0.2)' }}>
                    <h4 style={{ color: 'var(--error)', marginBottom: '12px' }}>Confirmation Step {unlearnStep} of 3</h4>
                    
                    {unlearnStep === 1 && (
                      <p style={{ fontSize: '14px', marginBottom: '16px' }}>
                        Are you sure you want to retract this node? This action will remove it from the knowledge graph.
                      </p>
                    )}
                    
                    {unlearnStep === 2 && (
                      <p style={{ fontSize: '14px', marginBottom: '16px' }}>
                        WARNING: This node belongs to the <strong>'{unlearnTargetNode?.parent_path || 'Root'}'</strong> sub-tree. Retracting it may impact dependent knowledge pathways. Proceed?
                      </p>
                    )}
                    
                    {unlearnStep === 3 && (
                      <p style={{ fontSize: '14px', marginBottom: '16px', fontWeight: 'bold' }}>
                        FINAL CONFIRMATION: Are you absolutely certain you want to permanently tombstone this node's vector embedding?
                      </p>
                    )}

                    <div style={{ display: 'flex', gap: '12px' }}>
                      <button className="btn btn-primary" style={{ backgroundColor: 'var(--error)', flex: 1 }} onClick={handleConfirmStep}>
                        {unlearnStep === 3 ? "Yes, Tombstone Vector" : "Yes, Proceed"}
                      </button>
                      <button className="btn btn-secondary" style={{ flex: 1 }} onClick={handleCancelUnlearn}>
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* QUERY SANDBOX / TELEMETRY LEDGER */}
        <section className="glass-card" style={{ marginTop: '40px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ fontSize: '20px', fontFamily: 'var(--font-display)' }}>Runtime Simulation Sandbox</h3>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button className="btn btn-secondary" onClick={handleInitiateSession}>
                Initiate Session
              </button>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px' }}>
            {/* Input sandbox */}
            <div>
              <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
                <input 
                  className="form-input" 
                  style={{ flex: 1 }}
                  placeholder="Test a symptom query..."
                  value={userQuery}
                  onChange={e => setUserQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleRunQuery()}
                />
                <button className="btn btn-primary" onClick={handleRunQuery} disabled={loadingSandbox}>
                  {loadingSandbox ? (
                    <RefreshCw size={16} className="animate-spin-fast" />
                  ) : (
                    "Run Query"
                  )}
                </button>
              </div>

              {/* Logs */}
              <div style={{ 
                height: '180px', 
                overflowY: 'auto', 
                border: '1px solid var(--border-light)', 
                borderRadius: '8px', 
                padding: '12px', 
                background: 'rgba(0,0,0,0.3)',
                fontFamily: 'monospace',
                fontSize: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                {sandboxLog.length === 0 ? (
                  <span style={{ color: 'var(--text-muted)' }}>Console awaiting initialization...</span>
                ) : (
                  sandboxLog.map((log, i) => (
                    <div key={i}>
                      <span style={{ 
                        color: log.node === 'human_intercept' ? 'var(--error)' : 
                               log.node === 'action_dispatch' ? 'var(--success)' : 'var(--secondary)',
                        fontWeight: 700 
                      }}>[{log.node.toUpperCase()}]</span> {log.msg}
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Telemetry info */}
            <div style={{ display: 'flex', flexDirection: 'column', justifyItems: 'space-between', fontSize: '13px' }}>
              <div>
                <h4 style={{ fontWeight: 600, marginBottom: '12px' }}>Checkpointer State</h4>
                {activeSessionState ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div><strong>Session ID:</strong> {activeSessionState.session_id.slice(0, 8)}...</div>
                    <div><strong>Active Node:</strong> {activeSessionState.current_node}</div>
                    <div>
                      <strong>Requires Human:</strong> 
                      <span style={{ marginLeft: '6px', color: activeSessionState.requires_review ? 'var(--error)' : 'var(--success)', fontWeight: 600 }}>
                        {activeSessionState.requires_review ? 'YES' : 'NO'}
                      </span>
                    </div>
                    <div>
                      <strong>State Paused:</strong> 
                      <span style={{ marginLeft: '6px', color: activeSessionState.is_paused ? 'var(--error)' : 'var(--success)', fontWeight: 600 }}>
                        {activeSessionState.is_paused ? 'YES' : 'NO'}
                      </span>
                    </div>
                    <div>
                      <strong>Variables Gathered:</strong>
                      <pre style={{ fontSize: '11px', background: 'rgba(0,0,0,0.1)', padding: '6px', borderRadius: '4px', marginTop: '4px' }}>
                        {JSON.stringify(activeSessionState.gathered_data, null, 2)}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-muted)' }}>No active session.</div>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* PRE-CONSULTATION TAB */}
        {activeTab === 'pre-consult' && (
          <div style={{ marginTop: '20px' }}>
            <PreConsultation />
          </div>
        )}

      </main>
    </div>
  );
}
