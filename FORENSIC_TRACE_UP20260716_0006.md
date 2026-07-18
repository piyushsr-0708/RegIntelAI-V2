# Forensic Trace: backend/main.py::get_document_session

**Test Document ID:** `UP20260716_0006`  
**Function:** `get_document_session`  
**File:** `backend/main.py`  
**Lines:** 452-527

---

## Pre-Execution File System State

### File Existence Check

| Path | Exists | Notes |
|------|--------|-------|
| `datasets/parsed/UP20260716_0006.json` | ✅ `True` | Pipeline Stage 1 complete |
| `datasets/normalized/UP20260716_0006.json` | ✅ `True` | Pipeline Stage 2 complete |
| `datasets/hierarchy/UP20260716_0006.json` | ✅ `True` | Pipeline Stage 3 complete |
| `datasets/logical_units/UP20260716_0006.json` | ✅ `True` | Pipeline Stage 4 complete |
| `datasets/requirements/UP20260716_0006.json` | ✅ `True` | Pipeline Stage 5 complete (37 requirements) |
| `datasets/enriched_requirements/UP20260716_0006.json` | ✅ `True` | Pipeline Stage 6 complete |
| `datasets/interpreted_controls/UP20260716_0006.json` | ❌ `False` | **Pipeline Stage 7 MISSING** |
| `datasets/reasoned_controls/UP20260716_0006.json` | ❌ `False` | **Pipeline Stage 8 MISSING** |
| `datasets/controls/UP20260716_0006.json` | ❌ `False` | **Pipeline Stage 9 MISSING** |
| `datasets/verification_rules/UP20260716_0006.json` | ✅ `True` | Pipeline Stage 10 complete |
| `datasets/verification_plans/UP20260716_0006.json` | ❌ `False` | **Pipeline Stage 11 MISSING** |
| `datasets/maps/UP20260716_0006.json` | ❌ `False` | **Pipeline Stage 12 MISSING** |

**Pipeline Status:** INCOMPLETE - Pipeline stopped or failed between Stage 6 and Stage 12

**Critical Finding:** The MAP Generator (Stage 12) never executed because the file `datasets/maps/UP20260716_0006.json` **DOES NOT EXIST**.

---

## Execution Trace (Line by Line)

### Entry Point
**Line 453:** Function entry  
```python
def get_document_session(
    document_id: str,  # ← "UP20260716_0006"
    current: CurrentUser = Depends(require_permission(Perm.MAP_READ)),
):
```

**Variables at entry:**
- `document_id` = `"UP20260716_0006"`
- `current` = `<CurrentUser object>` (authenticated user)

---

### Import Statements
**Line 461:** `import json`  
**Line 462:** `from pathlib import Path`

---

### Read Parsed Document Metadata

**Line 465:** Construct parsed_path
```python
parsed_path = project_root / "datasets" / "parsed" / f"{document_id}.json"
```
**Result:**
- `parsed_path` = `WindowsPath('d:/SuRaksha-v2/datasets/parsed/UP20260716_0006.json')`

**Line 466:** Check if parsed_path exists
```python
if not parsed_path.exists():
```
**File System Check:**
- `parsed_path.exists()` = `True` ✅
- Condition evaluates to `False`
- **Does NOT raise HTTPException**
- **Execution continues to line 469**

**Line 469-470:** Open and read parsed document
```python
with open(parsed_path, "r", encoding="utf-8") as f:
    parsed_data = json.load(f)
```
**Result:**
- File opened: `d:/SuRaksha-v2/datasets/parsed/UP20260716_0006.json` ✅
- `parsed_data` = `{...}` (dict with document metadata)

---

### Read Requirements

**Line 473:** Initialize requirements list
```python
requirements = []
```
**Result:**
- `requirements` = `[]` (empty list)

**Line 474:** Construct requirements_path
```python
requirements_path = project_root / "datasets" / "requirements" / f"{document_id}.json"
```
**Result:**
- `requirements_path` = `WindowsPath('d:/SuRaksha-v2/datasets/requirements/UP20260716_0006.json')`

**Line 475:** Check if requirements_path exists
```python
if requirements_path.exists():
```
**File System Check:**
- `requirements_path.exists()` = `True` ✅
- Condition evaluates to `True`
- **Execution enters if block (lines 476-478)**

