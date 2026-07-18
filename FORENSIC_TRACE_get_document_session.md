# Forensic Trace: backend/main.py::get_document_session

**Test Document ID:** `UP20260715_0001`  
**Function:** `get_document_session`  
**File:** `backend/main.py`  
**Lines:** 452-527

---

## Execution Trace (Line by Line)

### Entry Point
**Line 453:** Function entry  
```python
def get_document_session(
    document_id: str,  # ← "UP20260715_0001"
    current: CurrentUser = Depends(require_permission(Perm.MAP_READ)),
):
```

**Variables at entry:**
- `document_id` = `"UP20260715_0001"`
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
- `parsed_path` = `WindowsPath('d:/SuRaksha-v2/datasets/parsed/UP20260715_0001.json')`

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
- File opened: `d:/SuRaksha-v2/datasets/parsed/UP20260715_0001.json` ✅
- `parsed_data` = `{...}` (dict with document metadata)
- `parsed_data.get("page_count")` = (some integer value)

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
- `requirements_path` = `WindowsPath('d:/SuRaksha-v2/datasets/requirements/UP20260715_0001.json')`

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
- File opened: `d:/SuRaksha-v2/datasets/requirements/UP20260715_0001.json` ✅
- `req_data` = `{"requirements": [...]}`
- `req_data.get("requirements", [])` = `[{...}, {...}, ...]` (list of 53 requirement objects)
- **ASSIGNMENT #1:** `requirements` = `[list of 53 requirement dicts]`
- `len(requirements)` = `53`

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
- `maps_path` = `WindowsPath('d:/SuRaksha-v2/datasets/maps/UP20260715_0001.json')`

**Line 484:** Check if maps_path exists
```python
if maps_path.exists():
```
**File System Check:**
- `maps_path.exists()` = `True` ✅
- Condition evaluates to `True`
- **Execution enters if block (lines 485-488)**

**Line 485-488:** Open and read MAPs
```python
with open(maps_path, "r", encoding="utf-8") as f:
    maps_data = json.load(f)
    maps_list = maps_data.get("maps", [])
    departments = {m.get("department") for m in maps_list if m.get("department")}
```

**Line 485-486:** Open file and load JSON
- File opened: `d:/SuRaksha-v2/datasets/maps/UP20260715_0001.json` ✅
- `maps_data` = `{"document_id": "UP20260715_0001", "maps": [...]}`

**Line 487:** Extract maps array
```python
maps_list = maps_data.get("maps", [])
```
**Result:**
- **ASSIGNMENT #2:** `maps_list` = `[{...}, {...}, ...]` (list of 53 MAP objects)
- **IMMEDIATELY AFTER json.load():** `len(maps_list)` = `53` ✅

**Verified MAP structure:**
```json
{
  "map_id": "MAP_UP20260715_0001_ctrl_req5_1",
  "department": null,              ← THIS FIELD IS NULL
  "owner_department": "Compliance"
}
```

**Line 488:** Build departments set
```python
departments = {m.get("department") for m in maps_list if m.get("department")}
```

**Detailed Execution of Line 488:**

**Set comprehension iteration:**
```python
for m in maps_list:  # Iterates 53 times
    value = m.get("department")  # Returns None for all 53 MAPs
    if value:                    # None is falsy → False for all 53
        # Never adds anything to the set
```

**Step-by-step for each MAP:**
1. `m` = `{"map_id": "MAP_UP20260715_0001_ctrl_req5_1", "department": null, "owner_department": "Compliance", ...}`
2. `m.get("department")` = `None`
3. `if None:` = `False`
4. MAP is **filtered out** by the conditional
5. Nothing is added to the set

**Repeat 53 times with identical result**

**Result:**
- **ASSIGNMENT #2:** `departments` = `set()` (EMPTY SET) ❌
- `len(departments)` = `0` ❌

**THIS IS THE CRITICAL LINE WHERE DEPARTMENTS BECOMES 0**

**Actual department data in JSON (IGNORED by line 488):**
- `owner_department` field contains: `["Compliance", "Treasury", "IT", "Operations", "Internal Audit", "Risk"]`
- `department` field contains: `null` (for all 53 MAPs)

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
- `vp_path` = `WindowsPath('d:/SuRaksha-v2/datasets/verification_plans/UP20260715_0001.json')`

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
- `departments` = `set()` (empty, from line 488)
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
- `page_count` = (some integer, e.g., 10)

**Line 506:** Calculate word_count
```python
word_count = page_count * 350
```
**Result:**
- `word_count` = (e.g., 3500)

---

### Build Response Object

**Line 508-523:** Return statement
```python
return {
    "document_id": document_id,                    # "UP20260715_0001"
    "filename": f"{document_id}.pdf",              # "UP20260715_0001.pdf"
    "page_count": page_count,                      # (e.g., 10)
    "word_count": word_count,                      # (e.g., 3500)
    "requirements_count": len(requirements),       # 53 ✅
    "maps_count": len(maps_list),                  # 53 ✅ (CORRECT!)
    "departments_count": len(departments),         # 0 ❌ (WRONG!)
    "processing_complete": True,
    "metadata": parsed_data.get("metadata", {}),
    # Complete session data
    "requirements": requirements,                  # [list of 53 requirements]
    "maps": maps_list,                             # [list of 53 MAPs]
    "verification_plans": verification_plans,      # []
    "department_impact": department_impact,        # [] ❌ (WRONG!)
    "graph": {"nodes": [], "edges": []},
    "stages": [],
}
```

