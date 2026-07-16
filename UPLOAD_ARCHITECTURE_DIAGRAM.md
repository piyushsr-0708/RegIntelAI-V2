# Upload Feature Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE LAYER                          │
├─────────────────────────────────────────────────────────────────────────┤
│  • Frontend React Application                                           │
│  • Upload Component with File Input                                     │
│  • Authentication (JWT Token)                                           │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             │ POST /documents/upload
                             │ (multipart/form-data)
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│                        BACKEND API LAYER                                │
│                         (FastAPI)                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────────────────────────────────┐                │
│  │   POST /documents/upload Endpoint                  │                │
│  │                                                     │                │
│  │  1. Authenticate User (JWT)                        │                │
│  │  2. Check Permission (DOC_UPLOAD)                  │                │
│  │  3. Validate File Type (PDF only)                  │                │
│  │  4. Validate File Size (<50MB)                     │                │
│  │  5. Generate Document ID (UPYYYYMMDD_NNNN)         │                │
│  │  6. Save PDF to Upload Directory                   │                │
│  │  7. Queue Background Task                          │                │
│  │  8. Return Immediate Response                      │                │
│  └──────────┬─────────────────────────────────────────┘                │
│             │                                                           │
│             │ background_tasks.add_task()                              │
│             │                                                           │
│  ┌──────────▼─────────────────────────────────────────┐                │
│  │   _run_uploaded_document_pipeline()                │                │
│  │   (Background Task Wrapper)                        │                │
│  │                                                     │                │
│  │  1. Import DocumentPipelineOrchestrator            │                │
│  │  2. Instantiate with custom pdf_source_dir         │                │
│  │  3. Execute orchestrator.process_document()        │                │
│  │  4. Log success/failure                            │                │
│  └──────────┬─────────────────────────────────────────┘                │
│             │                                                           │
└─────────────┼───────────────────────────────────────────────────────────┘
              │
              │ orchestrator.process_document(document_id)
              │
┌─────────────▼───────────────────────────────────────────────────────────┐
│                    PIPELINE ORCHESTRATOR LAYER                          │
│              (DocumentPipelineOrchestrator)                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Constructor:                                                           │
│  ┌──────────────────────────────────────────────────────────┐          │
│  │  __init__(project_root, pdf_source_dir=None)             │          │
│  │                                                           │          │
│  │  if pdf_source_dir:                                      │          │
│  │      use pdf_source_dir          # Uploaded documents    │          │
│  │  else:                                                    │          │
│  │      use master_directions/pdfs  # Original RBI dataset  │          │
│  └──────────────────────────────────────────────────────────┘          │
│                                                                         │
│  process_document(document_id):                                         │
│  ┌──────────────────────────────────────────────────────────┐          │
│  │  Stage 1:  PDF Parser                                    │          │
│  │  Stage 2:  Document Normalizer                           │          │
│  │  Stage 3:  Hierarchy Builder                             │          │
│  │  Stage 4:  Logical Unit Builder                          │          │
│  │  Stage 5:  Requirement Extractor                         │          │
│  │  Stage 6:  Requirement Enricher                          │          │
│  │  Stage 7:  Compliance Interpreter                        │          │
│  │  Stage 8:  Compliance Reasoning Engine                   │          │
│  │  Stage 9:  Control Deriver                               │          │
│  │  Stage 10: Verification Rule Generator                   │          │
│  │  Stage 11: Verification Planner                          │          │
│  │  Stage 12: MAP Generator                                 │          │
│  │  Stage 13: Database Ingest (document-scoped)             │          │
│  │  Stage 14: Dashboard Aggregator                          │          │
│  └──────────────────────────────────────────────────────────┘          │
│                                                                         │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              │ Reads/Writes
                              │
