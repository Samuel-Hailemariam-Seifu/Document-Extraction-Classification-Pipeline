export type ConfidenceStatus = "high" | "needs_review" | "low";
export type DocumentStatus = "extracted" | "confirmed" | "failed";

export interface LineItem {
  description: string;
  quantity: number | null;
  unit_price: number | null;
  line_total: number | null;
  item_tax: number | null;
  item_discount: number | null;
}

export interface TaxLine {
  label: string;
  amount: number;
}

export interface ExtractedInvoice {
  vendor_name: string | null;
  vendor_address: string | null;
  invoice_number: string | null;
  document_date: string | null;
  due_date: string | null;
  payment_terms: string | null;
  line_items: LineItem[];
  subtotal: number | null;
  tax: number | null;
  tax_rate: number | null;
  tax_lines: TaxLine[];
  shipping: number | null;
  discount: number | null;
  total: number | null;
  currency: string | null;
}

export interface FieldIssue {
  field: string;
  message: string;
  severity: string;
}

export interface ValidationResult {
  status: ConfidenceStatus;
  issues: FieldIssue[];
  field_warnings: Record<string, string[]>;
}

export interface DocumentRecord {
  id: string;
  filename: string;
  content_type: string;
  file_url: string;
  extracted: ExtractedInvoice;
  validation: ValidationResult;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
}

export interface DocumentSummary {
  id: string;
  filename: string;
  vendor_name: string | null;
  document_date: string | null;
  total: number | null;
  currency: string | null;
  confidence_status: ConfidenceStatus;
  status: DocumentStatus;
  created_at: string;
}

export interface DocumentUpdate {
  vendor_name?: string | null;
  vendor_address?: string | null;
  invoice_number?: string | null;
  document_date?: string | null;
  due_date?: string | null;
  payment_terms?: string | null;
  line_items?: LineItem[];
  subtotal?: number | null;
  tax?: number | null;
  tax_rate?: number | null;
  tax_lines?: TaxLine[];
  shipping?: number | null;
  discount?: number | null;
  total?: number | null;
  currency?: string | null;
  confirm?: boolean;
}
