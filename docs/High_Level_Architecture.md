# Digital Twin Framework: High-Level Architecture (HLA)

## 1. Architectural Philosophy and Global Topology

The Digital Twin framework is fundamentally architected to separate concerns across four distinct operational planes. This separation ensures that the system is visually intuitive for non-technical experts, mathematically rigorous in its execution, secure in its data persistence, and fully auditable for enterprise compliance.

The global topology avoids the monolithic pitfalls of traditional applications by relying on a distributed, synchronized model. At its core, the system utilizes Supabase (PostgreSQL) as the absolute Single Source of Truth (SSOT). All other planes—the UI, the AI intelligence, and the physical audit files—are downstream projections or orchestrators of this central database.

### 1.1 The Four Pillars of the Architecture
1.  **The Visual Control Plane (Frontend Interface)**
2.  **The Intelligence & Orchestration Layer (Backend Engine)**
3.  **The Knowledge Graph Command Center (Storage SSOT)**
4.  **The File Projection Plane (Audit Ledger)**

---

## 2. High-Level Architecture Diagram

```mermaid
graph TD
    classDef frontend fill:#3b82f6,stroke:#2563eb,stroke-width:2px,color:#fff;
    classDef backend fill:#10b981,stroke:#059669,stroke-width:2px,color:#fff;
    classDef database fill:#f59e0b,stroke:#d97706,stroke-width:2px,color:#fff;
    classDef audit fill:#8b5cf6,stroke:#7c3aed,stroke-width:2px,color:#fff;

    subgraph Client & Expert Interface Layer
        UI[End-User Interfaces<br>Web Chat / Voice / Integrations]:::frontend
        ECP[Expert Control Plane<br>React Flow Canvas]:::frontend
    end

    subgraph Intelligence & Orchestration Layer (Python)
        IRE[Bimodal Intent Routing Engine<br>FastAPI]:::backend
        KG_Ret[Semantic Knowledge Retrieval<br>SentenceTransformers]:::backend
        LG_Core[Execution Core<br>LangGraph State Machine]:::backend
        HIL[Human Intercept Layer<br>Checkpointing]:::backend
        Act[Action Dispatcher<br>n8n Webhook Triggers]:::backend
    end

    subgraph Knowledge Graph Command Center
        SSOT[(Supabase PostgreSQL SSOT<br>Vector + Adjacency Matrix)]:::database
    end

    subgraph File Projection Plane (Audit)
        FPP[Obsidian Vault<br>Physical Markdown Ledger]:::audit
    end

    %% Flow Dynamics
    UI -->|Sanitized JSON Payload| IRE
    IRE -->|Informational Intent| KG_Ret
    IRE -->|Actionable Task/Mutation| LG_Core
    
    KG_Ret -->|Cosine Similarity Search| SSOT
    LG_Core -->|Standard Execution| Act
    LG_Core -->|Anomaly/Escalation| HIL
    
    HIL -->|Freeze State| ECP
    ECP -->|Manual Resolution| LG_Core
    Act -->|Dispatch| External[(External Systems / CRM / LMS)]
    
    SSOT -->|Row Webhooks - Async Sync| FPP
    SSOT -->|On-Demand Hydration| ECP
    ECP -->|Authoritative Updates| SSOT
```

---

## 3. Plane 1: The Visual Control Plane (Frontend)

The Visual Control Plane is the primary interface for the human expert. It is not designed for the end-user (who interacts via a standard chat/voice interface); rather, it is the cockpit from which the expert designs, validates, and alters the Twin's cognitive pathways.

### 3.1 Technology Stack
*   **Framework:** Next.js / React
*   **Canvas Rendering:** React Flow
*   **State Management:** Zustand
*   **Aesthetic Principle:** Glassmorphism

### 3.2 Component Details
*   **React Flow Canvas:** The complexity of tacit human knowledge is represented visually as a directed graph. Nodes represent discrete pieces of knowledge, rules, or actions. Edges represent the relationships (e.g., *requires*, *contradicts*, *precedes*). The expert can drag, drop, and connect nodes intuitively without writing code.
*   **Zustand Optimistic UI:** To prevent cognitive overload and interface lag, Zustand is used to implement a sub-100ms optimistic UI feedback loop. When an expert moves a node, the UI updates instantly locally, while the background API syncs with the database.
*   **On-Demand Hydration:** Loading a massive enterprise knowledge graph at once would crash the browser. The frontend utilizes recursive Common Table Expressions (CTEs) via the backend API to fetch only the root structures and their descendants up to a depth of +2. As the expert pans the canvas, data hydrates dynamically.

---

## 4. Plane 2: The Intelligence & Orchestration Layer (Backend)

This is the central nervous system of the Digital Twin. **Crucially, this layer is engineered exclusively in Python.** Node.js is intentionally bypassed to ensure maximum, native compatibility with semantic processing libraries, machine learning models, and LangGraph.

