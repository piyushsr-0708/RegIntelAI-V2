/**
 * stageUpload.js — RegIntel AI V2 Pipeline Stage 1
 *
 * Interface:
 *   run(input) → UploadOutput
 *
 * Input:  { file: File }
 * Output: { filename, file_size_bytes, mime_type, upload_timestamp, document_id }
 *
 * Real integration: replace body with actual file validation, virus scan,
 * and storage to a local temp directory via the Python acquisition module.
 */
import { deriveDocumentId } from "../pipelineUtils.js";

export async function run({ file }) {
  return {
    filename:          file.name,
    file_size_bytes:   file.size,
    mime_type:         file.type || "application/octet-stream",
    upload_timestamp:  new Date().toISOString(),
    document_id:       deriveDocumentId(file.name),
  };
}
