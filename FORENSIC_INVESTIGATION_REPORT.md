# Forensic Investigation Report: MAP Database Ingestion Failure

**Investigation Date:** 2026-01-XX  
**Document ID Tested:** UP20260715_0001  
**Issue:** Session Dashboard shows MAPs=0 and Departments=0 despite successful pipeline execution

---

## Executive Summary

**ROOT CAUSE IDENTIFIED:** Field name mismatch between MAP JSON schema and Session Dashboard endpoint

**STATUS:** MAPs ARE being ingested into the database correctly. The problem is in the Session Dashboard's JSON parsing logic.

**DATABASE STATE:** 
- ✅ 53 MAPs exist in database for UP20260715_0001
- ✅ All MAPs correctly assigned to "Compliance" department
- ✅ Database ingestion pipeline is working correctly

**ACTUAL BUG:**
The Session Dashboard endpoint (`GET /documents/{document_id}/session`) reads from JSON files and looks for a field called `department`, but the MAP Generator produces JSONs with the field `owner_department`.

---

## Complete Call Chain Trace

### 1. Upload Endpoint
**File:** `backend/main.py`  
**Function:** `upload_document`  
**Line:** 579-652  
**Execution:** ✅ EXECUTES  

**Flow:**
1. Receives file upload
2. Validates PDF format and size
3. Generates document ID: `UP{YYYYMMDD}_{NNNN}`
4. Saves PDF to `datasets/raw/uploaded_documents/pdfs/`
5. Queues background task `_run_uploaded_document_pipeline`

**Database Tables Written:** NONE (only file I/O)  
**Returned Value:** 
```json
{
  "document_id": "UP20260715_0001",
  "status": "processing",
  "message": "Document uploaded successfully. Processing in background."
}
```

---

### 2. Background Pipeline Orchestration
**File:** `backend/main.py`  
**Function:** `_run_uploaded_document_pipeline`  
**Line:** 536-572  
**Execution:** ✅ EXECUTES  

**Flow:**
1. Imports `DocumentPipelineOrchestrator`
2. Instantiates with `pdf_source_dir` = uploaded_documents/pdfs
3. Calls `orchestrator.process_document(document_id)`

**Skip Conditions:** NONE  
**Database Tables Written:** NONE (delegates to orchestrator)  
**Returned Value:** N/A (background task, logs results)

---

### 3. Document Pipeline Orchestrator
**File:** `pipeline/orchestrator/document_orchestrator.py`  
**Function:** `process_document`  
**Line:** 228-766  
**Execution:** ✅ EXECUTES  

**Flow:** Executes 14 sequential stages:
1. ✅ PDF Parser → `datasets/parsed/{doc_id}.json`
2. ✅ Document Normalizer → `datasets/normalized/{doc_id}.json`
3. ✅ Hierarchy Builder → `datasets/hierarchy/{doc_id}.json`
4. ✅ Logical Unit Builder → `datasets/logical_units/{doc_id}.json`
5. ✅ Requirement Extractor → `datasets/requirements/{doc_id}.json`
6. ✅ Requirement Enricher → `datasets/enriched_requirements/{doc_id}.json`
7. ✅ Compliance Interpreter → `datasets/interpreted_controls/{doc_id}.json`
8. ✅ Compliance Reasoning Engine → `datasets/reasoned_controls/{doc_id}.json`
9. ✅ Control Deriver → `datasets/controls/{doc_id}.json`
10. ✅ Verification Rule Generator → `datasets/verification_rules/{doc_id}.json`
11. ✅ Verification Planner → `datasets/verification_plans/{doc_id}.json`
12. ✅ MAP Generator → `datasets/maps/{doc_id}.json`
13. ✅ **Database Ingest** → WRITES TO DATABASE
14. ✅ Dashboard Aggregator → `datasets/frontend/frontend_state.json`

**Skip Conditions:** Stops on first failed stage (none failed for test document)  
**Database Tables Written:** Via Stage 13 (Database Ingest)  
**Returned Value:** `OrchestrationResult` with status="SUCCESS"

---

