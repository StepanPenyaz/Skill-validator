# pbi-writer 1.0.0 — outputs (opus)

## 01-api-order-cancel.md

### Title
Add an order cancellation endpoint for the customer in Order Service v2

### Description
Today a customer can cancel an order only through support, which takes on average 14 hours, generates ~9% of support inquiries and delays refunds until after shipment. We add `POST /api/v2/orders/{orderId}/cancel` (Bearer JWT, role `customer`, own orders only; missing/invalid token returns `401`) so the customer can cancel the order themselves.

- Request body: `reason` (required enum: `CHANGED_MIND`, `FOUND_CHEAPER`, `DELIVERY_TOO_LONG`, `OTHER`) and optional `comment` (up to 500 characters).
- Cancellation is allowed only in statuses `NEW`, `PAID`, `PACKING`; forbidden in `SHIPPED`, `DELIVERED`, `CANCELLED` (a repeated call on an already cancelled order is idempotent and returns `200`).
- For `PAID`/`PACKING` a full refund is initiated via Payment Service (`RefundRequested` event); stock reservations are released synchronously in the same transaction.
- Success body: `{ "orderId", "status": "CANCELLED", "cancelledAt" (ISO-8601 UTC), "refundStatus": "NONE | PENDING" }`.

Out of scope: partial cancellation of order items and the mobile app interface.

### AC
1. Given a customer's own order in status `NEW`, `PAID` or `PACKING`, when the customer calls `POST /api/v2/orders/{orderId}/cancel` with a valid `reason`, then the response is `200` with `status` = `CANCELLED` and `cancelledAt` in ISO-8601 UTC.
2. Given an order in status `PAID` or `PACKING`, when it is cancelled, then a `RefundRequested` event is sent to Payment Service and the response has `refundStatus` = `PENDING`.
3. Given an order with stock reservations, when it is cancelled, then the reservations are released within the same transaction as the status change.
4. Given an order already in status `CANCELLED`, when the cancel endpoint is called again, then the response is `200` with the current order state.
5. Given an order in status `SHIPPED` or `DELIVERED`, when the customer calls the cancel endpoint, then the response is `409`.
6. Given a request body without `reason`, with an unknown `reason` value, or with `comment` longer than 500 characters, when the endpoint is called, then the response is `400`.
7. Given an order that belongs to another customer, when the customer calls the cancel endpoint, then the response is `403`.
8. Given a non-existent `orderId`, when the cancel endpoint is called, then the response is `404`.
9. The p95 response time of the cancel endpoint is ≤ 300 ms.
10. Given a successful cancellation, when the audit log is checked, then it contains an entry with who cancelled, when, the reason and the previous status.

## 02-db-soft-delete.md

### Title
Switch user deletion in Identity DB to soft delete with restore and 30-day cleanup

### Description
Users are currently removed with `DELETE FROM users`; cascades wipe related `audit_events` and `orders`, an account cannot be restored within the 30 days required by company policy, and Legal needs the fact of the account's existence kept for audit. We switch to soft deletion in PostgreSQL 15:

- Schema: new columns `deleted_at TIMESTAMPTZ NULL`, `deleted_by UUID NULL REFERENCES users(id)`, index `idx_users_active` (`WHERE deleted_at IS NULL`); the unique index on `email` becomes partial `UNIQUE (email) WHERE deleted_at IS NULL`.
- `UserRepository.delete()` sets `deleted_at = now()` and `deleted_by` instead of deleting the row; `findById`, `findByEmail`, `list` exclude deleted rows by default, the admin API gets `includeDeleted=true`. The 3 queries in the billing-reports module that bypass the repository are moved to it.
- Login of a deleted user returns `401` exactly like a wrong password; new admin endpoint `POST /admin/users/{id}/restore` restores the user.
- A daily job at 03:00 UTC physically deletes users with `deleted_at` older than 30 days, leaving an anonymized record in `audit_events`.
- Migration keeps existing rows (`deleted_at` = NULL), uses `CREATE INDEX CONCURRENTLY` and ships with a rollback script.