┌─────────────────────────────▼───────────────────────────────────────────┐
│                         DATA STORAGE LAYER                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUT (PDF Source):                                                    │
│  ┌─────────────────────────────────────────────────────────┐           │
│  │  datasets/raw/master_directions/pdfs/  (IMMUTABLE)      │           │
│  │    ├── MD10190.pdf                                      │           │
│  │    ├── MD10191.pdf                                      │           │
│  │    └── ... (354 original documents)                     │           │
│  └─────────────────────────────────────────────────────────┘           │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────┐           │
│  │  datasets/raw/uploaded_documents/pdfs/  (NEW)           │           │
│  │    ├── UP20260715_0001.pdf                              │           │
│  │    ├── UP20260715_0002.pdf                              │           │
│  │    └── ...                                              │           │
│  └─────────────────────────────────────────────────────────┘           │
│                                                                         │
│  INTERMEDIATE ARTIFACTS (Shared by both datasets):                      │
│  ┌─────────────────────────────────────────────────────────┐           │
│  │  datasets/parsed/{document_id}.json                     │           │
│  │  datasets/normalized/{document_id}.json                 │           │
│  │  datasets/hierarchy/{document_id}.json                  │           │
│  │  datasets/logical_units/{document_id}.json              │           │
│  │  datasets/requirements/{document_id}.json               │           │
│  │  datasets/enriched_requirements/{document_id}.json      │           │
│  │  datasets/interpreted_controls/{document_id}.json       │           │
│  │  datasets/reasoned_controls/{document_id}.json          │           │
│  │  datasets/controls/{document_id}.json                   │           │
│  │  datasets/verification_rules/{document_id}.json         │           │
│  │  datasets/verification_plans/{document_id}.json         │           │
│  │  datasets/maps/{document_id}.json                       │           │
│  └─────────────────────────────────────────────────────────┘           │
│                                                                         │
│  DATABASE:                                                              │
│  ┌─────────────────────────────────────────────────────────┐           │
│  │  backend/database.db (SQLite)                           │           │
│  │    ├── controls (from both MD and UP documents)         │           │
│  │    ├── management_action_plans (MAPs)                   │           │
│  │    ├── control_assignments                              │           │
│  │    └── ...                                              │           │
│  └─────────────────────────────────────────────────────────┘           │
│                                                                         │
│  DASHBOARD:                                                             │
│  ┌─────────────────────────────────────────────────────────┐           │
│  │  datasets/frontend/frontend_state.json                  │           │
│  │    (Aggregated data from all documents)                 │           │
│  └─────────────────────────────────────────────────────────┘           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Original RBI Documents (MD Prefix)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  EXISTING WORKFLOW (Unchanged)                                          │
└─────────────────────────────────────────────────────────────────────────┘

  CLI Execution:
  $ python pipeline/orchestrator/document_orchestrator.py MD10190

  ┌──────────────────────────────────────────┐
  │  DocumentPipelineOrchestrator()          │
  │  (No pdf_source_dir parameter)           │
  └──────────────┬───────────────────────────┘
                 │
                 │ Default behavior
                 │
  ┌──────────────▼───────────────────────────┐
  │  pdf_source_dir =                        │
  │    datasets/raw/master_directions/pdfs/  │
  └──────────────┬───────────────────────────┘
                 │
                 │
  ┌──────────────▼───────────────────────────┐
  │  Read: MD10190.pdf                       │
  └──────────────┬───────────────────────────┘
                 │
                 │ 14-stage pipeline
                 │
  ┌──────────────▼───────────────────────────┐
  │  Write artifacts:                        │
  │    • parsed/MD10190.json                 │
  │    • controls/MD10190.json               │
  │    • maps/MD10190.json                   │
  │    • ... (all stages)                    │
  └──────────────┬───────────────────────────┘
                 │
                 │
  ┌──────────────▼───────────────────────────┐
  │  Database Ingest (document-scoped)       │
  │    ingest(document_id="MD10190")         │
  └──────────────┬───────────────────────────┘
                 │
                 │
  ┌──────────────▼───────────────────────────┐
  │  Dashboard Aggregator                    │
  │    Updates frontend_state.json           │
  └──────────────────────────────────────────┘
