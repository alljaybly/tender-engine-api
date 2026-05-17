const steps = [
  {
    number: "01",
    title: "Upload Tender",
    description: "Upload your tender document in PDF, DOCX, or TXT format. The system supports both machine-readable and scanned documents.",
    icon: "📤",
  },
  {
    number: "02",
    title: "AI Extracts Structure",
    description: "Our pipeline automatically extracts BOQ items, workforce requirements, schedule data, locations, and sector information.",
    icon: "⚙️",
  },
  {
    number: "03",
    title: "Generate Pricing + Reports",
    description: "Get comprehensive pricing estimates, confidence-scored results, and executive-ready PDF reports — all from a single upload.",
    icon: "📊",
  },
];

export default function HowItWorks() {
  return (
    <section className="bg-white py-24">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            How It Works
          </h2>
          <p className="mt-4 text-lg leading-8 text-gray-600">
            Three simple steps from document to actionable intelligence.
          </p>
        </div>
        <div className="mx-auto mt-16 max-w-5xl">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
            {steps.map((step, index) => (
              <div key={step.title} className="relative flex flex-col items-center text-center">
                {/* Connector line between steps */}
                {index < steps.length - 1 && (
                  <div className="absolute left-[60%] top-12 hidden h-0.5 w-[80%] bg-gray-200 md:block" aria-hidden="true" />
                )}
                <div className="flex h-24 w-24 items-center justify-center rounded-full bg-blue-50 text-3xl">
                  {step.icon}
                </div>
                <div className="mt-4 text-sm font-medium text-blue-600">{step.number}</div>
                <h3 className="mt-2 text-lg font-semibold text-gray-900">{step.title}</h3>
                <p className="mt-2 text-sm leading-6 text-gray-600 max-w-xs">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}