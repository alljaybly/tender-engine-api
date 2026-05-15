/**
 * API service layer for tender upload and processing pipeline.
 *
 * Backend reference: api/routes/process.py
 *
 * Endpoints:
 *   POST /api/process/upload       — Upload tender document
 *   GET  /api/process/status/{id}  — Poll job status
 *   GET  /api/process/result/{id}  — Retrieve processing result
 */
import { ApiRequestError, getStoredToken } from './api';
import type {
  ProcessUploadResponse,
  ProcessingJobStatus,
  ProcessingResult,
} from '../types/process';

const API_BASE_URL = '/api';

/**
 * Get auth headers for multipart/form-data uploads.
 * The standard `api.ts` client injects JSON Content-Type, which is
 * incompatible with multipart uploads, so we build the request manually.
 */
function getAuthHeaders(): Record<string, string> {
  const token = getStoredToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Upload a tender document for processing.
 *
 * Uses real multipart/form-data upload with Authorization header.
 * Throws ApiRequestError on failure.
 */
export async function uploadTender(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<ProcessUploadResponse> {
  const url = `${API_BASE_URL}/process/upload`;

  const formData = new FormData();
  formData.append('file', file);

  return new Promise<ProcessUploadResponse>((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    // Track upload progress
    if (onProgress) {
      xhr.upload.addEventListener('progress', (event: ProgressEvent) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      });
    }

    xhr.addEventListener('load', () => {
      try {
        const body = JSON.parse(xhr.responseText);

        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(body as ProcessUploadResponse);
        } else {
          const detail =
            body?.detail || `Upload failed with status ${xhr.status}`;
          let code = 'upload_failed';
          if (xhr.status === 401) code = 'unauthorized';
          else if (xhr.status === 413) code = 'file_too_large';
          else if (xhr.status === 422) code = 'validation_error';
          else if (xhr.status === 409) code = 'conflict';
          reject(new ApiRequestError(detail, xhr.status, code));
        }
      } catch {
        reject(
          new ApiRequestError(
            'Failed to parse upload response',
            xhr.status,
            'parse_error',
          ),
        );
      }
    });

    xhr.addEventListener('error', () => {
      reject(
        new ApiRequestError(
          'Network error during upload. Please check your connection.',
          0,
          'network_error',
        ),
      );
    });

    xhr.addEventListener('abort', () => {
      reject(
        new ApiRequestError('Upload was cancelled', 0, 'upload_cancelled'),
      );
    });

    xhr.open('POST', url);
    // Set auth headers
    const authHeaders = getAuthHeaders();
    for (const [key, value] of Object.entries(authHeaders)) {
      xhr.setRequestHeader(key, value);
    }
    // Do NOT set Content-Type — the browser sets it automatically
    // with the correct multipart boundary for FormData
    xhr.send(formData);
  });
}

/**
 * Poll the status of a processing job.
 *
 * GET /api/process/status/{job_id}
 */
export async function getJobStatus(
  jobId: string,
): Promise<ProcessingJobStatus> {
  const url = `${API_BASE_URL}/process/status/${encodeURIComponent(jobId)}`;

  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(url, { method: 'GET', headers });
  } catch {
    throw new ApiRequestError(
      'Network error. Cannot reach backend server.',
      0,
      'network_error',
    );
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const detail =
      (body as { detail?: string })?.detail ||
      `Request failed with status ${response.status}`;
    let code = 'request_failed';
    if (response.status === 401) code = 'unauthorized';
    else if (response.status === 404) code = 'not_found';
    else if (response.status >= 500) code = 'server_error';
    throw new ApiRequestError(detail, response.status, code);
  }

  return body as ProcessingJobStatus;
}

/**
 * Retrieve the full processing result for a completed or partial_success job.
 *
 * GET /api/process/result/{job_id}
 */
export async function getJobResult(
  jobId: string,
): Promise<ProcessingResult> {
  const url = `${API_BASE_URL}/process/result/${encodeURIComponent(jobId)}`;

  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(url, { method: 'GET', headers });
  } catch {
    throw new ApiRequestError(
      'Network error. Cannot reach backend server.',
      0,
      'network_error',
    );
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  // The backend returns 200 with a detail message for queued/processing jobs
  if (response.status === 200 && body && typeof body === 'object' && 'detail' in (body as Record<string, unknown>)) {
    const detail = (body as { detail: string }).detail;
    if (detail && detail.includes('still')) {
      throw new ApiRequestError(detail, 200, 'job_not_ready');
    }
  }

  if (!response.ok) {
    const detail =
      (body as { detail?: string })?.detail ||
      `Request failed with status ${response.status}`;
    let code = 'request_failed';
    if (response.status === 401) code = 'unauthorized';
    else if (response.status === 404) code = 'not_found';
    else if (response.status >= 500) code = 'server_error';
    throw new ApiRequestError(detail, response.status, code);
  }

  return body as ProcessingResult;
}