```

---

## Data Flow: Uploaded Documents (UP Prefix)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  NEW WORKFLOW (Upload Feature)                                          │
└─────────────────────────────────────────────────────────────────────────┘

  API Request:
  POST /documents/upload (with PDF file)

  ┌──────────────────────────────────────────┐
  │  Upload Endpoint Handler                 │
  │    • Validate PDF                        │
  │    • Generate ID: UP20260715_0001        │
  │    • Save to upload directory            │
  │    • Queue background task               │
  │    • Return immediately                  │
  └──────────────┬───────────────────────────┘
                 │
                 │ Background Task
                 │
  ┌──────────────▼───────────────────────────┐
  │  _run_uploaded_document_pipeline()       │
  │                                          │
  │  DocumentPipelineOrchestrator(           │
  │    pdf_source_dir=uploaded_docs_pdfs     │  ← Dependency Injection
  │  )                                       │
  └──────────────┬───────────────────────────┘
                 │
                 │ Custom pdf_source_dir
                 │
  ┌──────────────▼───────────────────────────┐
  │  pdf_source_dir =                        │
  │    datasets/raw/uploaded_documents/pdfs/ │
  └──────────────┬───────────────────────────┘
                 │
                 │
  ┌──────────────▼───────────────────────────┐
  │  Read: UP20260715_0001.pdf               │
  └──────────────┬───────────────────────────┘
                 │
                 │ 14-stage pipeline (identical)
                 │
  ┌──────────────▼───────────────────────────┐
  │  Write artifacts:                        │
  │    • parsed/UP20260715_0001.json         │
  │    • controls/UP20260715_0001.json       │
  │    • maps/UP20260715_0001.json           │
  │    • ... (all stages)                    │
  └──────────────┬───────────────────────────┘
                 │
                 │
  ┌──────────────▼───────────────────────────┐
  │  Database Ingest (document-scoped)       │
  │    ingest(document_id="UP20260715_0001") │
  └──────────────┬───────────────────────────┘
                 │
                 │
  ┌──────────────▼───────────────────────────┐
  │  Dashboard Aggregator                    │
  │    Updates frontend_state.json           │
  │    (Includes both MD and UP documents)   │
  └──────────────────────────────────────────┘
```

---

## Dependency Injection Pattern

```
┌─────────────────────────────────────────────────────────────────────────┐
│  WHY DEPENDENCY INJECTION?                                              │
└─────────────────────────────────────────────────────────────────────────┘

  APPROACH A (Rejected): Document-Type Routing
  ┌──────────────────────────────────────────┐
  │  Orchestrator                            │
  │                                          │
  │  if document_id.startswith("MD"):        │
  │      pdf_dir = master_directions         │  ❌ Tight coupling
  │  elif document_id.startswith("UP"):      │  ❌ Orchestrator knows
  │      pdf_dir = uploaded_documents        │     about doc types
  │  else:                                   │  ❌ Future types need
  │      raise ValueError()                  │     orchestrator changes
  └──────────────────────────────────────────┘


  APPROACH B (Selected): Dependency Injection
  ┌──────────────────────────────────────────┐
  │  Upload Endpoint                         │
  │                                          │
  │  DocumentPipelineOrchestrator(           │  ✅ Loose coupling
  │    pdf_source_dir=uploaded_docs_pdfs     │  ✅ Orchestrator is
  │  )                                       │     document-agnostic
  └─────────────┬────────────────────────────┘  ✅ Future extensibility
                │                                   without changes
                │
  ┌─────────────▼────────────────────────────┐
  │  Orchestrator (Generic)                  │
  │                                          │
  │  def __init__(self, project_root,        │
  │               pdf_source_dir=None):      │
  │      self.paths["raw_pdf"] =             │
  │        pdf_source_dir or default         │
  └──────────────────────────────────────────┘
```

---

## Key Architectural Principles

### 1. Separation of Concerns
```
┌─────────────────────────────────────────────────────────────────┐
│  Upload Endpoint        │  Orchestrator        │  Pipeline     │
├─────────────────────────┼──────────────────────┼───────────────┤
│  • File validation      │  • Stage execution   │  • PDF parse  │
│  • Document ID gen      │  • Error handling    │  • Extract    │
│  • Path determination   │  • Logging           │  • Generate   │
│  • Background queue     │  • Validation        │  • Transform  │
└─────────────────────────┴──────────────────────┴───────────────┘
   ↑                         ↑                      ↑
   Knows about document      Document-agnostic      Business logic
   sources and types                                only
```

