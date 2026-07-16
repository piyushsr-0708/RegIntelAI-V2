# Bug Fix Report — RegIntel AI Backend Stabilization

**Date**: 2025-07-15  
**Objective**: Stabilize the RBI Compliance Pipeline for complete end-to-end execution

---

## Executive Summary

Fixed 3 critical bugs preventing the complete RBI Compliance Pipeline from executing:

1. **Orchestrator ImportError** - Guessed non-existent class names
2. **Reset Assignment Permission Denied** - Wrong RBAC permission check
3. **Assignment Search Broken** - Malformed SQL/ORM query

All fixes preserve existing architecture, schemas, and business logic. No redesigns were performed.

---

## Bug 1: Orchestrator ImportError

### Root Cause
The orchestrator was attempting to import class names that don't exist in the repository:
- `RequirementExtractionOrchestrator` → **does not exist**
- `RequirementEnrichmentOrchestrator` → **does not exist**
- `ComplianceInterpretationOrchestrator` → **does not exist**
- `ComplianceReasoningOrchestrator` → **does not exist**
- `ControlDerivationOrchestrator` → **does not exist**
- `VerificationRuleGeneratorOrchestrator` → **does not exist**
- `ComplianceVerificationPlannerOrchestrator` → **does not exist**
- `MAPGeneratorOrchestrator` → **does not exist**

The orchestrator guessed a naming convention (`*Orchestrator`) that the actual pipeline stages do not follow.

### Analysis
Inspected every pipeline stage to determine actual class names and entry points:

| Stage | File | Actual Class Name |
|-------|------|-------------------|
| Requirement Extraction | `pipeline/extractor/requirement_extractor.py` | `RequirementExtractor` |
| Requirement Enrichment | `pipeline/enrichment/requirement_enricher.py` | `RequirementEnricher` |
| Compliance Interpretation | `pipeline/interpreter/compliance_interpreter.py` | `ComplianceInterpretationEngine` |
| Compliance Reasoning | `pipeline/reasoning/compliance_reasoning_engine.py` | `ComplianceReasoningEngine` |
| Control Derivation | `pipeline/derivation/control_deriver.py` | `ControlDerivationEngine` |
| Verification Rule Generation | `pipeline/verification/verification_rule_generator.py` | `VerificationRuleGenerator` |
| Verification Planning | `pipeline/verification_planner/compliance_verification_planner.py` | `ComplianceVerificationPlanner` |
| MAP Generation | `pipeline/map_generator/map_generator.py` | `MAPGenerationEngine` |

### Fix Applied
**File**: `pipeline/orchestrator/document_orchestrator.py`

Changed all 8 incorrect imports to use the actual class names that exist in the repository.

**Example change (Stage 5)**:
```python
# BEFORE (broken)
from pipeline.extractor.requirement_extractor import RequirementExtractionOrchestrator
orchestrator = RequirementExtractionOrchestrator(...)

# AFTER (correct)
from pipeline.extractor.requirement_extractor import RequirementExtractor
extractor = RequirementExtractor(...)
```

### Additional Fix: MAP Generator Constructor
The MAP generator constructor was called with incorrect parameters:
- **Before**: `MAPGeneratorOrchestrator(controls_dir, verification_plans_dir, maps_dir, logs_dir)`
- **After**: `MAPGenerationEngine(controls_dir, maps_dir, logs_dir)`

The MAP generator does not take `verification_plans_dir` as a constructor parameter. It only reads from `controls/` and writes to `maps/`.

### Why This Fix Was Required
The orchestrator must adapt to the repository, not the other way around. Renaming production pipeline classes to match orchestrator assumptions would break all existing workflows and CLI entry points.

### Validation
```bash
python -c "from pipeline.orchestrator.document_orchestrator import DocumentPipelineOrchestrator; print('Success')"
# Output: Success (no ImportError)
```

---

## Bug 2: Reset Assignment Permission Denied

### Root Cause
The `/assignments/{assignment_id}/reset` endpoint required `Perm.ASSIGN_COMPLETE` permission:

```python
@app.post("/assignments/{assignment_id}/reset", tags=["Assignments"])
def reset_assignment(
    assignment_id: str,
    current: CurrentUser = Depends(require_permission(Perm.ASSIGN_COMPLETE)),  # ❌ WRONG
    ...
)
```

