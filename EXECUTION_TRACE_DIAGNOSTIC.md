# Execution Trace Diagnostic Report
**Investigation**: Why no new verification_results or compliance_decisions JSON was produced  
**Method**: `AssignmentService.mark_assignment_complete()`  
**File**: `backend/database/services/assignment_service.py`

---

## Complete Execution Flow with Line Numbers

### ENTRY POINT: Line 400-410
```python
# Line 400-410: Database commit
self.db.commit()

# Line 403-406: PIPELINE EXECUTION CHAIN starts
# After successful database commit, trigger verification and decision.
# Failures in pipeline execution do NOT rollback assignment completion.
```

### CHECKPOINT 1: Extract Metadata (Lines 408-421)
```python
# Line 408-412: Initialize variables
document_id = None
requirement_id = None
plan_id = None

# Line 413-421: Extract from assignment.map_id
if assignment.map_id:  # BRANCH A
    map_record = self.db.query(ManagementActionPlan).filter_by(id=assignment.map_id).first()
    if map_record:  # BRANCH B
        document_id = map_record.source_document_id
        requirement_id = map_record.source_requirement_id
        
        # TASK 1: Derive plan_id from requirement_id to filter verification scope
        if requirement_id:  # BRANCH C
            plan_id = f"CVP_VR_{requirement_id}"
            logger.info(f"📋 Scoping verification to plan: {plan_id}")
```

**CRITICAL CHECKPOINT 1A: Lines 423-425**
```python
if not document_id:  # EXIT CONDITION 1
    logger.warning(f"Assignment {assignment_id} has no source_document_id, skipping verification")
    return assignment  # ← EARLY RETURN - NO VERIFICATION RUNS
```
**Question**: Did your test assignment have a valid `source_document_id`?  
**Impact**: If `document_id` is None, execution stops here. No agent decision, no verification, no decision engine.

**CHECKPOINT 1B: Lines 427-428**
```python
if not requirement_id:  # WARNING ONLY
    logger.warning(f"Assignment {assignment_id} has no source_requirement_id, verification may process entire document")
# ← Execution continues even without requirement_id
```

### CHECKPOINT 2: Locate Verification Plan (Lines 430-438)
```python
# Line 430-432: Get project root
current_file = Path(__file__).resolve()
project_root = current_file.parents[3]

# Line 434-435: Locate verification plan
plan_file = project_root / "datasets" / "verification_plans" / f"{document_id}.json"

# Line 437-439: Check if plan file exists
if not plan_file.exists():  # EXIT CONDITION 2
    logger.warning(f"Verification plan not found: {plan_file}, skipping verification")
    return assignment  # ← EARLY RETURN - NO VERIFICATION RUNS
```
**Question**: Does `datasets/verification_plans/MD13525.json` exist?  
**Impact**: If plan file doesn't exist, execution stops here. No agent decision, no verification, no decision engine.

---

## STAGE 0: Verification Agent Decision (Lines 441-524)

### Agent Invocation (Lines 441-450)
```python
# Line 441-442: Stage 0 begins
# ─── Stage 0: Verification Agent Decision ───
agent_decision_data = None  # Store for later persistence

# Line 443: Try block starts
try:
    # Line 444: Import agent service
    from backend.database.services.verification_agent_service import VerificationAgentService
    
    # Line 446: Create agent instance
    agent = VerificationAgentService(project_root)
    
    # Line 447-451: Call agent decision
    decision = agent.decide_verification_strategy(
        document_id=document_id,
        requirement_id=requirement_id,
        criticality=map_record.priority if map_record else None,
        department=assignment.department.name if assignment.department else None
    )
```

**CONDITIONS FOR AGENT TO BE CALLED:**
1. ✅ `document_id` is not None (passed Checkpoint 1A)
2. ✅ `plan_file` exists (passed Checkpoint 2)
3. ✅ Import succeeds (VerificationAgentService available)
4. ✅ No exception raised during `decide_verification_strategy()`

### Agent Decision Logging (Lines 453-458)
```python
# Line 453-458: Log agent analysis
logger.info(f"🤖 Verification Agent Analysis:")
logger.info(f"   Verdict: {decision.verdict}")
logger.info(f"   Reasoning: {decision.reasoning}")
logger.info(f"   Automated checks: {decision.automated_checks_available}/{decision.total_checks}")
logger.info(f"   Manual checks: {decision.manual_checks_required}/{decision.total_checks}")
logger.info(f"   Recommendation: {decision.recommended_action}")
```