**Line 476-478:** Open and read requirements
```python
with open(requirements_path, "r", encoding="utf-8") as f:
    req_data = json.load(f)
    requirements = req_data.get("requirements", [])
```
**Result:**
- File opened: `d:/SuRaksha-v2/datasets/requirements/UP20260716_0006.json` ✅
- `req_data` = `{"requirements": [...]}`
- `req_data.get("requirements", [])` = `[{...}, {...}, ...]` (list of 37 requirement objects)
- **ASSIGNMENT #1:** `requirements` = `[list of 37 requirement dicts]`
- `len(requirements)` = `37`

---

### Read MAPs

**Line 481:** Initialize maps_list
```python
maps_list = []
```
**Result:**
- **ASSIGNMENT #1:** `maps_list` = `[]` (empty list)

**Line 482:** Initialize departments set
```python
departments = set()
```
**Result:**
- **ASSIGNMENT #1:** `departments` = `set()` (empty set)

**Line 483:** Construct maps_path
```python
maps_path = project_root / "datasets" / "maps" / f"{document_id}.json"
```
**Result:**
- `maps_path` = `WindowsPath('d:/SuRaksha-v2/datasets/maps/UP20260716_0006.json')`

**Line 484:** Check if maps_path exists
```python
if maps_path.exists():
```
**File System Check:**
- `maps_path.exists()` = `False` ❌ **FILE DOES NOT EXIST**
- Condition evaluates to `False`
- **DOES NOT enter if block (lines 485-488)**
- **SKIPS lines 485-488 entirely**

**CRITICAL EXECUTION BRANCH:**
Because the file does not exist, the code **NEVER EXECUTES** lines 485-488:
- Line 485: `with open(maps_path, "r", encoding="utf-8") as f:` → **NOT EXECUTED**
- Line 486: `maps_data = json.load(f)` → **NOT EXECUTED**
- Line 487: `maps_list = maps_data.get("maps", [])` → **NOT EXECUTED**
- Line 488: `departments = {m.get("department") for m in maps_list if m.get("department")}` → **NOT EXECUTED**

**Result:**
- `maps_list` **REMAINS** = `[]` (from initialization at line 481) ❌
- `departments` **REMAINS** = `set()` (from initialization at line 482) ❌
- **NO REASSIGNMENT of maps_list occurs**
- **NO REASSIGNMENT of departments occurs**

**Answer to the question:**
- `len(maps_data["maps"])` **CANNOT BE DETERMINED** because `json.load()` at line 486 **NEVER EXECUTES**
- The file `datasets/maps/UP20260716_0006.json` **DOES NOT EXIST**
- Therefore, `maps_data` is **NEVER CREATED**

---

### Read Verification Plans

**Line 491:** Initialize verification_plans list
```python
verification_plans = []
```
**Result:**
- `verification_plans` = `[]` (empty list)

**Line 492:** Construct vp_path
```python
vp_path = project_root / "datasets" / "verification_plans" / f"{document_id}.json"
```
**Result:**
- `vp_path` = `WindowsPath('d:/SuRaksha-v2/datasets/verification_plans/UP20260716_0006.json')`

**Line 493:** Check if vp_path exists
```python
if vp_path.exists():
```
**File System Check:**
- `vp_path.exists()` = `False` ❌
- Condition evaluates to `False`
- **Does NOT enter if block**
- `verification_plans` remains `[]`

---

### Build Department Impact Summary

**Line 497:** Initialize department_impact list
```python
department_impact = []
```
**Result:**
- `department_impact` = `[]` (empty list)

**Line 498-502:** Loop over departments
```python
for dept in departments:  # departments is empty set
    dept_maps = [m for m in maps_list if m.get("department") == dept]
    department_impact.append({
        "department": dept,
        "map_count": len(dept_maps)
    })
```

**Execution:**
- `departments` = `set()` (empty, from line 482, never reassigned)
- `for dept in set():` = **ZERO ITERATIONS** ❌
- Loop body **NEVER EXECUTES**
- `department_impact` remains `[]` (empty list)

---

### Calculate Metadata

