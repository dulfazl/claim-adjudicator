"use client";

import { useEffect, useState } from "react";

import { DecisionView } from "@/components/decision-view";
import { UploadForm } from "@/components/upload-form";
import { decideClaim, decideSample, getSamples, sampleImageUrl } from "@/lib/api";
import type { ClaimResult, ImageVersion, SampleClaim } from "@/lib/api";

const VERSIONS: { id: ImageVersion; label: string; hint: string }[] = [
  { id: "clean", label: "Scan", hint: "A sharp scan or PDF export." },
  { id: "photo", label: "Phone photo", hint: "Tilted and slightly soft, as most uploads are." },
  { id: "rough", label: "Rough photo", hint: "Dim, angled and blurred. The sharpness check should stop it." },
];

const card = "rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm";

export function ClaimDesk() {
  const [samples, setSamples] = useState<SampleClaim[]>([]);
  const [version, setVersion] = useState<ImageVersion>("clean");
  const [title, setTitle] = useState("");
  const [result, setResult] = useState<ClaimResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getSamples()
      .then(setSamples)
      .catch((problem: Error) => setError(problem.message));
  }, []);

  async function run(label: string, request: () => Promise<ClaimResult>) {
    setBusy(true);
    setError("");
    setResult(null);
    setTitle(label);
    try {
      setResult(await request());
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-8 grid gap-6 lg:grid-cols-2">
      <div className="space-y-6">
        <section className={card}>
          <h2 className="text-lg font-semibold text-zinc-950">Try a sample claim</h2>
          <div className="mt-3 inline-flex rounded-lg bg-zinc-100 p-1" role="group" aria-label="Image quality">
            {VERSIONS.map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => setVersion(option.id)}
                aria-pressed={version === option.id}
                className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                  version === option.id ? "bg-white text-zinc-950 shadow-sm" : "text-zinc-600 hover:text-zinc-950"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
          <p className="mt-2 text-sm text-zinc-500">{VERSIONS.find((option) => option.id === version)?.hint}</p>

          <ul className="mt-4 divide-y divide-zinc-100">
            {samples.map((sample) => (
              <li key={sample.id} className="flex items-center gap-4 py-3">
                <div className="flex shrink-0 gap-1">
                  {sample.documents.map((name) => (
                    <a key={name} href={sampleImageUrl(name, version)} target="_blank" rel="noreferrer" title="Open the document">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={sampleImageUrl(name, version)}
                        alt={`Document ${name}`}
                        className="h-14 w-14 rounded-md border border-zinc-200 object-cover object-top"
                      />
                    </a>
                  ))}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-zinc-950">{sample.title}</p>
                  <p className="text-sm text-zinc-500">
                    {sample.member.name}, submitted {sample.submitted_on}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => run(sample.title, () => decideSample(sample.id, version))}
                  className="shrink-0 rounded-lg border border-zinc-300 px-3 py-1.5 text-sm font-semibold text-zinc-950 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Decide
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className={card}>
          <h2 className="text-lg font-semibold text-zinc-950">Or upload your own</h2>
          <p className="mb-4 mt-1 text-sm text-zinc-500">
            Use made-up documents only. Images are sent to Google&apos;s Gemini API on its free tier, which may keep them.
          </p>
          <UploadForm busy={busy} onSubmit={(form) => run(`Uploaded claim for ${form.get("member_name")}`, () => decideClaim(form))} />
        </section>
      </div>

      <section className={`${card} lg:sticky lg:top-6 lg:self-start`} aria-live="polite">
        <h2 className="text-lg font-semibold text-zinc-950">Decision</h2>
        <div className="mt-4">
          {busy && <p className="text-sm text-zinc-600">Checking the photos and reading the documents. This usually takes 5 to 15 seconds.</p>}
          {error && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
          {result && <DecisionView title={title} result={result} />}
          {!busy && !error && !result && <p className="text-sm text-zinc-500">Pick a sample claim or upload documents to see a decision here.</p>}
        </div>
      </section>
    </div>
  );
}
