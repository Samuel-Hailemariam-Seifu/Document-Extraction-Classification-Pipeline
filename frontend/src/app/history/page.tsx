import { HistoryTable } from "@/components/HistoryTable";
import { listDocuments } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  let documents: Awaited<ReturnType<typeof listDocuments>> = [];
  let error: string | null = null;

  try {
    documents = await listDocuments();
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to load history";
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight text-stone-900">
        History
      </h1>
      <p className="mb-8 text-sm text-stone-600">
        Previously processed documents. Open a row to review or correct extraction.
      </p>
      {error ? (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      ) : (
        <HistoryTable documents={documents} />
      )}
    </div>
  );
}