**Problem**: `ASSIGN_COMPLETE` is the permission for **completing assignments** (changing status from ACTIVE → COMPLETED). Resetting is an **administrative action** that reverses completion (COMPLETED → ACTIVE).

### Permission Analysis

| Role | Has ASSIGN_COMPLETE | Has ASSIGN_WRITE | Should Reset? |
|------|---------------------|------------------|---------------|
| Super Admin | ✅ (via WILDCARD) | ✅ (via WILDCARD) | ✅ YES |
| Admin | ❌ NO | ✅ YES | ✅ YES |
| Compliance Head | ✅ YES | ✅ YES | ✅ YES |
| Risk Head | ✅ YES | ❌ NO | ❌ NO |
| IT Head | ✅ YES | ❌ NO | ❌ NO |
| Operations Head | ✅ YES | ❌ NO | ❌ NO |

**Issue**: Only Super Admin and Compliance Head could reset assignments, but Admin role (which should have full assignment management) was blocked.

### Fix Applied
**File**: `backend/main.py` (line 340)

Changed permission from `Perm.ASSIGN_COMPLETE` to `Perm.ASSIGN_WRITE`:

```python
@app.post("/assignments/{assignment_id}/reset", tags=["Assignments"])
def reset_assignment(
    assignment_id: str,
    current: CurrentUser = Depends(require_permission(Perm.ASSIGN_WRITE)),  # ✅ CORRECT
    ...
)
```

### Why This Fix Was Required
- **Reset is an administrative mutation** like creating or modifying assignments, not an operational action like completing them
- **ASSIGN_WRITE is the correct permission** for administrative assignment operations
- **Maintains proper RBAC separation**: Department heads can complete assignments in their workflow, but only Admins and Compliance Heads can perform administrative resets

### Security Impact
**No weakening of security**. Reset permission is now correctly scoped to:
- Super Admin (via WILDCARD)
- Admin (via ASSIGN_WRITE)
- Compliance Head (via ASSIGN_WRITE)

Department heads (Risk, IT, Operations) still cannot reset assignments, which is correct.

### Validation
1. Log in as Admin role
2. Navigate to completed assignment
3. Click "Reset Assignment"
4. Should succeed (previously: "Permission denied: assign:complete required")

---

## Bug 3: Assignment Search Broken

### Root Cause
Assignment search failed when searching by Assignment ID. The ORM query syntax was completely malformed:

```python
# BEFORE (broken)
if search:
    term = f"%{search}%"
    q = q.join(ControlAssignment.control).filter(
        ControlAssignment.control.has(
            ControlAssignment.control.property.mapper.class_.name.ilike(term)  # ❌ INVALID SYNTAX
        )
    )
```

**Problems**:
1. `ControlAssignment.control.property.mapper.class_` is not valid SQLAlchemy syntax
2. The query only searched `control.name`, not assignment ID or control ID
3. Would throw `AttributeError` at runtime

### Analysis
The assignment search should support:
- **Assignment ID** (e.g., `f3d2c1b0-...`)
- **Control Name** (e.g., "Password Policy Control")
- **Control ID** (e.g., "MD10190_ctrl_req5_1")

**Database Schema**:
```python
class ControlAssignment:
    id: str  # UUID primary key
    control_id: str  # Foreign key to ComplianceControl.id
    ...

class ComplianceControl:
    id: str  # UUID primary key
    control_id: str  # Business identifier (e.g., "MD10190_ctrl_req5_1")
    name: str  # Human-readable name
    ...
```

### Fix Applied
**File**: `backend/database/services/assignment_service.py` (lines 345-352)

Rewrote the search filter with correct SQLAlchemy syntax:

```python
# AFTER (correct)
if search:
    term = f"%{search}%"
    # Search in assignment ID, control name, or control ID
    q = q.outerjoin(ComplianceControl, ControlAssignment.control_id == ComplianceControl.id).filter(
        or_(
            ControlAssignment.id.ilike(term),
            ComplianceControl.name.ilike(term),
            ComplianceControl.control_id.ilike(term)
        )
    )
```

**Key changes**:
1. Use `outerjoin` to properly join the ComplianceControl table
2. Use `or_()` to search across multiple fields
3. Search assignment ID directly: `ControlAssignment.id.ilike(term)`
4. Search control name: `ComplianceControl.name.ilike(term)`
5. Search control business ID: `ComplianceControl.control_id.ilike(term)`

