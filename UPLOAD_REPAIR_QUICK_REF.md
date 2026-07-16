# Upload Pipeline Integration - Quick Reference

## 🐛 Bugs Fixed

### Bug 1: BackgroundTasks Instantiation Error
```python
# ❌ BEFORE (WRONG)
background_tasks: BackgroundTasks = BackgroundTasks()

# ✅ AFTER (CORRECT)
background_tasks: BackgroundTasks = Depends()
```

### Bug 2: Frontend Upload Disconnected
```javascript
// ❌ BEFORE (MOCKED)
export async function run({ file }) {
  return { document_id: deriveDocumentId(file.name) };
}

// ✅ AFTER (REAL API)
export async function run({ file }) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    headers: { "Authorization": `Bearer ${token}` },
    body: formData,
  });
  return await response.json();
}
```

---

## 📂 Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `backend/main.py` | Fixed Depends() + added logging | ~60 |
| `frontend/src/pipeline/stages/stageUpload.js` | API integration | ~30 |
| `frontend/src/pipeline/stages/stageParser.js` | Backend acknowledgment | ~5 |

**Total:** 3 files, ~95 lines

---

## 🔍 Log Prefixes

| Prefix | Where | What |
|--------|-------|------|
| `[UPLOAD]` | Backend endpoint | File upload, validation, saving |
| `[BACKGROUND]` | Background task | Pipeline execution |
| `[stageUpload]` | Frontend stage | API communication |
| `[stageParser]` | Frontend stage | Stage progress |

---

## ✅ Validation Commands

### Backend Test
```bash
curl -X POST http://localhost:8000/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@test.pdf"
```

### Check Logs
```bash
tail -f logs\orchestrator.log | findstr "UPLOAD\|BACKGROUND"
```

### Verify Files
```bash
dir datasets\raw\uploaded_documents\pdfs\UP*.pdf
dir datasets\controls\UP*.json
dir datasets\maps\UP*.json
```

### Check Database
```bash
curl "http://localhost:8000/maps?search=UP20260715" \
  -H "Authorization: Bearer <token>"
```

---

## 🚀 Quick Start

```bash
# Terminal 1: Backend
.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000 --reload

# Terminal 2: Frontend
cd frontend && npm run dev

# Terminal 3: Monitor
tail -f logs\orchestrator.log

# Browser: http://localhost:5173/pipeline
# Login: admin/admin123
# Upload PDF → Watch logs
```

---

## 📊 Execution Flow

```
Frontend Upload
    ↓
POST /documents/upload
    ↓
Validate + Save PDF
    ↓
Schedule Background Task ← Fixed with Depends()
    ↓
Return {document_id, status: "processing"}
    ↓
[BACKGROUND] Pipeline Executes
    ↓
Controls + MAPs Generated
    ↓
Database Updated
```

---

## ⚠️ Key Points

1. **Backend processes asynchronously** - Frontend gets immediate response, real processing happens in background
2. **Frontend shows mock progress** - For UX only, real results in database
3. **Use server logs to track** - `[UPLOAD]` and `[BACKGROUND]` prefixes show real progress
4. **Check /maps endpoint** - Real results appear there after ~1 minute

---

## 🎯 Success Indicators

- ✅ `[UPLOAD] ✓ PDF saved successfully`
- ✅ `[UPLOAD] ✓ Background task scheduled successfully`
- ✅ `[BACKGROUND] Background task started`
- ✅ `[BACKGROUND] ✓ Orchestrator instantiated`
- ✅ `[BACKGROUND] ✓ Pipeline completed successfully`
- ✅ File exists: `datasets/raw/uploaded_documents/pdfs/UP*.pdf`
- ✅ Artifacts exist: `datasets/controls/UP*.json`
- ✅ MAPs in database: `GET /maps?search=UP*` returns results

---

**Status:** ✅ Complete  
**Doc:** `UPLOAD_PIPELINE_INTEGRATION_REPORT.md` (full details)
