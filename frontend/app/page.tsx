import { ClaimDesk } from "@/components/claim-desk";

const STEPS = [
  { name: "Check the photo", text: "Sharpness is measured from the pixels. A blurred photo is turned away before any model sees it." },
  { name: "Read the document", text: "An LLM turns the image into typed data: who, when, each line item and its category." },
  { name: "Apply the policy", text: "Plain rules decide what is payable. Every rupee that is cut comes with its reason." },
];

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
      <header className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-wide text-zinc-500">Outpatient health insurance</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-zinc-950">Claim adjudicator</h1>
        <p className="mt-3 text-zinc-600">
          Give it medical bills and prescriptions and it decides the claim: approved, partly approved, rejected, or sent to a person.
          The model only reads. The decision is made by rules you can inspect.
        </p>
      </header>

      <ol className="mt-6 grid gap-4 sm:grid-cols-3">
        {STEPS.map((step, index) => (
          <li key={step.name} className="rounded-xl bg-zinc-100 p-4">
            <p className="text-sm font-semibold text-zinc-950">
              {index + 1}. {step.name}
            </p>
            <p className="mt-1 text-sm text-zinc-600">{step.text}</p>
          </li>
        ))}
      </ol>

      <ClaimDesk />
    </main>
  );
}