### AC
1. Given an active user, when `UserRepository.delete()` is called, then the row remains in `users` with `deleted_at` = current time and `deleted_by` set to the deleting user's id.
2. Given a soft-deleted user, when any read path runs (`findById`, `findByEmail`, `list`, the moved billing-reports queries), then the user is not returned.
3. Given a soft-deleted user, when the admin API is called with `includeDeleted=true`, then the user is returned.
4. Given a soft-deleted user, when they log in with their correct password, then the response is `401` identical to the wrong-password response.
5. Given a soft-deleted user with e-mail X, when a new user is created with e-mail X, then creation succeeds.
6. Given a soft-deleted user whose e-mail is not used by an active user, when `POST /admin/users/{id}/restore` is called, then `deleted_at` and `deleted_by` are NULL.
7. Given a soft-deleted user whose e-mail is taken by an active user, when `POST /admin/users/{id}/restore` is called, then the response is `409`.
8. Given a user with `deleted_at` older than 30 days, when the daily 03:00 UTC job runs, then the user row is physically deleted and its `audit_events` records keep `user_id` with `email` and `name` set to NULL.
9. The migration runs on prod without blocking writes to `users` (`CREATE INDEX CONCURRENTLY`) in ≤ 5 minutes.
10. Given the migration has been applied, when the rollback script is executed, then the schema returns to its pre-migration state.

### Open questions
- Physical deletion after 30 days: what happens to the user's `orders` rows, given that the current cascades are the reason orders get lost?
- `deleted_by` references `users(id)`: what should happen to it when the admin who performed the deletion is later physically deleted by the cleanup job?

## 03-ui-report-export.md

### Title
Add filters, sorting and pagination to the Transactions Report page

### Description
Analysts currently get transaction data via SQL queries against the replica, which is unsafe and requires developer help, while `/reports/transactions` shows only the last 100 transactions without filters. We add a filter panel above the table for roles `finance_analyst` and `finance_admin`:

- **Period** — required date range, default last 7 days, maximum 92 days.
- **Status** — multi-select `Completed`, `Pending`, `Failed`, `Refunded`, all selected by default.
- **Amount** — "from"/"to" numbers with 2 decimal places.
- **Currency** — optional dropdown (EUR, USD, PLN, GBP).

"Apply" and "Reset" buttons; filters are stored in URL query parameters so a link can be shared. The table gets 50-row pagination, sorting by "Date" (default, descending) and "Amount", and a total count of found records.

Out of scope: saving filter presets.

### AC
1. Given the page is opened without query parameters, when it loads, then Period is the last 7 days and all four statuses are selected.
2. Given a Period longer than 92 days is selected, when the range is set, then the error "Period cannot exceed 92 days" is shown.
3. Given a Period longer than 92 days is selected, when the range is set, then the "Apply" button is disabled.
4. Given Amount "from" is greater than "to", when the values are entered, then an error is shown at the "to" field.
5. Given a link containing filter query parameters, when another user opens it, then the page shows the same filter values and results.
6. Given changed filters, when "Reset" is clicked, then all filters return to their default values.
7. Given more than 50 matching records, when the table is shown, then it displays 50 rows per page with pagination.
8. Given the page is opened, when the table loads, then it is sorted by "Date" descending.
9. Given the table is shown, when the user clicks the "Amount" column header, then rows are sorted by amount.
10. Given filters are applied, when results load, then the total number of found records is shown above the table.

---

### Title
Add CSV export of filtered transactions on the Transactions Report page

### Description
To replace unsafe SQL exports from the replica, analysts need to download the transactions they see in the report. We add an "Export to CSV" button on `/reports/transactions` for roles `finance_analyst` and `finance_admin` that exports **all** records matching the current filters (not only the current page).

