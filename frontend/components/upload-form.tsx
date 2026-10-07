"use client";

const field = "mt-1 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950 outline-none focus:border-zinc-950";

export function UploadForm({ busy, onSubmit }: { busy: boolean; onSubmit: (form: FormData) => void }) {
  return (
    <form
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(new FormData(event.currentTarget));
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm font-medium text-zinc-800">
          Member name
          <input name="member_name" required placeholder="As printed on the bill" className={field} />
        </label>
        <label className="block text-sm font-medium text-zinc-800">
          Submitted on
          <input
            name="submitted_on"
            type="date"
            required
            className={field}
            // Filled in on the client only, so the server-rendered page never depends on today's date.
            ref={(input) => {
              if (input && !input.value) input.valueAsDate = new Date();
            }}
          />
        </label>
      </div>
      <label className="block text-sm font-medium text-zinc-800">
        Already claimed this policy year (₹)
        <input name="used_this_year" type="number" min="0" step="0.01" defaultValue="0" className={field} />
      </label>
      <label className="block text-sm font-medium text-zinc-800">
        Documents (up to 4 images)
        <input
          name="files"
          type="file"
          required
          multiple
          accept="image/png,image/jpeg,image/webp"
          className="mt-1 block w-full text-sm text-zinc-700 file:mr-3 file:rounded-lg file:border-0 file:bg-zinc-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-zinc-950 hover:file:bg-zinc-200"
        />
      </label>
      <button
        type="submit"
        disabled={busy}
        className="rounded-lg bg-zinc-950 px-4 py-2 text-sm font-semibold text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Decide this claim
      </button>
    </form>
  );
}