### Agent Decision Persistence (Lines 460-493)
```python
# Line 460-480: Build agent_decision_data dict
from datetime import datetime
agent_decision_data = {
    "document_id": document_id,
    "requirement_id": requirement_id,
    "assignment_id": assignment_id,
    "verdict": decision.verdict,
    "reasoning": decision.reasoning,
    # ... (full structure)
}

# Line 482-483: Create output directory
agent_decisions_dir = project_root / "datasets" / "agent_decisions"
agent_decisions_dir.mkdir(exist_ok=True)

# Line 485-488: Write agent decision JSON
decision_file = agent_decisions_dir / f"{requirement_id or document_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
with open(decision_file, "w", encoding="utf-8") as f:
    json.dump(agent_decision_data, f, indent=2, ensure_ascii=False)
```

**RESULT**: Agent decision JSON is **ALWAYS WRITTEN** if agent successfully executes (lines 485-488).

---

## CRITICAL DECISION BRANCHES (Lines 490-520)

### BRANCH 1: NO_GO Verdict (Lines 490-493)
```python
# Line 490-493: NO_GO verdict
if decision.verdict == "NO_GO":  # EXIT CONDITION 3
    logger.warning(f"⛔ Verification blocked: {decision.reasoning}")
    logger.warning(f"   Action: {decision.recommended_action}")
    return assignment  # ← EARLY RETURN - NO EXECUTOR, NO DECISION ENGINE
```

**Behavior**: 
- **Executor called**: ❌ NO
- **Decision engine called**: ❌ NO
- **Reason**: Verification completely blocked by agent

---

### BRANCH 2: ESCALATE Verdict (Lines 495-508)
```python
# Line 495-508: ESCALATE verdict
if decision.verdict == "ESCALATE":
    logger.warning(f"⚠️ Escalated for manual review: {decision.reasoning}")
    logger.warning(f"   Action: {decision.recommended_action}")
    
    # KEY CHANGE: ESCALATE no longer terminates workflow
    # If automated checks are available, execute them
    if not decision.execute_automated:  # SUB-BRANCH A - EXIT CONDITION 4
        logger.info(f"   No automated checks available - routing to manual review only")
        # Future: Update assignment status to "ESCALATED" or similar
        return assignment  # ← EARLY RETURN - NO EXECUTOR, NO DECISION ENGINE
    
    logger.info(f"   Continuing with {decision.automated_checks_available} automated checks")
    logger.info(f"   {decision.manual_checks_required} checks flagged for manual review")
    # Fall through to verification execution
```

**Behavior**:
- **If `decision.execute_automated == False`**:
  - **Executor called**: ❌ NO
  - **Decision engine called**: ❌ NO
  - **Reason**: No automated checks available, manual review only
  
- **If `decision.execute_automated == True`**:
  - **Executor called**: ✅ YES (falls through to Stage 1)
  - **Decision engine called**: ✅ YES (falls through to Stage 2)
  - **Reason**: Automated checks exist, execute them despite escalation

**CRITICAL**: The value of `decision.execute_automated` determines whether executor runs!

---

### BRANCH 3: GO Verdict (Lines 510-513)
```python
# Line 510-513: GO verdict
if decision.verdict == "GO":
    logger.info(f"✅ Agent approved: {decision.reasoning}")
    logger.info(f"   Action: {decision.recommended_action}")
    # Fall through to verification execution
```

**Behavior**:
- **Executor called**: ✅ YES (falls through to Stage 1)
- **Decision engine called**: ✅ YES (falls through to Stage 2)
- **Reason**: Full approval, no restrictions

---

### Exception Handler (Lines 515-519)
```python
# Line 515-519: Exception catch block
except Exception as e:
    logger.error(f"❌ Verification agent failed for document {document_id}: {e}", exc_info=True)
    # Fallback: Continue with verification (preserve existing behavior)
    logger.warning("⚠️ Falling back to direct verification execution")
# ← Falls through to verification execution
```

**Behavior**:
- **If agent import fails or raises exception**:
  - **Executor called**: ✅ YES (fallback behavior)
  - **Decision engine called**: ✅ YES (fallback behavior)
  - **Reason**: Preserves backward compatibility, continues despite agent failure

---

## STAGE 1: Verification Executor (Lines 521-539)

### Executor Invocation (Lines 521-539)
```python
# Line 521-522: Stage 1 begins
# Stage 1: Execute Verification (independently wrapped)
try:
    # Line 523: Import executor
    from pipeline.executor.compliance_verification_executor import process_document
    
    # Line 525-527: Create args namespace
    # TASK 1: Pass plan_id to filter verification to specific requirement
    # Create args namespace as expected by executor
    args = argparse.Namespace(timeout=300, dry_run=False, document=None, plan=plan_id)
    
    # Line 529-532: Log execution
    if plan_id:
        logger.info(f"🎯 Executing verification for specific plan: {plan_id}")
    else:
        logger.warning(f"⚠️ No plan_id available, executing all plans for document {document_id}")
    
    # Line 534-535: Execute verification
    process_document(plan_file, args)
    logger.info(f"✅ Verification executed successfully for document {document_id}")
    
# Line 537-540: Exception handler
except Exception as e:
    logger.error(f"❌ Verification execution failed for document {document_id}: {e}", exc_info=True)
    # Continue to decision engine even if verification fails
```

