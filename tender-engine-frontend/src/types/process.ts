/**
 * TypeScript types matching the backend process schemas exactly.
 *
 * Backend reference: api/schemas/process.py
 */
export interface ProcessUploadResponse {
  job_id: string;
  status: string;
  filename: string;
  message: string;
}

export type JobStatusValue =
  | 'queued'
  | 'processing'
  | 'extracting'
  | 'boq_analysis'
  | 'pricing'
  | 'completed'
  | 'partial_success'
  | 'failed';

export interface ProcessingJobStatus {
  job_id: string;
  status: JobStatusValue;
  progress: string | null;
  created_at: string | null;
  updated_at: string | null;
  error_message: string | null;
}

export interface ExtractedBOQItem {
  item_no: string | null;
  description: string;
  quantity: number | null;
  unit: string | null;
  rate: number | null;
  amount: number | null;
}

export interface WorkforceData {
  [key: string]: unknown;
}

export interface ScheduleData {
  [key: string]: unknown;
}

export type ResultStatus = 'completed' | 'partial_success' | 'failed';

export interface ProcessingResult {
  job_id: string;
  status: ResultStatus;
  filename: string | null;

  /** Stage tracking (present for completed and partial_success) */
  completed_stages: string[];
  failed_stages: string[];

  /** Stage 1: Metadata */
  metadata: Record<string, unknown>;

  /** Stage 2: Document text */
  full_text: string | null;
  text_length: number | null;

  /** Stage 3: Extracted entities */
  detected_sector: string | null;
  detected_duration_months: number | null;
  detected_locations: string[];
  detected_workforce: Record<string, unknown>;
  detected_schedule: Record<string, unknown>;

  /** Stage 4: BOQ items */
  boq_items: ExtractedBOQItem[];
  boq_confidence: string | null;

  /** Stage 5: Pricing */
  pricing_result: Record<string, unknown> | null;
  pricing_status: string | null;
  pricing_unavailable_reason: string | null;

  /** Stage 6: Final combined output */
  warnings: string[];
  extraction_method: string | null;
  pipeline_version: string | null;
}

/** Statuses that indicate a job has finished processing. */
export const TERMINAL_STATUSES: readonly JobStatusValue[] = [
  'completed',
  'partial_success',
  'failed',
];

/** Mapping from status to human-readable label. */
export const STATUS_LABELS: Record<JobStatusValue, string> = {
  queued: 'Queued',
  processing: 'Processing',
  extracting: 'Extracting',
  boq_analysis: 'BOQ Analysis',
  pricing: 'Pricing',
  completed: 'Completed',
  partial_success: 'Partial Success',
  failed: 'Failed',
};

/** Allowed file types for upload. */
export const ALLOWED_FILE_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
] as const;

export const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt'] as const;

export const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB