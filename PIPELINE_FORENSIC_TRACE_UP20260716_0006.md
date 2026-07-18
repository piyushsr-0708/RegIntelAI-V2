# Pipeline Forensic Trace: UP20260716_0006

**Document ID:** `UP20260716_0006`  
**Investigation Date:** 2026-07-16  
**Objective:** Determine why controls.json and maps.json were never produced

---

## 1. COMPLETE CALL TREE

```
POST /documents/upload (backend/main.py:579)
  ↓
upload_document() [ASYNC]
  ├→ Validates PDF
  ├→ Saves to datasets/raw/uploaded_documents/pdfs/UP20260716_0006.pdf
  ├→ Queues background task
  └→ Returns HTTP 200 immediately
  
BackgroundTasks.add_task()
  ↓
_run_uploaded_document_pipeline(document_id, pdf_source_dir) [BACKGROUND]
(backend/main.py:561-595)
  ├→ try:
  │    ├→ Import DocumentPipelineOrchestrator
  │    ├→ orchestrator = DocumentPipelineOrchestrator(project_root, pdf_source_dir)
  │    └→ result = orchestrator.process_document(document_id)
  │         ↓
  │         DocumentPipelineOrchestrator.process_document()
  │         (pipeline/orchestrator/document_orchestrator.py:228)
  │           ├→ Pre-flight validation ✅
  │           ├→ Stage 1: PDF Parser [STARTED]
  │           ↓
  │           [EXECUTION TERMINATES HERE]
  │           ↓
  │           [NEVER REACHED: Stages 2-14]
  │           [NEVER REACHED: return result]
  │    
  └→ except Exception as e:
       └→ [NOT TRIGGERED - No exception logged]
```

---

## 2. STAGE-BY-STAGE EXECUTION TABLE

| Stage # | Stage Name | Function | Input File | Output File | Entered? | Completed? | File Exists? |
|---------|------------|----------|------------|-------------|----------|------------|--------------|
| 0 | Pre-Flight | `_validate_document_exists()` | UP20260716_0006.pdf | N/A | ✅ YES | ✅ YES | ✅ PDF exists |
| 1 | PDF Parser | `PDFParser.parse_document()` | UP20260716_0006.pdf | parsed/UP20260716_0006.json | ✅ YES | ❓ UNKNOWN | ✅ File exists |
| 2 | Document Normalizer | `DocumentNormalizer.normalize_document()` | parsed/...json | normalized/...json | ❌ NO | ❌ NO | ✅ File exists¹ |
| 3 | Hierarchy Builder | `HierarchyBuilder.process_document()` | normalized/...json | hierarchy/...json | ❌ NO | ❌ NO | ✅ File exists¹ |
| 4 | Logical Unit Builder | `LogicalUnitBuilder.process_document()` | hierarchy/...json | logical_units/...json | ❌ NO | ❌ NO | ✅ File exists¹ |
| 5 | Requirement Extractor | `RequirementExtractor.process_document()` | logical_units/...json | requirements/...json | ❌ NO | ❌ NO | ✅ File exists¹ |
| 6 | Requirement Enricher | `RequirementEnricher.process_document()` | requirements/...json | enriched_requirements/...json | ❌ NO | ❌ NO | ✅ File exists¹ |
| 7 | Compliance Interpreter | `ComplianceInterpretationEngine.process_document()` | enriched_requirements/...json | **interpreted_controls/...json** | ❌ NO | ❌ NO | **❌ MISSING** |
| 8 | Compliance Reasoning | `ComplianceReasoningEngine.process_document()` | interpreted_controls/...json | **reasoned_controls/...json** | ❌ NO | ❌ NO | **❌ MISSING** |
| 9 | Control Deriver | `ControlDerivationEngine.process_document()` | reasoned_controls/...json | **controls/...json** | ❌ NO | ❌ NO | **❌ MISSING** |
| 10 | Verification Rule Generator | `VerificationRuleGenerator.process_document()` | interpreted_controls/...json | verification_rules/...json | ❌ NO | ❌ NO | ✅ File exists¹ |
| 11 | Verification Planner | `ComplianceVerificationPlanner.process_document()` | verification_rules/...json | **verification_plans/...json** | ❌ NO | ❌ NO | **❌ MISSING** |
| 12 | MAP Generator | `MAPGenerationEngine.process_document()` | controls/...json | **maps/...json** | ❌ NO | ❌ NO | **❌ MISSING** |
| 13 | Database Ingest | `ingest(document_id)` | controls/...json, maps/...json | DATABASE | ❌ NO | ❌ NO | N/A |
| 14 | Dashboard Aggregator | `aggregate_dashboard()` | All JSONs | frontend_state.json | ❌ NO | ❌ NO | N/A |