**CONDITIONS FOR EXECUTOR TO BE CALLED:**
1. ✅ Passed Checkpoint 1A (`document_id` exists)
2. ✅ Passed Checkpoint 2 (`plan_file` exists)
3. ✅ Agent verdict was NOT "NO_GO"
4. ✅ If verdict was "ESCALATE", then `decision.execute_automated == True`
5. ✅ Import of `compliance_verification_executor` succeeds

**OUTPUT**: Writes `datasets/verification_results/{document_id}.json`

---

## STAGE 2: Decision Engine (Lines 542-552)

### Decision Engine Invocation (Lines 542-552)
```python
# Line 542-543: Stage 2 begins
# Stage 2: Execute Decision Engine (independently wrapped)
try:
    # Line 544: Import decision engine
    from pipeline.decision.compliance_decision_engine import process_document
    
    # Line 546-547: Execute decision engine
    # Process document to generate compliance decision
    process_document(document_id, plan_file)
    logger.info(f"✅ Compliance decision generated successfully for document {document_id}")
    
# Line 549-551: Exception handler
except Exception as e:
    logger.error(f"❌ Decision engine failed for document {document_id}: {e}", exc_info=True)
# ← Falls through to return

# Line 553: Final return
return assignment
```

**CONDITIONS FOR DECISION ENGINE TO BE CALLED:**
1. ✅ Passed Checkpoint 1A (`document_id` exists)
2. ✅ Passed Checkpoint 2 (`plan_file` exists)
3. ✅ Agent verdict was NOT "NO_GO"
4. ✅ If verdict was "ESCALATE", then `decision.execute_automated == True`
5. ✅ Import of `compliance_decision_engine` succeeds

**OUTPUT**: Writes `datasets/compliance_decisions/{document_id}_{timestamp}.json`

**NOTE**: Decision engine runs even if executor fails (line 540 comment: "Continue to decision engine even if verification fails")

---

## Summary: Exit Conditions and Early Returns

| Exit Condition | Line | Condition | Executor Runs? | Decision Engine Runs? | Agent Decision JSON Written? |
|----------------|------|-----------|----------------|----------------------|------------------------------|
| **EXIT 1** | 425 | `document_id` is None | ❌ NO | ❌ NO | ❌ NO |
| **EXIT 2** | 439 | `plan_file` doesn't exist | ❌ NO | ❌ NO | ❌ NO |
| **EXIT 3** | 493 | Agent verdict = "NO_GO" | ❌ NO | ❌ NO | ✅ YES |
| **EXIT 4** | 506 | Agent verdict = "ESCALATE" AND `execute_automated == False` | ❌ NO | ❌ NO | ✅ YES |
| **CONTINUE** | - | Agent verdict = "GO" | ✅ YES | ✅ YES | ✅ YES |
| **CONTINUE** | - | Agent verdict = "ESCALATE" AND `execute_automated == True` | ✅ YES | ✅ YES | ✅ YES |
| **FALLBACK** | 519 | Agent import/execution fails | ✅ YES | ✅ YES | ❌ NO |

---

## Diagnostic Questions for Your Test Case

Based on your observation that:
- ✅ Assignment completion succeeds
- ✅ UI synchronization succeeds
- ✅ Duplicate protection succeeds
- ❌ No new `verification_results` JSON produced
- ❌ No new `compliance_decisions` JSON produced

**This indicates one of the following occurred:**

### Most Likely: EXIT 4 - ESCALATE with execute_automated=False
```
Agent verdict = "ESCALATE"
decision.execute_automated = False
Line 506 returns early
```

**Check backend logs for**:
```
⚠️ Escalated for manual review: [reasoning]
   No automated checks available - routing to manual review only
```

### Alternative: EXIT 3 - NO_GO
```
Agent verdict = "NO_GO"
Line 493 returns early
```

**Check backend logs for**:
```
⛔ Verification blocked: [reasoning]
```

### Less Likely: Missing Metadata
```
Either:
- document_id is None (EXIT 1, line 425)
- plan_file doesn't exist (EXIT 2, line 439)
```

**Check backend logs for**:
```
Assignment {assignment_id} has no source_document_id, skipping verification
OR
Verification plan not found: {plan_file}, skipping verification
```

---

## Answer to Specific Questions

### Q1: Under what conditions is VerificationAgentService.decide_verification_strategy() called?
**Answer**: Lines 444-451  
**Conditions**:
1. `document_id` is not None (line 423 check passed)
2. `plan_file` exists (line 437 check passed)
3. VerificationAgentService import succeeds (line 444)

