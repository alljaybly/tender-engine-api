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
      {/* Top Bar with Logo */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <img
                src="/images/logo.png"
                alt="Tender Engine"
                className="h-8 w-auto"
              />
              <div className="hidden sm:block">
                <span className="text-sm font-bold text-gray-900">
                  Tender Engine
                </span>
                <span className="ml-2 inline-flex items-center rounded-md bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
                  DEMO
                </span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate('/register')}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 transition-all hover:shadow-md active:scale-[0.98]"
              >
                Create Free Account
              </button>
              <button
                onClick={() => navigate('/login')}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 shadow-sm hover:bg-gray-50 transition-all"
              >
                Login
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Demo Notice Banner */}
      <div className="bg-gradient-to-r from-amber-50 to-yellow-50 border-b border-amber-200">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 text-amber-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
              <p className="text-sm text-amber-800">
                <span className="font-semibold">{DEMO_LABEL}</span> — This is a preview of what your processed tender results will look like.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Processed Tender Result</h1>
          <p className="mt-1 text-sm text-gray-500">
            File: {result.filename} &middot; Status: {result.status}
          </p>
        </div>

        {/* Controls Row */}
        <div className="mb-6 flex flex-wrap items-center gap-4">
          <div className="inline-flex rounded-lg shadow-sm border border-gray-200 overflow-hidden" role="group">
            <button
              onClick={() => setViewMode('executive')}
              className={`px-5 py-2.5 text-sm font-semibold transition-all ${
                viewMode === 'executive'
                  ? 'bg-blue-600 text-white shadow-inner'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              <svg className="inline h-4 w-4 mr-1.5 -mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
              </svg>
              Executive Summary
            </button>
            <button
              onClick={() => setViewMode('technical')}
              className={`px-5 py-2.5 text-sm font-semibold transition-all ${
                viewMode === 'technical'
                  ? 'bg-blue-600 text-white shadow-inner'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              <svg className="inline h-4 w-4 mr-1.5 -mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
              </svg>
              Technical Details
            </button>
          </div>

          <div className="flex gap-2">
            <button
              disabled
              className="rounded-lg border border-gray-200 bg-gray-100 px-3.5 py-2 text-xs font-medium text-gray-400 cursor-not-allowed"
              title="Available with registered account"
            >
              Export PDF
            </button>
            <button
              disabled
              className="rounded-lg border border-gray-200 bg-gray-100 px-3.5 py-2 text-xs font-medium text-gray-400 cursor-not-allowed"
              title="Available with registered account"
            >
              Export Excel
            </button>
          </div>
          <span className="text-xs text-gray-400 italic flex items-center gap-1">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
            </svg>
            Sign in to enable exports
          </span>
        </div>

        {viewMode === 'executive' ? (
          <ExecutiveView result={result} scores={scores} />
        ) : (
          <TechnicalView result={result} />
        )}

        {/* ── Bottom CTA ─────────────────────────────────────────── */}
        <div className="mt-12 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-700 p-8 sm:p-10 shadow-xl text-center">
          <div className="mx-auto max-w-2xl">
            <h2 className="text-2xl sm:text-3xl font-bold text-white">
              Ready to Process Your Own Tenders?
            </h2>
            <p className="mt-3 text-blue-100 text-sm sm:text-base leading-relaxed">
              Upload your tender documents and get BOQ extraction, pricing intelligence, workforce estimates, and transparent confidence scoring — just like this demo.
            </p>
            <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-4">
              <button
                onClick={() => navigate('/register')}
                className="inline-flex items-center gap-2 rounded-xl bg-white px-8 py-3.5 text-sm font-bold text-blue-700 shadow-lg hover:bg-blue-50 transition-all hover:shadow-xl hover:-translate-y-0.5 active:scale-[0.98]"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
                </svg>
                Create Free Account
              </button>
              <button
                onClick={() => navigate('/')}
                className="inline-flex items-center gap-2 rounded-xl border border-blue-400 px-8 py-3.5 text-sm font-semibold text-white hover:bg-blue-500 transition-all hover:shadow-lg active:scale-[0.98]"
              >
                Learn More
              </button>
            </div>
            <p className="mt-4 text-xs text-blue-200">
              Free during beta. No credit card required.
            </p>
          </div>
        </div>
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
        <div className="flex items-center gap-2 mb-4">
          <div className="h-8 w-8 rounded-lg bg-blue-50 flex items-center justify-center">
            <svg className="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-900">Executive Summary</h2>
        </div>
        <p className="text-sm leading-7 text-gray-700 whitespace-pre-line">
          {result.executive_summary}
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Total Estimated Amount"
          value={formatCurrency(result.pricing_result?.total_estimated_amount ?? 0)}
          subtext="incl. contingency & fees"
          icon={
            <svg className="h-5 w-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          accent="green"
        />
        <MetricCard
          label="Sector"
          value={result.detected_sector ?? 'N/A'}
          subtext={`Duration: ${result.detected_duration_months} months`}
          icon={
            <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z" />
            </svg>
          }
          accent="blue"
        />
        <MetricCard
          label="BOQ Items"
          value={`${result.boq_items.length}`}
          subtext={`Confidence: ${result.boq_confidence}`}
          icon={
            <svg className="h-5 w-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
            </svg>
          }
          accent="purple"
        />
        <MetricCard
          label="Workforce"
          value={`${result.detected_workforce?.total_personnel ?? 0}`}
          subtext="Total personnel"
          icon={
            <svg className="h-5 w-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
            </svg>
          }
          accent="amber"
        />
      </div>

      {/* Confidence Scores — more prominent */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-1">
          <div className="h-8 w-8 rounded-lg bg-emerald-50 flex items-center justify-center">
            <svg className="h-4 w-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-900">Confidence Scores</h2>
        </div>
        <p className="text-sm text-gray-500 mb-5 ml-10">
          Transparency is built in. Each extraction stage reports its confidence level — no inflated scores.
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <ConfidenceCard label="Overall" value={scores.overall} description="Aggregate reliability" />
          <ConfidenceCard label="BOQ Extraction" value={scores.boq_extraction} description="Item extraction accuracy" />
          <ConfidenceCard label="Workforce" value={scores.workforce} description="Personnel estimates" />
          <ConfidenceCard label="Sector Detection" value={scores.sector} description="Industry classification" />
          <ConfidenceCard label="Pricing" value={scores.pricing} description="Cost estimation" />
        </div>
      </div>

      {/* Warnings — more prominent */}
      {result.warnings.length > 0 && (
        <div className="rounded-xl border-2 border-amber-200 bg-amber-50 p-6 shadow-md">
          <div className="flex items-start gap-3">
            <div className="h-10 w-10 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
              <svg className="h-5 w-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
            </div>
            <div className="flex-1">
              <h2 className="text-base font-bold text-amber-900">Warnings — May Need Human Review</h2>
              <p className="text-sm text-amber-700 mt-0.5">
                Partial-success transparency. These items were extracted but have lower confidence.
              </p>
              <ul className="mt-3 space-y-2">
                {result.warnings.map((w, i) => (
                  <li key={i} className="text-sm text-amber-800 flex items-start gap-2.5 bg-amber-100/70 rounded-lg px-3.5 py-2.5">
                    <svg className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                    </svg>
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
        <div className="rounded-xl border-2 border-red-200 bg-red-50 p-6 shadow-md">
          <div className="flex items-start gap-3">
            <div className="h-10 w-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
              <svg className="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <div>
              <h2 className="text-base font-bold text-red-900">Failed Stages</h2>
              <p className="text-sm text-red-700 mt-0.5">
                Not all stages completed. These are clearly visible — no hidden failures.
              </p>
              <ul className="mt-3 space-y-2">
                {result.failed_stages.map((s, i) => (
                  <li key={i} className="text-sm text-red-800 flex items-start gap-2.5 bg-red-100/70 rounded-lg px-3.5 py-2.5">
                    <svg className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* All Good — no warnings */}
      {result.warnings.length === 0 && result.failed_stages.length === 0 && (
        <div className="rounded-xl border-2 border-emerald-200 bg-emerald-50 p-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-emerald-100 flex items-center justify-center">
              <svg className="h-5 w-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-emerald-800">All stages completed with no warnings.</p>
              <p className="text-xs text-emerald-600">All extractions passed confidence thresholds.</p>
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
        <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-purple-50 flex items-center justify-center">
              <svg className="h-4 w-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Bill of Quantities</h2>
            <span className="ml-auto text-xs text-gray-400">{result.boq_items.length} items</span>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-500 text-xs uppercase tracking-wider">Item</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-500 text-xs uppercase tracking-wider">Description</th>
                <th className="px-4 py-3 text-right font-semibold text-gray-500 text-xs uppercase tracking-wider">Qty</th>
                <th className="px-4 py-3 text-right font-semibold text-gray-500 text-xs uppercase tracking-wider">Unit</th>
                <th className="px-4 py-3 text-right font-semibold text-gray-500 text-xs uppercase tracking-wider">Rate</th>
                <th className="px-4 py-3 text-right font-semibold text-gray-500 text-xs uppercase tracking-wider">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {result.boq_items.map((item, i) => (
                <tr key={i} className="hover:bg-blue-50/50 transition-colors">
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{item.item_no}</td>
                  <td className="px-4 py-3 text-gray-900 max-w-xs truncate">{item.description}</td>
                  <td className="px-4 py-3 text-right text-gray-900 tabular-nums">{item.quantity?.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-gray-500">{item.unit}</td>
                  <td className="px-4 py-3 text-right text-gray-900 tabular-nums font-medium">{formatCurrency(item.rate ?? 0)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-gray-900 tabular-nums">{formatCurrency(item.amount ?? 0)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50">
              <tr>
                <td colSpan={5} className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Total BOQ Amount</td>
                <td className="px-4 py-3 text-right text-sm font-bold text-gray-900 tabular-nums">
                  {formatCurrency(result.pricing_result?.total_boq_amount ?? 0)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Pricing Breakdown — clearer visual */}
      {result.pricing_result && (
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-5">
            <div className="h-8 w-8 rounded-lg bg-green-50 flex items-center justify-center">
              <svg className="h-4 w-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Pricing Breakdown</h2>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 space-y-1">
            <div className="flex justify-between items-center py-2">
              <span className="text-sm text-gray-600">Total BOQ Amount</span>
              <span className="text-sm font-semibold text-gray-900 tabular-nums">{formatCurrency(result.pricing_result.total_boq_amount)}</span>
            </div>
            <div className="border-t border-gray-200" />
            <div className="flex justify-between items-center py-2">
              <span className="text-sm text-gray-600">+ Contingency (10%)</span>
              <span className="text-sm text-amber-600 tabular-nums">{formatCurrency(result.pricing_result.contingency_10_percent)}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-sm text-gray-600">+ Escalation (8%)</span>
              <span className="text-sm text-amber-600 tabular-nums">{formatCurrency(result.pricing_result.escalation_8_percent)}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-sm text-gray-600">+ Professional Fees (5%)</span>
              <span className="text-sm text-amber-600 tabular-nums">{formatCurrency(result.pricing_result.professional_fees)}</span>
            </div>
            <div className="border-t-2 border-gray-300 mt-2 pt-2">
              <div className="flex justify-between items-center py-1">
                <span className="text-sm font-bold text-gray-900">Total Estimated Amount</span>
                <span className="text-base font-bold text-green-700 tabular-nums">{formatCurrency(result.pricing_result.total_estimated_amount)}</span>
              </div>
            </div>
          </div>
          <p className="mt-3 text-xs text-gray-400">
            Pricing mode: {result.pricing_result.pricing_mode.replace(/_/g, ' ')} &middot; Markups applied: Yes
          </p>
        </div>
      )}

      {/* Workforce */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-5">
          <div className="h-8 w-8 rounded-lg bg-amber-50 flex items-center justify-center">
            <svg className="h-4 w-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-900">Workforce Requirements</h2>
          <span className="ml-auto text-xs text-gray-400">{result.detected_workforce?.total_personnel} total</span>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {result.detected_workforce &&
            Object.entries(result.detected_workforce)
              .filter(([key]) => key !== 'total_personnel')
              .map(([category, info]) => {
                const data = info as { count: number; source: string };
                return (
                  <div key={category} className="rounded-lg border border-gray-100 bg-gray-50 p-4 hover:bg-gray-100 transition-colors">
                    <div className="text-sm font-medium text-gray-900">{category}</div>
                    <div className="mt-1 text-2xl font-bold text-gray-900 tabular-nums">{data.count}</div>
                    <div className="mt-1 flex items-center gap-1">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        data.source === 'extracted' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                      }`}>
                        {data.source}
                      </span>
                    </div>
                  </div>
                );
              })}
        </div>
      </div>

      {/* Schedule */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-5">
          <div className="h-8 w-8 rounded-lg bg-blue-50 flex items-center justify-center">
            <svg className="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-900">Project Schedule</h2>
          <span className="ml-auto text-xs text-gray-400">Start: {result.detected_schedule?.start_date}</span>
        </div>
        <div className="space-y-3">
          {result.detected_schedule?.phases.map((phase, i) => {
            const colors = [
              'bg-blue-500 ring-blue-200',
              'bg-indigo-500 ring-indigo-200',
              'bg-violet-500 ring-violet-200',
              'bg-purple-500 ring-purple-200',
            ];
            return (
              <div key={i} className="flex items-center gap-4 bg-gray-50 rounded-lg px-4 py-3">
                <div className={`h-3 w-3 rounded-full ${colors[i % colors.length]} ring-4 flex-shrink-0`} />
                <span className="text-sm text-gray-700 flex-1 font-medium">{phase.phase}</span>
                <span className="text-sm text-gray-500 font-medium tabular-nums">{phase.duration}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Shared Sub-components                                             */
/* ------------------------------------------------------------------ */
function MetricCard({ label, value, subtext, icon, accent }: { label: string; value: string; subtext: string; icon: React.ReactNode; accent: string }) {
  const borderColors: Record<string, string> = {
    green: 'border-l-green-500',
    blue: 'border-l-blue-500',
    purple: 'border-l-purple-500',
    amber: 'border-l-amber-500',
  };

  return (
    <div className={`rounded-xl border border-gray-200 bg-white p-5 shadow-sm border-l-4 ${borderColors[accent] || 'border-l-gray-500'} hover:shadow-md transition-shadow`}>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{label}</p>
        {icon}
      </div>
      <p className="text-xl font-bold text-gray-900 truncate tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-gray-400">{subtext}</p>
    </div>
  );
}

function ConfidenceCard({ label, value, description }: { label: string; value: number; description: string }) {
  const color =
    value >= 0.9 ? 'bg-green-500' : value >= 0.7 ? 'bg-amber-500' : 'bg-red-500';
  const bgColor =
    value >= 0.9 ? 'bg-green-50 border-green-200' : value >= 0.7 ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200';
  const textColor =
    value >= 0.9 ? 'text-green-700' : value >= 0.7 ? 'text-amber-700' : 'text-red-700';

  return (
    <div className={`rounded-lg border ${bgColor} p-4`}>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm font-semibold text-gray-800">{label}</span>
        <span className={`text-sm font-bold ${textColor}`}>{formatPercent(value)}</span>
      </div>
      <div className="h-2.5 w-full rounded-full bg-gray-200/70 mb-1.5">
        <div className={`h-2.5 rounded-full ${color} transition-all`} style={{ width: formatPercent(value) }} />
      </div>
      <p className="text-xs text-gray-500">{description}</p>
    </div>
  );
}