### 2. Immutability of Original Dataset
```
┌─────────────────────────────────────────────────────────────────┐
│  datasets/raw/                                                  │
│  ├── master_directions/  ← IMMUTABLE (read-only, preserved)    │
│  │   ├── pdfs/                                                 │
│  │   └── metadata.csv                                          │
│  │                                                             │
│  └── uploaded_documents/ ← MUTABLE (write-enabled, separate)   │
│      └── pdfs/                                                 │
└─────────────────────────────────────────────────────────────────┘

  No code path can modify master_directions
  Uploaded documents completely independent
```

### 3. Backward Compatibility
```
┌─────────────────────────────────────────────────────────────────┐
│  BEFORE (Original Behavior)                                     │
│  ────────────────────────────────────────────────────────────── │
│  orchestrator = DocumentPipelineOrchestrator(project_root)      │
│  orchestrator.process_document("MD10190")                       │
│                                                                 │
│  → Uses: datasets/raw/master_directions/pdfs/MD10190.pdf        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  AFTER (Still Works Identically)                                │
│  ────────────────────────────────────────────────────────────── │
│  orchestrator = DocumentPipelineOrchestrator(project_root)      │
│  orchestrator.process_document("MD10190")                       │
│                                                                 │
│  → Uses: datasets/raw/master_directions/pdfs/MD10190.pdf        │
│         (Default behavior preserved)                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  NEW (Upload Feature)                                           │
│  ────────────────────────────────────────────────────────────── │
│  orchestrator = DocumentPipelineOrchestrator(                   │
│      project_root,                                              │
│      pdf_source_dir=uploaded_docs_pdfs  ← Optional parameter    │
│  )                                                              │
│  orchestrator.process_document("UP20260715_0001")               │
│                                                                 │
│  → Uses: datasets/raw/uploaded_documents/pdfs/UP...pdf          │
│         (New behavior via dependency injection)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Interaction Diagram

```
                            User Action
                                 │
                                 │ Upload PDF
                                 ▼
        ┌────────────────────────────────────────┐
        │      Frontend Application              │
        │  (React Upload Component)              │
        └────────────────┬───────────────────────┘
                         │ POST /documents/upload
                         │ Authorization: Bearer <token>
                         │ Content-Type: multipart/form-data
                         │
        ┌────────────────▼───────────────────────┐
        │     FastAPI Backend                    │
        │  • Authentication Middleware           │
        │  • Permission Check (DOC_UPLOAD)       │
        └────────────────┬───────────────────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
  ┌──────────────────┐      ┌──────────────────┐
  │  Sync Handler    │      │ Background Task  │
  │                  │      │                  │
  │  • Validate      │      │  • Orchestrator  │
  │  • Save PDF      │      │  • Pipeline      │
  │  • Generate ID   │      │  • Ingest        │
  │  • Queue Task    │      │  • Dashboard     │
  │  • Return 200    │      │                  │
  └──────────────────┘      └────────┬─────────┘
            │                        │
            │ Immediate Response     │ ~1 minute later
            │                        │
            ▼                        ▼
  ┌──────────────────┐      ┌──────────────────┐
  │  User sees:      │      │  Database        │
  │  • Document ID   │      │  • Controls      │
  │  • Status        │      │  • MAPs          │
  │  "Processing"    │      │  • Assignments   │
  └──────────────────┘      └────────┬─────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │  Dashboard UI    │
                            │  Shows new MAPs  │
                            │  from uploaded   │
                            │  document        │
                            └──────────────────┘