---

### Q2: Under what conditions is compliance_verification_executor.process_document() called?
**Answer**: Line 535  
**Conditions**:
1. `document_id` is not None (line 423 check passed)
2. `plan_file` exists (line 437 check passed)
3. **AND ONE OF**:
   - Agent verdict = "GO" (line 510)
   - Agent verdict = "ESCALATE" AND `decision.execute_automated == True` (line 503-508)
   - Agent failed with exception (line 515-519, fallback behavior)

---

### Q3: Under what conditions is compliance_decision_engine.process_document() called?
**Answer**: Line 547  
**Conditions**: **SAME AS EXECUTOR** (conditions from Q2)
1. `document_id` is not None
2. `plan_file` exists
3. Agent verdict was NOT "NO_GO"
4. If "ESCALATE", then `execute_automated == True`
5. OR agent failed (fallback)

**NOTE**: Decision engine runs even if executor threw exception (line 540 comment)

---

### Q4: Does an ESCALATE verdict intentionally prevent executor execution?
**Answer**: **CONDITIONAL**  
**Line 503**: `if not decision.execute_automated:`
- **If `execute_automated == False`**: YES, prevents execution (line 506 returns early)
- **If `execute_automated == True`**: NO, allows execution (line 508 falls through)

**This is intentional behavior**: ESCALATE means "needs manual review", but if automated checks exist (`execute_automated == True`), they should still run to provide data for manual reviewers.

---

### Q5: Does a GO verdict always execute the executor?
**Answer**: **YES**, assuming no exceptions  
**Line 510-513**: GO verdict has no additional conditionals, falls through to Stage 1 (line 521)

---

### Q6: Which exact return statement prevented new JSON artifacts during your test?
**Answer**: **Most Likely Line 506** (EXIT 4)

```python
# Line 503-506
if not decision.execute_automated:  # This condition was TRUE
    logger.info(f"   No automated checks available - routing to manual review only")
    return assignment  # ← THIS RETURN STATEMENT
```

**Why this is most likely**:
1. ✅ Agent decision JSON **WAS** written (lines 485-488 always execute before verdicts)
2. ❌ Verification results JSON **WAS NOT** written (executor never ran)
3. ❌ Compliance decision JSON **WAS NOT** written (decision engine never ran)

**This pattern matches**: Agent ran successfully → wrote decision → returned early at line 506

---

### Q7: Check Your Backend Logs

Look for this exact log sequence:

```
🤖 Verification Agent Analysis:
   Verdict: ESCALATE
   Reasoning: [some reasoning about manual review needed]
   Automated checks: 0/3  ← KEY: 0 automated checks
   Manual checks: 3/3
   Recommendation: [some action]
⚠️ Escalated for manual review: [reasoning]
   Action: [action]
   No automated checks available - routing to manual review only  ← EXIT POINT
```

**If you see this**, then execution **intentionally** stopped at line 506.

---

## Expected vs Actual Behavior

### Is This a Bug?

**Answer**: **NO, this is expected behavior**

**Reasoning**:
1. The verification agent analyzed the plan for MD13525_req32
2. It determined that 0 automated checks are available (all checks are manual)
3. It set `execute_automated = False`
4. Code at line 503 checked this flag
5. Code at line 506 returned early (intentional design)
6. No executor ran (expected when no automated checks)
7. No decision engine ran (expected when no verification ran)

### When Would This Be a Bug?

**It would be a bug IF**:
1. The verification plan actually HAS machine-verifiable checks, BUT
2. The agent incorrectly determined `execute_automated = False`

**To verify**:
- Check `datasets/verification_plans/MD13525.json`
- Find `CVP_VR_MD13525_req32` plan
- Count checks where `"machine_verifiable": true`
- If count > 0, then agent made wrong decision (BUG)
- If count == 0, then agent was correct (NOT A BUG)

---

## Conclusion

**Root Cause**: Line 506 early return triggered by ESCALATE verdict with `execute_automated == False`

**Is this expected?**: YES, if the plan truly has 0 machine-verifiable checks

**To confirm**: Check the agent decision JSON file that WAS written:
```bash
# Look for latest agent decision for MD13525_req32
ls -lt datasets/agent_decisions/MD13525_req32_*.json | head -1
cat [that file]
```

Look for:
```json
{
  "verdict": "ESCALATE",
  "execute_automated": false,  ← If false, line 506 return is expected
  "automated_checks_available": 0,  ← If 0, behavior is correct
  "reasoning": "..." ← Will explain why
}
```

**If `execute_automated` is `false` and `automated_checks_available` is 0, this is CORRECT BEHAVIOR, not a bug.**

---

**End of Diagnostic Report**
