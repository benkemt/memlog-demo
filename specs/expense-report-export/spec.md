---
id: SPEC-expense-report-export
topic: Expense report export
---

# Expense report export

## Why

At month end, accounting retypes every approved expense into the accounting software by hand. It
takes two days and introduces errors.

## Capabilities

- **CAP-1**
  - **intent:** A finance user can export the approved expenses of a month as one CSV file to import
    them into the accounting software.
  - **success:** The CSV of a test month imports without error, with one row per approved expense.
- **CAP-3**
  - **intent:** A finance user can export a PDF summary of the month's approved expenses for the
    auditor.
  - **success:** For a test month, the totals in the PDF equal the sums of the CSV export.

## Constraints

- Only approved expenses are exported; draft and rejected expenses never appear in an export.
- Only users with the finance role can export.
- The CSV is semicolon-separated with the columns `date;employee;category;amount;currency`, and dates
  are written as DD/MM/YYYY.

## Non-goals

- No direct integration with the accounting software's API; the file is imported by hand.

## Assumptions

- Amounts are exported in the currency in which they were approved, without conversion.

## Open Questions

- CAP-3: which totals must the PDF summary show: per employee, per category, or both?
