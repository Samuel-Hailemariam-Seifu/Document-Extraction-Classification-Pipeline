import Link from "next/link";
import { notFound } from "next/navigation";
import { DocumentDetailView } from "@/components/DocumentDetailView";
import { DocumentPreview } from "@/components/DocumentPreview";
import { ReviewForm } from "@/components/ReviewForm";
import { getDocument } from "@/lib/api";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export default async function DocumentReviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let doc;
  try {
    doc = await getDocument(id);
  } catch {
    notFound();
  }

  const isConfirmed = doc.status === "confirmed";

  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-6xl flex-col px-4 py-4 sm:px-6">
      <Link
        href="/history"
        className="mb-3 shrink-0 text-sm text-stone-500 hover:text-stone-800"
      >
        ← History
      </Link>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-2 lg:gap-6">
        <div className="min-h-0 lg:min-h-0">
          <DocumentPreview documentId={doc.id} filename={doc.filename} />
        </div>
        <div className="flex min-h-0 flex-col overflow-hidden rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          {isConfirmed ? (
            <DocumentDetailView document={doc} />
          ) : (
            <ReviewForm document={doc} />
          )}
        </div>
      </div>
    </div>
  );
}
