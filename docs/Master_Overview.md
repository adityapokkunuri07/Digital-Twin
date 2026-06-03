# Digital Twin Framework — Synthesized Master Overview

**Synthesis Sources:** `001-CSO` · `002-HLA` · `003-LLA` · `004-SDA`  
**Classification:** Internal — Architecture & Product Vision  
**Last Synthesized:** 2026-06-02

---

## 1. Executive Summary

The **Digital Twin** (formally: *Autonomous Expert Proxy*) is a domain-agnostic, enterprise-grade cognitive replica designed to operationalize the specialized, tacit knowledge and real-world execution capabilities of any highly skilled professional. It is **not** a chatbot, a basic RAG pipeline, or a conventional conversational AI. It is a strictly bounded, Python-orchestrated state machine that emulates not only *what* an expert knows, but *how they think*, *how they speak*, and *what tasks they physically execute* on a daily basis.

### 1.1 Core Philosophy — The "Jarvis" Paradigm

The system functions as an infinite-scale frontline proxy that:

| Capability | Description |
|---|---|
| **Routine Absorption** | Handles 100% of routine interactions, inquiries, and repetitive workflow assignments autonomously. |
| **Radical Transparency** | Logs every action in an immutable, cryptographic execution ledger for full auditability. |
| **Instant Self-Suspension** | Immediately suspends its own operation and yields to the human expert the moment it detects a scenario requiring nuance, escalation, or explicit intervention. |

### 1.2 Domain Agnosticism

While the foundational documents reference Healthcare and Education as primary verticals, the architecture is a **horizontally scalable framework**. The core execution engine, knowledge graph schema, bimodal routing, and state machine topology remain invariant across domains. Onboarding a new expert from *any* industry (Legal, Finance, Engineering, etc.) requires only:

1.  Configuring a new **AI Journalist** onboarding interview to extract the expert's domain-specific Chain of Thought (CoT), communication style, and operational protocols.
2.  Populating the **Supabase adjacency matrix** with the expert's knowledge nodes and relational edges.
3.  Mapping deterministic **n8n webhook** actions relevant to that domain's tooling (CRM, LMS, EHR, etc.).

The cognitive engine itself requires zero structural modification.

### 1.3 Behavioral & Tone Cloning

To ensure end-users perceive interactions as authentic, the system employs **Stylistic Persistence** — the output generator bypasses generic LLM phrasing and maps responses directly to the expert's recorded communication matrix. Tone dynamically shifts based on workflow state (e.g., encouraging and Socratic when tutoring; direct and clinical when summarizing lab results).

### 1.4 Zero-Hallucination Epistemic Fencing

The Digital Twin operates within an **absolute epistemic fence**. Its knowledge is aggressively bounded by the expert's explicit CoT stored in the Supabase SSOT. A **Rejection Protocol** ensures that out-of-domain queries are intercepted at the bimodal routing layer — the twin is mathematically prevented from speculating and will gracefully deflect, stating the boundaries of its expertise.

---

## 2. Global Architecture Topology

*Synthesized from Documents 002-HLA and 003-LLA.*

The framework is built on a **distributed, synchronized topology** that separates the Visual Control Plane, the Intelligence & Orchestration Layer, the Knowledge Graph Command Center, and the File Projection Plane. Supabase (PostgreSQL) operates as the **absolute Single Source of Truth (SSOT)**.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        User / Client Interface                         │
│            (Web / Chat / Voice / Document Upload via OCR)              │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │  (Sanitized Payload)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     Intent Routing Engine (Python)                      │
│        (Bimodal Router: Smooth Read Path vs. Active Action Path)       │
└─────────┬────────────────────────────────────────────────────┬─────────┘
          │ (Informational)                                    │ (Actionable)
          ▼                                                    ▼
┌─────────────────────────┐                 ┌────────────────────────────┐
│  Knowledge Retrieval    │                 │ LangGraph Execution Core   │
│  (pgvector Semantic     │                 │ (Python State Machine)     │
│   Search on SSOT)       │                 │ (4-Node Execution Thread)  │
└─────────┬───────────────┘                 └─────────┬──────────────────┘
          │                                           │
          │                                           ▼
          │                                 ┌────────────────────────────┐
          │                                 │ Human Intercept Layer      │
          │                                 │ (Thread Freezing / HITL)   │
          │                                 └─────────┬──────────────────┘
          │                                           │
          ▼                                           ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    Unified Knowledge Graph (SSOT)                      │