**Line 505:** Extract page_count
```python
page_count = parsed_data.get("page_count", 0)
```
**Result:**
- `page_count` = (some integer)

**Line 506:** Calculate word_count
```python
word_count = page_count * 350
```
**Result:**
- `word_count` = (calculated value)

---

### Build Response Object

**Line 508-523:** Return statement
```python
return {
    "document_id": document_id,                    # "UP20260716_0006"
    "filename": f"{document_id}.pdf",              # "UP20260716_0006.pdf"
    "page_count": page_count,                      # (some value)
    "word_count": word_count,                      # (calculated)
    "requirements_count": len(requirements),       # 37 ✅
    "maps_count": len(maps_list),                  # 0 ❌ (empty list from line 481)
    "departments_count": len(departments),         # 0 ❌ (empty set from line 482)
    "processing_complete": True,                   # ❌ INCORRECT (processing is NOT complete)
    "metadata": parsed_data.get("metadata", {}),
    # Complete session data
    "requirements": requirements,                  # [list of 37 requirements]
    "maps": maps_list,                             # [] ❌ (empty list)
    "verification_plans": verification_plans,      # []
    "department_impact": department_impact,        # [] ❌ (empty list)
    "graph": {"nodes": [], "edges": []},
    "stages": [],
}
```

---

## Final Variable States Before Return

### Path Variables
| Variable | Value | Exists? |
|----------|-------|---------|
| `document_id` | `"UP20260716_0006"` | N/A |
| `parsed_path` | `WindowsPath('d:/SuRaksha-v2/datasets/parsed/UP20260716_0006.json')` | `True` ✅ |
| `requirements_path` | `WindowsPath('d:/SuRaksha-v2/datasets/requirements/UP20260716_0006.json')` | `True` ✅ |
| `maps_path` | `WindowsPath('d:/SuRaksha-v2/datasets/maps/UP20260716_0006.json')` | `False` ❌ |
| `vp_path` | `WindowsPath('d:/SuRaksha-v2/datasets/verification_plans/UP20260716_0006.json')` | `False` ❌ |

### Files Opened
1. `d:/SuRaksha-v2/datasets/parsed/UP20260716_0006.json` (line 469)
2. `d:/SuRaksha-v2/datasets/requirements/UP20260716_0006.json` (line 476)
3. **NOT OPENED:** `d:/SuRaksha-v2/datasets/maps/UP20260716_0006.json` (file does not exist)