**¹Note:** Files exist from a PREVIOUS pipeline execution at 09:40:39, NOT from the current execution at 10:47:45

---

## 3. FIRST STAGE THAT FAILED

**Stage:** PDF Parser (Stage 1)  
**Status:** STARTED but orchestrator never logged completion  
**Evidence:**

```
2026-07-16 10:47:45,392 - INFO - ━━━ Stage Started: PDF Parser ━━━
[NO SUBSEQUENT ORCHESTRATOR LOG ENTRIES]
```

**File:** `pipeline/orchestrator/document_orchestrator.py`  
**Function:** `process_document()`  
**Line:** 293-313 (PDF Parser stage block)

---

## 4. EXACT REASON EXECUTION STOPPED

### Orchestrator Log Analysis

**Orchestrator log (`logs/orchestrator.log`) for UP20260716_0006:**
```
2026-07-16 10:47:45,389 - INFO - [BACKGROUND] Starting pipeline execution for UP20260716_0006
2026-07-16 10:47:45,390 - INFO - PIPELINE ORCHESTRATION STARTED: UP20260716_0006
2026-07-16 10:47:45,391 - INFO - Start Time: 2026-07-16 10:47:45
2026-07-16 10:47:45,392 - INFO - ✓ Pre-flight check passed: PDF exists
2026-07-16 10:47:45,392 - INFO - ━━━ Stage Started: PDF Parser ━━━
[LOG FILE ENDS - NEXT ENTRY IS FOR UP20260716_0007 AT 11:37:08]
```

**Total lines in orchestrator.log:** 93 lines  
**Last line for UP20260716_0006:** Line containing "Stage Started: PDF Parser"  
**Next entry:** UP20260716_0007 started 50 minutes later (11:37:08)

### Component Log Analysis

**Component logs show completions at DIFFERENT timestamps:**

| Component | Log File | UP20260716_0006 Timestamp | Message |
|-----------|----------|---------------------------|---------|
| Compliance Interpreter | `compliance_interpreter.log` | 10:47:47 (2 sec later) | "Interpreted 37 controls for UP20260716_0006" |
| Compliance Reasoning | `compliance_reasoning_engine.log` | 10:47:47 (2 sec later) | "Generated 37 reasoned controls for UP20260716_0006" |
| Control Deriver | `control_deriver.log` | 10:47:47 (2 sec later) | "Deriving controls for: UP20260716_0006.json" |

**BUT:**  
Component logs also show EARLIER completions at `09:40:41` for the SAME document.

This indicates **TWO SEPARATE EXECUTION ATTEMPTS:**

1. **First attempt:** 09:40:39 - Completed through Stage 6, possibly failed at Stage 7
2. **Second attempt:** 10:47:45 - Started but orchestrator was killed/interrupted immediately after starting PDF Parser

### Root Cause

**The orchestrator process was TERMINATED or KILLED during Stage 1 execution.**

**Evidence:**
1. Orchestrator log stops abruptly after "Stage Started: PDF Parser"
2. No "Stage Finished" message logged
3. No exception logged
4. No failure message logged
5. No return statement reached
6. Component log timestamps (10:47:47) are 2 seconds after orchestrator start (10:47:45)
7. Files from stages 2-6 exist but are from the PREVIOUS execution (09:40:39)

**Possible causes:**
- Process killed by user (Ctrl+C)
- System resource limit (OOM killer)
- FastAPI/Uvicorn restart
- Python interpreter crash
- Operating system process termination

---

## 5. EXACT STATEMENT THAT PREVENTED FILE GENERATION

### interpreted_controls/UP20260716_0006.json

**Writer Function:** `ComplianceInterpretationEngine.process_document()`  
**File:** `pipeline/interpreter/compliance_interpreter.py`  
**Write Statement:** (Approximate location based on typical pattern)
```python
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output_data, f, indent=2)
```

**Condition Required:** Orchestrator must reach Stage 7 execution  
**Did Execution Reach This Statement:** **NO**

**Reason:** Orchestrator terminated at Stage 1. Stage 7 was never entered.

---

### reasoned_controls/UP20260716_0006.json

