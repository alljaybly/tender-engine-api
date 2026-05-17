/**
 * ResultViewer — Displays real backend processing results.
 *
 * Shows all fields from ProcessingResult:
 *   - filename, detected_sector, detected_duration_months
 *   - detected_locations, workforce data, schedule data
 *   - BOQ items, pricing result, pricing status
 *   - warnings, failed_stages, completed_stages
 *
 * Visual distinctions:
 *   - completed → green success indicators
 *   - partial_success → amber warning panels (NOT success)
 *   - failed → red error panels
 *
 * Actions:
 *   - Download Excel Export button (for completed or partial_success jobs)
 *   - Retry buttons for recoverable failed stages
 */
import { useState } from 'react';
import { downloadExcelExport, downloadPdfReport, retryJob } from '../services/process';
import type { ProcessingResult, ExtractedBOQItem } from '../types/process';

interface ResultViewerProps {
  result: ProcessingResult;
}

function WarningPanel({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null;

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-md px-4 py-3">
      <div className="flex items-start gap-2">
        <svg
          className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5"
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
        <div className="flex-1">
          <p className="text-sm font-medium text-amber-800">Warnings</p>
          <ul className="mt-1 text-sm text-amber-700 list-disc list-inside space-y-1">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function FailedStagesPanel({ failedStages }: { failedStages: string[] }) {
  if (failedStages.length === 0) return null;

  return (
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
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
        <div className="flex-1">
          <p className="text-sm font-medium text-red-800">Failed Stages</p>
          <p className="text-sm text-red-600 mt-1">
            The following processing stages failed and their results are
            unavailable:
          </p>
          <ul className="mt-1 text-sm text-red-700 list-disc list-inside space-y-1">
            {failedStages.map((stage, i) => (
              <li key={i}>{stage}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function StatusBanner({ result }: { result: ProcessingResult }) {
  switch (result.status) {
    case 'completed':
      return (
        <div className="bg-green-50 border border-green-200 rounded-md px-4 py-3">
          <div className="flex items-center gap-2">
            <svg
              className="h-5 w-5 text-green-500 flex-shrink-0"
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
            <p className="text-sm font-medium text-green-800">
              Processing completed successfully — all stages finished.
            </p>
          </div>
        </div>
      );
    case 'partial_success':
      return (
        <div className="bg-amber-50 border border-amber-200 rounded-md px-4 py-3">
          <div className="flex items-start gap-2">
            <svg
              className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5"
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
              <p className="text-sm font-medium text-amber-800">
                Partial Success — some stages completed, but others failed.
              </p>
              <p className="text-sm text-amber-600 mt-1">
                Successfully extracted data is displayed below. Unavailable
                sections are marked with failure reasons.
              </p>
            </div>
          </div>
        </div>
      );
    case 'failed':
      return (
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
                Processing Failed
              </p>
              {result.warnings.length > 0 && (
                <p className="text-sm text-red-600 mt-1">
                  {result.warnings[0]}
                </p>
              )}
            </div>
          </div>
        </div>
      );
  }
}

function SectionCard({
  title,
  children,
  empty = false,
  isEmpty = false,
}: {
  title: string;
  children: React.ReactNode;
  empty?: boolean;
  isEmpty?: boolean;
}) {
  if (isEmpty || empty) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="px-5 py-4 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
        </div>
        <div className="px-5 py-4">
          <p className="text-sm text-gray-400 italic">Not available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="px-5 py-4 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
      </div>
      <div className="px-5 py-4">{children}</div>
    </div>
  );
}

function MetadataCard({ metadata }: { metadata: Record<string, unknown> }) {
  const entries = Object.entries(metadata);
  if (entries.length === 0) return null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="px-5 py-4 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700">File Metadata</h3>
      </div>
      <div className="px-5 py-4">
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {entries.map(([key, value]) => (
            <div key={key}>
              <dt className="text-xs font-medium text-gray-500 capitalize">
                {key.replace(/_/g, ' ')}
              </dt>
              <dd className="mt-0.5 text-sm text-gray-900">
                {String(value)}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}

function BOQTable({ items }: { items: ExtractedBOQItem[] }) {
  if (items.length === 0) return null;

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-2 px-3 font-medium text-gray-500 text-xs uppercase">
              Item
            </th>
            <th className="text-left py-2 px-3 font-medium text-gray-500 text-xs uppercase">
              Description
            </th>
            <th className="text-right py-2 px-3 font-medium text-gray-500 text-xs uppercase">
              Qty
            </th>
            <th className="text-left py-2 px-3 font-medium text-gray-500 text-xs uppercase">
              Unit
            </th>
            <th className="text-right py-2 px-3 font-medium text-gray-500 text-xs uppercase">
              Rate
            </th>
            <th className="text-right py-2 px-3 font-medium text-gray-500 text-xs uppercase">
              Amount
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-2 px-3 text-gray-700">{item.item_no || '-'}</td>
              <td className="py-2 px-3 text-gray-900 max-w-xs truncate">
                {item.description}
              </td>
              <td className="py-2 px-3 text-right text-gray-700">
                {item.quantity != null ? item.quantity : '-'}
              </td>
              <td className="py-2 px-3 text-gray-700">{item.unit || '-'}</td>
              <td className="py-2 px-3 text-right text-gray-700">
                {item.rate != null
                  ? `R${item.rate.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                  : '-'}
              </td>
              <td className="py-2 px-3 text-right text-gray-900 font-medium">
                {item.amount != null
                  ? `R${item.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                  : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PricingSection({ result }: { result: ProcessingResult }) {
  const pricingUnavailable = result.pricing_status === 'failed' || !result.pricing_result;

  if (pricingUnavailable) {
    return (
      <SectionCard title="Pricing">
        <div className="bg-red-50 border border-red-200 rounded-md px-3 py-2">
          <p className="text-sm font-medium text-red-800">
            Pricing Unavailable
          </p>
          {result.pricing_unavailable_reason && (
            <p className="text-sm text-red-600 mt-1">
              {result.pricing_unavailable_reason}
            </p>
          )}
          {result.failed_stages.includes('pricing_calculation') && (
            <p className="text-sm text-red-600 mt-1">
              The pricing calculation stage failed during processing.
            </p>
          )}
        </div>
      </SectionCard>
    );
  }

  return (
    <SectionCard title="Pricing" empty={false}>
      {result.pricing_result && (
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {Object.entries(result.pricing_result).map(([key, value]) => (
            <div key={key}>
              <dt className="text-xs font-medium text-gray-500 capitalize">
                {key.replace(/_/g, ' ')}
              </dt>
              <dd className="mt-0.5 text-sm text-gray-900">
                {typeof value === 'number'
                  ? `R${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                  : String(value)}
              </dd>
            </div>
          ))}
        </dl>
      )}
      {result.pricing_status === 'completed' && (
        <div className="mt-2">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
            Pricing completed
          </span>
        </div>
      )}
    </SectionCard>
  );
}

export default function ResultViewer({ result }: ResultViewerProps) {
  const [exportingExcel, setExportingExcel] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleDownloadExcel = async () => {
    setExportingExcel(true);
    setExportError(null);
    try {
      await downloadExcelExport(result.job_id, `${result.filename ?? 'tender'}_export.xlsx`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to download export';
      setExportError(message);
    } finally {
      setExportingExcel(false);
    }
  };

  const handleDownloadPdf = async () => {
    setExportingPdf(true);
    setExportError(null);
    try {
      await downloadPdfReport(result.job_id, `${result.filename ?? 'tender'}_report.pdf`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to download PDF';
      setExportError(message);
    } finally {
      setExportingPdf(false);
    }
  };

  const canExport = result.status === 'completed' || result.status === 'partial_success';

  if (result.status === 'failed') {
    return (
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="px-6 py-5 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Result</h2>
        </div>
        <div className="px-6 py-5 space-y-4">
          <StatusBanner result={result} />
          {result.warnings.length > 0 && <WarningPanel warnings={result.warnings} />}
          {result.filename && (
            <p className="text-sm text-gray-500">
              File: <span className="font-medium text-gray-700">{result.filename}</span>
            </p>
          )}
        </div>
      </div>
    );
  }

  const hasBOQ = result.boq_items && result.boq_items.length > 0;
  const hasWorkforce =
    result.detected_workforce &&
    Object.keys(result.detected_workforce).length > 0;
  const hasSchedule =
    result.detected_schedule &&
    Object.keys(result.detected_schedule).length > 0;
  const hasMetadata =
    result.metadata && Object.keys(result.metadata).length > 0;

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="px-6 py-5 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Result</h2>
      </div>

      <div className="px-6 py-5 space-y-5">
        {/* Status banner */}
        <StatusBanner result={result} />

        {/* Warnings */}
        {result.warnings.length > 0 && (
          <WarningPanel warnings={result.warnings} />
        )}

        {/* Failed stages */}
        {result.failed_stages.length > 0 && (
          <FailedStagesPanel failedStages={result.failed_stages} />
        )}

        {/* Filename */}
        {result.filename && (
          <div className="text-sm text-gray-500">
            File: <span className="font-medium text-gray-700">{result.filename}</span>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex flex-wrap gap-3">
          {/* Download Excel Export */}
          {canExport && (
            <button
              onClick={handleDownloadExcel}
              disabled={exportingExcel}
              className="inline-flex items-center px-4 py-2 border border-gray-300
                text-sm font-medium rounded-md shadow-sm text-gray-700
                bg-white hover:bg-gray-50 focus:outline-none focus:ring-2
                focus:ring-offset-2 focus:ring-blue-500
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors"
            >
              {exportingExcel ? (
                <>
                  <svg
                    className="animate-spin -ml-1 mr-2 h-4 w-4 text-gray-500"
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
                  Generating...
                </>
              ) : (
                <>
                  <svg
                    className="-ml-1 mr-2 h-4 w-4 text-gray-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  Download Excel Export
                </>
              )}
            </button>
          )}

          {/* Download PDF Report */}
          {canExport && (
            <button
              onClick={handleDownloadPdf}
              disabled={exportingPdf}
              className="inline-flex items-center px-4 py-2 border border-gray-300
                text-sm font-medium rounded-md shadow-sm text-gray-700
                bg-white hover:bg-gray-50 focus:outline-none focus:ring-2
                focus:ring-offset-2 focus:ring-blue-500
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors"
            >
              {exportingPdf ? (
                <>
                  <svg
                    className="animate-spin -ml-1 mr-2 h-4 w-4 text-gray-500"
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
                  Generating...
                </>
              ) : (
                <>
                  <svg
                    className="-ml-1 mr-2 h-4 w-4 text-gray-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  Download PDF Report
                </>
              )}
            </button>
          )}
        </div>

        {/* Export error */}
        {exportError && (
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
                  Export Failed
                </p>
                <p className="text-sm text-red-600 mt-1">{exportError}</p>
              </div>
            </div>
          </div>
        )}

        {/* Stage tracking */}
        {result.completed_stages.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Processing Stages
            </h3>
            <div className="flex flex-wrap gap-2">
              {result.completed_stages.map((stage) => (
                <span
                  key={stage}
                  className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700"
                >
                  <svg
                    className="h-3 w-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M4.5 12.75l6 6 9-13.5"
                    />
                  </svg>
                  {stage.replace(/_/g, ' ')}
                </span>
              ))}
              {result.failed_stages.map((stage) => (
                <span
                  key={stage}
                  className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700"
                >
                  <svg
                    className="h-3 w-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                  {stage.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Metadata */}
        {hasMetadata && <MetadataCard metadata={result.metadata} />}

        {/* Extracted entities */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <SectionCard title="Sector" isEmpty={!result.detected_sector}>
            <p className="text-sm font-medium text-gray-900 capitalize">
              {result.detected_sector || 'Not detected'}
            </p>
          </SectionCard>

          <SectionCard
            title="Duration"
            isEmpty={result.detected_duration_months == null}
          >
            <p className="text-sm font-medium text-gray-900">
              {result.detected_duration_months != null
                ? `${result.detected_duration_months} months`
                : 'Not detected'}
            </p>
          </SectionCard>

          <SectionCard
            title="Locations"
            isEmpty={result.detected_locations.length === 0}
          >
            {result.detected_locations.length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {result.detected_locations.map((loc, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 capitalize"
                  >
                    {loc}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 italic">None detected</p>
            )}
          </SectionCard>

          <SectionCard title="Confidence" isEmpty={!result.boq_confidence}>
            <p className="text-sm font-medium text-gray-900 capitalize">
              {result.boq_confidence || 'Not available'}
            </p>
          </SectionCard>
        </div>

        {/* Workforce */}
        <SectionCard title="Workforce" isEmpty={!hasWorkforce}>
          {hasWorkforce ? (
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {Object.entries(result.detected_workforce).map(([key, value]) => (
                <div key={key}>
                  <dt className="text-xs font-medium text-gray-500 capitalize">
                    {key.replace(/_/g, ' ')}
                  </dt>
                  <dd className="mt-0.5 text-sm text-gray-900">
                    {String(value)}
                  </dd>
                </div>
              ))}
            </dl>
          ) : null}
        </SectionCard>

        {/* Schedule */}
        <SectionCard title="Schedule" isEmpty={!hasSchedule}>
          {hasSchedule ? (
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {Object.entries(result.detected_schedule).map(([key, value]) => (
                <div key={key}>
                  <dt className="text-xs font-medium text-gray-500 capitalize">
                    {key.replace(/_/g, ' ')}
                  </dt>
                  <dd className="mt-0.5 text-sm text-gray-900">
                    {String(value)}
                  </dd>
                </div>
              ))}
            </dl>
          ) : null}
        </SectionCard>

        {/* BOQ Items */}
        <SectionCard title="BOQ Items" empty={!hasBOQ}>
          {hasBOQ ? (
            <BOQTable items={result.boq_items} />
          ) : (
            <p className="text-sm text-gray-400 italic">Not available</p>
          )}
        </SectionCard>

        {/* Pricing */}
        {result.pricing_status !== 'failed' && result.pricing_result ? (
          <PricingSection result={result} />
        ) : null}

        {/* Pricing failure — show separately if partial_success */}
        {result.status === 'partial_success' &&
          (result.pricing_status === 'failed' || !result.pricing_result) && (
            <PricingSection result={result} />
          )}

        {/* Extraction info */}
        {(result.extraction_method || result.pipeline_version) && (
          <div className="text-xs text-gray-400 border-t border-gray-100 pt-3">
            {result.extraction_method && (
              <span className="mr-4">
                Method: {result.extraction_method}
              </span>
            )}
            {result.pipeline_version && (
              <span>Pipeline: {result.pipeline_version}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}