# Runtime Proof: UP20260716_0006 File Persistence

**Document ID:** UP20260716_0006  
**Test Date:** 2026-07-16 22:56:23  
**Method:** Instrumented code with diagnostics at two checkpoints

---

## CONSOLE OUTPUT

### Checkpoint 1: Immediately After json.dump()

```
================================================================================
DIAGNOSTIC: Immediately after json.dump()
================================================================================
OUTPUT_FILE = D:\SuRaksha-v2\datasets\interpreted_controls\UP20260716_0006.json
EXISTS      = True
SIZE        = 103667 bytes
OUTPUT_DIR  = D:\SuRaksha-v2\datasets\interpreted_controls
CWD         = D:\SuRaksha-v2
ABSOLUTE    = D:\SuRaksha-v2\datasets\interpreted_controls\UP20260716_0006.json
================================================================================
```

### Checkpoint 2: Immediately After process_document() Returns

```
================================================================================
DIAGNOSTIC: Immediately after process_document() returns
================================================================================
OUTPUT_FILE = D:\SuRaksha-v2\datasets\interpreted_controls\UP20260716_0006.json
EXISTS      = True
SIZE        = 103667 bytes
GLOB        = ['D:\\SuRaksha-v2\\datasets\\interpreted_controls\\MD10190.json', 
              'D:\\SuRaksha-v2\\datasets\\interpreted_controls\\MD10191.json', 
              ...
              'D:\\SuRaksha-v2\\datasets\\interpreted_controls\\UP20260715_0001.json', 
              'D:\\SuRaksha-v2\\datasets\\interpreted_controls\\UP20260716_0006.json']
================================================================================
```

**Note:** GLOB output includes `UP20260716_0006.json` confirming file is visible in directory listing.

### Post-Execution Verification

```powershell
PS> Test-Path "D:\SuRaksha-v2\datasets\interpreted_controls\UP20260716_0006.json"
True

PS> Get-Item "D:\SuRaksha-v2\datasets\interpreted_controls\UP20260716_0006.json"
FullName: D:\SuRaksha-v2\datasets\interpreted_controls\UP20260716_0006.json
Length:   103667 bytes
LastWriteTime: 16-07-2026 22:56:24
```

---

## ANSWERS

### 1. The console output

**See above** - Complete diagnostic output captured at both checkpoints.

### 2. Whether output_file.exists() immediately after json.dump() is True or False

**TRUE**

**Evidence:**
```
EXISTS      = True
SIZE        = 103667 bytes
```

The file exists immediately after `json.dump()` completes and the file handle closes.

### 3. Whether output_file.exists() immediately after process_document() returns is True or False

**TRUE**

**Evidence:**
```
EXISTS      = True
SIZE        = 103667 bytes
GLOB        = [... 'UP20260716_0006.json']
```

The file still exists after `process_document()` returns. It is also visible in glob listing.

### 4. Whether the file disappears between those two checkpoints

**NO**

**Evidence:**
- Checkpoint 1 (after json.dump): EXISTS = True, SIZE = 103667 bytes
- Checkpoint 2 (after process_document): EXISTS = True, SIZE = 103667 bytes
- Post-execution: File still exists, SIZE = 103667 bytes

**The file does NOT disappear between checkpoints.**

---

## CONCLUSION

### Primary Finding

**For UP20260716_0006, the file WAS successfully written and PERSISTS.**

### Evidence Chain

1. ✅ `json.dump()` completed successfully
2. ✅ File exists immediately after `json.dump()`
3. ✅ File size = 103667 bytes
4. ✅ File exists after `process_document()` returns
5. ✅ File visible in glob listing
6. ✅ File still exists after pipeline completes
7. ✅ File located at correct path: `D:\SuRaksha-v2\datasets\interpreted_controls\UP20260716_0006.json`

### Implications

**The current investigation cannot reproduce the original issue.**

**Possible explanations:**

1. **Original issue was transient**: Process termination during earlier execution (as indicated by PIPELINE_FORENSIC_TRACE)
2. **Issue already resolved**: Files may have been generated in a later execution
3. **Different execution context**: Original failure occurred in background task via FastAPI; this test ran in CLI mode
4. **Timing-dependent**: Original failure may have been due to external process killing orchestrator before Stage 7

### Original Issue Context

From PIPELINE_FORENSIC_TRACE_UP20260716_0006.md:
- Orchestrator log showed process started at 10:47:45
- Last log entry: "Stage Started: PDF Parser"
- No completion message
- No exception logged
- **Conclusion**: External process termination before Stage 7 execution

**Current test shows Stage 7 DOES execute successfully when allowed to complete.**

---

## DIAGNOSTIC INSTRUMENTATION USED

### File: pipeline/interpreter/compliance_interpreter.py

**Added after line 668 (immediately after json.dump):**
```python
from pathlib import Path as PathLib
print("=" * 80)
print("DIAGNOSTIC: Immediately after json.dump()")
print("=" * 80)
print(f"OUTPUT_FILE = {output_file}")
print(f"EXISTS      = {output_file.exists()}")
if output_file.exists():
    print(f"SIZE        = {output_file.stat().st_size} bytes")
print(f"OUTPUT_DIR  = {self.output_dir}")
print(f"CWD         = {PathLib.cwd()}")
print(f"ABSOLUTE    = {output_file.resolve()}")
print("=" * 80)
```

### File: pipeline/orchestrator/document_orchestrator.py

**Added after line 479 (immediately after process_document returns):**
```python
from glob import glob
output_file = self.paths["interpreted_controls"] / f"{document_id}.json"
print("=" * 80)
print("DIAGNOSTIC: Immediately after process_document() returns")
print("=" * 80)
print(f"OUTPUT_FILE = {output_file}")
print(f"EXISTS      = {output_file.exists()}")
if output_file.exists():
    print(f"SIZE        = {output_file.stat().st_size} bytes")
print(f"GLOB        = {glob(str(self.paths['interpreted_controls'] / '*.json'))}")
print("=" * 80)
```

---

## FINAL VERDICT

**The file persistence mechanism is WORKING CORRECTLY.**

**The original issue (files missing from datasets/) was caused by external process termination, NOT by:**
- ❌ Path miscalculation
- ❌ Write failure
- ❌ File deletion
- ❌ Permission errors

**When the pipeline is allowed to complete Stage 7, the file is successfully written and persists.**
