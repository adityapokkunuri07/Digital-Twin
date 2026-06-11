# Digital Twin Framework: Working Operations & Compliance Mechanics

## 1. Introduction to Day-to-Day Operations

The true test of the Digital Twin framework is not in its static architecture, but in how it operates, adapts, and maintains compliance in a dynamic enterprise environment. A "working" Digital Twin must seamlessly handle updates to the expert's knowledge, provide absolute transparency into its decision-making, and ensure that outdated or incorrect information is compliantly unlearned.

This document details the critical operational lifecycles that govern the Digital Twin day-to-day.

---

## 2. The Cross-Plane Synchronization Lifecycle (The Modification Loop)

As an expert's knowledge evolves (e.g., a new medical guideline is published, or a new legal precedent is set), the Twin must be updated. This update process spans all four architectural planes to guarantee that the UI, the Database, the AI Engine, and the Audit Ledger are in absolute, perfect parity. 

This synchronization is governed by the **Modification Loop**.

### 2.1 Step 1: The Local UI Phase (Optimistic Update)
The expert logs into the React Flow dashboard (The Visual Control Plane). They drag a new node onto the canvas or draw a new edge connecting two existing concepts. 
To ensure a fluid user experience, the frontend state manager (Zustand) updates the UI instantly. The user sees the change occur in sub-100 milliseconds.

### 2.2 Step 2: The Database Verification Phase
Simultaneously, a background API request is sent to the Python backend. The backend submits the change to the Supabase PostgreSQL database. 
Crucially, database triggers (e.g., `trg_validate_node_hierarchy`) intercept the request before committing. The database mathematically verifies the logic—ensuring, for example, that the new connection does not create an infinite circular dependency.

### 2.3 Step 3: The Commit and Downstream Sync Phase
If the DB accepts the change, it is atomically committed. Immediately, a **Row-Level Webhook** fires from Supabase.
This webhook alerts a Python Sync Worker that the SSOT has changed. The Python worker performs physical File I/O, regenerating the specific Markdown (`.md`) file corresponding to that node in the Obsidian Vault. 

### 2.4 Step 4: The Snap-Back (Error Handling)
If the DB *rejects* the change in Step 2 (due to a logical violation), the webhook does not fire. The backend returns a 400 error to the frontend. The React Flow UI intercepts this error and instantly "snaps" the node or edge back to its original position, visually indicating to the expert that the authoritative change failed.

---

## 3. The "Mom and Child" Unlearning Workflow (Vector Tombstoning)

In enterprise environments (particularly Healthcare and Law), destructive database commands (`DELETE`) are strictly prohibited due to liability tracing. If the AI makes a recommendation today based on Rule A, and tomorrow Rule A is deleted, auditors three years from now will have no record of *why* the AI acted the way it did.

To solve this, the Digital Twin uses a compliant deprecation state machine known as the "Mom and Child" unlearning workflow.

### 3.1 Step-by-Step Deprecation
1.  **Quarantine Initiation:** The expert drags an outdated node into a designated "Quarantine" drop-zone on the UI canvas.
2.  **Tacit Interrogation:** The Twin pauses and prompts the expert with a modal dialog: *"Why are we unlearning this protocol?"* This forces the expert to type out an explicit unlearning rationale.
3.  **Vector Tombstoning:** The backend executes an `UPDATE` command, not a `DELETE`. The 1536-dimensional `embedding` column for that node is set to `NULL`. 
    *   *Result:* Because the vector is nullified, it is mathematically removed from the HNSW index. The AI can no longer "see" or retrieve this knowledge during semantic searches. It is functionally dead to the AI.
4.  **Hierarchy Retention:** The `node_id` and its structural `parent_id` are permanently retained in the database schema. The structural skeleton of the graph remains intact.
5.  **Rationale Injection:** The expert's typed rationale is baked into the node's JSONB `metadata` column, creating an immutable audit record (e.g., `status: "quarantined"`, `rationale: "Replaced by FDA Guideline V4"`, `timestamp: 2026-06-11`).

---

## 4. The Glass Box Audit Trail

Traditional LLMs are "Black Boxes"—it is impossible to deterministically prove *why* a neural network generated a specific sequence of tokens. The Digital Twin operates as a "Glass Box."

### 4.1 Immutable Execution Traces
Every time the Twin interacts with a user, the backend generates an execution trace. This trace logs:
*   The raw sanitized input.
*   The exact cosine similarity scores of the vectors retrieved.
*   The specific `node_id`s from Supabase that were injected into the context window.
*   Every state transition logged by LangGraph.
*   The exact JSON payload dispatched to n8n webhooks.

This telemetry is stored in an immutable `execution_traces` table. If an enterprise faces a compliance audit, they can query this table and print out a cryptographic, step-by-step ledger proving exactly which rules the Twin followed for any given transaction.

---

## 5. The Shadow Evaluation Loop (Continuous Improvement)

The Digital Twin is designed to highlight gaps in the expert's mapped knowledge through telemetry.

### 5.1 Monitoring the Circuit Breaker
As the Twin handles live traffic, it monitors how often it hits **Node 3 (Human Intercept)**. 
If the Twin encounters a specific symptom, user request, or data anomaly that forces it to freeze the thread and ask for the human expert's help, it logs that event.

### 5.2 Proactive Upgrades
A background Shadow Evaluation job runs nightly to analyze this telemetry. If it detects a pattern—for example, the Twin froze 15 times this week when users asked about "Protocol X"—it signals a cognitive gap.

The dashboard will generate a proactive alert for the expert: *"I am repeatedly freezing threads regarding Protocol X because my boundaries are too strict. I suggest you update my mapped knowledge here."* 

By observing the variance between the Twin's frozen state and how the human expert ultimately resolved the manual override, the system can even draft proposed new nodes and edges, presenting them to the expert for a simple one-click approval. This creates a powerful, continuous feedback loop where the Twin helps map its own future capabilities.
