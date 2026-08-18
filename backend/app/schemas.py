from datetime import date
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Extraction schema (strict structured output from the vision model)
# ---------------------------------------------------------------------------


class LineItem(BaseModel):
    description: str = Field(..., description="Item or service description")
    quantity: Optional[float] = Field(None, description="Quantity purchased")
    unit_price: Optional[float] = Field(None, description="Price per unit")
    line_total: Optional[float] = Field(None, description="Total for this line")
    item_tax: Optional[float] = Field(
        None,
        description="Line-level tax if broken out on this row; otherwise null",
    )
    item_discount: Optional[float] = Field(
        None,
        description="Line-level discount if broken out on this row; otherwise null",
    )


class TaxLine(BaseModel):
    label: str = Field(..., description="Tax component label, e.g. State tax")
    amount: float = Field(..., description="Tax amount for this component")


class ExtractedInvoice(BaseModel):
    vendor_name: Optional[str] = Field(None, description="Merchant / vendor name")
    vendor_address: Optional[str] = Field(
        None, description="Vendor mailing/billing address as printed"
    )
    invoice_number: Optional[str] = Field(None, description="Invoice or receipt number")
    document_date: Optional[date] = Field(
        None, description="Issue date of the invoice/receipt (not the due date)"
    )
    due_date: Optional[date] = Field(
        None, description="Payment due date if present; distinct from document_date"
    )
    payment_terms: Optional[str] = Field(
        None, description="Payment terms as printed, e.g. Net 30"
    )
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: Optional[float] = Field(None, description="Sum before tax")
    tax: Optional[float] = Field(
        None,
        description="Total tax amount (sole tax, or sum of tax_lines when multiple)",
    )
    tax_rate: Optional[float] = Field(
        None,
        description="Tax rate as a fraction when stated, e.g. 0.085 for 8.5%",
    )
    tax_lines: list[TaxLine] = Field(
        default_factory=list,
        description="Per-component tax rows when the document lists multiple taxes",
    )
    shipping: Optional[float] = Field(None, description="Shipping / freight amount")
    discount: Optional[float] = Field(None, description="Document-level discount amount")
    total: Optional[float] = Field(None, description="Grand total")
    currency: Optional[str] = Field(
        None, description="ISO-ish currency code when explicitly stated or clearly implied"
    )

    @field_validator("invoice_number", mode="before")
    @classmethod
    def coerce_invoice_number(cls, value: Any) -> Optional[str]:
        """Models often emit purely numeric invoice IDs as JSON numbers."""
        if value is None:
            return None
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            return str(value)
        text = str(value).strip()
        return text or None


# ---------------------------------------------------------------------------
# Validation / confidence layer
# ---------------------------------------------------------------------------


class ConfidenceStatus(str, Enum):
    HIGH = "high"
    NEEDS_REVIEW = "needs_review"
    LOW = "low"


class FieldIssue(BaseModel):
    """A validation problem tied to one or more fields."""

    field: str = Field(..., description="Primary field name, e.g. 'subtotal' or 'line_items'")
    message: str
    severity: str = Field("warning", description="'warning' or 'error'")


class ValidationResult(BaseModel):
    status: ConfidenceStatus
    issues: list[FieldIssue] = Field(default_factory=list)
    # Convenience map: field name -> list of messages (for UI highlighting)
    field_warnings: dict[str, list[str]] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# API response / persistence shapes
# ---------------------------------------------------------------------------


class DocumentStatus(str, Enum):
    EXTRACTED = "extracted"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class DocumentRecord(BaseModel):
    id: UUID
    filename: str
    content_type: str
    # Relative path or URL the frontend can use to preview the original file
    file_url: str
    extracted: ExtractedInvoice
    validation: ValidationResult
    status: DocumentStatus = DocumentStatus.EXTRACTED
    created_at: str
    updated_at: str


class DocumentSummary(BaseModel):
    id: UUID
    filename: str
    vendor_name: Optional[str]
    document_date: Optional[date]
    total: Optional[float]
    currency: Optional[str]
    confidence_status: ConfidenceStatus
    status: DocumentStatus
    created_at: str


class DocumentUpdate(BaseModel):
    """User corrections from the review UI."""

    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    invoice_number: Optional[str] = None
    document_date: Optional[date] = None
    due_date: Optional[date] = None
    payment_terms: Optional[str] = None
    line_items: Optional[list[LineItem]] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_lines: Optional[list[TaxLine]] = None
    shipping: Optional[float] = None
    discount: Optional[float] = None
    total: Optional[float] = None
    currency: Optional[str] = None
    confirm: bool = Field(
        True,
        description="If true, mark the document as confirmed after applying edits",
    )


class ErrorResponse(BaseModel):
    detail: str
