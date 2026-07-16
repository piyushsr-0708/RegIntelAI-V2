# Session Dashboard Fix Report

## Problem Statement

**Observed Behavior:**
- Document uploaded: 20 pages
- Session Dashboard shows: 115 pages (incorrect)
- Dashboard appears to load data from stale artifacts or mock simulation

## Root Cause Analysis

### Data Flow Investigation

The Session Dashboard displays data from a **completely independent frontend mock pipeline simulation** that has NO connection to the actual backend document processing.

#### Current (Broken) Flow:

```
User uploads 20-page PDF
    ↓
Backend API (/documents/upload)
    ↓
Python Pipeline (background processing)
    ↓
Datasets (parsed/, requirements/, maps/) ✓ CORRECT DATA
    ↓
Database ✓ CORRECT DATA

[COMPLETELY SEPARATE]

Frontend Mock Pipeline Simulation:
    ↓
stageParser.js → Generates FAKE random page count (8-128 pages)
    ↓
stageDashboardAggregator.js → Aggregates fake data
    ↓
SessionContext (React in-memory state)
    ↓
SessionDashboard.jsx → Displays FAKE DATA ✗
```

### Specific Root Cause

File: `frontend/src/pipeline/stages/stageParser.js`

```javascript
// Line 18-19: Random fake data generation
const pages = 8 + Math.floor(rng() * 120);  // Generates 8-128 random pages
const words = pages * (280 + Math.floor(rng() * 120));
```

The frontend pipeline runs as a **UI simulation only** and generates completely fake data using a seeded random number generator. This data is displayed on the Session Dashboard, while the actual uploaded document is processed correctly by the backend but never displayed.

## Solution Implemented

### 1. Backend API Endpoint (Added)

**File Modified:** `backend/main.py`

Added new endpoint: `GET /documents/{document_id}/session`

This endpoint:
- Reads actual parsed document metadata from `datasets/parsed/{document_id}.json`
- Reads actual requirements count from `datasets/requirements/{document_id}.json`
- Reads actual MAPs count and departments from `datasets/maps/{document_id}.json`
- Returns real metadata including:
  - `page_count` (actual PDF page count)
  - `word_count` (estimated from pages)
  - `requirements_count` (actual extracted requirements)
  - `maps_count` (actual generated MAPs)
  - `departments_count` (actual departments impacted)

### 2. Frontend Dashboard Update (Modified)

**File Modified:** `frontend/src/pages/SessionDashboard.jsx`

Changes:
- Added `React.useEffect` hook to detect uploaded documents (document_id starts with "UP")
- Fetches real data from backend API `/documents/{document_id}/session`
- Merges real data with session context
- Displays real metadata instead of mock simulation data

Key logic:
```javascript
// Detect uploaded documents
if (docId && docId.startsWith("UP")) {
  fetch(`http://localhost:8000/documents/${docId}/session`, ...)
    .then(data => {
      // Merge real data with session
      setRealData(data);
    });
}

// Display merged data
const displaySession = realData ? {
  ...session,
  pages: realData.page_count,  // Real data
  requirements_found: realData.requirements_count,  // Real data
  maps_generated: realData.maps_count,  // Real data
  // etc.
} : session;  // Fallback to mock for non-uploaded docs
```

## Files Modified

1. **backend/main.py** (Added ~70 lines)
   - New endpoint: `/documents/{document_id}/session`
   - Returns actual document metadata from datasets

2. **frontend/src/pages/SessionDashboard.jsx** (Modified ~50 lines)
   - Added React import
   - Added useEffect to fetch real data for uploaded documents
   - Merged real data with mock session data
   - Updated all references to use `displaySession` instead of `session`

## Validation Steps

### Manual Testing Required:

1. **Upload a new PDF:**
   ```bash
   # Use frontend upload UI or curl
   curl -F "file=@test.pdf" http://localhost:8000/documents/upload \
     -H "Authorization: Bearer <token>"
   ```

2. **Wait for backend processing to complete** (check backend logs)

3. **Open Session Dashboard** for the uploaded document

4. **Verify displayed metadata matches uploaded document:**
   - ✓ Filename correct
   - ✓ Page count correct (not random 8-128)
   - ✓ Word count reasonable (not random)
   - ✓ Requirement count matches backend extraction
   - ✓ MAP count matches backend generation
   - ✓ Department count matches backend assignment

### Automated Validation Script:

**File:** `validate_session_fix.py`

Runs automated tests of the API endpoint:
```bash
python validate_session_fix.py
```

Expected output:
```
PASS: All values match expected data
```

## Regression Testing

### What Should NOT Break:

1. **Non-uploaded documents** (existing MD* documents):
   - Should continue to work with current mock pipeline
   - SessionDashboard will NOT fetch API data (no "UP" prefix)
   - Displays mock simulation data as before

2. **Pipeline page simulation:**
   - Still runs for UI feedback
   - Still generates mock stages and timing
   - Only SessionDashboard display is corrected

3. **Existing sessions in SessionContext:**
   - Remain unchanged
   - Only newly viewed uploaded sessions fetch real data

## Known Limitations

1. **Mock stages still displayed:**
   - The "Pipeline Summary" section still shows mock stage timings
   - Real pipeline timing not yet integrated
   - Could be fixed by storing actual stage durations during backend processing

2. **Dual data flow:**
   - Frontend still runs mock simulation in parallel with backend
   - Only SessionDashboard display is corrected
   - Full solution would eliminate frontend mock entirely

3. **No real-time updates:**
   - Dashboard fetches data once on load
   - Does not poll for updates during backend processing
   - User must refresh page to see completed processing

## Testing Checklist

- [ ] Backend server running on port 8000
- [ ] Frontend server running on port 5173
- [ ] Upload new PDF document
- [ ] Wait for backend processing completion
- [ ] Navigate to Session Dashboard
- [ ] Verify page count matches uploaded PDF
- [ ] Verify word count is reasonable (not random)
- [ ] Verify requirements count matches backend extraction
- [ ] Verify MAPs count matches backend generation
- [ ] Verify departments count is correct
- [ ] Verify filename displays original upload name
- [ ] Verify existing (non-uploaded) sessions still work
- [ ] Verify no console errors in browser

## Success Criteria

✅ **PASS if:**
- Uploaded document metadata (pages, words, requirements, MAPs) matches actual backend-processed data
- Filename displayed is original uploaded filename, not random
- No regression in existing functionality

❌ **FAIL if:**
- Dashboard still shows random/incorrect metadata for uploaded documents
- API returns 404 or errors
- Existing sessions break
- Console errors appear

## Conclusion

**Root Cause:** Frontend mock pipeline simulation displayed instead of actual backend data

**Fix:** Added backend API endpoint + frontend fetch logic to display real data for uploaded documents

**Impact:** Minimal - only uploaded documents (UP* prefix) fetch real data; existing functionality unchanged

**Files Modified:** 2 files (backend/main.py, frontend/src/pages/SessionDashboard.jsx)

**Validation:** Manual testing required - automated script provided
