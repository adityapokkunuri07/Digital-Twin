import React, { useState } from 'react';

const WorkflowBuilder = ({ configId, onGenerateComplete, onCancel }) => {
    const [workflowName, setWorkflowName] = useState('');
    const [tasks, setTasks] = useState([{ description: '', actor: 'TWIN' }]);
    const [isGenerating, setIsGenerating] = useState(false);
    const [error, setError] = useState(null);
    const [rejections, setRejections] = useState([]);

    const handleAddTask = () => {
        setTasks([...tasks, { description: '', actor: 'TWIN' }]);
    };

    const handleRemoveTask = (index) => {
        const newTasks = [...tasks];
        newTasks.splice(index, 1);
        setTasks(newTasks);
        
        // Remove any rejection associated with this index
        if (rejections.length > 0) {
            setRejections(rejections.filter(r => r.task_index !== index));
        }
    };

    const handleTaskChange = (index, field, value) => {
        const newTasks = [...tasks];
        newTasks[index][field] = value;
        setTasks(newTasks);
    };

    const handleGenerate = async () => {
        if (!workflowName.trim()) {
            setError("Please provide a workflow name.");
            return;
        }

        const validTasks = tasks.filter(t => t.description.trim() !== '');
        if (validTasks.length === 0) {
            setError("Please add at least one valid task description.");
            return;
        }

        setIsGenerating(true);
        setError(null);
        setRejections([]);

        try {
            const response = await fetch('http://localhost:8000/api/workflows/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    workflow_name: workflowName,
                    config_id: configId,
                    tasks: validTasks
                })
            });

            if (!response.ok) {
                const data = await response.json();
                if (response.status === 400 && data.detail && data.detail.rejections) {
                    setRejections(data.detail.rejections);
                    setError("Some tasks are not supported. Please review and modify them.");
                } else {
                    setError(data.detail || "Failed to generate workflow.");
                }
                setIsGenerating(false);
                return;
            }

            const result = await response.json();
            setIsGenerating(false);
            if (onGenerateComplete) {
                onGenerateComplete(result.workflow_id);
            }
        } catch (err) {
            setError(err.message || "An error occurred.");
            setIsGenerating(false);
        }
    };

    return (
        <div className="glass-card workflow-builder" style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div>
                <h2 style={{ fontSize: '24px', fontFamily: 'var(--font-display)', fontWeight: '700', margin: 0, color: 'var(--primary)' }}>Create Custom Workflow</h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
                    Describe your clinical tasks in plain English. The AI will translate them into a structured workflow configuration.
                </p>
            </div>
            
            {error && (
                <div style={{ 
                    backgroundColor: 'rgba(239, 68, 68, 0.1)', 
                    color: 'var(--error)', 
                    padding: '12px 16px', 
                    borderRadius: '8px', 
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    fontSize: '14px'
                }}>
                    {error}
                </div>
            )}

            <div className="input-group">
                <span className="input-label">Workflow Name</span>
                <input 
                    type="text" 
                    value={workflowName}
                    onChange={(e) => setWorkflowName(e.target.value)}
                    placeholder="e.g., Post-Op Cardiac Follow-up"
                    className="form-input"
                />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3 style={{ fontSize: '18px', margin: 0 }}>Tasks</h3>
                    <button 
                        onClick={handleAddTask}
                        className="btn btn-secondary"
                        style={{ padding: '6px 12px', fontSize: '13px' }}
                    >
                        + Add Task
                    </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {tasks.map((task, index) => {
                        const rejection = rejections.find(r => r.task_index === index);
                        
                        return (
                            <div 
                                key={index} 
                                style={{ 
                                    position: 'relative',
                                    padding: '16px',
                                    background: 'rgba(255,255,255,0.02)', 
                                    border: rejection ? '1px solid var(--error)' : '1px solid var(--border-light)',
                                    borderRadius: '8px',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    gap: '16px'
                                }}
                            >
                                <button 
                                    onClick={() => handleRemoveTask(index)}
                                    style={{
                                        position: 'absolute',
                                        top: '12px',
                                        right: '12px',
                                        background: 'transparent',
                                        border: 'none',
                                        color: 'var(--text-muted)',
                                        cursor: 'pointer',
                                        fontSize: '14px'
                                    }}
                                    title="Remove Task"
                                >
                                    ✕
                                </button>
                                
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 200px', gap: '16px', alignItems: 'start' }}>
                                    <div className="input-group" style={{ margin: 0 }}>
                                        <span className="input-label">Description (What should be done?)</span>
                                        <textarea 
                                            value={task.description}
                                            onChange={(e) => handleTaskChange(index, 'description', e.target.value)}
                                            placeholder="e.g., Ask the patient about their symptoms and duration. Escalate if fever > 103."
                                            className="form-input"
                                            style={{ minHeight: '80px', resize: 'vertical' }}
                                        />
                                    </div>
                                    <div className="input-group" style={{ margin: 0 }}>
                                        <span className="input-label">Assigned Actor</span>
                                        <select 
                                            value={task.actor}
                                            onChange={(e) => handleTaskChange(index, 'actor', e.target.value)}
                                            className="form-input"
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <option value="TWIN">AI Twin</option>
                                            <option value="DOCTOR">Human Doctor</option>
                                        </select>
                                    </div>
                                </div>
                                
                                {rejection && (
                                    <div style={{ 
                                        marginTop: '4px', 
                                        fontSize: '13px', 
                                        color: 'var(--error)', 
                                        backgroundColor: 'rgba(239, 68, 68, 0.05)', 
                                        padding: '8px 12px', 
                                        borderRadius: '6px',
                                        border: '1px solid rgba(239, 68, 68, 0.2)'
                                    }}>
                                        <strong style={{ fontWeight: 600 }}>Rejected:</strong> {rejection.reason}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '16px' }}>
                <button 
                    onClick={onCancel}
                    className="btn btn-secondary"
                >
                    Cancel
                </button>
                <button 
                    onClick={handleGenerate}
                    disabled={isGenerating}
                    className="btn btn-primary"
                >
                    {isGenerating ? 'Translating...' : 'Generate & Save Workflow'}
                </button>
            </div>
        </div>
    );
};

export default WorkflowBuilder;
