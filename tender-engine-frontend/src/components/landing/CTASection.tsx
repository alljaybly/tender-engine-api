interface CTASectionProps {
  onGetStarted: () => void;
  onTryDemo: () => void;
}

export default function CTASection({ onGetStarted, onTryDemo }: CTASectionProps) {
  return (
    <section className="bg-white py-24">
      <div className="mx-auto max-w-4xl px-6 text-center">
        <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
          Start Processing Tenders Smarter
        </h2>
        <p className="mt-4 text-lg leading-8 text-gray-600 max-w-2xl mx-auto">
          Join early adopters who are already using Tender Engine to transform their tender workflows.
        </p>
        <div className="mt-10 flex items-center justify-center gap-x-6">
          <button
            onClick={onGetStarted}
            className="rounded-md bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 transition-colors"
          >
            Create Free Account
          </button>
          <button
            onClick={onTryDemo}
            className="rounded-md border border-gray-300 px-6 py-3 text-sm font-semibold text-gray-700 shadow-sm hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-400 transition-colors"
          >
            Try Interactive Demo
          </button>
        </div>
      </div>
    </section>
  );
}