│                    [ Supabase PostgreSQL Master ]                      │
│        (knowledge_nodes, knowledge_edges, pgvector, ltree)             │
└─────────┬────────────────────────────────────────────────────┬─────────┘
          │ (Row Webhooks)                                     │ (On-Demand Hydration)
          ▼                                                    ▼
┌─────────────────────────┐                 ┌────────────────────────────┐
│ File Projection Plane   │                 │ Expert Control Plane       │
│ [ Obsidian Vault ]      │                 │ [ React Flow Canvas ]      │
│ (Physical .md Audit     │                 │ (Glassmorphism Dashboard)  │
│  Ledger)                │                 │ (Zustand State Mgmt)       │
└─────────────────────────┘                 └────────────────────────────┘
```

### 2.1 The Visual Control Plane (Frontend)

The primary interface for the human expert to design, validate, and alter the twin's cognitive pathways.

| Component | Technology | Purpose |
|---|---|---|
| **Rendering Engine** | React Flow | Node-edge rendering, canvas interactions, drag-and-drop mechanics. |
| **State Management** | Zustand | Sub-100ms optimistic UI feedback loop rendering before DB commits. |
| **Data Fetching** | On-Demand Hydration | Recursive CTEs fetch root structures + descendants to Depth +2 only. |
| **Aesthetic** | Glassmorphism | Minimalist, distraction-free design to prevent cognitive overload. |

### 2.2 The Intelligence & Orchestration Layer (Backend — Python)

> **Tech Stack Enforcement:** The backend intelligence, orchestration, and routing layers are **exclusively engineered in Python**. Node.js is intentionally bypassed for all cognitive intelligence layers to ensure maximum compatibility with semantic processing libraries, embedding models, and LangGraph state management.

| Component | Technology | Purpose |
|---|---|---|
| **API Gateway** | FastAPI | Orchestrates graph traversals, AI Journalist onboarding, payload validation. |
| **Execution Engine** | LangGraph | 4-node state machine for deterministic task execution with thread-locking. |
| **Automation Dispatch** | n8n (Webhooks) | External action orchestration (emails, calendars, CRM/LMS updates). |
| **Semantic Encoding** | SentenceTransformers | Vector embedding generation for bimodal intent classification. |

### 2.3 The Knowledge Graph Command Center (Storage — SSOT)

The persistence layer is designed as an **adjacency matrix** using PostgreSQL, acting as the absolute SSOT. Content records are isolated from their relational mapping, allowing a single protocol to maintain multiple contextual connections.

**Core Schema:**

```sql
-- Table A: knowledge_nodes (Records, CoT, Embeddings)
CREATE TABLE knowledge_nodes (
    node_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id     UUID REFERENCES knowledge_nodes(node_id) ON DELETE CASCADE,
    order_index   INTEGER NOT NULL,
    content       TEXT NOT NULL,
    embedding     vector(1536),     -- Semantic search vector
    metadata      JSONB DEFAULT '{}'::jsonb, -- CoT & Unlearning Rationale
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table B: knowledge_edges (Cross-reference relational mapping)
CREATE TABLE knowledge_edges (
    edge_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id     UUID REFERENCES knowledge_nodes(node_id),
    target_node_id     UUID REFERENCES knowledge_nodes(node_id),
    relationship_type  VARCHAR(50) NOT NULL, -- 'requires', 'contradicts', 'related_to'
    UNIQUE(source_node_id, target_node_id)
);
```

**Performance Indexes:**

| Index | Type | Purpose |
|---|---|---|
| `idx_knowledge_nodes_parent_id` | B-Tree | Recursive parent-child tree traversals. |
| `idx_knowledge_nodes_parent_order` | B-Tree (Composite) | Sequential cursor pagination for large node arrays. |
| `idx_knowledge_nodes_embedding` | HNSW (`vector_cosine_ops`) | High-performance approximate nearest neighbor (ANN) vector search. |

**Retrieval Distance Metric:** Cosine Similarity — `Sim(A, B) = (A · B) / (‖A‖ × ‖B‖)`

### 2.4 The File Projection Plane (Obsidian Audit Layer)

Database records are mirrored into a human-readable Obsidian Vault via asynchronous sync workers triggered by Supabase Row Webhooks. Expert reasoning and unlearning rationales are permanently injected into the YAML frontmatter of each `.md` document.

```
[Supabase DB Master] ──(DB Row Webhook)──► [Sync Worker (Python)] ──(File I/O)──► [Obsidian Vault]
```

---

## 3. The Execution Engine & State Machine

*Synthesized from Documents 003-LLA and 004-SDA.*

### 3.1 Bimodal Intent Routing

The routing engine evaluates every inbound payload (after Zero-Trust PII sanitization) and splits traffic into two deterministic paths:

| Path | Trigger Condition | Execution |
|---|---|---|
| **Smooth Read Path** | Cosine similarity > 0.85 & no state mutation required. | Direct `pgvector` semantic fetch from the SSOT → vetted response generation. |
| **Active Action Path** | Task extraction match OR state mutation required. | Invocation of the LangGraph 4-node execution thread. |

**Routing Pseudocode (Python / FastAPI):**

```python
@app.post("/api/v1/interact")
async def intent_router(request: Request):
    payload = await request.json()
    sanitized_query = sanitize_pii(payload.get("query"))
    query_vector = embedder.encode(sanitized_query)
    intent = classify_intent(query_vector)

    if intent == "INFORMATIONAL":
        context = query_supabase_vector_match(query_vector, threshold=0.85)
        return {"route": "smooth", "data": format_vetted_response(context)}

    elif intent == "ACTIONABLE":
        initial_state = {"user_input": sanitized_query, "clinical_variables": {}}
        result = digital_twin_graph.invoke(initial_state)
        return {"route": "graph_execution", "data": result}
```

### 3.2 The 4-Node LangGraph Execution Thread

When the bimodal router classifies an interaction as **Actionable**, control is handed to a deterministic, Python-based LangGraph state machine. The graph operates on a strictly typed state object that accumulates data as it traverses nodes.

**State Schema:**

| State Variable | Type | Description |
|---|---|---|
| `session_id` | `UUID` | Unique identifier for the active thread. |
| `user_input` | `String` | Raw, sanitized inbound payload. |
| `extracted_variables` | `Dict` | Key-value pairs extracted during data gathering (symptoms, code snippets, etc.). |
| `clinical_or_academic_baseline` | `List[Vector]` | Context fetched from the Supabase Knowledge Graph. |
| `anomaly_flag` | `Boolean` | Triggered if a variable falls outside standard protocol bounds. |
| `execution_status` | `String (Enum)` | `GATHERING` · `PROCESSING` · `BLOCKED_BY_HUMAN` · `COMPLETED` |

**Graph Topology:**

```
┌────────────────────────────────────────────────────────────────────────┐
│                      LangGraph Execution Thread                        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    NODE 1: DATA GATHERING                              │
│   Initiates adaptive extraction loops until all required variables     │
│   are collected from the user via multi-turn dialogue.                 │
└─────────┬────────────────────────────────────────────────────┬─────────┘
          │ (Loop until complete)                              │ (All Variables Extracted)
          ▲                                                    ▼
          │                      ┌───────────────────────────────────────┐
          └──────────────────────┤ NODE 2: DATA PROCESSING & EVALUATION  │
                                 │ Cross-references extracted data       │
                                 │ against the expert's baseline in the  │
                                 │ Supabase SSOT.                        │
                                 └─────────┬───────────────────┬─────────┘
                                           │                   │
                     (Standard Processing) │                   │ (Anomaly / Escalation)
                                           ▼                   ▼
┌──────────────────────────────────────────┐    ┌────────────────────────┐
│ NODE 4: ACTION / SKILLS DISPATCHER       │    │ NODE 3: HUMAN INTERCEPT│
│ Triggers deterministic n8n webhooks,     │    │ Thread instantly frozen │
│ DB commits, external tool calls.         │    │ via LangGraph           │
│ Does NOT use LLMs — pure Python          │    │ checkpointer.           │
│ function calling.                        │    │                         │
└─────────┬────────────────────────────────┘    └─────────┬──────────────┘
          │                                               │
          ▼                                               ▼
[ Session Completed & Logged ]                  [ Expert Takes Manual Control ]
```

**Node Descriptions:**

1.  **Node 1 — Data Gathering:** Initiates adaptive, multi-turn extraction loops to collect all required variables from the user. The node self-loops until all necessary data points are captured.
2.  **Node 2 — Data Processing & Evaluation:** Cross-references the `extracted_variables` against the expert's validated baseline fetched from the Supabase Knowledge Graph. Determines if the case is standard or anomalous.
3.  **Node 3 — Human Intercept (HITL):** The definitive circuit breaker. Triggered by anomaly detection, unmapped workflows, or direct user request for the human. The thread is **instantly frozen** via the LangGraph checkpointer, and the full graph state is serialized to a checkpoint database.
4.  **Node 4 — Action / Skills Dispatcher:** Executes deterministic, Python-driven function calls to trigger external integrations (n8n webhooks, DB commits, OCR pipelines). Explicitly does **not** use LLMs for execution.

### 3.3 Concurrency & Thread Isolation

| Mechanism | Description |
|---|---|
| **Active Execution Locks** | During Data Processing, the session thread is locked. Inbound user messages are queued to prevent parallel mutations from corrupting the `extracted_variables` state dictionary. |
| **Thread Checkpointing** | On Human Intercept trigger, the exact graph state (including all variables gathered to that millisecond) is serialized and persisted to a SQLite/Postgres checkpoint database. |
| **Manual Override** | The expert loads the frozen graph state from their control plane, resolves the issue, and manually releases the queue isolation lock. |

### 3.4 External Skill Processing Fabric

#### n8n Orchestration

Rather than hardcoding API integrations, the Python backend dispatches JSON payloads to modular **n8n webhooks**:

-   **Email/Notification Dispatch** — Graded rubrics, pre-care instructions, intervention alerts.
-   **Calendar Management** — Expert availability adjustments, follow-up scheduling.
-   **System Updates** — Structured data pushes to external CRM, LMS, or EHR APIs.

#### Automated Document & OCR Pipeline

```
[User Uploads Document] → [OCR / Vision Model Extraction] → [Structural Markdown Parsing]
                                                                       │
                                                                       ▼
                                                          [Injection into user_input
                                                           state variable for Node 2
                                                           evaluation against SSOT]
```

---

## 4. Enterprise Compliance & Auditing

### 4.1 The "Mom and Child" Unlearning Workflow (Vector Tombstoning)

To satisfy enterprise compliance and liability tracing requirements, **destructive `DELETE` commands are strictly prohibited**. When an expert deprecates a piece of knowledge, the system initiates a compliant deprecation state machine:

| Step | Action | Technical Implementation |
|---|---|---|
| **1. Quarantine** | Expert drags the node into a designated UI drop-zone on the React Flow canvas. | UI event triggers the deprecation API endpoint. |
| **2. Tacit Interrogation** | The twin intercepts the action and prompts the expert for the specific **unlearning rationale**. | Modal dialog captures the expert's explicit reasoning. |
| **3. Vector Nullification (Tombstoning)** | The `embedding` column is set to `NULL`. | The vector is mathematically removed from the HNSW index, making the node invisible to all semantic similarity searches. |
| **4. Hierarchy Retention** | `node_id` and `parent_id` are retained. | The structural ledger is preserved for compliance tracing. |
| **5. Rationale Injection** | The expert's rationale is permanently written into the node's JSONB `metadata`. | Immutable audit record: `status: "quarantined"`, `unlearning_rationale: "..."`, `deprecated_at: <timestamp>`. |

**Quarantine Execution (Python):**

```python
def deprecate_knowledge_node(node_id: str, expert_rationale: str):
    """Executes the Mom and Child unlearning protocol."""
    update_payload = {
        "embedding": None,  # Vector Tombstoning
        "metadata": {
            "status": "quarantined",
            "unlearning_rationale": expert_rationale,
            "deprecated_at": current_timestamp()
        }
    }
    supabase.table('knowledge_nodes') \
        .update(update_payload) \
        .eq('node_id', node_id) \
        .execute()
    # Supabase DB Row Webhook auto-fires to rebuild the Obsidian .md file
    return True
```

### 4.2 Obsidian File Projection (Audit Plane)

Every database record is mirrored into a physical Markdown file in the Obsidian Vault. The expert's extracted Chain of Thought and unlearning rationales are permanently baked into YAML frontmatter:

```yaml
---
node_id: "550e8400-e29b-41d4-a716-446655440000"
parent_id: "770e8400-e29b-41d4-a716-446655440111"
sync_status: "verified"
chain_of_thought: |
  "In cases presenting with elevated markers, standard protocol
   must be bypassed to prioritize immediate fluid resuscitation
   due to the risk of cascading systemic failure."
quarantine_status: false
---

# Clinical Protocol V2
Standard guidelines for evaluating...
```

If the database trigger (`trg_validate_node_hierarchy`) rejects a modification, the webhook does not fire, and the UI snaps the node back to its origin — ensuring **absolute parity** between the visual plane, the database, and the physical markdown ledger.

### 4.3 The Glass Box Audit Trail & Shadow Evaluation

| System | Function |
|---|---|
| **Immutable Execution Traces** | Every LangGraph node transition, every Supabase query, and every n8n webhook dispatch is logged into an `execution_traces` table — a complete, step-by-step cryptographic ledger of *why* the twin took each action. |
| **Shadow Evaluation Loop** | When the Human Intercept is triggered, telemetry records the exact context that caused the AI to halt. A background job analyzes the variance between the twin's frozen state and the expert's manual resolution. |
| **Override Pattern Detection** | If recurring manual overrides are detected for a specific topic, the system generates an alert on the React Flow dashboard, recommending the expert update the underlying protocol mapping to close the cognitive gap. |

### 4.4 Cross-Plane Synchronization Lifecycle

The Modification Loop ensures harmony across all four planes:

1.  **Local UI Phase** — Expert modifies the graph on the React Flow canvas. Zustand updates the UI instantaneously (optimistic).
2.  **Database Verification Phase** — Background API request hits the Python backend. DB triggers validate hierarchy (prevent circular dependencies).
3.  **Commit Phase** — Nodes and edges are atomically updated in Supabase.
4.  **Downstream Sync Phase** — DB Row Webhook fires → Python sync worker rebuilds the corresponding Obsidian `.md` file with updated YAML frontmatter. If the DB rejects the change, the UI snaps the node back.

---

## 5. Development Tech Stack Summary

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend (UI)** | React Flow, Zustand | Glassmorphism visual control plane with sub-100ms optimistic rendering. Drag-and-drop knowledge graph configuration. |
| **Backend (Intelligence)** | **Python** — FastAPI, LangGraph, SentenceTransformers | All cognitive intelligence, orchestration, bimodal routing, and state machine logic. **Node.js is intentionally excluded** from these layers. |
| **Database (SSOT)** | Supabase (PostgreSQL), pgvector | Adjacency matrix knowledge graph. HNSW vector indexing for ANN search. JSONB metadata for CoT and compliance. |
| **Automation (Skills)** | n8n (Webhook orchestration) | Modular, deterministic external action dispatch (email, calendar, CRM/LMS/EHR). |
| **Document Processing** | OCR / Vision Models | Automated extraction and structural parsing of user-uploaded physical documents. |
| **Audit & Compliance** | Obsidian Vault (Markdown) | Physical file projection of DB state. YAML frontmatter houses CoT and unlearning rationales. |
| **Telemetry** | `execution_traces` table | Immutable, cryptographic audit ledger for full compliance tracing. |
| **Checkpointing** | SQLite / Postgres | LangGraph thread state persistence for Human Intercept freezing and resumption. |

---

> **End of Synthesized Master Overview.**  
> *Source Documents: 001-CSO · 002-HLA · 003-LLA · 004-SDA*
