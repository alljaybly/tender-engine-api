interface FeatureCard {
  title: string;
  description: string;
  icon: string;
}

const features: FeatureCard[] = [
  {
    title: "BOQ Extraction",
    description: "Automatically extract Bills of Quantities with item numbers, descriptions, quantities, and rates from tender documents.",
    icon: "📋",
  },
  {
    title: "OCR Support",
    description: "Process scanned PDFs and images with built-in OCR for documents that lack machine-readable text.",
    icon: "🔍",
  },
  {
    title: "Workforce Estimation",
    description: "Extract workforce requirements, skill categories, and personnel counts from tender specifications.",
    icon: "👷",
  },
  {
    title: "Pricing Intelligence",
    description: "Generate accurate pricing estimates based on extracted BOQ items and market rate data.",
    icon: "💰",
  },
  {
    title: "Executive Reports",
    description: "Generate professional PDF reports with executive summaries, confidence scores, and key insights.",
    icon: "📄",
  },
  {
    title: "Excel Exports",
    description: "Export structured BOQ data and pricing to Excel for further analysis and reporting.",
    icon: "📊",
  },
  {
    title: "Retry Failed Stages",
    description: "Recover from partial processing by retrying only the stages that failed, not the entire document.",
    icon: "🔄",
  },
  {
    title: "Confidence Scoring",
    description: "Each extraction includes a confidence score so you know exactly how reliable the results are.",
    icon: "🎯",
  },
];

export default function FeatureGrid() {
  return (
    <section className="bg-gray-50 py-24">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            Everything You Need to Process Tenders
          </h2>
          <p className="mt-4 text-lg leading-8 text-gray-600">
            Unlike black-box automation systems, failed stages and uncertainty remain visible.
          </p>
        </div>
        <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="relative rounded-xl border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="text-2xl mb-4">{feature.icon}</div>
              <h3 className="text-base font-semibold text-gray-900">{feature.title}</h3>
              <p className="mt-2 text-sm leading-6 text-gray-600">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}