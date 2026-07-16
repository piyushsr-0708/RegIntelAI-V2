# Upload Feature Demo Checklist

**Demo Date:** _____________  
**Presenter:** _____________

---

## Pre-Demo Setup (30 minutes before)

### ✅ System Health Check

- [ ] **Backend compiles without errors**
  ```bash
  .venv\Scripts\python.exe -m py_compile backend/main.py
  .venv\Scripts\python.exe -m py_compile pipeline/orchestrator/document_orchestrator.py
  ```

- [ ] **Validation tests pass**
  ```bash
  .venv\Scripts\python.exe test_upload_feature.py
  ```
  Expected: 7/7 tests passed

- [ ] **Original dataset intact**
  ```bash
  dir datasets\raw\master_directions\pdfs\*.pdf | Measure-Object | Select-Object -ExpandProperty Count
  ```
  Expected: 354 files

- [ ] **Database accessible**
  ```bash
  .venv\Scripts\python.exe verify_database.py
  ```

---

### ✅ Service Startup

- [ ] **Start backend server**
  ```bash
  .venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000 --reload
  ```
  
  Verify in browser: http://localhost:8000/docs
  Expected: FastAPI Swagger UI loads

- [ ] **Start frontend** (if applicable)
  ```bash
  cd frontend
  npm run dev
  ```
  
  Verify in browser: http://localhost:5173
  Expected: Frontend loads

- [ ] **Check logs directory**
  ```bash
  dir logs\orchestrator.log
  ```
  Expected: File exists and is writable

---

### ✅ Test User Authentication

- [ ] **Login as Admin**
  ```bash
  curl -X POST http://localhost:8000/auth/login ^
    -H "Content-Type: application/json" ^
    -d "{\"username\": \"admin\", \"password\": \"admin123\"}"
  ```
  
  Expected: Returns `access_token`

- [ ] **Save token for demo**
  ```bash
  # Save token to environment variable or text file
  set DEMO_TOKEN=<your_access_token>
  ```

---

## Demo Script

### Part 1: Show Existing System (2 minutes)

- [ ] **Show original RBI dataset**
  - Navigate to: `datasets/raw/master_directions/pdfs/`
  - Show MD10190.pdf and other files
  - Explain: "These are the 354 original RBI circulars"

- [ ] **Show dashboard with existing data**
  - Open browser: http://localhost:8000/maps
  - Or use frontend if available
  - Show existing MAPs from MD documents

- [ ] **Emphasize immutability**
  - "This original dataset must never be modified"
  - "We need a separate upload system"

---

### Part 2: Upload Demo Document (3 minutes)

#### Option A: Using curl (Technical)

- [ ] **Prepare test PDF**
  - Use any small PDF file (< 5MB)
  - Rename to: `test_circular.pdf`
  - Place in project root

- [ ] **Execute upload command**
  ```bash
  curl -X POST http://localhost:8000/documents/upload ^
    -H "Authorization: Bearer %DEMO_TOKEN%" ^
    -F "file=@test_circular.pdf"
  ```

- [ ] **Show response**
  ```json
  {
    "document_id": "UP20260715_0001",
    "filename": "test_circular.pdf",
    "status": "processing",
    "message": "Document uploaded successfully. Processing in background."
  }
  ```

- [ ] **Highlight key points**
  - Document ID format: UPYYYYMMDD_NNNN (human-readable)
  - Status: "processing" (immediate response)
  - Processing happens in background

#### Option B: Using Frontend (User-Friendly)

- [ ] **Open upload page** (if implemented)
- [ ] **Select PDF file**
- [ ] **Click Upload button**
- [ ] **Show success message with document ID**

---

### Part 3: Show Separation (2 minutes)

- [ ] **Show uploaded document location**
  - Navigate to: `datasets/raw/uploaded_documents/pdfs/`
  - Show: `UP20260715_0001.pdf`
  - Explain: "Completely separate from original dataset"

- [ ] **Show original dataset untouched**
  - Navigate to: `datasets/raw/master_directions/pdfs/`
  - Show: Still has exactly 354 files
  - No new files added

