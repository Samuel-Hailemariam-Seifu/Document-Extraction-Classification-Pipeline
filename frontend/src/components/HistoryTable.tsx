"use client";

import { useRouter } from "next/navigation";
import type { DocumentSummary } from "@/lib/types";
import { ConfidenceBadge } from "./ConfidenceBadge";

function formatMoney(total: number | null, currency: string | null) {
  if (total == null) return "—";
  const code = currency ?? "";
  return `${code ? code + " " : ""}${total.toFixed(2)}`;
}

function formatDate(value: string | null) {
  if (!value) return "—";
  return value;
}

function formatStatus(status: DocumentSummary["status"]) {
  if (status === "confirmed") return "Confirmed";
  if (status === "failed") return "Failed";
  return "Extracted";
}

function HistoryRow({ doc }: { doc: DocumentSummary }) {
  const router = useRouter();
  const href = `/documents/${doc.id}`;

  return (
    <tr
      role="link"
      tabIndex={0}
      onClick={() => router.push(href)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          router.push(href);
        }
      }}
      className="cursor-pointer transition hover:bg-stone-50 focus-visible:bg-stone-50 focus-visible:outline-none"
    >
      <td className="px-4 py-3 font-medium text-stone-900">
        {doc.vendor_name || doc.filename}
      </td>
      <td className="px-4 py-3 text-stone-600">{formatDate(doc.document_date)}</td>
      <td className="px-4 py-3 text-stone-600">
        {formatMoney(doc.total, doc.currency)}
      </td>
      <td className="px-4 py-3">
        <ConfidenceBadge status={doc.confidence_status} />
      </td>
      <td className="px-4 py-3 text-stone-600">{formatStatus(doc.status)}</td>
      <td className="px-4 py-3 text-stone-500">
        {new Date(doc.created_at).toLocaleString()}
      </td>
      <td className="px-4 py-3 text-right text-sm font-medium text-stone-700">
        View →
      </td>
    </tr>
  );
}

export function HistoryTable({ documents }: { documents: DocumentSummary[] }) {
  if (documents.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-stone-300 bg-stone-50 px-4 py-10 text-center text-sm text-stone-500">
        No documents yet. Upload an invoice to get started.
      </p>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-stone-200">
      <table className="w-full text-left text-sm">
        <thead className="bg-stone-50 text-xs uppercase tracking-wide text-stone-500">
          <tr>
            <th className="px-4 py-3 font-medium">Vendor</th>
            <th className="px-4 py-3 font-medium">Date</th>
            <th className="px-4 py-3 font-medium">Total</th>
            <th className="px-4 py-3 font-medium">Confidence</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Processed</th>
            <th className="px-4 py-3 font-medium text-right">Detail</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100 bg-white">
          {documents.map((doc) => <HistoryRow key={doc.id} doc={doc} />)}
        </tbody>
      </table>
    </div>
  );
}
