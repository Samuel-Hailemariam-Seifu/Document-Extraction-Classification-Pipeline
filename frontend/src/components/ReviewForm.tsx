"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { DocumentRecord, ExtractedInvoice, LineItem } from "@/lib/types";
import { updateDocument } from "@/lib/api";
import { ConfidenceBadge } from "./ConfidenceBadge";

function emptyLine(): LineItem {
  return {
    description: "",
    quantity: null,
    unit_price: null,
    line_total: null,
    item_tax: null,
    item_discount: null,
  };
}

function normalizeExtracted(extracted: ExtractedInvoice): ExtractedInvoice {
  return {
    vendor_name: extracted.vendor_name ?? null,
    vendor_address: extracted.vendor_address ?? null,
    invoice_number: extracted.invoice_number ?? null,
    document_date: extracted.document_date ?? null,
    due_date: extracted.due_date ?? null,
    payment_terms: extracted.payment_terms ?? null,
    line_items: (extracted.line_items ?? []).map((item) => ({
      description: item.description ?? "",
      quantity: item.quantity ?? null,
      unit_price: item.unit_price ?? null,
      line_total: item.line_total ?? null,
      item_tax: item.item_tax ?? null,
      item_discount: item.item_discount ?? null,
    })),
    subtotal: extracted.subtotal ?? null,
    tax: extracted.tax ?? null,
    tax_rate: extracted.tax_rate ?? null,
    tax_lines: extracted.tax_lines ?? [],
    shipping: extracted.shipping ?? null,
    discount: extracted.discount ?? null,
    total: extracted.total ?? null,
    currency: extracted.currency ?? null,
  };
}

function FieldShell({
  label,
  warnings,
  children,
  className = "",
}: {
  label: string;
  warnings?: string[];
  children: React.ReactNode;
  className?: string;
}) {
  const hasWarn = Boolean(warnings?.length);
  return (
    <label className={`block min-w-0 ${className}`}>
      <span className="mb-0.5 block text-[10px] font-medium uppercase tracking-wide text-stone-500">
        {label}
      </span>
      <div
        className={
          hasWarn
            ? "[&_input]:border-red-400 [&_input]:ring-1 [&_input]:ring-red-300 [&_textarea]:border-red-400"
            : ""
        }
      >
        {children}
      </div>
      {hasWarn &&
        warnings!.map((msg) => (
          <p key={msg} className="mt-0.5 text-[10px] leading-snug text-red-700">
            {msg}
          </p>
        ))}
    </label>
  );
}

const inputClass =
  "w-full rounded-md border border-stone-300 bg-white px-2.5 py-1.5 text-sm text-stone-900 outline-none focus:border-stone-500 focus:ring-1 focus:ring-stone-400";

function numOrEmpty(value: number | null | undefined): string | number {
  return value ?? "";
}

function parseOptionalNumber(raw: string): number | null {
  return raw === "" ? null : Number(raw);
}

