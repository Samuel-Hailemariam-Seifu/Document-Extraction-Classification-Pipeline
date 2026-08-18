import Link from "next/link";
import { UploadZone } from "@/components/UploadZone";
import { HistoryTable } from "@/components/HistoryTable";
import { listDocuments } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let recent: Awaited<ReturnType<typeof listDocuments>> = [];
  let listError: string | null = null;

  try {
    recent = (await listDocuments()).slice(0, 5);
  } catch {
    listError = "Backend unreachable — start the API to see history.";
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <div className="mb-10 max-w-lg">
        <h1 className="text-3xl font-semibold tracking-tight text-stone-900">
          Extract invoice data
        </h1>
        <p className="mt-2 text-stone-600">
          Upload a PDF or image. We return structured fields with confidence
          flags when something looks off — not silently wrong totals.
        </p>
      </div>

      <UploadZone />

      <section className="mt-16">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-stone-500">
            Recent
          </h2>
          <Link
            href="/history"
            className="text-sm text-stone-600 underline-offset-2 hover:text-stone-900 hover:underline"
          >
            View all
          </Link>
        </div>
        {listError ? (
          <p className="text-sm text-stone-500">{listError}</p>
        ) : (
          <HistoryTable documents={recent} />
        )}
      </section>
    </div>
  );
}
