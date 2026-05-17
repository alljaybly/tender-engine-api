interface HeroSectionProps {
  onTryDemo: () => void;
  onGetStarted: () => void;
}

export default function HeroSection({ onTryDemo, onGetStarted }: HeroSectionProps) {
  return (
    <section className="relative overflow-hidden bg-white">
      {/* Subtle background pattern */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#f0f0f0_1px,transparent_1px),linear-gradient(to_bottom,#f0f0f0_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-30" />
      </div>

      <div className="mx-auto max-w-7xl px-6 py-24 sm:py-32 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl">
            Transform Tender Documents Into Pricing Intelligence
          </h1>
          <p className="mt-6 text-lg leading-8 text-gray-600 max-w-2xl mx-auto">
            Automatically extract BOQs, workforce estimates, pricing insights, and executive reports from complex tender documents.
          </p>
          <div className="mt-10 flex items-center justify-center gap-x-6">
            <button
              onClick={onTryDemo}
              className="rounded-md bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 transition-colors"
            >
              Try Demo
            </button>
            <button
              onClick={onGetStarted}
              className="rounded-md border border-gray-300 px-6 py-3 text-sm font-semibold text-gray-700 shadow-sm hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-400 transition-colors"
            >
              Get Started
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}