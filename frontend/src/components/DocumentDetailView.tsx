import type { DocumentRecord } from "@/lib/types";
import { ConfidenceBadge } from "./ConfidenceBadge";

function display(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function displayMoney(value: number | null, currency: string | null) {
  if (value == null) return "—";
  return `${currency ? `${currency} ` : ""}${value.toFixed(2)}`;
}

function Field({
  label,
  value,
  className = "",
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className={`min-w-0 ${className}`}>
      <p className="text-[10px] font-medium uppercase tracking-wide text-stone-500">
        {label}
      </p>
      <p className="mt-0.5 text-sm text-stone-900">{value}</p>
    </div>
  );
}

export function DocumentDetailView({ document: doc }: { document: DocumentRecord }) {
  const { extracted: data } = doc;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-3 shrink-0 flex flex-wrap items-start justify-between gap-2 border-b border-stone-200 pb-2">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-stone-900">Document details</h2>
          <p className="truncate text-xs text-stone-500">{doc.filename}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-800 ring-1 ring-inset ring-emerald-200">
            Confirmed
          </span>
          <ConfidenceBadge status={doc.validation.status} />
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        <div className="grid grid-cols-2 gap-x-3 gap-y-3 lg:grid-cols-3">
          <Field
            label="Vendor"
            value={display(data.vendor_name)}
            className="col-span-2 lg:col-span-2"
          />
          <Field label="Invoice #" value={display(data.invoice_number)} />
          <Field
            label="Vendor address"
            value={display(data.vendor_address)}
            className="col-span-2 lg:col-span-3"
          />
          <Field label="Issue date" value={display(data.document_date)} />
          <Field label="Due date" value={display(data.due_date)} />
          <Field label="Payment terms" value={display(data.payment_terms)} />
          <Field label="Currency" value={display(data.currency)} />
          <Field label="Tax rate" value={display(data.tax_rate)} />
          <Field label="Subtotal" value={displayMoney(data.subtotal, data.currency)} />
          <Field label="Tax" value={displayMoney(data.tax, data.currency)} />
          <Field label="Shipping" value={displayMoney(data.shipping, data.currency)} />
          <Field label="Discount" value={displayMoney(data.discount, data.currency)} />
          <Field label="Total" value={displayMoney(data.total, data.currency)} />
        </div>

        {data.tax_lines.length > 0 && (
          <div>
            <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-stone-500">
              Tax lines
            </p>
            <div className="space-y-1">
              {data.tax_lines.map((line, idx) => (
                <div
                  key={idx}
                  className="flex justify-between gap-4 rounded-md border border-stone-200 px-3 py-2 text-sm"
                >
                  <span className="text-stone-700">{line.label}</span>
                  <span className="font-medium text-stone-900">
                    {displayMoney(line.amount, data.currency)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.line_items.length > 0 && (
          <div>
            <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-stone-500">
              Line items
            </p>
            <div className="space-y-2">
              {data.line_items.map((item, idx) => (
                <div
                  key={idx}
                  className="rounded-md border border-stone-200 px-3 py-2.5 text-sm"
                >
                  <p className="font-medium text-stone-900">
                    {item.description || "—"}
                  </p>
                  <div className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-stone-600 sm:grid-cols-5">
                    <span>Qty: {display(item.quantity)}</span>
                    <span>Unit: {displayMoney(item.unit_price, data.currency)}</span>
                    <span>Total: {displayMoney(item.line_total, data.currency)}</span>
                    <span>Tax: {displayMoney(item.item_tax, data.currency)}</span>
                    <span>Disc.: {displayMoney(item.item_discount, data.currency)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <p className="text-xs text-stone-500">
          Confirmed {new Date(doc.updated_at).toLocaleString()}
        </p>
      </div>
    </div>
  );
}
