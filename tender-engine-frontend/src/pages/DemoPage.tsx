import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { demoResult, DEMO_LABEL } from '../demo/demoResult';
import AppFooter from '../components/layout/AppFooter';

type ViewMode = 'executive' | 'technical';

function formatCurrency(amount: number, currency = 'ZAR'): string {
  return new Intl.NumberFormat('en-ZA', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

export default function DemoPage() {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<ViewMode>('executive');

  const result = demoResult;
  const scores = result.confidence_scores;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Demo Banner */}
      <div className="bg-amber-50 border-b border-amber-200">
        <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center rounded-md bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
                INTERACTIVE PRODUCT DEMONSTRATION
              </span>
              <p className="text-sm text-amber-700">{DEMO_LABEL}</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => navigate('/register')}
                className="rounded-md bg-blue-600 px-4 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-500 transition-colors"
              >
                Create Free Account
              </button>
              <button
                onClick={() => navigate('/login')}
                className="rounded-md border border-gray-300 bg-white px-4 py-1.5 text-xs font-semibold text-gray-700 shadow-sm hover:bg-gray-50 transition-colors"
              >
                Login
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Processed Tender Result</h1>
          <p className="mt-1 text-sm text-gray-500">
            File: {result.filename} &middot; Status: {result.status}
          </p>
        </div>

        {/* View Toggle */}
        <div className="mb-6 flex items-center gap-4">
          <div className="inline-flex rounded-md shadow-sm" role="group">
            <button
              onClick={() => setViewMode('executive')}
              className={`px-4 py-2 text-sm font-medium rounded-l-md border ${
                viewMode === 'executive'
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}
            >
              Executive Summary
            </button>
            <button
              onClick={() => setViewMode('technical')}
              className={`px-4 py-2 text-sm font-medium rounded-r-md border-t border-b border-r ${
                viewMode === 'technical'
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}
            >
              Technical Details
            </button>
          </div>

          {/* Export buttons (disabled in demo) */}
          <div className="flex gap-2">
            <button
              disabled
              className="rounded-md border border-gray-300 bg-gray-100 px-3 py-2 text-xs font-medium text-gray-400 cursor-not-allowed"
              title="Available with registered account"
            >
              Export PDF
            </button>
            <button
              disabled
              className="rounded-md border border-gray-300 bg-gray-100 px-3 py-2 text-xs font-medium text-gray-400 cursor-not-allowed"
              title="Available with registered account"
            >
              Export Excel
            </button>
          </div>
          <span className="text-xs text-gray-400 italic">Sign in to enable exports</span>
        </div>

        {viewMode === 'executive' ? (
          <ExecutiveView result={result} scores={scores} />
        ) : (
          <TechnicalView result={result} />
        )}
      </main>
      <AppFooter />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Executive Summary View                                             */
/* ------------------------------------------------------------------ */
function ExecutiveView({
  result,
  scores,
}: {
  result: typeof demoResult;
  scores: NonNullable<(typeof demoResult)['confidence_scores']>;
}) {
  return (
    <div className="space-y-6">
      {/* Executive Summary Card */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">Executive Summary</h2>
        <p className="mt-3 text-sm leading-7 text-gray-700 whitespace-pre-line">
          {result.executive_summary}
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Total Estimated Amount"
          value={formatCurrency(result.pricing_result?.total_estimated_amount ?? 0)}
          subtext="incl. contingency & fees"
        />
        <MetricCard
          label="Sector"
          value={result.detected_sector ?? 'N/A'}
          subtext={`Duration: ${result.detected_duration_months} months`}
        />
        <MetricCard
          label="BOQ Items"
          value={`${result.boq_items.length}`}
          subtext={`Confidence: ${result.boq_confidence}`}
        />
        <MetricCard
          label="Workforce"
          value={`${result.detected_workforce?.total_personnel ?? 0}`}
          subtext="Total personnel"
        />
      </div>

      {/* Confidence Scores */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Confidence Scores</h2>
        <p className="text-sm text-gray-500 mb-4">
          Transparency is built in. Each extraction stage reports its confidence level so you know exactly how reliable the results are.
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <ConfidenceBar label="Overall" value={scores.overall} />
          <ConfidenceBar label="BOQ Extraction" value={scores.boq_extraction} />
          <ConfidenceBar label="Workforce" value={scores.workforce} />
          <ConfidenceBar label="Sector Detection" value={scores.sector} />
          <ConfidenceBar label="Pricing" value={scores.pricing} />
        </div>
      </div>

      {/* Warnings */}
      {result.warnings.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
          <div className="flex items-start gap-2">
            <span className="text-amber-500 text-lg mt-0.5">⚠️</span>
            <div>
              <h2 className="text-sm font-semibold text-amber-800">Warnings</h2>
              <p className="text-xs text-amber-600 mt-0.5">
                Partial-success transparency — these items may need human review.
              </p>
              <ul className="mt-2 space-y-1">
                {result.warnings.map((w, i) => (
                  <li key={i} className="text-sm text-amber-700 flex items-start gap-2">
                    <span className="mt-1 block h-1.5 w-1.5 rounded-full bg-amber-400 flex-shrink-0" />
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Failed Stages */}
      {result.failed_stages.length > 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 shadow-sm">
          <div className="flex items-start gap-2">
            <span className="text-red-500 text-lg mt-0.5">✕</span>
            <div>
              <h2 className="text-sm font-semibold text-red-800">Failed Stages</h2>
              <p className="text-xs text-red-600 mt-0.5">
                Not all stages completed successfully. These are clearly visible — no hidden failures.
              </p>
              <ul className="mt-2 space-y-1">
                {result.failed_stages.map((s, i) => (
                  <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                    <span className="mt-1 block h-1.5 w-1.5 rounded-full bg-red-400 flex-shrink-0" />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Technical Details View                                             */
/* ------------------------------------------------------------------ */
function TechnicalView({ result }: { result: typeof demoResult }) {
  return (
    <div className="space-y-6">
      {/* BOQ Items Table */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Bill of Quantities</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Item</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Description</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Qty</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Unit</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Rate</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {result.boq_items.map((item, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-500">{item.item_no}</td>
                  <td className="px-4 py-3 text-gray-900">{item.description}</td>
                  <td className="px-4 py-3 text-right text-gray-900">{item.quantity?.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-gray-500">{item.unit}</td>
                  <td className="px-4 py-3 text-right text-gray-900">{formatCurrency(item.rate ?? 0)}</td>
                  <td className="px-4 py-3 text-right font-medium text-gray-900">{formatCurrency(item.amount ?? 0)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50 font-medium">
              <tr>
                <td colSpan={5} className="px-4 py-3 text-right text-gray-700">Total BOQ Amount</td>
                <td className="px-4 py-3 text-right text-gray-900">
                  {formatCurrency(result.pricing_result?.total_boq_amount ?? 0)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Pricing Breakdown */}
      {result.pricing_result && (
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Pricing Breakdown</h2>
          <dl className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
            <PricingRow label="Total BOQ Amount" value={formatCurrency(result.pricing_result.total_boq_amount)} />
            <PricingRow label="Contingency (10%)" value={formatCurrency(result.pricing_result.contingency_10_percent)} />
            <PricingRow label="Escalation (8%)" value={formatCurrency(result.pricing_result.escalation_8_percent)} />
            <PricingRow label="Professional Fees (5%)" value={formatCurrency(result.pricing_result.professional_fees)} />
            <PricingRow label="Total Estimated Amount" value={formatCurrency(result.pricing_result.total_estimated_amount)} bold />
          </dl>
        </div>
      )}

      {/* Workforce */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Workforce Requirements</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {result.detected_workforce &&
            Object.entries(result.detected_workforce)
              .filter(([key]) => key !== 'total_personnel')
              .map(([category, info]) => {
                const data = info as { count: number; source: string };
                return (
                  <div key={category} className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                    <div className="text-sm font-medium text-gray-900">{category}</div>
                    <div className="mt-1 text-2xl font-bold text-gray-900">{data.count}</div>
                    <div className="text-xs text-gray-500 capitalize">Source: {data.source}</div>
                  </div>
                );
              })}
        </div>
      </div>

      {/* Schedule */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Project Schedule</h2>
        <p className="text-sm text-gray-500 mb-3">Start: {result.detected_schedule?.start_date}</p>
        <div className="space-y-2">
          {result.detected_schedule?.phases.map((phase, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="h-2 w-2 rounded-full bg-blue-500" />
              <span className="text-sm text-gray-700 flex-1">{phase.phase}</span>
              <span className="text-sm text-gray-500">{phase.duration}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Shared Sub-components                                             */
/* ------------------------------------------------------------------ */
function MetricCard({ label, value, subtext }: { label: string; value: string; subtext: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-xl font-bold text-gray-900 truncate">{value}</p>
      <p className="mt-1 text-xs text-gray-400">{subtext}</p>
    </div>
  );
}

function ConfidenceBar({ label, value }: { label: string; value: number }) {
  const color =
    value >= 0.9 ? 'bg-green-500' : value >= 0.7 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium text-gray-900">{formatPercent(value)}</span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-200">
        <div className={`h-2 rounded-full ${color}`} style={{ width: formatPercent(value) }} />
      </div>
    </div>
  );
}

function PricingRow({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex justify-between items-center py-1">
      <span className={`text-sm ${bold ? 'font-semibold text-gray-900' : 'text-gray-600'}`}>{label}</span>
      <span className={`text-sm ${bold ? 'font-bold text-gray-900' : 'text-gray-900'}`}>{value}</span>
    </div>
  );
}