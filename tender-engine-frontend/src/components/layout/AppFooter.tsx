/**
 * AppFooter — Reusable footer component for Tender Engine AI.
 *
 * Provides:
 * - Terms of Service link
 * - Privacy Policy link
 * - Copyright notice
 * - Honesty Architecture transparency statement
 *
 * Use this component on every major page for consistent legal UX.
 */
import { Link } from 'react-router-dom';

export default function AppFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-gray-900 border-t border-gray-800">
      <div className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
        {/* Main footer content */}
        <div className="flex flex-col items-center justify-between gap-6 sm:flex-row">
          {/* Brand */}
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded bg-blue-600 flex items-center justify-center">
              <span className="text-xs font-bold text-white">TE</span>
            </div>
            <span className="text-sm text-gray-400">Tender Engine</span>
          </div>

          {/* Legal links */}
          <div className="flex items-center gap-6">
            <Link
              to="/terms"
              className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              Terms of Service
            </Link>
            <Link
              to="/privacy"
              className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              Privacy Policy
            </Link>
          </div>

          {/* Copyright */}
          <p className="text-xs text-gray-500">
            &copy; {currentYear >= 2026 ? currentYear : 2026} Tender Engine AI. All rights reserved.
          </p>
        </div>

        {/* Transparency statement */}
        <div className="mt-6 border-t border-gray-800 pt-4 text-center">
          <p className="text-xs text-gray-600 max-w-2xl mx-auto">
            AI-generated insights with visible confidence scoring and transparent processing results.
            Designed for South African procurement professionals.
          </p>
        </div>
      </div>
    </footer>
  );
}