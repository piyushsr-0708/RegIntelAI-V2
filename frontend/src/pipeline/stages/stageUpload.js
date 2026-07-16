/**
 * stageUpload.js — RegIntel AI V2 Pipeline Stage 1
 *
 * Interface:
 *   run(input) → UploadOutput
 *
 * Input:  { file: File }
 * Output: { filename, file_size_bytes, mime_type, upload_timestamp, document_id }
 *
 * Connects to backend POST /documents/upload endpoint for real processing.
 */
import { deriveDocumentId } from "../pipelineUtils.js";

const API_BASE_URL = "http://localhost:8000";

export async function run({ file }) {
  console.log("[stageUpload] Starting upload stage");
  console.log("[stageUpload] File:", file.name, "Size:", file.size, "bytes");

  // Get auth token — AuthContext stores it in sessionStorage under 'regintel_jwt'
  const token = sessionStorage.getItem("regintel_jwt");
  if (!token) {
    console.error("[stageUpload] No auth token found — falling back to local document_id derivation");
    // Return minimal output so downstream stages still have a valid document_id and filename.
    return {
      filename:         file.name,
      file_size_bytes:  file.size,
      mime_type:        file.type || "application/pdf",
      upload_timestamp: new Date().toISOString(),
      document_id:      deriveDocumentId(file.name),
    };
  }

  console.log("[stageUpload] Auth token found, preparing upload request");

  // Create FormData for multipart upload
  const formData = new FormData();
  formData.append("file", file);

  console.log("[stageUpload] Sending POST request to /documents/upload");

  try {
    const response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
      },
      body: formData,
    });

    console.log("[stageUpload] Response status:", response.status);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: "Upload failed" }));
      console.error("[stageUpload] Upload failed:", errorData);
      throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
    }

    const data = await response.json();
    console.log("[stageUpload] Upload successful:", data);

    // Return data in expected format for pipeline
    return {
      filename:          file.name,
      file_size_bytes:   file.size,
      mime_type:         file.type || "application/pdf",
      upload_timestamp:  new Date().toISOString(),
      document_id:       data.document_id, // Use server-generated ID
      backend_status:    data.status,
      backend_message:   data.message,
    };
  } catch (error) {
    console.error("[stageUpload] Error during upload:", error);

    // Degrade gracefully: return a locally-derived document_id so the
    // frontend simulation stages can still produce valid session data.
    return {
      filename:         file.name,
      file_size_bytes:  file.size,
      mime_type:        file.type || "application/pdf",
      upload_timestamp: new Date().toISOString(),
      document_id:      deriveDocumentId(file.name),
    };
  }
}