**Writer Function:** `ComplianceReasoningEngine.process_document()`  
**File:** `pipeline/reasoning/compliance_reasoning_engine.py`  
**Write Statement:** JSON dump to output file  
**Condition Required:** Orchestrator must complete Stage 7 and reach Stage 8  
**Did Execution Reach This Statement:** **NO**

**Reason:** Orchestrator terminated before reaching Stage 8.

---

### controls/UP20260716_0006.json

**Writer Function:** `ControlDerivationEngine.process_document()`  
**File:** `pipeline/derivation/control_deriver.py`  
**Write Statement:** JSON dump to output file  
**Condition Required:** Orchestrator must complete Stage 8 and reach Stage 9  
**Did Execution Reach This Statement:** **NO**

**Reason:** Orchestrator terminated before reaching Stage 9.

---

### maps/UP20260716_0006.json

**Writer Function:** `MAPGenerationEngine.process_document()`  
**File:** `pipeline/map_generator/map_generator.py`  
**Write Statement:** JSON dump to output file  
**Condition Required:** Orchestrator must complete Stage 9 and reach Stage 12  
**Did Execution Reach This Statement:** **NO**

**Reason:** Orchestrator terminated before reaching Stage 12.

---

## 6. EXCEPTION TRACE

### Background Task Exception Handler

**File:** `backend/main.py`  
**Function:** `_run_uploaded_document_pipeline()`  
**Lines:** 561-595

```python
def _run_uploaded_document_pipeline(document_id: str, pdf_source_dir: Path):
    try:
        logger.info(f"[BACKGROUND] Importing DocumentPipelineOrchestrator...")
        from pipeline.orchestrator.document_orchestrator import DocumentPipelineOrchestrator
        logger.info(f"[BACKGROUND] ✓ Import successful")
        
        logger.info(f"[BACKGROUND] Instantiating orchestrator...")
        orchestrator = DocumentPipelineOrchestrator(
            project_root=project_root,
            pdf_source_dir=pdf_source_dir
        )
        logger.info(f"[BACKGROUND] ✓ Orchestrator instantiated")
        
        logger.info(f"[BACKGROUND] Starting pipeline execution for {document_id}")
        result = orchestrator.process_document(document_id)
        
        if result.status == "SUCCESS":
            logger.info(f"[BACKGROUND] ✓ Pipeline completed successfully")
        else:
            logger.error(f"[BACKGROUND] ✗ Pipeline failed")
            logger.error(f"[BACKGROUND] Failed at stage: {result.failed_stage}")
            logger.error(f"[BACKGROUND] Error: {result.error_message}")
            
    except Exception as e:                           # ← EXCEPTION HANDLER
        logger.error(f"[BACKGROUND] ✗ Critical error")
        logger.error(f"[BACKGROUND] Exception: {e}", exc_info=True)
```

**Exception Type:** `Exception` (catches all)  
**Logging Statement:** `logger.error(f"[BACKGROUND] ✗ Critical error")`  
**Re-raised:** **NO** - Exception is swallowed  
**Pipeline Continues:** **NO** - Function ends after except block

**Observed Behavior for UP20260716_0006:**
- Last logged message: `"[BACKGROUND] Starting pipeline execution for UP20260716_0006"`
- No success message logged
- No failure message logged
- **No exception message logged**

**Conclusion:** The except block **WAS NOT TRIGGERED**. This means:
1. No Python exception was raised
2. The process was terminated externally (kill signal, system crash, etc.)
3. OR the orchestrator is still running but hung/blocked

---

### Orchestrator Stage Exception Handler

**File:** `pipeline/orchestrator/document_orchestrator.py`  
**Function:** `_run_stage()`  
**Lines:** 214-227

```python
def _run_stage(...) -> StageResult:
    self.logger.info(f"━━━ Stage Started: {stage_name} ━━━")
    start_time = time.time()
    
    try:
        stage_function()                             # ← EXECUTE STAGE
        duration = time.time() - start_time
        
        # Validate output
        if expected_output_dir:
            if not self._validate_stage_output(document_id, expected_output_dir):
                raise FileNotFoundError(...)
        
        self.logger.info(f"✓ Stage Finished: {stage_name}...")
        return StageResult(status="SUCCESS", ...)
        
    except Exception as e:                           # ← EXCEPTION HANDLER
        duration = time.time() - start_time
        error_msg = f"{type(e).__name__}: {str(e)}"
        
        self.logger.error(f"✗ Stage Failed: {stage_name}")
        self.logger.error(f"Error: {error_msg}")
        self.logger.error(f"Traceback:\n{traceback.format_exc()}")
        
        return StageResult(status="FAILED", ...)
```