- [ ] **Show directory structure**
  ```
  datasets/raw/
  ├── master_directions/    ← Original (immutable)
  └── uploaded_documents/   ← New (separate)
  ```

---

### Part 4: Monitor Processing (2 minutes)

- [ ] **Show logs in real-time**
  ```bash
  tail -f logs\orchestrator.log | findstr "UP20260715"
  ```

- [ ] **Explain pipeline stages**
  - Stage 1: PDF Parser
  - Stage 2: Document Normalizer
  - ...
  - Stage 13: Database Ingest
  - Stage 14: Dashboard Aggregator

- [ ] **Show generated artifacts**
  ```bash
  dir datasets\parsed\UP20260715_0001.json
  dir datasets\controls\UP20260715_0001.json
  dir datasets\maps\UP20260715_0001.json
  ```

---

### Part 5: Show Results (3 minutes)

- [ ] **Wait for processing to complete**
  - Look for: "✓ PIPELINE ORCHESTRATION COMPLETED" in logs
  - Typical time: ~1 minute

- [ ] **Query MAPs from uploaded document**
  ```bash
  curl "http://localhost:8000/maps?search=UP20260715" ^
    -H "Authorization: Bearer %DEMO_TOKEN%"
  ```

- [ ] **Show dashboard includes both datasets**
  - Open: http://localhost:8000/maps
  - Show: MAPs from both MD and UP documents
  - Filter: Show ability to search by document ID

- [ ] **Show MAP details**
  - Click on a MAP from uploaded document
  - Show: Full control details, verification plan, etc.
  - Demonstrate: Approve MAP, create assignment

---

### Part 6: Highlight Architecture (2 minutes)

- [ ] **Show code changes (minimal)**
  - Open: `pipeline/orchestrator/document_orchestrator.py`
  - Show: 3 lines modified (pdf_source_dir parameter)
  - Emphasize: Orchestrator remains document-agnostic

- [ ] **Show dependency injection**
  - Open: `backend/main.py`
  - Show: Upload endpoint passes pdf_source_dir to orchestrator
  - Explain: No document-type routing in orchestrator

- [ ] **Show backward compatibility**
  - Run existing pipeline on MD document:
  ```bash
  .venv\Scripts\python.exe pipeline\orchestrator\document_orchestrator.py MD10190
  ```
  - Show: Works identically as before

---

## Demo Talking Points

### Key Messages

1. **Original Dataset Immutability**
   - "354 original RBI circulars remain completely untouched"
   - "Separate directory structure ensures no accidental modifications"

2. **Minimal Implementation**
   - "Only 2 files modified, ~73 lines of code"
   - "No changes to the 14-stage pipeline logic"
   - "No new frameworks or services introduced"

3. **Backward Compatibility**
   - "All existing functionality works identically"
   - "Existing endpoints unchanged"
   - "CLI execution for MD documents preserved"

4. **Architecture Excellence**
   - "Dependency injection keeps orchestrator document-agnostic"
   - "Upload endpoint owns path resolution"
   - "Future document sources require zero orchestrator changes"

5. **User Experience**
   - "Immediate feedback with document ID"
   - "Background processing (user doesn't wait)"
   - "Same dashboard for all documents"

---

## Q&A Preparation

### Expected Questions & Answers

**Q: What happens if pipeline processing fails?**
A: The PDF remains saved, but no controls/MAPs are generated. Error is logged to `logs/orchestrator.log`. Future enhancement: add retry mechanism and user notification.

**Q: Can users check upload progress?**
A: Currently no dedicated status endpoint. Users can poll the MAPs endpoint with the document ID. Future enhancement: WebSocket or SSE for real-time updates.

**Q: Is there a size limit for uploads?**
A: Yes, 50MB maximum. This is suitable for typical regulatory PDF documents (3-5MB average).

**Q: What file types are supported?**
A: Only PDF files. The system validates file extension before accepting.