### Data Variables
| Variable | Final Value | Length | Source |
|----------|-------------|--------|--------|
| `requirements` | `[list of requirement dicts]` | `37` ✅ | From JSON file |
| `maps_list` | `[]` | `0` ❌ | **Never reassigned from initialization** |
| `maps_data` | **UNDEFINED** | N/A | **Never created (json.load() never executed)** |
| `departments` | `set()` | `0` ❌ | **Never reassigned from initialization** |
| `verification_plans` | `[]` | `0` | From initialization (file doesn't exist) |
| `department_impact` | `[]` | `0` ❌ | From initialization (empty departments) |

### Response Object Values
```python
{
    "document_id": "UP20260716_0006",
    "filename": "UP20260716_0006.pdf",
    "page_count": <integer>,
    "word_count": <integer>,
    "requirements_count": 37,      # ✅ CORRECT
    "maps_count": 0,               # ❌ WRONG (pipeline incomplete)
    "departments_count": 0,        # ❌ WRONG (pipeline incomplete)
    "processing_complete": True,   # ❌ LIE (processing is NOT complete)
    "metadata": {...},
    "requirements": [37 items],
    "maps": [],                    # ❌ EMPTY (should have MAPs if pipeline completed)
    "verification_plans": [],
    "department_impact": [],       # ❌ EMPTY
    "graph": {"nodes": [], "edges": []},
    "stages": []
}
```

---

## Reassignment Timeline for maps_list

### All Assignments and Reassignments
1. **Line 481:** `maps_list = []` (initialization to empty list)
2. **Line 487:** `maps_list = maps_data.get("maps", [])` → **NEVER EXECUTES** (line 484 condition is False)
3. **NO FURTHER STATEMENTS**

**Final value:** `maps_list` = `[]` (remains as initialized at line 481)

### All Assignments and Reassignments for departments
1. **Line 482:** `departments = set()` (initialization to empty set)
2. **Line 488:** `departments = {m.get("department") for m in maps_list if m.get("department")}` → **NEVER EXECUTES** (line 484 condition is False)
3. **NO FURTHER STATEMENTS**

**Final value:** `departments` = `set()` (remains as initialized at line 482)

---

## Root Cause Analysis

### Why maps_count = 0 for UP20260716_0006

**Statement that causes maps_count to be 0:**

**Line 484:** `if maps_path.exists():`

**Reason:**
1. The file `datasets/maps/UP20260716_0006.json` **DOES NOT EXIST**
2. `maps_path.exists()` returns `False`
3. The conditional at line 484 prevents entry into the if block
4. Lines 485-488 **NEVER EXECUTE**
5. `maps_list` is **NEVER REASSIGNED** from its initialization value of `[]`
6. Response returns `maps_count = len(maps_list) = len([]) = 0`

### Why the File Does Not Exist

**Pipeline Status:** The document pipeline for UP20260716_0006 **DID NOT COMPLETE**.

**Evidence from file system:**
- Stages 1-6 completed ✅ (parsed, normalized, hierarchy, logical_units, requirements, enriched_requirements)
- Stage 7 MISSING ❌ (interpreted_controls)
- Stage 8 MISSING ❌ (reasoned_controls)
- Stage 9 MISSING ❌ (controls)
- Stage 10 completed ✅ (verification_rules)
- Stage 11 MISSING ❌ (verification_plans)
- Stage 12 MISSING ❌ (maps)

**Evidence from orchestrator log:**
```
2026-07-16 10:47:45,390 - INFO - PIPELINE ORCHESTRATION STARTED: UP20260716_0006
2026-07-16 10:47:45,392 - INFO - ✓ Pre-flight check passed: PDF exists
```
**No completion log found** - Pipeline started but did not complete all 14 stages.

**The MAP Generator (Stage 12) never executed because:**
1. The pipeline either failed at an earlier stage (likely Stage 7, 8, or 9)
2. OR the pipeline execution was interrupted
3. Therefore, `datasets/maps/UP20260716_0006.json` was never created
4. Therefore, `get_document_session` returns `maps_count = 0`

---

## Critical Findings

### Immediate Answer
**Q:** What is the value of `len(maps_data["maps"])` immediately after `json.load()` in `get_document_session()`?

**A:** **UNDEFINED / NEVER EXECUTED**

The statement `maps_data = json.load(f)` at line 486 **NEVER EXECUTES** because:
- The file `datasets/maps/UP20260716_0006.json` does not exist
- Line 484 conditional `if maps_path.exists():` evaluates to `False`
- The if block (lines 485-488) is skipped entirely
- `maps_data` is never created
- Therefore, `len(maps_data["maps"])` cannot be evaluated

### maps_list Trace
**Q:** Trace every subsequent reassignment of maps_list until the response is returned.

**A:** **ZERO REASSIGNMENTS**

`maps_list` is assigned exactly once:
- **Line 481:** `maps_list = []` (initialization)
- **Line 487:** Would reassign, but **NEVER EXECUTES**
- **NO OTHER STATEMENTS** modify `maps_list`

`maps_list` remains `[]` (empty list) throughout execution and is returned in the response with `maps_count = 0`.

---

## Conclusion

**For document UP20260716_0006:**

1. **The pipeline did not complete** - Only 7 of 14 stages succeeded
2. **The MAP file does not exist** - `datasets/maps/UP20260716_0006.json` is missing
3. **json.load() never executes** - Line 486 is skipped due to missing file
4. **maps_list is never populated** - Remains as empty list from initialization
5. **The response incorrectly reports** `"processing_complete": True` when processing actually failed

**This is a different failure mode than UP20260715_0001:**
- UP20260715_0001: Pipeline completed, MAP file exists with 53 MAPs, but wrong field accessed
- UP20260716_0006: Pipeline incomplete, MAP file doesn't exist, maps_list never populated

**The function returns maps_count=0 because the file doesn't exist, not because of a field name bug.**