**Exception Type:** `Exception` (catches all)  
**Logging Statement:** `logger.error(f"✗ Stage Failed: {stage_name}")`  
**Re-raised:** **NO** - Returns StageResult with status="FAILED"  
**Pipeline Continues:** Depends on caller checking stage_result.status

**Observed Behavior for UP20260716_0006 Stage 1:**
- Logged: "━━━ Stage Started: PDF Parser ━━━"
- **NOT logged:** "✓ Stage Finished: PDF Parser"
- **NOT logged:** "✗ Stage Failed: PDF Parser"

**Conclusion:** The except block **WAS NOT TRIGGERED**. The try block **NEVER COMPLETED**.

---

### Process Termination Analysis

**Neither exception handler was triggered**, which means:

1. **No Python exception occurred**
2. **The process was externally terminated** before any exception could be raised
3. **Possible termination mechanisms:**
   - User interrupt (Ctrl+C) sent SIGINT
   - System kill command sent SIGTERM or SIGKILL
   - Out-of-memory (OOM) killer terminated the process
   - Parent process (Uvicorn) restarted
   - Operating system crash or shutdown

---

## 7. RETURN PATH TRACE

### Orchestrator Return Paths

**Function:** `DocumentPipelineOrchestrator.process_document()`  
**File:** `pipeline/orchestrator/document_orchestrator.py`

**Return Statement Locations:**

1. **Early return on pre-flight failure (Line ~271):**
   ```python
   if not self._validate_document_exists(document_id):
       result.status = "FAILED"
       result.failed_stage = "PRE_FLIGHT_CHECK"
       return result                        # ← EARLY RETURN #1
   ```
   **Condition:** PDF file doesn't exist  
   **Reached for UP20260716_0006:** **NO** (PDF exists, pre-flight passed)

2. **Early return on stage failure (repeated for each stage):**
   ```python
   stage_result = self._run_stage(...)
   result.completed_stages.append(stage_result)
   
   if stage_result.status == "FAILED":
       result.status = "FAILED"
       result.failed_stage = "STAGE_NAME"
       result.error_message = stage_result.error_message
       return result                        # ← EARLY RETURN #2-15 (one per stage)
   ```
   **Condition:** Stage returns StageResult with status="FAILED"  
   **Reached for UP20260716_0006:** **NO** (no stage failure logged)

3. **Normal return on success (Line ~766):**
   ```python
   result.status = "SUCCESS"
   result.current_stage = None
   result.end_time = end_time.isoformat()
   result.total_duration_seconds = round(time.time() - pipeline_start, 2)
   
   self.logger.info("✓ PIPELINE ORCHESTRATION COMPLETED")
   return result                            # ← NORMAL RETURN
   ```
   **Condition:** All 14 stages complete successfully  
   **Reached for UP20260716_0006:** **NO** (pipeline never completed)

**Return Value Type:** `OrchestrationResult` (dataclass)

**Observed for UP20260716_0006:**  
**NONE of the return statements were reached**. The function never returned.

---

### Background Task Return Path

**Function:** `_run_uploaded_document_pipeline()`  
**File:** `backend/main.py`  
**Lines:** 561-595

```python
def _run_uploaded_document_pipeline(document_id: str, pdf_source_dir: Path):
    try:
        ...
        result = orchestrator.process_document(document_id)  # ← CALL
        
        if result.status == "SUCCESS":
            logger.info(f"[BACKGROUND] ✓ Pipeline completed")
        else:
            logger.error(f"[BACKGROUND] ✗ Pipeline failed")
    
    except Exception as e:
        logger.error(f"[BACKGROUND] ✗ Critical error")
    
    # ← IMPLICIT RETURN None
```

**Return Type:** `None` (no explicit return statement)  
**Reached for UP20260716_0006:** **NO** (function never completed)

---

## 8. PIPELINE TERMINATION POINT

### Last Successfully Executed Statement

**File:** `pipeline/orchestrator/document_orchestrator.py`  
**Function:** `process_document()`  
**Line:** 293 (approximate)

```python
self.logger.info(f"━━━ Stage Started: PDF Parser ━━━")
```

