import { ArrowRight, Play } from 'lucide-react';

interface HeroSectionProps {
  onTryDemo: () => void;
  onGetStarted: () => void;
}

export default function HeroSection({ onTryDemo, onGetStarted }: HeroSectionProps) {
  return (
    <section className="relative overflow-hidden bg-white">
      {/* Subtle gradient background */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#f0f0f0_1px,transparent_1px),linear-gradient(to_bottom,#f0f0f0_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-30" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-gradient-to-b from-blue-50/80 to-transparent rounded-full blur-3xl" />
      </div>

      <div className="mx-auto max-w-7xl px-6 py-24 sm:py-32 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-50 border border-blue-100 text-xs font-semibold text-blue-700 mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            AI-Powered Tender Intelligence
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl leading-tight">
            Transform Tender Documents Into{' '}
            <span className="text-blue-600">Pricing Intelligence</span>
          </h1>
          <p className="mt-6 text-lg leading-8 text-gray-600 max-w-2xl mx-auto">
            Automatically extract BOQs, workforce estimates, pricing insights,
            and executive reports from complex tender documents — with
            transparent confidence scoring.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <button
              onClick={onTryDemo}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-3.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 transition-all hover:shadow-md active:scale-[0.98]"
            >
              <Play className="h-4 w-4" />
              Try Demo
            </button>
            <button
              onClick={onGetStarted}
              className="inline-flex items-center gap-2 rounded-xl border border-gray-300 bg-white px-6 py-3.5 text-sm font-semibold text-gray-700 shadow-sm hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-400 transition-all hover:shadow-md active:scale-[0.98]"
            >
              Get Started
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}