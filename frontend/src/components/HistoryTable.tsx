"use client";

import Link from "next/link";
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
            <th className="px-4 py-3 font-medium">Processed</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100 bg-white">
          {documents.map((doc) => (
            <tr key={doc.id} className="transition hover:bg-stone-50">
              <td className="px-4 py-3">
                <Link
                  href={`/documents/${doc.id}`}
                  className="font-medium text-stone-900 underline-offset-2 hover:underline"
                >
                  {doc.vendor_name || doc.filename}
                </Link>
              </td>
              <td className="px-4 py-3 text-stone-600">
                {formatDate(doc.document_date)}
              </td>
              <td className="px-4 py-3 text-stone-600">
                {formatMoney(doc.total, doc.currency)}
              </td>
              <td className="px-4 py-3">
                <ConfidenceBadge status={doc.confidence_status} />
              </td>
              <td className="px-4 py-3 text-stone-500">
                {new Date(doc.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
