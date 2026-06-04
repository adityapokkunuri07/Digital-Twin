import React, { useState, useEffect } from 'react';
import { 
  Activity, Layers, UserCheck, FileText, FolderOpen, Send, 
  ShieldAlert, RefreshCw, CheckCircle2, AlertTriangle,
  Play, RotateCcw, Sparkles, Search, Eye, Trash2,
  ChevronDown, ChevronRight, Folder, File
} from 'lucide-react';

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
  const [activeTab, setActiveTab] = useState('workflow');
  
  // --- Global State ---
  const [configId, setConfigId] = useState('11111111-1111-1111-1111-111111111111'); // Matches sample_data.sql
  const [activeVersion, setActiveVersion] = useState('1.0.0');
  const [isFeasible, setIsFeasible] = useState(true);
  const [validationErrors, setValidationErrors] = useState([]);
  const [apiStatus, setApiStatus] = useState('offline'); // online / offline

  // --- Workflow Configurator State ---
  const [steps, setSteps] = useState([
    { id: "step_1", name: "Intake", inputs: [], outputs: ["symptoms", "temperature"], dependencies: [] },
    { id: "step_2", name: "Diagnosis Gate", inputs: ["symptoms", "temperature"], outputs: ["is_severe", "diagnosis_summary"], dependencies: ["step_1"] },
    { id: "step_3", name: "Action Escalator", inputs: ["is_severe", "diagnosis_summary"], outputs: ["escalation_done"], dependencies: ["step_2"] }
  ]);
  const [autopilot, setAutopilot] = useState(true);
  const [newStep, setNewStep] = useState({ name: '', inputs: '', outputs: '', dependencies: '' });

  // --- Onboarding Journalist State ---
  const [transcript, setTranscript] = useState(
    "Dr. Sterling: Initial intake gathers vitals including blood pressure and temperature. " +
    "Then, we evaluate if patient complains of chest tightness. " +
    "If temperature is >= 103, we escalate to emergency. " +
    "Action plans involve scheduling immediate checkups or dispatching medical alerts."
  );
  const [saturationScore, setSaturationScore] = useState(0.45);
  const [isSaturationSatisfied, setIsSaturationSatisfied] = useState(false);
  const [nextPrompt, setNextPrompt] = useState("Explain how you evaluate blood pressure limits?");
  const [chatLog, setChatLog] = useState([
    { sender: 'journalist', text: "Welcome Dr. Sterling. Please explain your standard clinical intake routine?" },
    { sender: 'expert', text: "Dr. Sterling: Initial intake gathers vitals including blood pressure and temperature. Then, we evaluate if patient complains of chest tightness." }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [cotNodes, setCotNodes] = useState([]);
  const [cotEdges, setCotEdges] = useState([]);

  // --- Ingestion State ---
  const [rawText, setRawText] = useState(
    "# Clinical Triage Guidelines\n\n" +
    "This document covers the cardiac intake and evaluation procedures.\n\n" +
    "## Intake Protocol\n\n" +
    "Collect patient complains and vitals. Core variables include temperature and chest tightness. Vitals must be checked immediately.\n\n" +
    "## Evaluation Standards\n\n" +
    "Assess results. If temperature exceeds 103, trigger emergency alarms. If chest pain is checked, halt immediately.\n\n" +
    "## Treatment Action\n\n" +
    "Escalate critical cases to physicians or schedule routine followups."
  );
  const [ingestedChunks, setIngestedChunks] = useState([]);
  const [ingesting, setIngesting] = useState(false);

  // --- Obsidian & Unlearning State ---
  const [obsidianFiles, setObsidianFiles] = useState([]);
  const [selectedObsidianFile, setSelectedObsidianFile] = useState(null);
  const [unlearnNodeInput, setUnlearnNodeInput] = useState('');
  const [unlearnRationale, setUnlearnRationale] = useState('Guidelines changed due to updated AHA recommendations.');

  // --- Query Sandbox State ---
  const [sessionId, setSessionId] = useState(null);
  const [userQuery, setUserQuery] = useState("My temperature is 104 and my chest feels tight");
  const [sandboxLog, setSandboxLog] = useState([]);
  const [activeSessionState, setActiveSessionState] = useState(null);
  const [loadingSandbox, setLoadingSandbox] = useState(false);

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

  const handleUnlearn = async () => {
    if (!unlearnNodeInput.trim()) return;
    const payload = {
      node_ids: [unlearnNodeInput],
      rationale: unlearnRationale
    };
    
    const updateLocalState = () => {
      setObsidianFiles(prev => prev.map(f => {
        if (f.node_id === unlearnNodeInput || f.path.includes(unlearnNodeInput)) {
          return { ...f, quarantine_status: true, unlearning_rationale: unlearnRationale };
        }
        return f;
      }));
      if (selectedObsidianFile && (selectedObsidianFile.node_id === unlearnNodeInput || selectedObsidianFile.path.includes(unlearnNodeInput))) {
        setSelectedObsidianFile(prev => ({ ...prev, quarantine_status: true, unlearning_rationale: unlearnRationale }));
      }
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
        alert("Mom-and-Child Unlearning complete. Vector tombstoned!");
        return;
      } catch (err) {
        console.error(err);
      }
    }

    updateLocalState();
    alert(`[MOCK UNLEARNING] Node ${unlearnNodeInput} tombstoned successfully. Embedding set to NULL!`);
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
          <div style={{ display: 'grid', gridTemplateColumns: '250px 1fr 340px', gap: '24px' }}>
            {/* File Explorer */}
            <div className="glass-card" style={{ maxHeight: '600px', overflowY: 'auto' }}>
              <h3 style={{ fontSize: '18px', marginBottom: '16px' }}>Vault Files</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {obsidianFiles.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', padding: '20px 0', textAlign: 'center', fontSize: '12px' }}>
                    No sync triggers recorded. Save configs or finalize onboarding.
                  </div>
                ) : (
                  buildFileTree(obsidianFiles).map((node, i) => (
                    <FileTreeNode 
                      key={i} 
                      node={node} 
                      level={0}
                      selectedFile={selectedObsidianFile}
                      onSelect={(file) => setSelectedObsidianFile(file)}
                      onUnlearnSelect={(id) => setUnlearnNodeInput(id)}
                    />
                  ))
                )}
              </div>
            </div>

            {/* Markdown Viewer */}
            <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', padding: '0', overflow: 'hidden', height: '600px' }}>
              <div style={{ padding: '16px', borderBottom: '1px solid var(--border-light)', background: 'rgba(0,0,0,0.2)' }}>
                <h3 style={{ fontSize: '16px', margin: 0, fontFamily: 'monospace' }}>
                  {selectedObsidianFile ? selectedObsidianFile.path : 'Select a file'}
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
                  <div style={{ color: 'var(--text-muted)', display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
                    Select a Markdown file from the explorer to view the projected SSOT state.
                  </div>
                )}
              </div>
            </div>

            {/* Mom-Child Unlearning panel */}
            <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxHeight: '600px' }}>
              <h3 style={{ fontSize: '18px', color: 'var(--error)' }}>Retract Knowledge</h3>
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

              <button className="btn btn-primary" style={{ backgroundColor: 'var(--error)' }} onClick={handleUnlearn}>
                Tombstone Vector
              </button>
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
      </main>
    </div>
  );
}