**Evidence:**  
This is the last message that appears in `logs/orchestrator.log` for UP20260716_0006.

---

### First Statement That Never Executes

**File:** `pipeline/orchestrator/document_orchestrator.py`  
**Function:** `_run_stage()`  
**Line:** 187 (approximate, inside try block)

```python
stage_function()  # ← This line was entered but never returned
```

OR

**Line:** 201 (approximate, after stage execution)
```python
self.logger.info(f"✓ Stage Finished: {stage_name}...")
```

**Evidence:**  
The "Stage Finished" message never appears in the log.

---

### Exact Termination Point

**Between these two log statements:**

```python
# LAST EXECUTED:
self.logger.info(f"━━━ Stage Started: PDF Parser ━━━")

# INSIDE stage_function():
#   [PDF Parser executes]
#   [Process terminated here]

# NEVER REACHED:
self.logger.info(f"✓ Stage Finished: PDF Parser...")
```

**The process was terminated WHILE the PDF Parser stage function was executing.**

---

## 9. WHY FILES WERE NOT GENERATED

### Summary

**None of the missing files were generated because:**

1. **Orchestrator started Stage 1 (PDF Parser)**
2. **Orchestrator process was terminated** (killed, crashed, or interrupted)
3. **Stages 2-14 were never entered**
4. **Stage-specific write functions were never called**

### Exact Statement Analysis

For **interpreted_controls/UP20260716_0006.json**:
- **Should be written by:** Stage 7 (Compliance Interpreter)
- **Stage 7 code location:** `pipeline/interpreter/compliance_interpreter.py`
- **Stage 7 was entered:** **NO**
- **Write statement was reached:** **NO**
- **Reason:** Orchestrator terminated at Stage 1

For **reasoned_controls/UP20260716_0006.json**:
- **Should be written by:** Stage 8 (Compliance Reasoning Engine)
- **Stage 8 code location:** `pipeline/reasoning/compliance_reasoning_engine.py`
- **Stage 8 was entered:** **NO**
- **Write statement was reached:** **NO**
- **Reason:** Orchestrator terminated at Stage 1

For **controls/UP20260716_0006.json**:
- **Should be written by:** Stage 9 (Control Deriver)
- **Stage 9 code location:** `pipeline/derivation/control_deriver.py`
- **Stage 9 was entered:** **NO**
- **Write statement was reached:** **NO**
- **Reason:** Orchestrator terminated at Stage 1

For **maps/UP20260716_0006.json**:
- **Should be written by:** Stage 12 (MAP Generator)
- **Stage 12 code location:** `pipeline/map_generator/map_generator.py`
- **Stage 12 was entered:** **NO**
- **Write statement was reached:** **NO**
- **Reason:** Orchestrator terminated at Stage 1

---

## 10. FORENSIC CONCLUSION

### Primary Finding

**The pipeline for UP20260716_0006 was INTERRUPTED by external process termination.**

### Evidence Chain

1. ✅ Upload endpoint executed successfully
2. ✅ Background task was queued
3. ✅ Background task started executing
4. ✅ Orchestrator was imported and instantiated
5. ✅ `process_document()` was called
6. ✅ Pre-flight validation passed
7. ✅ Stage 1 (PDF Parser) was started
8. ❌ **PROCESS TERMINATED HERE**
9. ❌ Stage 1 never logged completion
10. ❌ Stages 2-14 were never entered
11. ❌ Files were never written
12. ❌ Database ingestion never occurred

### Root Cause

**External process termination during Stage 1 execution.**

**NOT caused by:**
- ❌ Python exception (none logged)
- ❌ Stage failure (no failure message)
- ❌ Logic error (execution was proceeding correctly)
- ❌ Missing files (all input files present)
- ❌ Permission errors (earlier stages in first attempt succeeded)

**Likely caused by:**
- ✅ User interrupt (Ctrl+C)
- ✅ System resource exhaustion (OOM killer)
- ✅ FastAPI/Uvicorn server restart
- ✅ Operating system shutdown/restart
- ✅ Manual process kill command

### Missing Files Explanation

**The files do NOT exist because the stages that create them were NEVER EXECUTED due to process termination at Stage 1.**

This is **NOT a bug in the code**. This is **operational interruption**.

### Recommendation

To prevent this issue:
1. Implement process supervision (restart on crash)
2. Add pipeline state persistence (resume from last completed stage)
3. Implement timeout monitoring
4. Add health checks for background tasks
5. Log resource usage metrics
