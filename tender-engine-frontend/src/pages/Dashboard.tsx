/**
 * Dashboard — Tender processing control center.
 *
 * Sections:
 *   1. Upload section (UploadCard)
 *   2. Processing history section (TenderHistory)
 *   3. Result viewer section (ResultViewer via polling)
 *   4. Status indicators
 *   5. Warning/error display
 *
 * Layout:
 *   - Responsive grid
 *   - Clean professional SaaS style
 *   - No flashy gradients
 *   - Clarity over decoration
 */
import { useState, useCallback, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import UploadCard from '../components/UploadCard';
import TenderHistory from '../components/TenderHistory';
import ResultViewer from '../components/ResultViewer';
import { useProcessingStatus } from '../hooks/useProcessingStatus';
import { getJobResult } from '../services/process';
import type {
  ProcessUploadResponse,
  ProcessingJobStatus,
  ProcessingResult,
  JobStatusValue,
} from '../types/process';
import { TERMINAL_STATUSES } from '../types/process';

interface HistoryItem {
  jobId: string;
  filename: string;
  uploadedAt: string;
  status: ProcessingJobStatus;
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // ── State ──────────────────────────────────────────────────────────
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [result, setResult] = useState<ProcessingResult | null>(null);
  const [resultLoading, setResultLoading] = useState(false);
  const [resultError, setResultError] = useState<string | null>(null);

  // ── Polling for the active job ─────────────────────────────────────
  const {
    status: activeStatus,
    error: statusError,
    isTerminal,
  } = useProcessingStatus({
    jobId: activeJobId,
    autoStart: activeJobId !== null,
  });

  // Update history when the active job's status changes
  useEffect(() => {
    if (activeJobId && activeStatus) {
      setHistory((prev) =>
        prev.map((item) =>
          item.jobId === activeJobId
            ? { ...item, status: activeStatus }
            : item,
        ),
      );
    }
  }, [activeJobId, activeStatus]);

  // When job reaches terminal state, fetch the result
  useEffect(() => {
    if (activeJobId && isTerminal) {
      setResultLoading(true);
      setResultError(null);

      getJobResult(activeJobId)
        .then((res) => {
          setResult(res);
          setSelectedJobId(activeJobId);
        })
        .catch((err: unknown) => {
          const message =
            err instanceof Error ? err.message : 'Failed to fetch result';
          setResultError(message);
        })
        .finally(() => {
          setResultLoading(false);
        });
    }
  }, [activeJobId, isTerminal]);

  // ── Handlers ───────────────────────────────────────────────────────
  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  const handleUploadSuccess = useCallback(
    (response: ProcessUploadResponse) => {
      // Add to history
      const newItem: HistoryItem = {
        jobId: response.job_id,
        filename: response.filename,
        uploadedAt: new Date().toISOString(),
        status: {
          job_id: response.job_id,
          status: 'queued' as JobStatusValue,
          progress: null,
          created_at: null,
          updated_at: null,
          error_message: null,
        },
      };

      setHistory((prev) => [...prev, newItem]);

      // Set as active job (triggers polling)
      setActiveJobId(response.job_id);
      setSelectedJobId(response.job_id);
      setResult(null);
      setResultError(null);
    },
    [],
  );

  const handleSelectJob = useCallback(
    async (jobId: string) => {
      setSelectedJobId(jobId);
      setResultLoading(true);
      setResultError(null);

      // Check if we already have the status in history
      const existing = history.find((item) => item.jobId === jobId);
      const isTerminalExisting = existing
        ? TERMINAL_STATUSES.includes(
            existing.status.status as JobStatusValue,
          )
        : false;

      if (isTerminalExisting) {
        // Fetch result directly
        try {
          const res = await getJobResult(jobId);
          setResult(res);
        } catch (err: unknown) {
          const message =
            err instanceof Error ? err.message : 'Failed to fetch result';
          setResultError(message);
        } finally {
          setResultLoading(false);
        }
      } else {
        // Set as active job to trigger/continue polling
        setActiveJobId(jobId);
        setResult(null);
        setResultLoading(false);
      }
    },
    [history],
  );

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50">
      {/* ── Header ───────────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-gray-900">
                Tender Engine
              </h1>
              <span className="hidden sm:inline text-sm text-gray-400">
                Processing Dashboard
              </span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">{user?.email}</span>
              <button
                onClick={handleLogout}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ── Main Content ──────────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* ── Left Column: Upload + History ───────────────────── */}
          <div className="lg:col-span-1 space-y-6">
            {/* Upload Section */}
            <UploadCard onUploadSuccess={handleUploadSuccess} />

            {/* Currently processing indicator */}
            {activeJobId && !isTerminal && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
                <div className="flex items-center gap-2">
                  <svg
                    className="animate-spin h-4 w-4 text-blue-500"
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
                  <div className="text-sm text-blue-700">
                    <span className="font-medium">Processing:</span>{' '}
                    {activeStatus?.progress || 'Waiting...'}
                  </div>
                </div>
              </div>
            )}

            {/* Status polling error */}
            {statusError && (
              <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                <div className="flex items-start gap-2">
                  <svg
                    className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5"
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
                  <p className="text-sm text-red-700">{statusError}</p>
                </div>
              </div>
            )}

            {/* Processing History */}
            <TenderHistory
              items={history}
              onSelectJob={handleSelectJob}
              selectedJobId={selectedJobId}
            />
          </div>

          {/* ── Right Column: Result Viewer ──────────────────────── */}
          <div className="lg:col-span-2">
            {selectedJobId && resultLoading && (
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                <div className="px-6 py-5 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">
                    Loading Result
                  </h2>
                </div>
                <div className="px-6 py-12 text-center">
                  <svg
                    className="animate-spin mx-auto h-8 w-8 text-blue-500 mb-3"
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
                  <p className="text-sm text-gray-500">
                    Retrieving processing result...
                  </p>
                </div>
              </div>
            )}

            {selectedJobId && resultError && (
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                <div className="px-6 py-5 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">
                    Error
                  </h2>
                </div>
                <div className="px-6 py-8">
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
                      <div>
                        <p className="text-sm font-medium text-red-800">
                          Failed to Load Result
                        </p>
                        <p className="text-sm text-red-600 mt-1">
                          {resultError}
                        </p>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleSelectJob(selectedJobId)}
                    className="mt-4 px-4 py-2 text-sm font-medium text-blue-700 bg-blue-50 rounded-md hover:bg-blue-100 transition-colors"
                  >
                    Retry
                  </button>
                </div>
              </div>
            )}

            {selectedJobId && result && !resultLoading && !resultError && (
              <ResultViewer result={result} />
            )}

            {selectedJobId &&
              !result &&
              !resultLoading &&
              !resultError &&
              activeStatus &&
              !isTerminal && (
                <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                  <div className="px-6 py-5 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-900">
                      Processing
                    </h2>
                  </div>
                  <div className="px-6 py-12 text-center">
                    <svg
                      className="animate-spin mx-auto h-10 w-10 text-blue-500 mb-4"
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
                    <p className="text-sm font-medium text-gray-700 mb-1">
                      Your document is being processed
                    </p>
                    <p className="text-sm text-gray-500">
                      Status:{' '}
                      <span className="font-medium text-blue-600">
                        {activeStatus.progress || 'Queued'}
                      </span>
                    </p>
                    <p className="text-xs text-gray-400 mt-2">
                      This page will update automatically once processing
                      completes.
                    </p>
                  </div>
                </div>
              )}

            {/* Empty state when no job is selected */}
            {!selectedJobId && !activeJobId && (
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                <div className="px-6 py-12 text-center">
                  <svg
                    className="mx-auto h-16 w-16 text-gray-300 mb-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={1}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                    />
                  </svg>
                  <h2 className="text-xl font-semibold text-gray-700 mb-2">
                    Tender Processing Dashboard
                  </h2>
                  <p className="text-gray-500 max-w-md mx-auto mb-6">
                    Upload a tender document to get started. Once processed,
                    you'll see extracted data including sector, duration,
                    locations, BOQ items, and pricing.
                  </p>
                  <div className="flex justify-center gap-8 text-sm text-gray-400">
                    <div className="text-center">
                      <p className="font-medium text-gray-600">Step 1</p>
                      <p>Upload document</p>
                    </div>
                    <div className="text-center">
                      <p className="font-medium text-gray-600">Step 2</p>
                      <p>Auto-processing</p>
                    </div>
                    <div className="text-center">
                      <p className="font-medium text-gray-600">Step 3</p>
                      <p>View results</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}