### 4.1 Technology Stack
*   **API Framework:** FastAPI
*   **Execution Engine:** LangGraph
*   **Semantic Encoding:** SentenceTransformers
*   **Automation:** n8n (External Orchestration)

### 4.2 Component Details
*   **Bimodal Intent Router:** Every inbound payload is first stripped of Personally Identifiable Information (PII) via a Zero-Trust middleware. The sanitized query is then vectorized. The Router determines if the intent is *Informational* (requiring a simple read from the database) or *Actionable* (requiring task execution and state mutation).
*   **LangGraph Execution Core:** For actionable intents, control is passed to a LangGraph state machine. This is a deterministic thread that gathers data, processes it against the expert's rules, and determines the next action. It is strictly bounded and cannot hallucinate workflow steps.
*   **Human Intercept Layer (HITL):** Built on LangGraph's checkpointer mechanism. If the engine hits an edge case, it serializes the exact memory state to a checkpoint DB and halts. It waits for the expert on the Control Plane to manually resolve the block.
*   **Action Dispatcher:** Instead of hardcoding API integrations, the Python backend fires standardized JSON payloads to n8n webhooks. n8n acts as the "hands" of the Twin, managing the intricate authentications required to update CRMs, schedule calendar events, or send emails.

---

## 5. Plane 3: The Knowledge Graph Command Center (Storage)

The persistence layer is an adjacency matrix hosted on PostgreSQL, serving as the absolute Single Source of Truth. 

### 5.1 Technology Stack
*   **Database Engine:** Supabase (PostgreSQL)
*   **Vector Search:** `pgvector` extension

### 5.2 Schema Architecture
The design separates content from its relational mapping. This allows a single piece of knowledge to be connected in multiple different workflows without data duplication.
*   **`knowledge_nodes` Table:** Stores the actual content. It utilizes the `ltree` extension for hierarchical paths (if applicable) or self-referential `parent_id` foreign keys. Crucially, it houses a 1536-dimensional `embedding` column for vector storage, and a `metadata` JSONB column for audit trails and "Chain of Thought" rationales.
*   **`knowledge_edges` Table:** Maps the relationships. A row here links `source_node_id` to `target_node_id` and defines the `relationship_type` (e.g., 'prerequisite_for', 'mutually_exclusive').

### 5.3 Performance and Indexing
To ensure real-time latency even with massive expert graphs, specific indexes are strictly enforced:
*   **HNSW Indexing:** Hierarchical Navigable Small World indexes on the `embedding` column using `vector_cosine_ops` enable blazing-fast Approximate Nearest Neighbor (ANN) semantic searches.
*   **B-Tree Composite Indexes:** Placed on `parent_id` and `order_index` to facilitate rapid structural traversals for the React Flow UI.

---

## 6. Plane 4: The File Projection Plane (Audit)

Enterprise compliance often requires data to exist in human-readable, portable formats independent of a database engine. The framework solves this by mirroring the DB into a physical file system.

### 6.1 Technology Stack
*   **File Format:** Markdown (`.md`)
*   **Metadata System:** YAML Frontmatter
*   **Vault Platform:** Obsidian
*   **Sync Mechanism:** Supabase Row Webhooks + Python I/O Workers

### 6.2 Component Details
*   **Asynchronous Mirroring:** Whenever a row in `knowledge_nodes` is created, updated, or logically deleted (tombstoned), a PostgreSQL trigger fires a row-level webhook. A lightweight Python worker catches this webhook and performs physical File I/O on the server.
*   **YAML Frontmatter:** The worker writes or overwrites a Markdown file. All structured data—such as the node ID, synchronization status, the expert's explicitly extracted Chain of Thought, and deprecation rationales—are baked directly into the YAML frontmatter at the top of the file.
*   **Obsidian Consumption:** The resulting folder of Markdown files acts as an Obsidian Vault. Compliance officers, auditors, or the experts themselves can open this vault in Obsidian to browse their brain visually and textually, completely independent of the web application.

---

## 7. Security and Data Flow Summary

The architecture inherently protects data through bounded pathways:
1.  **Ingress:** User data hits FastAPI. PII is sanitized immediately before the string is ever embedded or passed to an LLM for formatting.
2.  **Processing:** Bimodal routing ensures that read-only requests never touch the execution engine, preventing malicious prompt injection from manipulating state variables.
3.  **Execution:** Actions are dispatched via internal network webhooks to n8n. The AI engine never holds direct OAuth tokens for external systems; it only holds the authorization to trigger specific, pre-defined n8n workflows.
4.  **Egress:** Final responses are formatted based strictly on the retrieved context from Supabase, ensuring the output is confined within the expert's epistemic fence.
