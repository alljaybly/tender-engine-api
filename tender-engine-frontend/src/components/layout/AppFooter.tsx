import { Link } from 'react-router-dom';
import { Mail } from 'lucide-react';

export default function AppFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-slate-800 bg-slate-950">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="grid gap-8 md:grid-cols-[1.2fr_1fr_1fr] md:items-start">
          <div>
            <div className="flex items-center gap-3">
              <img src="/images/logo.png" alt="Tender Engine" className="h-10 w-10 rounded-md object-contain" />
              <div>
                <p className="text-sm font-bold text-white">Tender Engine</p>
                <p className="text-xs font-medium text-slate-400">AI tender extraction for Africa</p>
              </div>
            </div>
            <p className="mt-4 max-w-md text-sm leading-6 text-slate-400">
              AI-generated tender insights with visible confidence scoring, warnings, and transparent processing results.
            </p>
          </div>

          <div>
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-300">Product</h2>
            <div className="mt-4 grid gap-3 text-sm">
              <Link to="/demo" className="text-slate-400 transition hover:text-white">Live Demo</Link>
              <a href="/#contractors" className="text-slate-400 transition hover:text-white">For Contractors</a>
              <Link to="/for-procurement" className="text-slate-400 transition hover:text-white">For Procurement Offices</Link>
              <a href="/#pricing" className="text-slate-400 transition hover:text-white">Pricing</a>
            </div>
          </div>

          <div>
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-300">Company</h2>
            <div className="mt-4 grid gap-3 text-sm">
              <Link to="/terms" className="text-slate-400 transition hover:text-white">Terms</Link>
              <Link to="/privacy" className="text-slate-400 transition hover:text-white">Privacy</Link>
              <a href="mailto:tenderengine@zohomail.com" className="inline-flex items-center gap-2 text-slate-400 transition hover:text-white">
                <Mail className="h-4 w-4" />
                tenderengine@zohomail.com
              </a>
            </div>
          </div>
        </div>

        <div className="mt-8 flex flex-col gap-3 border-t border-slate-800 pt-6 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <p>&copy; {currentYear >= 2026 ? currentYear : 2026} Tender Engine AI. All rights reserved.</p>
          <p>Designed for South African contractors and procurement professionals.</p>
        </div>
      </div>
    </footer>
  );
}