```

---

## File System Layout

```
D:\SuRaksha-v2/
│
├── backend/
│   ├── main.py                         ← Modified: Added upload endpoint
│   ├── permissions.py                  ← Existing: DOC_UPLOAD permission
│   └── database/
│       └── ingest.py                   ← Existing: Document-scoped mode
│
├── pipeline/
│   └── orchestrator/
│       └── document_orchestrator.py    ← Modified: Added pdf_source_dir param
│
├── datasets/
│   ├── raw/
│   │   ├── master_directions/          ← IMMUTABLE
│   │   │   ├── pdfs/
│   │   │   │   ├── MD10190.pdf
│   │   │   │   ├── MD10191.pdf
│   │   │   │   └── ... (354 files)
│   │   │   └── metadata.csv
│   │   │
│   │   └── uploaded_documents/         ← NEW
│   │       └── pdfs/
│   │           ├── UP20260715_0001.pdf
│   │           └── UP20260715_0002.pdf
│   │
│   ├── parsed/                         ← Shared by both datasets
│   │   ├── MD10190.json
│   │   └── UP20260715_0001.json
│   │
│   ├── controls/                       ← Shared by both datasets
│   │   ├── MD10190.json
│   │   └── UP20260715_0001.json
│   │
│   ├── maps/                           ← Shared by both datasets
│   │   ├── MD10190.json
│   │   └── UP20260715_0001.json
│   │
│   └── frontend/
│       └── frontend_state.json         ← Aggregates both datasets
│
├── test_upload_feature.py              ← NEW: Validation script
├── UPLOAD_FEATURE_IMPLEMENTATION_REPORT.md    ← NEW: Full docs
├── UPLOAD_FEATURE_QUICKSTART.md        ← NEW: Developer guide
├── UPLOAD_IMPLEMENTATION_SUMMARY.md    ← NEW: Executive summary
└── UPLOAD_ARCHITECTURE_DIAGRAM.md      ← NEW: This file
```

---

## Security & Permission Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Authentication & Authorization Flow                            │
└─────────────────────────────────────────────────────────────────┘

  Request: POST /documents/upload
       ↓
  ┌───────────────────────────────────────┐
  │ 1. Extract JWT from Authorization     │
  │    header                             │
  └───────────────┬───────────────────────┘
                  │
                  ▼
  ┌───────────────────────────────────────┐
  │ 2. Verify JWT signature and expiry    │
  └───────────────┬───────────────────────┘
                  │
                  ▼
  ┌───────────────────────────────────────┐
  │ 3. Extract user ID and role from      │
  │    JWT claims                         │
  └───────────────┬───────────────────────┘
                  │
                  ▼
  ┌───────────────────────────────────────┐
  │ 4. Check if user has DOC_UPLOAD       │
  │    permission                         │
  │                                       │
  │    Roles with DOC_UPLOAD:             │
  │    • Super Admin (wildcard)           │
  │    • Admin                            │
  │    • Compliance Head                  │
  └───────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
   ✅ Allowed          ❌ Denied
        │                   │
        │                   ▼
        │              Return 403
        │              Forbidden
        │
        ▼
   Process Upload
```

---

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Upload Error Handling                                          │
└─────────────────────────────────────────────────────────────────┘

  POST /documents/upload
       ↓
  ┌───────────────────────────────────────┐
  │ Validate: Is PDF?                     │
  └───────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
       Yes                 No → 400 "Only PDF files accepted"
        │
        ▼
  ┌───────────────────────────────────────┐
  │ Validate: Size < 50MB?                │
  └───────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
       Yes                 No → 400 "File too large"
        │
        ▼
  ┌───────────────────────────────────────┐
  │ Generate Document ID                  │
  └───────────────┬───────────────────────┘
                  │
                  ▼
  ┌───────────────────────────────────────┐
  │ Save PDF to Disk                      │
  └───────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
     Success             Failure → 500 "Failed to save"
        │                           (with logging)
        ▼
  ┌───────────────────────────────────────┐
  │ Queue Background Task                 │
  └───────────────┬───────────────────────┘
                  │
                  ▼
  ┌───────────────────────────────────────┐
  │ Return 200 with Document ID           │
  └───────────────────────────────────────┘


  Background Task:
  ┌───────────────────────────────────────┐
  │ Pipeline Execution                    │
  └───────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
     Success             Failure
        │                   │
        │                   ▼
        │              Log error to
        │              logs/orchestrator.log
        │              (User not notified)
        │
        ▼
  ┌───────────────────────────────────────┐
  │ Controls and MAPs generated           │
  │ Available in dashboard                │
  └───────────────────────────────────────┘
```

---

This diagram provides a visual representation of the upload feature architecture, showing how all components interact while maintaining the immutability of the original RBI dataset.
