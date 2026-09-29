### Title
Add filters and CSV export to the "Transactions Report" page of the back-office portal

### Description
Finance analysts export data with SQL queries to the replica, which is unsafe and requires help from developers; the page `/reports/transactions` currently shows only the last 100 transactions without filters. As `finance_analyst` or `finance_admin`, I want to filter transactions by period, status, amount and currency and export the result to CSV on my own. Filters are stored in the URL query parameters; the table gets pagination (50 rows) and sorting by "Date" and "Amount"; the "Export to CSV" button exports all records matching the current filters.
Out of scope: export to XLSX, filter presets, scheduled exports.

### AC
1. The filter panel contains: "Period" (required, default last 7 days), "Status" (multi-select `Completed`/`Pending`/`Failed`/`Refunded`, all by default), "Amount" from/to (2 decimal places), "Currency" (EUR, USD, PLN, GBP, optional), buttons "Apply" and "Reset".
2. Given a period longer than 92 days is selected, Then "Period cannot exceed 92 days" is shown and the "Apply" button is disabled.
3. Given "Amount from" > "Amount to", Then the error is displayed at the "to" field.
4. "Reset" returns all filters to default values; applied filters are reflected in the URL query parameters, and opening such a link restores the same filters.
5. The table shows 50 rows per page, sorting by "Date" (default descending) and "Amount", and above the table — the total number of found records.
6. The "Export to CSV" button is visible only to the roles `finance_analyst` and `finance_admin`.
7. The export includes all records matching the current filters (not only the current page); the file is UTF-8 with BOM, delimiter `;`, dates ISO-8601, dot as the decimal separator, name `transactions_{from}_{to}.csv`.
8. Given more than 100,000 records are found, Then "More than 100,000 records found, refine the filters" is shown and the file is not generated.
9. While the file is being generated, the button is inactive and shows a loading indicator; when the result set is empty, the button is inactive.
10. For an export of up to 10,000 rows the file is generated in ≤ 10 seconds.
