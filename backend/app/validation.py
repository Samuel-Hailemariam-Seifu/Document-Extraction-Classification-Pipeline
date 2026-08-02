"""Server-side confidence / validation checks over extracted invoice data.

This is the portfolio differentiator: we never silently trust the model.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from app.schemas import (
    ConfidenceStatus,
    ExtractedInvoice,
    FieldIssue,
    ValidationResult,
)

# Rounding tolerance for money math (cents)
MONEY_TOLERANCE = 0.02

# Dates older than this many years are treated as implausible
MAX_DOCUMENT_AGE_YEARS = 30

REQUIRED_FIELDS = ("vendor_name", "document_date", "total")


def _approx_equal(a: Optional[float], b: Optional[float], tol: float = MONEY_TOLERANCE) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= tol


def validate_extraction(data: ExtractedInvoice, today: Optional[date] = None) -> ValidationResult:
    """Run deterministic checks and return overall confidence + per-field warnings."""
    today = today or date.today()
    issues: list[FieldIssue] = []

    # --- Required fields present? ---
    for field in REQUIRED_FIELDS:
        value = getattr(data, field)
        if value is None or (isinstance(value, str) and not value.strip()):
            issues.append(
                FieldIssue(
                    field=field,
                    message=f"Required field '{field}' is missing or empty",
                    severity="error",
                )
            )

    if not data.line_items:
        issues.append(
            FieldIssue(
                field="line_items",
                message="No line items were extracted",
                severity="warning",
            )
        )

    # --- Line items sum to subtotal? ---
    if data.line_items and data.subtotal is not None:
        line_sum = 0.0
        any_total = False
        for item in data.line_items:
            if item.line_total is not None:
                line_sum += item.line_total
                any_total = True
            elif item.quantity is not None and item.unit_price is not None:
                line_sum += item.quantity * item.unit_price
                any_total = True

        if any_total and not _approx_equal(line_sum, data.subtotal):
            issues.append(
                FieldIssue(
                    field="subtotal",
                    message=(
                        f"Line items sum to {line_sum:.2f} but subtotal is "
                        f"{data.subtotal:.2f}"
                    ),
                    severity="warning",
                )
            )
            issues.append(
                FieldIssue(
                    field="line_items",
                    message="Line items do not match subtotal",
                    severity="warning",
                )
            )

    # --- Per-line arithmetic (account for optional item_tax / item_discount) ---
    for idx, item in enumerate(data.line_items):
        if (
            item.quantity is not None
            and item.unit_price is not None
            and item.line_total is not None
        ):
            expected_line = item.quantity * item.unit_price
            if item.item_discount is not None:
                expected_line -= item.item_discount
            if item.item_tax is not None:
                expected_line += item.item_tax
            if not _approx_equal(expected_line, item.line_total):
                issues.append(
                    FieldIssue(
                        field=f"line_items[{idx}]",
                        message=(
                            f"Line {idx + 1}: expected {expected_line:.2f} "
                            f"(qty * unit_price"
                            f"{' - item_discount' if item.item_discount is not None else ''}"
                            f"{' + item_tax' if item.item_tax is not None else ''}"
                            f") != line_total ({item.line_total:.2f})"
                        ),
                        severity="warning",
                    )
                )

    # --- tax_rate × subtotal ≈ tax ---
    if data.tax_rate is not None and data.subtotal is not None and data.tax is not None:
        expected_tax = data.subtotal * data.tax_rate
        if not _approx_equal(expected_tax, data.tax):
            issues.append(
                FieldIssue(
                    field="tax_rate",
                    message=(
                        f"Tax rate doesn't match tax amount: "
                        f"subtotal × tax_rate = {expected_tax:.2f}, tax is {data.tax:.2f}"
                    ),
                    severity="warning",
                )
            )
            issues.append(
                FieldIssue(
                    field="tax",
                    message="Tax rate doesn't match tax amount",
                    severity="warning",
                )
            )

    # --- sum(tax_lines) ≈ tax ---
    if data.tax_lines and data.tax is not None:
        lines_sum = sum(tl.amount for tl in data.tax_lines)
        if not _approx_equal(lines_sum, data.tax):
            issues.append(
                FieldIssue(
                    field="tax_lines",
                    message=(
                        f"Tax line items don't sum to tax total: "
                        f"sum is {lines_sum:.2f}, tax is {data.tax:.2f}"
                    ),
                    severity="warning",
                )
            )
            issues.append(
                FieldIssue(
                    field="tax",
                    message="Tax line items don't sum to tax total",
                    severity="warning",
                )
            )

    # --- subtotal + tax + shipping − discount ≈ total ---
    # Document-level only: do NOT also add item_tax / item_discount here
    # (those belong on line rows; folding them in would double-count against
    # document-level tax/discount when the model already rolled them up).
    if data.subtotal is not None and data.total is not None:
        tax = data.tax if data.tax is not None else 0.0
        shipping = data.shipping if data.shipping is not None else 0.0
        discount = data.discount if data.discount is not None else 0.0
        expected = data.subtotal + tax + shipping - discount
        if not _approx_equal(expected, data.total):
            issues.append(
                FieldIssue(
                    field="total",
                    message=(
                        f"Subtotal ({data.subtotal:.2f}) + tax ({tax:.2f})"
                        f" + shipping ({shipping:.2f}) - discount ({discount:.2f})"
                        f" = {expected:.2f}, but total is {data.total:.2f}"
                    ),
                    severity="warning",
                )
            )
            if data.shipping is not None:
                issues.append(
                    FieldIssue(
                        field="shipping",
                        message="Shipping does not reconcile with subtotal, tax, discount, and total",
                        severity="warning",
                    )
                )
            if data.discount is not None:
                issues.append(
                    FieldIssue(
                        field="discount",
                        message="Discount does not reconcile with subtotal, tax, shipping, and total",
                        severity="warning",
                    )
                )
            if data.tax is not None:
                issues.append(
                    FieldIssue(
                        field="tax",
                        message="Tax does not reconcile with subtotal, shipping, discount, and total",
                        severity="warning",
                    )
                )

    # --- due_date vs document_date ---
    if data.due_date is not None and data.document_date is not None:
        if data.due_date < data.document_date:
            issues.append(
                FieldIssue(
                    field="due_date",
                    message="Due date is before issue date",
                    severity="warning",
                )
            )

    # --- Plausible document date? ---
    if data.document_date is not None:
        if data.document_date > today:
            issues.append(
                FieldIssue(
                    field="document_date",
                    message=f"Document date {data.document_date.isoformat()} is in the future",
                    severity="error",
                )
            )
        else:
            try:
                oldest = today.replace(year=today.year - MAX_DOCUMENT_AGE_YEARS)
            except ValueError:
                oldest = today - timedelta(days=365 * MAX_DOCUMENT_AGE_YEARS)

            if data.document_date < oldest:
                issues.append(
                    FieldIssue(
                        field="document_date",
                        message=(
                            f"Document date {data.document_date.isoformat()} is older than "
                            f"{MAX_DOCUMENT_AGE_YEARS} years"
                        ),
                        severity="warning",
                    )
                )

    # --- Currency present? (soft) ---
    if not data.currency:
        issues.append(
            FieldIssue(
                field="currency",
                message="Currency could not be determined; default may be wrong",
                severity="warning",
            )
        )

    field_warnings: dict[str, list[str]] = {}
    for issue in issues:
        # Normalize line_items[N] -> line_items for form highlighting
        key = issue.field.split("[")[0]
        field_warnings.setdefault(key, []).append(issue.message)

    status = _score_confidence(issues)
    return ValidationResult(status=status, issues=issues, field_warnings=field_warnings)


def add_issues(result: ValidationResult, new_issues: list[FieldIssue]) -> ValidationResult:
    """Append issues and recompute confidence / field_warnings."""
    if not new_issues:
        return result
    issues = list(result.issues) + list(new_issues)
    field_warnings = {k: list(v) for k, v in result.field_warnings.items()}
    for issue in new_issues:
        key = issue.field.split("[")[0]
        field_warnings.setdefault(key, []).append(issue.message)
    return ValidationResult(
        status=_score_confidence(issues),
        issues=issues,
        field_warnings=field_warnings,
    )


def _score_confidence(issues: list[FieldIssue]) -> ConfidenceStatus:
    """Map issue counts/severity to overall confidence.

    Rules (adjustable — review these before going live):
    - 0 issues                         -> high
    - only warnings, fewer than 3      -> needs_review
    - 1+ errors OR 3+ warnings         -> low
    """
    if not issues:
        return ConfidenceStatus.HIGH

    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")

    if errors >= 1 or warnings >= 3:
        return ConfidenceStatus.LOW
    return ConfidenceStatus.NEEDS_REVIEW
