/**
 * TenderHistory — Displays uploaded processing jobs with status badges.
 *
 * Persists history in frontend state during session.
 * Provides status badges with appropriate styling:
 *   - queued / processing → blue (informational)
 *   - completed → green (success)
 *   - partial_success → amber/yellow (WARNING, NOT success)
 *   - failed → red (error)
 */
import type { ProcessingJobStatus, JobStatusValue } from '../types/process';
import { STATUS_LABELS, TERMINAL_STATUSES } from '../types/process';

interface HistoryItem {
  jobId: string;
  filename: string;
  uploadedAt: string;
  status: ProcessingJobStatus;
}

interface TenderHistoryProps {
  /** List of job history items from the dashboard state. */
  items: HistoryItem[];
  /** Called when user clicks on a job to view its result. */
  onSelectJob: (jobId: string) => void;
  /** The currently selected job ID (if any). */
  selectedJobId: string | null;
}

function StatusBadge({ status }: { status: JobStatusValue }) {
  const label = STATUS_LABELS[status] || status;

  let bgColor: string;
  let textColor: string;
  let dotColor: string;

  switch (status) {
    case 'queued':
      bgColor = 'bg-blue-50';
      textColor = 'text-blue-700';
      dotColor = 'bg-blue-500';
      break;
    case 'processing':
    case 'extracting':
    case 'boq_analysis':
    case 'pricing':
      bgColor = 'bg-blue-50';
      textColor = 'text-blue-700';
      dotColor = 'bg-blue-500';
      break;
    case 'completed':
      bgColor = 'bg-green-50';
      textColor = 'text-green-700';
      dotColor = 'bg-green-500';
      break;
    case 'partial_success':
      // Use WARNING (amber) styling — NOT success styling
      bgColor = 'bg-amber-50';
      textColor = 'text-amber-700';
      dotColor = 'bg-amber-500';
      break;
    case 'failed':
      bgColor = 'bg-red-50';
      textColor = 'text-red-700';
      dotColor = 'bg-red-500';
      break;
    default:
      bgColor = 'bg-gray-50';
      textColor = 'text-gray-700';
      dotColor = 'bg-gray-500';
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${bgColor} ${textColor}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      {label}
    </span>
  );
}

export default function TenderHistory({
  items,
  onSelectJob,
  selectedJobId,
}: TenderHistoryProps) {
  if (items.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="px-6 py-5 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            Processing History
          </h2>
        </div>
        <div className="px-6 py-8 text-center">
          <svg
            className="mx-auto h-10 w-10 text-gray-300 mb-3"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12h6m-3-3v6m-7 4h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          </svg>
          <p className="text-sm text-gray-500">
            No processing jobs yet. Upload a tender document to get started.
          </p>
        </div>
      </div>
    );
  }

  // Sort by uploadedAt descending (most recent first)
  const sortedItems = [...items].sort(
    (a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime(),
  );

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="px-6 py-5 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">
          Processing History
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          {items.length} job{items.length !== 1 ? 's' : ''} uploaded this session
        </p>
      </div>

      <div className="divide-y divide-gray-100">
        {sortedItems.map((item) => {
          const isSelected = item.jobId === selectedJobId;
          const isTerminal = TERMINAL_STATUSES.includes(
            item.status.status as JobStatusValue,
          );

          return (
            <button
              key={item.jobId}
              onClick={() => onSelectJob(item.jobId)}
              className={`w-full text-left px-6 py-4 hover:bg-gray-50 transition-colors ${
                isSelected ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {item.filename}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(item.uploadedAt).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {item.status.progress && !isTerminal && (
                    <span className="text-xs text-gray-400 truncate max-w-[120px]">
                      {item.status.progress}
                    </span>
                  )}
                  <StatusBadge status={item.status.status as JobStatusValue} />
                </div>
              </div>

              {/* Progress indicator for non-terminal jobs */}
              {!isTerminal && (
                <div className="mt-2">
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div
                      className="bg-blue-500 h-1.5 rounded-full animate-pulse"
                      style={{ width: '60%' }}
                    />
                  </div>
                </div>
              )}

              {/* Error message for failed jobs */}
              {item.status.status === 'failed' && item.status.error_message && (
                <p className="mt-1 text-xs text-red-600 truncate">
                  {item.status.error_message}
                </p>
              )}

              {/* Warning indicator for partial_success */}
              {item.status.status === 'partial_success' && (
                <div className="mt-1 flex items-center gap-1">
                  <svg
                    className="h-3.5 w-3.5 text-amber-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                    />
                  </svg>
                  <span className="text-xs text-amber-600">
                    Processing completed with warnings
                  </span>
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export type { HistoryItem };