---

## Final Variable States Before Return

### Path Variables
| Variable | Value | Exists? |
|----------|-------|---------|
| `document_id` | `"UP20260715_0001"` | N/A |
| `parsed_path` | `WindowsPath('d:/SuRaksha-v2/datasets/parsed/UP20260715_0001.json')` | `True` ✅ |
| `requirements_path` | `WindowsPath('d:/SuRaksha-v2/datasets/requirements/UP20260715_0001.json')` | `True` ✅ |
| `maps_path` | `WindowsPath('d:/SuRaksha-v2/datasets/maps/UP20260715_0001.json')` | `True` ✅ |
| `vp_path` | `WindowsPath('d:/SuRaksha-v2/datasets/verification_plans/UP20260715_0001.json')` | `False` ❌ |

**Note:** There is no `session_id` or `graph_path` variable in this function.

### Files Opened
1. `d:/SuRaksha-v2/datasets/parsed/UP20260715_0001.json` (line 469)
2. `d:/SuRaksha-v2/datasets/requirements/UP20260715_0001.json` (line 476)
3. `d:/SuRaksha-v2/datasets/maps/UP20260715_0001.json` (line 485)

### Data Variables
| Variable | Final Value | Length |
|----------|-------------|--------|
| `requirements` | `[list of requirement dicts]` | `53` ✅ |
| `maps_list` | `[list of MAP dicts]` | `53` ✅ |
| `maps_data` | `{"document_id": "UP20260715_0001", "maps": [...]}` | N/A |
| `departments` | `set()` | `0` ❌ |
| `verification_plans` | `[]` | `0` |
| `department_impact` | `[]` | `0` ❌ |

### Response Object Values
```python
{
    "document_id": "UP20260715_0001",
    "filename": "UP20260715_0001.pdf",
    "page_count": <integer>,
    "word_count": <integer>,
    "requirements_count": 53,      # ✅ CORRECT
    "maps_count": 53,              # ✅ CORRECT
    "departments_count": 0,        # ❌ WRONG (should be 6)
    "processing_complete": True,
    "metadata": {...},
    "requirements": [53 items],
    "maps": [53 items],
    "verification_plans": [],
    "department_impact": [],       # ❌ WRONG (should have 6 items)
    "graph": {"nodes": [], "edges": []},
    "stages": []
}
```

---

## Critical Finding: Line 488 Analysis

### The Statement That Causes departments_count to Become 0

**Line 488:**
```python
departments = {m.get("department") for m in maps_list if m.get("department")}
```

### Why This Line Produces 0 Departments

**Execution breakdown:**

1. **Input:** `maps_list` with 53 MAP objects
2. **Iteration:** Loops through all 53 MAPs
3. **Field access:** `m.get("department")` for each MAP
4. **Field value:** Returns `None` (null in JSON) for all 53 MAPs
5. **Conditional filter:** `if m.get("department")` evaluates `if None:`
6. **Boolean evaluation:** `None` is falsy → `False`
7. **Filter result:** All 53 MAPs are **excluded** from the set
8. **Final set:** `set()` (empty)

### Root Cause

**Wrong field accessed:**
- Code accesses: `"department"` (contains `null`)
- Data is in: `"owner_department"` (contains `"Compliance"`, `"Treasury"`, etc.)

### Evidence from JSON

**Actual MAP structure in UP20260715_0001.json:**
```json
{
  "map_id": "MAP_UP20260715_0001_ctrl_req5_1",
  "department": null,                    ← Line 488 accesses THIS (null)
  "owner_department": "Compliance"       ← Line 488 IGNORES THIS (has data)
}
```

**Verified unique values:**
- `department` field: `null` for all 53 MAPs
- `owner_department` field: 6 unique values (`["Compliance", "Treasury", "IT", "Operations", "Internal Audit", "Risk"]`)

---

## Reassignment Timeline

### maps_list Reassignments
1. **Line 481:** `maps_list = []` (initialization)
2. **Line 487:** `maps_list = maps_data.get("maps", [])` (assignment from JSON, length = 53)
3. **NO FURTHER REASSIGNMENTS**

### departments Reassignments
1. **Line 482:** `departments = set()` (initialization)
2. **Line 488:** `departments = {m.get("department") for m in maps_list if m.get("department")}` (set comprehension, result = empty set)
3. **NO FURTHER REASSIGNMENTS**

---

## Conclusion

**Statement that causes maps_count to remain correct but departments_count to become 0:**

**Line 488:** `departments = {m.get("department") for m in maps_list if m.get("department")}`

**Reason:**
- Accesses wrong field name (`"department"` instead of `"owner_department"`)
- All MAPs have `"department": null`
- Conditional `if m.get("department")` filters out all nulls
- Result: Empty set, `departments_count = 0`

**Note:** `maps_count` remains correct (53) because `maps_list` is correctly assigned from `maps_data.get("maps", [])` at line 487 and never modified afterward.
