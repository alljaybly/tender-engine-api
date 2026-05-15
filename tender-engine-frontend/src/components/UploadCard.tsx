/**
 * UploadCard — Tender document upload component.
 *
 * Supports:
 * - PDF, DOCX, TXT file upload
 * - File validation (type, size)
 * - Real multipart/form-data upload via XHR with progress tracking
 * - Duplicate warnings from backend
 * - Disabled state during upload
 * - Loading/error states
 */
import { useState, useRef, type ChangeEvent } from 'react';
import { uploadTender } from '../services/process';
import {
  ALLOWED_EXTENSIONS,
  MAX_FILE_SIZE,
} from '../types/process';
import type { ProcessUploadResponse } from '../types/process';

interface UploadCardProps {
  /** Called when upload succeeds with the response data. */
  onUploadSuccess: (response: ProcessUploadResponse) => void;
}

export default function UploadCard({ onUploadSuccess }: UploadCardProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /**
   * Validate a selected file.
   * Returns an error string, or null if valid.
   */
  function validateFile(selectedFile: File): string | null {
    const ext = '.' + selectedFile.name.split('.').pop()?.toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(ext as typeof ALLOWED_EXTENSIONS[number])) {
      return `Unsupported file type "${ext}". Allowed: PDF, DOCX, TXT.`;
    }

    if (selectedFile.size > MAX_FILE_SIZE) {
      return `File too large (${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB). Maximum size is 50 MB.`;
    }

    if (selectedFile.size === 0) {
      return 'File is empty. Please select a non-empty file.';
    }

    return null;
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const selectedFile = e.target.files?.[0] || null;
    setFile(selectedFile);
    setError(null);
    setSuccessMessage(null);
    setProgress(0);

    if (selectedFile) {
      const validationError = validateFile(selectedFile);
      if (validationError) {
        setError(validationError);
        setFile(null);
        // Reset file input so the user can re-select
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }
    }
  }

  async function handleUpload() {
    if (!file) {
      setError('Please select a file first.');
      return;
    }

    // Re-validate before upload
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setUploading(true);
    setError(null);
    setSuccessMessage(null);
    setProgress(0);

    try {
      const response = await uploadTender(file, (percent: number) => {
        setProgress(percent);
      });

      setProgress(100);
      setSuccessMessage(
        `${file.name} uploaded successfully! Job ID: ${response.job_id}`,
      );
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      onUploadSuccess(response);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Upload failed. Please try again.';
      setError(message);
    } finally {
      setUploading(false);
    }
  }

  function handleCancel() {
    setFile(null);
    setError(null);
    setSuccessMessage(null);
    setProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="px-6 py-5 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Upload Tender</h2>
        <p className="mt-1 text-sm text-gray-500">
          Upload a tender document (PDF, DOCX, or TXT) for automated processing.
        </p>
      </div>

      <div className="px-6 py-5 space-y-4">
        {/* File input */}
        <div>
          <label
            htmlFor="tender-file-upload"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Select file
          </label>
          <input
            ref={fileInputRef}
            id="tender-file-upload"
            type="file"
            accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
            onChange={handleFileChange}
            disabled={uploading}
            className="block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-md file:border-0
              file:text-sm file:font-medium
              file:bg-blue-50 file:text-blue-700
              hover:file:bg-blue-100
              disabled:opacity-50 disabled:cursor-not-allowed
              cursor-pointer"
          />
          <p className="mt-1 text-xs text-gray-400">
            Supported: PDF, DOCX, TXT (max 50 MB)
          </p>
        </div>

        {/* Selected file info */}
        {file && !uploading && !error && (
          <div className="flex items-center justify-between bg-gray-50 rounded-md px-3 py-2">
            <div className="flex items-center gap-2 min-w-0">
              <svg
                className="h-5 w-5 text-gray-400 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                />
              </svg>
              <span className="text-sm text-gray-700 truncate">
                {file.name}
              </span>
              <span className="text-xs text-gray-400 flex-shrink-0">
                ({(file.size / 1024).toFixed(1)} KB)
              </span>
            </div>
          </div>
        )}

        {/* Upload progress bar */}
        {uploading && (
          <div>
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>Uploading...</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md px-4 py-3">
            <div className="flex items-start gap-2">
              <svg
                className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
                />
              </svg>
              <div className="text-sm text-red-700 whitespace-pre-wrap">
                {error}
              </div>
            </div>
          </div>
        )}

        {/* Success message */}
        {successMessage && (
          <div className="bg-green-50 border border-green-200 rounded-md px-4 py-3">
            <div className="flex items-start gap-2">
              <svg
                className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div className="text-sm text-green-700">{successMessage}</div>
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3">
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="inline-flex items-center px-4 py-2 border border-transparent
              text-sm font-medium rounded-md shadow-sm text-white
              bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2
              focus:ring-offset-2 focus:ring-blue-500
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors"
          >
            {uploading ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Uploading...
              </>
            ) : (
              'Upload & Process'
            )}
          </button>

          {(file || error) && (
            <button
              onClick={handleCancel}
              disabled={uploading}
              className="inline-flex items-center px-4 py-2 border border-gray-300
                text-sm font-medium rounded-md shadow-sm text-gray-700
                bg-white hover:bg-gray-50 focus:outline-none focus:ring-2
                focus:ring-offset-2 focus:ring-blue-500
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors"
            >
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
}