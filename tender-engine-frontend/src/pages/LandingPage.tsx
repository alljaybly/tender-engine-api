import { useNavigate } from 'react-router-dom';
import HeroSection from '../components/landing/HeroSection';
import FeatureGrid from '../components/landing/FeatureGrid';
import HowItWorks from '../components/landing/HowItWorks';
import ScreenshotCard from '../components/landing/ScreenshotCard';
import CTASection from '../components/landing/CTASection';
import LeadCaptureForm from '../components/landing/LeadCaptureForm';
import AppFooter from '../components/layout/AppFooter';
import BetaBanner from '../components/layout/BetaBanner';

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white">
      {/* Beta Warning Banner */}
      <BetaBanner />

      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-50 border-b border-gray-100 bg-white/80 backdrop-blur-sm">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 lg:px-8">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <span className="text-sm font-bold text-white">TE</span>
            </div>
            <span className="text-lg font-semibold text-gray-900">Tender Engine</span>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/login')}
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              Login
            </button>
            <button
              onClick={() => navigate('/register')}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 transition-colors"
            >
              Register
            </button>
          </div>
        </nav>
      </header>

      {/* Hero */}
      <HeroSection
        onTryDemo={() => navigate('/demo')}
        onGetStarted={() => navigate('/register')}
      />

      {/* Screenshot / Preview Section */}
      <section className="bg-gray-50 py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <h2 className="text-center text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            See Tender Engine in Action
          </h2>
          <div className="mt-16 space-y-24">
            <ScreenshotCard
              title="Executive Dashboard"
              description="View a clear, confidence-scored breakdown of every tender extraction. See completed stages, warnings, and failed items at a glance."
              imageSrc="/images/executive-dashboard.png"
            />
            <ScreenshotCard
              title="Detailed BOQ & Pricing"
              description="Extracted BOQ items with rates, amounts, and full pricing breakdown — all with transparent confidence scores for every data point."
              imageSrc="/images/boq-pricing-extract.png"
              align="right"
            />
          </div>
        </div>
      </section>

      {/* How It Works */}
      <HowItWorks />

      {/* Differentiator / Trust Section */}
      <section className="bg-gray-50 py-24">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            Transparency Is Built In
          </h2>
          <p className="mt-4 text-lg leading-8 text-gray-600">
            Unlike black-box automation systems, failed stages and uncertainty remain visible.
            Every extraction includes a confidence score so you know exactly how reliable the results are.
          </p>
          <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-3 text-left">
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="text-2xl mb-3">🔍</div>
              <h3 className="text-sm font-semibold text-gray-900">Honest Confidence Scoring</h3>
              <p className="mt-1 text-xs text-gray-600">Every stage reports its confidence — no inflated scores.</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="text-2xl mb-3">⚠️</div>
              <h3 className="text-sm font-semibold text-gray-900">Partial-Success Visibility</h3>
              <p className="mt-1 text-xs text-gray-600">Completed stages, warnings, and failures are all clearly shown.</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="text-2xl mb-3">🔄</div>
              <h3 className="text-sm font-semibold text-gray-900">Retry Architecture</h3>
              <p className="mt-1 text-xs text-gray-600">Retry only the stages that failed — not the entire document.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Grid */}
      <FeatureGrid />

      {/* CTA */}
      <CTASection
        onGetStarted={() => navigate('/register')}
        onTryDemo={() => navigate('/demo')}
      />

      {/* Lead Capture */}
      <LeadCaptureForm />

      {/* Footer */}
      <AppFooter />
    </div>
  );
}