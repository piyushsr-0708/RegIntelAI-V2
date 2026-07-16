# Upload Feature Quick Start Guide

## For Developers

### Testing the Upload Endpoint

#### 1. Start the Backend Server
```bash
cd D:\SuRaksha-v2
.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000 --reload
```

#### 2. Get an Access Token
```bash
# Login as admin
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Save the access_token from response
```

#### 3. Upload a PDF Document
```bash
curl -X POST http://localhost:8000/documents/upload \
  -H "Authorization: Bearer <your_access_token>" \
  -F "file=@path/to/test_circular.pdf"
```

**Expected Response:**
```json
{
  "document_id": "UP20260715_0001",
  "filename": "test_circular.pdf",
  "status": "processing",
  "message": "Document uploaded successfully. Processing in background."
}
```

#### 4. Monitor Pipeline Processing
```bash
# Watch orchestrator logs
tail -f logs/orchestrator.log | grep "UP20260715"
```

#### 5. Check Results
```bash
# After ~1 minute, check if MAPs were generated
curl -X GET http://localhost:8000/maps?search=UP20260715 \
  -H "Authorization: Bearer <your_access_token>"
```

---

## For Frontend Developers

### API Endpoint Specification

**Endpoint:** `POST /documents/upload`

**Authentication:** Required (Bearer token)

**Required Permission:** `doc:upload` (Admin, Compliance Head, Super Admin)

**Content-Type:** `multipart/form-data`

**Request:**
```javascript
const formData = new FormData();
formData.append('file', pdfFile); // File object from input

fetch('http://localhost:8000/documents/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`
  },
  body: formData
})
  .then(response => response.json())
  .then(data => {
    console.log('Document ID:', data.document_id);
    console.log('Status:', data.status);
    // Show success message to user
    // Optionally: poll for processing status
  })
  .catch(error => {
    console.error('Upload failed:', error);
    // Show error message to user
  });
```

**Success Response (200):**
```json
{
  "document_id": "UP20260715_0001",
  "filename": "uploaded_circular.pdf",
  "status": "processing",
  "message": "Document uploaded successfully. Processing in background."
}
```

**Error Responses:**

| Status | Reason | Response |
|--------|--------|----------|
| 400 | Not a PDF file | `{"detail": "Only PDF files are accepted"}` |
| 400 | File too large | `{"detail": "File too large. Maximum size is 50MB"}` |
| 401 | Not authenticated | `{"detail": "Not authenticated"}` |
| 403 | Missing permission | `{"detail": "Insufficient permissions"}` |
| 500 | Server error | `{"detail": "Failed to save uploaded document"}` |

---

## React Component Example

```typescript
import React, { useState } from 'react';
import { useAuth } from './auth-context'; // Your auth hook

interface UploadResponse {
  document_id: string;
  filename: string;
  status: string;
  message: string;
}

