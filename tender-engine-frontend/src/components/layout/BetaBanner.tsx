export default function BetaBanner() {
  return (
    <div className="w-full bg-gradient-to-r from-orange-500 via-red-500 to-orange-500">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-2.5">
        <div className="flex items-center justify-center gap-2 sm:gap-3">
          <span className="inline-flex items-center rounded-md bg-white/20 px-2 py-0.5 text-xs font-bold uppercase tracking-wider text-white">
            Early Beta
          </span>
          <p className="text-xs sm:text-sm font-medium text-white leading-tight">
            Free during beta — first request may take ~30s while backend wakes up.
          </p>
        </div>
      </div>
    </div>
  );
}