### 4. Database Ingest Entry Point
**File:** `backend/database/ingest.py`  
**Function:** `ingest`  
**Line:** 13-53  
**Execution:** ✅ EXECUTES  

**Flow:**
1. Creates database session
2. Instantiates `PipelineIngestionService(db)`
3. **Document-scoped mode:** Reads `datasets/controls/{document_id}.json`
4. Calls `service.ingest_document(data)` → ingests controls
5. Reads `datasets/maps/{document_id}.json`
6. Calls `service.ingest_maps(data)` → ingests MAPs

**Skip Conditions:** NONE (document_id provided)  
**Database Tables Written:** 
- Calls `service.ingest_document()` 
- Calls `service.ingest_maps()`

**Returned Value:** NONE (prints status messages)

---

### 5. MAP Ingestion Service
**File:** `backend/database/services/pipeline_ingestion_service.py`  
**Function:** `ingest_maps`  
**Line:** 95-184  
**Execution:** ✅ EXECUTES  

**Flow:**
1. Reads MAP JSON: `maps_json = {..., "maps": [...]}`
2. For each MAP in `maps_json["maps"]`:
   - **Resolves Department:** `dept_name = map_data.get("owner_department", "Unknown")`
   - Upserts department to `departments` table
   - **Resolves Control:** Parses `control_id` → finds `requirement_id` → queries `requirement_control_mapping` → gets `control.id`
   - **Derives AI fields:** priority, ai_rationale, verification_plan, automation_percent, risk_score
   - **Upserts MAP:** Inserts/updates row in `management_action_plans` table
3. Commits transaction

**Database Tables Written:**
- ✅ `departments` (upsert)
- ✅ `management_action_plans` (upsert)

**Returned Value:** NONE (commits to database, logs success)

**DATABASE VERIFICATION:**
```sql
SELECT COUNT(*) FROM management_action_plans 
WHERE source_document_id = 'UP20260715_0001';
-- Result: 53 rows ✅

SELECT DISTINCT d.name 
FROM management_action_plans m
JOIN departments d ON m.department_id = d.id
WHERE m.source_document_id = 'UP20260715_0001';
-- Result: "Compliance" ✅
```

---

## Session Dashboard Endpoint Bug

**File:** `backend/main.py`  
**Function:** `get_document_session`  
**Line:** 452-523  
**Execution:** ✅ EXECUTES when frontend requests `/documents/{document_id}/session`

**Flow:**
1. Reads `datasets/parsed/{document_id}.json`
2. Reads `datasets/requirements/{document_id}.json`
3. **Reads `datasets/maps/{document_id}.json`**
4. Parses `maps_list = maps_data.get("maps", [])`
5. **BUG HERE:** `departments = {m.get("department") for m in maps_list if m.get("department")}`

**THE PROBLEM:**
- MAP JSON schema uses: `"owner_department": "Compliance"`
- Session endpoint looks for: `"department": ...`
- Result: `departments` set is EMPTY
- Result: `departments_count = 0`
- Result: `maps_count` shows count from JSON (53) but dashboard shows wrong department count

---

## Evidence: Field Name Mismatch

### MAP JSON Schema (Generated by MAP Generator)
```json
{
  "map_id": "MAP_UP20260715_0001_ctrl_req5_1",
  "control_id": "UP20260715_0001_ctrl_req5_1",
  "document_id": "UP20260715_0001",
  "title": "MAP: ...",
  "owner_department": "Compliance",  ← USES THIS FIELD
  "department": null,                ← THIS IS NULL
  "compliance_domain": [...],
  "tasks": [...]
}
```

### Session Endpoint Parsing Logic (backend/main.py:486)
```python
departments = {m.get("department") for m in maps_list if m.get("department")}
#                    ^^^^^^^^^^^ LOOKS FOR THIS FIELD
```

### Correct Field in Ingestion Service (pipeline_ingestion_service.py:101)
```python
dept_name = map_data.get("owner_department", "Unknown")
#                        ^^^^^^^^^^^^^^^^^^ USES CORRECT FIELD
```

---

## Root Cause Analysis

**Execution stops before MAP rows are inserted:** ❌ FALSE  
**MAP rows ARE being inserted:** ✅ TRUE (verified in database)

