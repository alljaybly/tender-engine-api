interface ScreenshotCardProps {
  title: string;
  description: string;
  align?: 'left' | 'right';
}

export default function ScreenshotCard({ title, description, align = 'left' }: ScreenshotCardProps) {
  return (
    <div className={`flex flex-col ${align === 'right' ? 'md:flex-row-reverse' : 'md:flex-row'} items-center gap-8 md:gap-16`}>
      <div className="flex-1">
        <h3 className="text-xl font-semibold text-gray-900">{title}</h3>
        <p className="mt-3 text-base leading-7 text-gray-600">{description}</p>
      </div>
      <div className="flex-1 w-full">
        <div className="aspect-video rounded-lg border border-gray-200 bg-gray-100 flex items-center justify-center shadow-sm">
          <div className="text-center px-4">
            <svg className="mx-auto h-10 w-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
            </svg>
            <p className="mt-2 text-sm text-gray-400">Screenshot placeholder</p>
          </div>
        </div>
      </div>
    </div>
  );
}