export function DocumentUploader() {
  const { accessToken } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [uploadedDoc, setUploadedDoc] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are allowed');
      return;
    }

    // Validate file size (50MB)
    if (file.size > 50 * 1024 * 1024) {
      setError('File size must be less than 50MB');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8000/documents/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data: UploadResponse = await response.json();
      setUploadedDoc(data);
      
      // Optional: Redirect to document detail page
      // navigate(`/documents/${data.document_id}`);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="document-uploader">
      <h2>Upload RBI Circular</h2>
      
      <input
        type="file"
        accept=".pdf"
        onChange={handleFileSelect}
        disabled={uploading}
      />

      {uploading && (
        <div className="upload-status">
          <p>Uploading document...</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          <p>{error}</p>
        </div>
      )}

      {uploadedDoc && (
        <div className="success-message">
          <p>✓ Document uploaded successfully</p>
          <p>Document ID: <strong>{uploadedDoc.document_id}</strong></p>
          <p>Processing in background. Check the dashboard in ~1 minute.</p>
        </div>
      )}
    </div>
  );
}
```

---

## Document ID Format

**Pattern:** `UPYYYYMMDD_NNNN`

**Examples:**
- `UP20260715_0001` - First upload on July 15, 2026
- `UP20260715_0002` - Second upload on July 15, 2026
- `UP20260716_0001` - First upload on July 16, 2026

**Components:**
- `UP` - Prefix for uploaded documents
- `YYYYMMDD` - Upload date (2026-07-15)
- `NNNN` - 4-digit sequence number (resets daily)

**Comparison with Original RBI Documents:**
- Original: `MD10190`, `MD10191`, etc. (MD prefix)
- Uploaded: `UP20260715_0001`, `UP20260715_0002`, etc. (UP prefix)

---

## File Storage Locations

### Uploaded PDFs
```
datasets/raw/uploaded_documents/pdfs/
├── UP20260715_0001.pdf
├── UP20260715_0002.pdf
└── ...
```

### Generated Artifacts
All generated files use the document ID:
```
datasets/
├── parsed/UP20260715_0001.json
├── requirements/UP20260715_0001.json
├── controls/UP20260715_0001.json
├── maps/UP20260715_0001.json
└── ...
```

### Original RBI Dataset (Read-Only)
```
datasets/raw/master_directions/pdfs/
├── MD10190.pdf
├── MD10191.pdf
└── ... (354 documents)
```

**Important:** Never modify files in `master_directions/`

---

## Processing Status

### Immediate Response
After upload, endpoint returns immediately with `status: "processing"`.

### Background Processing Timeline
1. **0-10s:** PDF parsing
2. **10-20s:** Requirement extraction
3. **20-30s:** Control generation
4. **30-40s:** Verification planning
5. **40-50s:** MAP generation
6. **50-60s:** Database ingestion

**Total Time:** ~1 minute for typical regulatory document

### Checking Status
Currently no status endpoint. Options:

**Option 1: Poll MAPs endpoint**
```javascript
const checkDocumentStatus = async (documentId: string) => {
  const response = await fetch(
    `http://localhost:8000/maps?search=${documentId}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const data = await response.json();
  return data.total > 0; // true if processing complete
};

// Poll every 10 seconds
const pollInterval = setInterval(async () => {
  const isReady = await checkDocumentStatus(documentId);
  if (isReady) {
    clearInterval(pollInterval);
    // Processing complete, refresh UI
  }
}, 10000);
```

**Option 2: Check logs (dev only)**
```bash
tail -f logs/orchestrator.log | grep "UP20260715"
```

---

## Troubleshooting

### Upload Fails with "Not authenticated"
**Fix:** Ensure JWT token is valid and included in Authorization header

### Upload Fails with "Insufficient permissions"
**Fix:** User must have `doc:upload` permission (Admin, Compliance Head, or Super Admin role)

### Upload Succeeds but No MAPs Generated
**Possible causes:**
1. Pipeline failed during processing (check `logs/orchestrator.log`)
2. PDF is not a valid regulatory document
3. Document has no extractable requirements

**Debug:**
```bash
# Check orchestrator logs
cat logs/orchestrator.log | grep "UP20260715"

# Check if intermediate files were created
ls datasets/parsed/UP20260715_0001.json
ls datasets/controls/UP20260715_0001.json
ls datasets/maps/UP20260715_0001.json
```

### File Too Large Error
**Fix:** Compress PDF or split into multiple documents. Current limit: 50MB

### Wrong File Type Error
**Fix:** Only `.pdf` files accepted. Convert to PDF if needed.

---

## Validation Script

Run automated tests to verify implementation:

```bash
python test_upload_feature.py
```

**Expected output:**
```
✓ PASS: test_document_id_generation
✓ PASS: test_orchestrator_backward_compatibility
✓ PASS: test_orchestrator_pdf_source_override
✓ PASS: test_upload_directory_structure
✓ PASS: test_database_ingest_document_scoped
✓ PASS: test_permissions_configuration
✓ PASS: test_original_dataset_immutability

Results: 7/7 tests passed
✓ ALL TESTS PASSED - Implementation is validated
```

---

## Future Enhancements

### Coming Soon
1. **Progress Tracking** - Real-time processing status updates
2. **Upload History** - Database table tracking all uploads
3. **Duplicate Detection** - Prevent re-uploading same document
4. **Content Validation** - Verify PDF contains regulatory content
5. **Status Endpoint** - `GET /documents/{doc_id}/status`

### Not Implemented (Out of Scope)
- OCR for scanned PDFs (assumes text-based PDFs)
- Multi-file upload (one file at a time)
- Upload queue management
- Manual retry for failed processing
- Download original uploaded PDF

---

## Support

**Issues?** Check:
1. `logs/orchestrator.log` - Pipeline execution logs
2. `test_upload_feature.py` - Run validation tests
3. `UPLOAD_FEATURE_IMPLEMENTATION_REPORT.md` - Full technical documentation

**Need Help?** Contact: [Your contact info]