- Format: UTF-8 with BOM, delimiter `;`, dates in ISO-8601, amounts with a dot as decimal separator; file name `transactions_{from}_{to}.csv`.
- Limit 100,000 rows; above it the message "More than 100,000 records found, refine the filters" is shown and no file is generated.
- During generation the button is inactive with a loading indicator; for up to 10,000 rows generation takes ≤ 10 seconds. The button is inactive when the result set is empty.

Out of scope: XLSX export, scheduled exports.

### AC
1. Given a user with role `finance_analyst` or `finance_admin`, when they open the page, then the "Export to CSV" button is visible.
2. Given filters matching more records than fit on one page, when the user exports, then the file contains all matching records.
3. Given an export, when the file is opened, then it is encoded in UTF-8 with BOM.
4. Given an export, when the file is opened, then columns are separated by `;`.
5. Given an export, when the file is opened, then dates are in ISO-8601 and amounts use a dot as the decimal separator.
6. Given a Period from `{from}` to `{to}`, when the export finishes, then the file is named `transactions_{from}_{to}.csv`.
7. Given more than 100,000 matching records, when the user clicks export, then the message "More than 100,000 records found, refine the filters" is shown and no file is generated.
8. Given an export is in progress, when the file is being generated, then the button is inactive and shows a loading indicator.
9. Given up to 10,000 matching records, when the user exports, then the file is generated in ≤ 10 seconds.
10. Given the current filters return no records, when the page is shown, then the export button is inactive.

### Open questions
- Which columns (and in what order) must the CSV contain?
- In which format and time zone are `{from}`/`{to}` in the file name and the ISO-8601 dates in the file?

Split into two PBIs because filters/table and CSV export are independently deliverable features on the same page.

## 04-nfr-login-rate-limit.md

### Title
Add per-account and per-IP rate limiting to the POST /auth/login endpoint

### Description
The Q3 pentest (finding F-04, Medium, requirement SR-017) showed that `POST /auth/login` in Auth Service has no attempt limit: ~40,000 brute-force attempts on one account in 10 minutes were neither blocked nor alerted. We add protection:

- **Per account:** 5 consecutive failed attempts within a sliding 15-minute window lock the account for 15 minutes (`429` with `Retry-After` in seconds, even with the correct password); a successful login resets the counter.
- **Per IP:** max 30 login attempts per minute from one IP (any accounts), otherwise `429` with `Retry-After`.
- **Uniform responses:** wrong login and wrong password return the same `401`, body and comparable response time.
- **Storage:** counters in Redis with TTL equal to the window; on Redis failure the service is fail-open, logs an ERROR event and increments `auth_ratelimit_backend_errors_total`.
- **Observability:** each lock is logged as `ACCOUNT_LOCKED` (no password, IP hash); more than 20 locks in 5 minutes fire an alert to #security-alerts.
- **Unlock:** `security_admin` can remove a lock via `DELETE /admin/auth/locks/{userId}`.

F-04 is closed when a repeated pentest cannot make more than 5 attempts per account within 15 minutes. Out of scope: CAPTCHA, MFA, device-fingerprint locking.

### AC
1. Given 5 consecutive failed login attempts for an account within 15 minutes, when a 6th login with the correct password is sent within the next 15 minutes, then the response is `429` with a `Retry-After` header in seconds.
2. Given 4 failed attempts followed by a successful login, when one more failed attempt is made, then the account is not locked.
3. Given 30 login attempts from one IP within a minute, when a 31st attempt is sent in the same minute, then the response is `429` with a `Retry-After` header.
4. Given a non-existent login and an existing login with a wrong password, when both are submitted, then both responses are `401` with an identical body.
5. Given a non-existent login and an existing login with a wrong password, when both are submitted, then their response times differ by no more than [clarify: acceptable time difference].
6. Given Redis is unavailable, when a user logs in with valid credentials, then the login succeeds.
7. Given Redis is unavailable, when a login is processed, then an ERROR-level event is written and `auth_ratelimit_backend_errors_total` is incremented.
8. Given an account gets locked, when the logs are checked, then an `ACCOUNT_LOCKED` event exists with the IP hash and without the password.
9. Given more than 20 accounts are locked within 5 minutes, when the threshold is exceeded, then an alert is sent to #security-alerts.
10. Given a locked account, when a user with role `security_admin` calls `DELETE /admin/auth/locks/{userId}`, then the next login with the correct password succeeds.

