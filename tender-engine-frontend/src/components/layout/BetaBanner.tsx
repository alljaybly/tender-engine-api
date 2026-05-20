export default function BetaBanner() {
  return (
    <div className="w-full bg-amber-50 border-b border-amber-200">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-3 sm:py-4">
        <div className="flex items-center justify-center gap-3 rounded-lg bg-amber-100/80 px-4 py-3 sm:px-6 sm:py-4">
          <svg
            className="h-5 w-5 sm:h-6 sm:w-6 flex-shrink-0 text-amber-700 animate-pulse"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
            />
          </svg>
          <p className="text-sm sm:text-base font-bold text-amber-900 leading-tight">
            First request may take ~30+ seconds while backend wakes up (free beta infrastructure).
          </p>
        </div>
      </div>
    </div>
  );
}