export function ReviewForm({ document: initial }: { document: DocumentRecord }) {
  const router = useRouter();
  const [doc, setDoc] = useState(initial);
  const [form, setForm] = useState<ExtractedInvoice>(() =>
    normalizeExtracted(initial.extracted),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const warnings = doc.validation.field_warnings;

  const setField = <K extends keyof ExtractedInvoice>(key: K, value: ExtractedInvoice[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const updateLine = (index: number, patch: Partial<LineItem>) => {
    setForm((prev) => {
      const next = [...prev.line_items];
      next[index] = { ...next[index], ...patch };
      return { ...prev, line_items: next };
    });
  };

  const issueSummary = useMemo(
    () => doc.validation.issues.map((i) => i.message),
    [doc.validation.issues],
  );

  async function onConfirm() {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateDocument(doc.id, { ...form, confirm: true });
      setDoc(updated);
      setForm(normalizeExtracted(updated.extracted));
      router.push("/history");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-3 shrink-0 flex flex-wrap items-start justify-between gap-2 border-b border-stone-200 pb-2">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-stone-900">Extracted data</h2>
          <p className="truncate text-xs text-stone-500">{doc.filename}</p>
        </div>
        <ConfidenceBadge status={doc.validation.status} />
      </div>

      {issueSummary.length > 0 && (
        <div className="mb-3 shrink-0 max-h-20 overflow-y-auto rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1.5">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-amber-900">
            Validation flags
          </p>
          <ul className="mt-0.5 list-disc space-y-0.5 pl-4 text-xs text-amber-950">
            {issueSummary.map((msg) => (
              <li key={msg}>{msg}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
        {/* Scalar fields */}
        <div className="grid grid-cols-2 gap-x-3 gap-y-2 lg:grid-cols-3">
          <FieldShell label="Vendor" warnings={warnings.vendor_name} className="col-span-2 lg:col-span-2">
            <input
              className={inputClass}
              value={form.vendor_name ?? ""}
              onChange={(e) => setField("vendor_name", e.target.value || null)}
            />
          </FieldShell>
          <FieldShell label="Invoice #" warnings={warnings.invoice_number}>
            <input
              className={inputClass}
              value={form.invoice_number ?? ""}
              onChange={(e) => setField("invoice_number", e.target.value || null)}
            />
          </FieldShell>

          <FieldShell
            label="Vendor address"
            warnings={warnings.vendor_address}
            className="col-span-2 lg:col-span-3"
          >
            <textarea
              className={`${inputClass} min-h-[2.5rem] resize-none`}
              rows={2}
              value={form.vendor_address ?? ""}
              onChange={(e) => setField("vendor_address", e.target.value || null)}
            />
          </FieldShell>

          <FieldShell label="Issue date" warnings={warnings.document_date}>
            <input
              type="date"
              className={inputClass}
              value={form.document_date ?? ""}
              onChange={(e) => setField("document_date", e.target.value || null)}
            />
          </FieldShell>
          <FieldShell label="Due date" warnings={warnings.due_date}>
            <input
              type="date"
              className={inputClass}
              value={form.due_date ?? ""}
              onChange={(e) => setField("due_date", e.target.value || null)}
            />
          </FieldShell>
          <FieldShell label="Payment terms" warnings={warnings.payment_terms}>
            <input
              className={inputClass}
              value={form.payment_terms ?? ""}
              onChange={(e) => setField("payment_terms", e.target.value || null)}
            />
          </FieldShell>

          <FieldShell label="Currency" warnings={warnings.currency}>
            <input
              className={inputClass}
              value={form.currency ?? ""}
              onChange={(e) => setField("currency", e.target.value || null)}
            />
          </FieldShell>
          <FieldShell label="Tax rate" warnings={warnings.tax_rate}>
            <input
              type="number"
              step="any"
              className={inputClass}
              value={numOrEmpty(form.tax_rate)}
              onChange={(e) => setField("tax_rate", parseOptionalNumber(e.target.value))}
            />
          </FieldShell>
          <FieldShell label="Subtotal" warnings={warnings.subtotal}>
            <input
              type="number"
              step="any"
              className={inputClass}
              value={numOrEmpty(form.subtotal)}
              onChange={(e) => setField("subtotal", parseOptionalNumber(e.target.value))}
            />
          </FieldShell>

          <FieldShell label="Tax" warnings={warnings.tax}>
            <input
              type="number"
              step="any"
              className={inputClass}
              value={numOrEmpty(form.tax)}
              onChange={(e) => setField("tax", parseOptionalNumber(e.target.value))}
            />
          </FieldShell>
          <FieldShell label="Shipping" warnings={warnings.shipping}>
            <input
              type="number"
              step="any"
              className={inputClass}
              value={numOrEmpty(form.shipping)}
              onChange={(e) => setField("shipping", parseOptionalNumber(e.target.value))}
            />
          </FieldShell>
          <FieldShell label="Discount" warnings={warnings.discount}>
            <input
              type="number"
              step="any"
              className={inputClass}
              value={numOrEmpty(form.discount)}
              onChange={(e) => setField("discount", parseOptionalNumber(e.target.value))}
            />
          </FieldShell>
          <FieldShell label="Total" warnings={warnings.total} className="col-span-2 lg:col-span-1">
            <input
              type="number"
              step="any"
              className={inputClass}
              value={numOrEmpty(form.total)}
              onChange={(e) => setField("total", parseOptionalNumber(e.target.value))}
            />
          </FieldShell>
        </div>

        {(form.tax_lines?.length ?? 0) > 0 && (
          <div className="grid grid-cols-2 gap-2 lg:grid-cols-3">
            {warnings.tax_lines?.map((msg) => (
              <p key={msg} className="col-span-full text-[10px] text-red-700">
                {msg}
              </p>
            ))}
            {form.tax_lines.map((tl, idx) => (
              <div key={idx} className="grid grid-cols-2 gap-1.5">
                <input
                  className={inputClass}
                  value={tl.label}
                  onChange={(e) => {
                    const next = [...form.tax_lines];
                    next[idx] = { ...next[idx], label: e.target.value };
                    setField("tax_lines", next);
                  }}
                />
                <input
                  type="number"
                  step="any"
                  className={inputClass}
                  value={tl.amount}
                  onChange={(e) => {
                    const next = [...form.tax_lines];
                    next[idx] = {
                      ...next[idx],
                      amount: e.target.value === "" ? 0 : Number(e.target.value),
                    };
                    setField("tax_lines", next);
                  }}
                />
              </div>
            ))}
          </div>
        )}

        {/* Line items */}
        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-[10px] font-medium uppercase tracking-wide text-stone-500">
              Line items
            </span>
            <button
              type="button"
              className="text-[10px] font-medium text-stone-700 underline-offset-2 hover:underline"
              onClick={() =>
                setForm((prev) => ({
                  ...prev,
                  line_items: [...prev.line_items, emptyLine()],
                }))
              }
            >
              Add line
            </button>
          </div>
          {warnings.line_items?.map((msg) => (
            <p key={msg} className="mb-1 text-[10px] text-red-700">
              {msg}
            </p>
          ))}
          <div className="space-y-2">
            {form.line_items.map((item, idx) => (
              <div
                key={idx}
                className={`rounded-md border p-2 ${
                  warnings.line_items ? "border-red-300" : "border-stone-200"
                }`}
              >
                <input
                  className={`${inputClass} mb-1.5`}
                  placeholder="Description"
                  value={item.description}
                  onChange={(e) => updateLine(idx, { description: e.target.value })}
                />
                <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-5">
                  <input
                    type="number"
                    step="any"
                    className={inputClass}
                    placeholder="Qty"
                    value={numOrEmpty(item.quantity)}
                    onChange={(e) =>
                      updateLine(idx, { quantity: parseOptionalNumber(e.target.value) })
                    }
                  />
                  <input
                    type="number"
                    step="any"
                    className={inputClass}
                    placeholder="Unit"
                    value={numOrEmpty(item.unit_price)}
                    onChange={(e) =>
                      updateLine(idx, { unit_price: parseOptionalNumber(e.target.value) })
                    }
                  />
                  <input
                    type="number"
                    step="any"
                    className={inputClass}
                    placeholder="Total"
                    value={numOrEmpty(item.line_total)}
                    onChange={(e) =>
                      updateLine(idx, { line_total: parseOptionalNumber(e.target.value) })
                    }
                  />
                  <input
                    type="number"
                    step="any"
                    className={inputClass}
                    placeholder="Item tax"
                    value={numOrEmpty(item.item_tax)}
                    onChange={(e) =>
                      updateLine(idx, { item_tax: parseOptionalNumber(e.target.value) })
                    }
                  />
                  <input
                    type="number"
                    step="any"
                    className={inputClass}
                    placeholder="Item disc."
                    value={numOrEmpty(item.item_discount)}
                    onChange={(e) =>
                      updateLine(idx, {
                        item_discount: parseOptionalNumber(e.target.value),
                      })
                    }
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-3 shrink-0 border-t border-stone-200 pt-3">
        {error && (
          <div
            role="alert"
            className="mb-2 flex items-start justify-between gap-2 rounded-md border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs text-red-800"
          >
            <p className="min-w-0 flex-1">{error}</p>
            <button
              type="button"
              className="shrink-0 font-medium underline-offset-2 hover:underline"
              onClick={() => setError(null)}
            >
              Dismiss
            </button>
          </div>
        )}
        <button
          type="button"
          disabled={saving}
          onClick={() => void onConfirm()}
          className="w-full rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-800 disabled:opacity-60"
        >
          {saving ? "Saving…" : doc.status === "confirmed" ? "Save changes" : "Confirm"}
        </button>
      </div>
    </div>
  );
}