**Q: Can the same document be uploaded twice?**
A: Yes, it will get a different document ID each time. Future enhancement: content hash comparison for duplicate detection.

**Q: How long does processing take?**
A: Approximately 1 minute for a typical regulatory document. This includes all 14 pipeline stages plus database ingestion.

**Q: Who can upload documents?**
A: Only users with DOC_UPLOAD permission: Super Admin, Admin, and Compliance Head roles.

**Q: What happens to metadata.csv?**
A: It's preserved in master_directions but not used by the pipeline. Uploaded documents don't need metadata.csv.

**Q: Can we upload non-RBI documents?**
A: Technically yes, but the pipeline is optimized for RBI regulatory content. Future enhancement: add content validation.

**Q: How does this scale?**
A: Current implementation uses FastAPI BackgroundTasks (in-process). For production scale: consider Celery + Redis for distributed task queue.

---

## Troubleshooting

### Issue: Upload fails with 401 Unauthorized
**Solution:** Ensure JWT token is valid and not expired. Re-login if needed.

### Issue: Upload fails with 403 Forbidden
**Solution:** User needs DOC_UPLOAD permission. Login as Admin or Compliance Head.

### Issue: Upload succeeds but no MAPs generated after 2 minutes
**Solution:** Check `logs/orchestrator.log` for pipeline errors. Verify PDF is valid.

### Issue: Backend won't start
**Solution:** 
- Check port 8000 is available
- Verify database file exists
- Check virtual environment is activated

### Issue: Cannot find uploaded PDF
**Solution:** Check `datasets/raw/uploaded_documents/pdfs/` directory. Verify document ID matches response.

---

## Post-Demo Cleanup (Optional)

- [ ] **Stop backend server** (Ctrl+C)
- [ ] **Stop frontend** (Ctrl+C)
- [ ] **Remove test uploads** (optional)
  ```bash
  del datasets\raw\uploaded_documents\pdfs\UP20260715_*.pdf
  del datasets\parsed\UP20260715_*.json
  del datasets\controls\UP20260715_*.json
  del datasets\maps\UP20260715_*.json
  ```
- [ ] **Archive logs** (optional)
  ```bash
  copy logs\orchestrator.log logs\orchestrator_demo_%DATE%.log
  ```

---

## Success Criteria

Demo is successful if:

✅ Upload endpoint accepts PDF and returns document ID  
✅ Processing completes without errors  
✅ Generated MAPs appear in dashboard  
✅ Original dataset remains untouched (354 files)  
✅ Both MD and UP documents visible in unified dashboard  
✅ Backward compatibility demonstrated (MD pipeline still works)  

---

## Backup Plan

If live demo fails:

**Option 1: Use Pre-Recorded Demo**
- Record successful upload + processing beforehand
- Show video instead of live execution

**Option 2: Show Validation Tests**
- Run `test_upload_feature.py`
- Show 7/7 tests passing
- Walk through code instead of live execution

**Option 3: Show Documentation**
- Open `UPLOAD_ARCHITECTURE_DIAGRAM.md`
- Walk through architecture visually
- Show code snippets from implementation

---

## Demo Materials Checklist

Files to have ready:

- [ ] `test_circular.pdf` (sample PDF for upload)
- [ ] `test_upload_feature.py` (validation script)
- [ ] `UPLOAD_FEATURE_QUICKSTART.md` (API reference)
- [ ] `UPLOAD_ARCHITECTURE_DIAGRAM.md` (visual aid)
- [ ] `UPLOAD_IMPLEMENTATION_SUMMARY.md` (executive summary)
- [ ] Access token (saved in text file or environment variable)
- [ ] Browser bookmark: http://localhost:8000/docs
- [ ] Browser bookmark: http://localhost:8000/maps
- [ ] Terminal windows pre-configured:
  - Terminal 1: Backend server
  - Terminal 2: Log viewer
  - Terminal 3: API commands

---

**Good luck with the demo! 🚀**

Remember: The key achievement is preserving the original dataset while enabling new uploads through minimal architectural changes and dependency injection.
