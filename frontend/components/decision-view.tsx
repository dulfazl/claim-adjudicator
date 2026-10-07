import type { ClaimResult, Status } from "@/lib/api";

const STATUS: Record<Status, { label: string; tone: string }> = {
  APPROVED: { label: "Approved", tone: "bg-emerald-50 text-emerald-800 ring-emerald-200" },
  PARTIAL: { label: "Partly approved", tone: "bg-amber-50 text-amber-800 ring-amber-200" },
  REJECTED: { label: "Rejected", tone: "bg-rose-50 text-rose-800 ring-rose-200" },
  MANUAL_REVIEW: { label: "Needs manual review", tone: "bg-sky-50 text-sky-800 ring-sky-200" },
  RETAKE_PHOTO: { label: "Clearer photo needed", tone: "bg-zinc-100 text-zinc-800 ring-zinc-300" },
};

function rupees(value: string | number): string {
  return Number(value).toLocaleString("en-IN", { style: "currency", currency: "INR" });
}

export function DecisionView({ title, result }: { title: string; result: ClaimResult }) {
  const { decision, documents } = result;
  const status = STATUS[decision.status];
  const decided = decision.status !== "MANUAL_REVIEW" && decision.status !== "RETAKE_PHOTO";

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-zinc-500">{title}</p>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <span className={`rounded-full px-3 py-1 text-sm font-semibold ring-1 ring-inset ${status.tone}`}>{status.label}</span>
          {decided && (
            <p className="text-zinc-700">
              <span className="text-2xl font-semibold text-zinc-950">{rupees(decision.approved)}</span> approved of{" "}
              {rupees(decision.claimed)} claimed
            </p>
          )}
        </div>
      </div>

      {decision.items.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-zinc-200 text-xs uppercase tracking-wide text-zinc-500">
              <tr>
                <th className="py-2 pr-3 font-medium">Item</th>
                <th className="px-3 py-2 text-right font-medium">Claimed</th>
                <th className="px-3 py-2 text-right font-medium">Payable</th>
                <th className="py-2 pl-3 font-medium">Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {decision.items.map((item, index) => {
                const cut = Number(item.payable) < Number(item.claimed);
                return (
                  <tr key={index} className="align-top">
                    <td className="py-2 pr-3">
                      {item.description}
                      <span className="block text-xs text-zinc-500">{item.category}</span>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">{rupees(item.claimed)}</td>
                    <td className={`px-3 py-2 text-right font-medium tabular-nums ${cut ? "text-rose-700" : "text-emerald-700"}`}>
                      {rupees(item.payable)}
                    </td>
                    <td className="py-2 pl-3 text-zinc-600">{item.reason}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold text-zinc-950">How this was decided</h3>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-zinc-700">
          {decision.steps.map((step, index) => (
            <li key={index}>{step}</li>
          ))}
        </ol>
      </div>

      {documents.length > 0 && (
        <details className="rounded-lg border border-zinc-200 p-4 text-sm">
          <summary className="cursor-pointer font-semibold text-zinc-950">What the model read from each document</summary>
          <div className="mt-3 space-y-4">
            {documents.map((doc, index) => (
              <dl key={index} className="grid grid-cols-[8rem_1fr] gap-x-3 gap-y-1 text-zinc-700">
                <dt className="text-zinc-500">Type</dt>
                <dd>{doc.document_type}</dd>
                <dt className="text-zinc-500">Provider</dt>
                <dd>{doc.provider_name ?? "not printed"}</dd>
                <dt className="text-zinc-500">Patient</dt>
                <dd>{doc.patient_name ?? "not printed"}</dd>
                <dt className="text-zinc-500">Doctor</dt>
                <dd>{doc.doctor_name ?? "not printed"}</dd>
                <dt className="text-zinc-500">Number</dt>
                <dd>{doc.bill_number ?? "not printed"}</dd>
                <dt className="text-zinc-500">Date</dt>
                <dd>{doc.bill_date ?? "not printed"}</dd>
                <dt className="text-zinc-500">Diagnosis</dt>
                <dd>{doc.diagnosis ?? "not printed"}</dd>
                <dt className="text-zinc-500">Total</dt>
                <dd>{doc.total_amount === null ? "none" : rupees(doc.total_amount)}</dd>
              </dl>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