### Open questions
- R3 requires a "comparable response time" but gives no threshold — what maximum difference is acceptable?
- Should failed-attempt counting and the `429` lock also apply to non-existent logins? Otherwise a `429` after 5 attempts reveals that the account exists, contradicting R3.
- In fail-open mode during a Redis outage attempts are unlimited — is that acceptable against the F-04 closing criterion?

## 05-integration-payment-webhooks.md

### Title
Receive PayGate payment webhooks in Order Service instead of status polling

### Description
Order Service polls PayGate every 60 seconds for each pending payment; with ~2,000 pending payments at peak this loads both sides and delays order confirmation by up to a minute. We switch to PayGate push notifications via the public endpoint `POST /integrations/paygate/webhook`.

- **Verification:** HMAC-SHA256 over the raw body in `X-PayGate-Signature` (hex) — missing/invalid → `401`, not processed; `X-PayGate-Timestamp` older than 5 minutes → `400`. The shared secret lives in the secrets manager and is rotatable without downtime (two active secrets).
- **Processing:** events `payment.succeeded`, `payment.failed`, `payment.refunded` are validated, stored in an inbox table and acknowledged with `200` in under 2 seconds; other types get `200` and are logged at DEBUG. Duplicate `eventId` (kept 7 days) is acknowledged without state change; an older event (by `occurredAt`) must not overwrite newer state. Business processing (order status update, publishing `OrderPaid` / `OrderPaymentFailed`) runs asynchronously from the inbox.
- **Failures:** temporary DB failure returns `5xx` (PayGate retries for 24 hours); inbox processing is retried 5 times (1 min, 5 min, 15 min, 1 h, 6 h), then moves to dead-letter with an alert.
- **Monitoring:** `paygate_webhook_received_total{type,result}`, `paygate_inbox_lag_seconds`, `paygate_inbox_dead_letter_total`.
- Polling stays behind the feature flag `paygate.polling.enabled` and is disabled after one week of stable webhook operation.

Out of scope: removing the polling code.

### AC
1. Given a correctly signed `payment.succeeded` request with a fresh timestamp, when it hits the webhook endpoint, then the event is stored in the inbox table and `200` is returned in under 2 seconds.
2. Given a request with a missing or invalid `X-PayGate-Signature`, when it hits the endpoint, then the response is `401` and nothing is stored in the inbox.
3. Given a correctly signed request with `X-PayGate-Timestamp` older than 5 minutes, when it hits the endpoint, then the response is `400`.
4. Given a correctly signed request with an event type other than the three handled ones, when it hits the endpoint, then the response is `200` and the event is only logged at DEBUG.
5. Given an `eventId` already processed within the last 7 days, when the same event arrives again, then the response is `200` and the order state does not change.
6. Given an order state set by an event with a newer `occurredAt`, when an event with an older `occurredAt` is processed, then the order state is not overwritten.
7. Given a stored `payment.succeeded` inbox record, when asynchronous processing completes, then the order status is updated and `OrderPaid` is published.
8. Given the database is temporarily unavailable, when a valid webhook arrives, then the endpoint returns a `5xx` response.
9. Given an inbox record whose processing fails 5 times (after 1 min, 5 min, 15 min, 1 h, 6 h retries), when the last retry fails, then the record moves to dead-letter status and an alert is fired.
10. Given two active secrets during rotation, when requests signed with either secret arrive, then both pass signature verification.

### Open questions
- Is `X-PayGate-Timestamp` covered by the HMAC signature? If not, the 5-minute replay check can be bypassed by altering the header; also, how should a request without this header be handled?
- What business effect should `payment.refunded` have (order status, published event)? The document names only `OrderPaid` and `OrderPaymentFailed`.
