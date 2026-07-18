# Runtime Path Proof: Uploaded-Document Execution Path

**Document ID:** UP20260716_0006  
**Investigation:** Determine actual runtime paths passed to ComplianceInterpretationEngine  
**Method:** Static code analysis of uploaded-document execution path

---

## EXECUTION PATH TRACE

### Step 1: Backend Instantiation

**File:** `backend/main.py`  
**Lines:** 30-31

```python
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
```

**Runtime Values:**
```
__file__         = D:\SuRaksha-v2\backend\main.py
parent           = D:\SuRaksha-v2\backend
parent.parent    = D:\SuRaksha-v2
```

**Result:**
```python
project_root = D:\SuRaksha-v2
```

---

### Step 2: Orchestrator Instantiation

**File:** `backend/main.py`  
**Lines:** 577-580

```python
orchestrator = DocumentPipelineOrchestrator(
    project_root=project_root,
    pdf_source_dir=pdf_source_dir
)
```

**Values Passed:**
```python
project_root = D:\SuRaksha-v2
```

---

### Step 3: Orchestrator __init__

**File:** `pipeline/orchestrator/document_orchestrator.py`  
**Lines:** 106-107

```python
def __init__(self, project_root: Path, pdf_source_dir: Optional[Path] = None):
    self.project_root = project_root
```

**Runtime Values:**
```python
self.project_root = D:\SuRaksha-v2
```

**CRITICAL FINDING:**
The orchestrator receives `project_root` as a **PARAMETER**.
The module-level `project_root` at line 27 is **NOT USED** in `__init__`.

---

### Step 4: self.paths Construction

**File:** `pipeline/orchestrator/document_orchestrator.py`  
**Lines:** 113-128

```python
self.paths = {
    "raw_pdf": pdf_dir,
    "parsed": project_root / "datasets" / "parsed",
    "normalized": project_root / "datasets" / "normalized",
    "hierarchy": project_root / "datasets" / "hierarchy",
    "logical_units": project_root / "datasets" / "logical_units",
    "requirements": project_root / "datasets" / "requirements",
    "enriched_requirements": project_root / "datasets" / "enriched_requirements",
    "interpreted_controls": project_root / "datasets" / "interpreted_controls",
    "reasoned_controls": project_root / "datasets" / "reasoned_controls",
    "controls": project_root / "datasets" / "controls",
    "verification_rules": project_root / "datasets" / "verification_rules",
    "verification_plans": project_root / "datasets" / "verification_plans",
    "maps": project_root / "datasets" / "maps",
    "frontend": project_root / "datasets" / "frontend",
    "logs": project_root / "logs"
}
```

**Note:** Uses `project_root` parameter (not module-level variable)

**Runtime Values:**
```python
self.paths["enriched_requirements"] = D:\SuRaksha-v2\datasets\enriched_requirements
self.paths["interpreted_controls"] = D:\SuRaksha-v2\datasets\interpreted_controls
self.paths["logs"]                  = D:\SuRaksha-v2\logs
```

---

### Step 5: ComplianceInterpretationEngine Instantiation

**File:** `pipeline/orchestrator/document_orchestrator.py`  
**Lines:** 473-477

```python
def run_compliance_interpreter():
    from pipeline.interpreter.compliance_interpreter import ComplianceInterpretationEngine
    engine = ComplianceInterpretationEngine(
        self.paths["enriched_requirements"],
        self.paths["interpreted_controls"],
        self.paths["logs"]
    )
```

**Actual Constructor Call:**
```python
ComplianceInterpretationEngine(
    input_dir  = D:\SuRaksha-v2\datasets\enriched_requirements,
    output_dir = D:\SuRaksha-v2\datasets\interpreted_controls,
    log_dir    = D:\SuRaksha-v2\logs
)
```

---

## ANSWERS

### Q1. What absolute output_dir is passed?

```
D:\SuRaksha-v2\datasets\interpreted_controls
```

---

### Q2. Is it correct?

**YES**

The output_dir is the CORRECT path.

---

### Q3. If NO, show the exact statement producing the incorrect path.

**N/A** - The path is correct.

---

### Q4. If YES, the path hypothesis is disproven.

**CONFIRMED: The `parents[2]` path hypothesis is DISPROVEN.**

**Why the Previous Analysis Was Wrong:**

1. **Module-level vs Parameter:**
   - Line 27: `project_root = current_dir.parents[2]` is module-level (for sys.path)
   - Line 106: `def __init__(self, project_root: Path, ...)` receives parameter
   - The parameter SHADOWS the module-level variable

2. **Backend Passes Correct Value:**
   - Backend calculates: `project_root = Path(__file__).parent.parent`
   - Result: `D:\SuRaksha-v2` ✅

3. **Orchestrator Uses Parameter:**
   - `self.project_root = project_root` (parameter, not module-level)
   - All paths constructed from `self.project_root` are correct

---

## MODULE-LEVEL project_root SCOPE

**File:** `pipeline/orchestrator/document_orchestrator.py`  
**Lines:** 27-29

```python
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[2]  # D:\
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
```

**Purpose:** Add project root to sys.path for imports  
**Scope:** Module-level only  
**Used by:** Import system, NOT used in __init__  
**Value:** `D:\` (incorrect, but irrelevant for uploaded-document execution)

**This variable is SHADOWED by the `project_root` parameter in `__init__`.**

---

## CONCLUSION

**For uploaded-document execution path:**

1. ✅ Backend passes `D:\SuRaksha-v2`
2. ✅ Orchestrator receives `D:\SuRaksha-v2`
3. ✅ Orchestrator constructs paths with `D:\SuRaksha-v2`
4. ✅ ComplianceInterpretationEngine receives `D:\SuRaksha-v2\datasets\interpreted_controls`

**The output_dir is CORRECT.**

**The module-level `parents[2]` calculation is irrelevant for uploaded-document execution.**

---

## IMPLICATION

**If files are missing from `D:\SuRaksha-v2\datasets\interpreted_controls\`, the cause is NOT path miscalculation.**

**Possible causes:**
1. Write operation never executed (process termination before Stage 7)
2. Write operation failed silently (permission error, disk full)
3. Files written but deleted afterwards (cleanup process, antivirus)
4. Directory creation failed (mkdir permission error)

**The path calculation is correct. The bug is elsewhere.**