**The REAL issue:** Session Dashboard endpoint has a field name bug that causes it to report incorrect statistics.

### Why Assignment Center Shows Historical MAPs

The Assignment Center queries the `management_action_plans` table directly:
```python
GET /maps  # Queries database table
```

Historical MAPs exist from previous document ingestion runs. The bug does NOT affect database queries - only the session endpoint's JSON parsing.

---

## Execution Tree

```
POST /documents/upload
  └─→ _run_uploaded_document_pipeline (BackgroundTask)
       └─→ DocumentPipelineOrchestrator.process_document()
            ├─→ Stage 1-11: Generate JSONs ✅
            ├─→ Stage 12: MAP Generator ✅
            │    └─→ datasets/maps/UP20260715_0001.json
            │         └─→ Contains: owner_department="Compliance"
            │
            ├─→ Stage 13: Database Ingest ✅
            │    └─→ ingest(document_id)
            │         └─→ PipelineIngestionService.ingest_maps()
            │              ├─→ Reads: map_data.get("owner_department") ✅
            │              ├─→ Upserts departments table ✅
            │              └─→ Inserts 53 rows into management_action_plans ✅
            │
            └─→ Stage 14: Dashboard Aggregator ✅

GET /documents/{document_id}/session (Frontend Request)
  └─→ get_document_session()
       ├─→ Reads datasets/maps/UP20260715_0001.json ✅
       ├─→ Parses: m.get("department") ❌ WRONG FIELD
       └─→ Returns: departments_count=0 ❌ BUG HERE
```

---

## Proof of Execution

### Database State
```python
# Query executed:
from backend.database.session import SessionLocal
from backend.database.models import ManagementActionPlan

db = SessionLocal()
maps = db.query(ManagementActionPlan).filter(
    ManagementActionPlan.source_document_id == 'UP20260715_0001'
).all()

# Result: 53 rows ✅
```

### File System State
```
datasets/maps/UP20260715_0001.json → EXISTS ✅ (53 MAPs)
datasets/controls/UP20260715_0001.json → EXISTS ✅
datasets/requirements/UP20260715_0001.json → EXISTS ✅
```

---

## Conclusion

**Execution Path Status:** COMPLETE - all 14 stages executed successfully  
**Database Insertion Status:** SUCCESS - 53 MAPs inserted  
**Bug Location:** Session Dashboard endpoint JSON parsing  
**Field Name Inconsistency:**
- MAP Generator produces: `owner_department`
- Database Ingestion reads: `owner_department` ✅
- Session Endpoint reads: `department` ❌

**Next Steps:**
1. Fix `get_document_session` to use `owner_department` instead of `department`
2. OR fix MAP Generator to populate both fields for backward compatibility
3. Verify fix resolves Session Dashboard display issue

**No changes needed to:**
- Upload endpoint ✅
- Pipeline orchestrator ✅
- Database ingestion service ✅
- MAP Generator ✅ (schema is correct)

---

## Visual Summary

### What Actually Happens (DATABASE) ✅
```
Upload → Pipeline → MAP Generator → Database Ingestion
                         ↓                    ↓
                   owner_department    reads owner_department
                         ↓                    ↓
                   "Compliance"         ✅ 53 MAPs in DB
                                        ✅ Department: Compliance
```

### What Session Dashboard Shows (JSON PARSING) ❌
```
Frontend → GET /session → reads maps JSON → looks for "department" field
                               ↓                        ↓
                         "department": null      departments_count = 0
                         "owner_department": "Compliance"  ← IGNORED
```

### Fix Location
**File:** `backend/main.py`  
**Line:** 486  
**Change:**
```python
# BEFORE (WRONG):
departments = {m.get("department") for m in maps_list if m.get("department")}

# AFTER (CORRECT):
departments = {m.get("owner_department") for m in maps_list if m.get("owner_department")}
```

Also update line 490-492:
```python
# BEFORE:
dept_maps = [m for m in maps_list if m.get("department") == dept]

# AFTER:
dept_maps = [m for m in maps_list if m.get("owner_department") == dept]
```
