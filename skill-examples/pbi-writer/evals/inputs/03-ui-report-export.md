# UI Specification: Filters and CSV export on the "Transactions Report" page

**Product:** Back-office portal · **Page:** `/reports/transactions` · **Roles:** `finance_analyst`, `finance_admin`

## Prerequisites
Analysts export data through SQL queries to the replica, which is unsafe and requires help from developers. The page currently shows the last 100 transactions without filters.

## Filters
A filter panel is placed above the table:
1. **Period** — date range picker, required. Default — the last 7 days. Maximum range — 92 days; when a larger one is selected, show the error "Period cannot exceed 92 days" and disable the "Apply" button.
2. **Status** — multi-select: `Completed`, `Pending`, `Failed`, `Refunded`. All are selected by default.
3. **Amount** — two fields "from" and "to" (numbers, 2 decimal places). If "from" > "to", show an error at the "to" field.
4. **Currency** — dropdown list (EUR, USD, PLN, GBP), optional.

Buttons: "Apply" and "Reset" (returns default values). Filters are stored in the URL query parameters so that the link can be shared.

## Table
Pagination of 50 rows, sorting by the columns "Date" (default, descending) and "Amount". The total number of found records is shown above the table.

## Export
- The "Export to CSV" button is visible to the roles `finance_analyst` and `finance_admin`.
- **All** records matching the current filters are exported, not only the current page.
- Format: UTF-8 with BOM, delimiter `;`, dates in ISO-8601, amount with a dot as the decimal separator. File name: `transactions_{from}_{to}.csv`.
- Limit: no more than 100,000 rows. If there are more records, show the message "More than 100,000 records found, refine the filters", the file is not generated.
- While the file is being generated, the button is inactive and shows a loading indicator. For exports of up to 10,000 rows the generation time is ≤ 10 seconds.
- When the result set is empty, the export button is inactive.

## Out of scope
Export to XLSX, saving filter presets, scheduled exports.