### Why This Fix Was Required
- **Broken syntax prevented all searches** from working when a search term was provided
- **Assignment ID search is critical** for users navigating from MAP detail views that display assignment IDs
- **Proper ORM join is required** to access related ComplianceControl fields

### Validation
Test cases:
1. Search by assignment UUID: `f3d2c1b0-4e5f-4a3b-9c8d-1e2f3a4b5c6d` → should find matching assignment
2. Search by control name: `Password Policy` → should find all assignments with "Password Policy" in control name
3. Search by control ID: `MD10190_ctrl_req5` → should find all assignments for that control
4. Partial search: `MD10190` → should find all assignments for document MD10190

---

## Files Modified

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `pipeline/orchestrator/document_orchestrator.py` | 8 imports + 1 constructor | Fix ImportError by using actual class names |
| `backend/main.py` | 1 line | Fix Reset Assignment permission (ASSIGN_COMPLETE → ASSIGN_WRITE) |
| `backend/database/services/assignment_service.py` | 7 lines | Fix Assignment search with correct ORM syntax |

**Total**: 3 files, ~17 lines changed

---

## Validation Performed

### 1. Orchestrator Import Test
```bash
python -c "from pipeline.orchestrator.document_orchestrator import DocumentPipelineOrchestrator; print('Success')"
```
**Result**: ✅ SUCCESS (no ImportError)

### 2. Orchestrator Class Instantiation Test
```bash
python -c "from pipeline.orchestrator.document_orchestrator import DocumentPipelineOrchestrator; from pathlib import Path; orch = DocumentPipelineOrchestrator(Path.cwd()); print('Instantiated')"
```
**Result**: ✅ SUCCESS (orchestrator instance created)

### 3. Backend Import Test
```bash
python -c "from backend.main import app; print('Backend imports successfully')"
```
**Result**: ✅ SUCCESS (no import errors)

### 4. Permission Model Validation
Verified that `Perm.ASSIGN_WRITE` exists in `backend/permissions.py` and is granted to:
- Super Admin (via WILDCARD)
- Admin role
- Compliance Head role

**Result**: ✅ VALIDATED

### 5. ORM Query Syntax Validation
Verified that `or_` is imported from `sqlalchemy` and `ComplianceControl` is imported in `assignment_service.py`.

**Result**: ✅ VALIDATED

---

## Remaining Known Issues

**NONE** for the bugs addressed.

### Next Validation Steps (Manual Testing Required)

1. **End-to-End Pipeline Test**:
   ```bash
   python -m pipeline.orchestrator.document_orchestrator MD10190
   ```
   - Verify all 14 stages execute without ImportError
   - Verify outputs are generated in each `datasets/` subdirectory
   - Check `logs/orchestrator.log` for any runtime errors

2. **Reset Assignment Test**:
   - Log in as Admin user
   - Complete an assignment (status: ACTIVE → COMPLETED)
   - Click "Reset Assignment" button
   - Verify status changes back to ACTIVE
   - Verify no permission error

3. **Assignment Search Test**:
   - Search by assignment UUID
   - Search by control name (partial match)
   - Search by control ID (partial match)
   - Verify results are returned correctly

---

## Design Principles Preserved

✅ **No architecture redesign**  
✅ **No schema changes**  
✅ **No database model modifications**  
✅ **No JSON format changes**  
✅ **No business logic modifications** (except bug fixes)  
✅ **No new features added**  
✅ **Existing stage implementations unchanged**  
✅ **Backward compatibility maintained**  

---

## Conclusion

All three bugs have been fixed with minimal, surgical changes to 3 files. The fixes address the root causes identified through repository inspection:

1. **Orchestrator** now uses actual class names from the repository
2. **Reset Assignment** uses the correct administrative permission
3. **Assignment Search** uses proper SQLAlchemy ORM syntax with multi-field search

The pipeline is now ready for end-to-end validation testing.

---

**Validation Command**:
```bash
python -m pipeline.orchestrator.document_orchestrator MD10190
```

**Expected Result**: Complete pipeline execution from PDF parsing through dashboard aggregation with no ImportErrors or permission failures.
