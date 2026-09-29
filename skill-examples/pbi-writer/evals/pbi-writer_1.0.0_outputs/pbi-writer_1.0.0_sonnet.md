## 01-api-order-cancel.md

### Title
Add an order cancellation endpoint for the customer in Order Service v2

### Description
Customers can currently cancel an order only through support, which takes about 14 hours on average, drives roughly 9% of inquiries and delays refunds until after shipment. We are adding `POST /api/v2/orders/{orderId}/cancel` (Bearer JWT, role `customer`, own orders only) that accepts `reason` (enum `CHANGED_MIND`, `FOUND_CHEAPER`, `DELIVERY_TOO_LONG`, `OTHER`, required) and `comment` (up to 500 characters, optional). Cancellation is allowed only in statuses `NEW`, `PAID`, `PACKING`. For `PAID` and `PACKING` a full refund is initiated through Payment Service (event `RefundRequested`), and warehouse stock reservations are released synchronously in the same transaction. The operation is idempotent. The successful response body is `{ "orderId", "status": "CANCELLED", "cancelledAt" (ISO-8601 UTC), "refundStatus": "NONE | PENDING" }`.
Out of scope: partial cancellation of order items and the mobile app interface (a separate task).

### AC
1. Given a customer's own order in status `NEW`, `PAID` or `PACKING` and a valid `reason`, when the customer calls `POST /api/v2/orders/{orderId}/cancel`, then the response is `200` with `orderId`, `status` = `CANCELLED`, `cancelledAt` (ISO-8601 UTC) and `refundStatus`.
2. Given an order in status `PAID` or `PACKING`, when it is cancelled, then a full refund is requested via Payment Service with the event `RefundRequested`.
3. Given a cancelled order, when the cancellation completes, then the stock reservations in the warehouse are already released within the same transaction.
4. Given an order that is already `CANCELLED`, when the cancel endpoint is called again, then the response is `200` with the current order state and not an error.
5. Given an order in status `SHIPPED` or `DELIVERED`, when the cancel endpoint is called, then the response is `409`.
6. Given a request body with no `reason`, an unknown `reason` value, or a `comment` longer than 500 characters, when the cancel endpoint is called, then the response is `400`.
7. Given a missing or invalid token, when the cancel endpoint is called, then the response is `401`.
8. Given an order that belongs to another customer, when the cancel endpoint is called, then the response is `403`.
9. Given an `orderId` that does not exist, when the cancel endpoint is called, then the response is `404`.
10. The p95 response time of the cancel endpoint is ≤ 300 ms, and every cancellation is written to the audit log with who, when, reason and previous status.

### Open questions
- The business rules list `CANCELLED` among the statuses where cancellation is forbidden, but the idempotency rule says a repeated call on a cancelled order returns `200`. Confirm that `200` applies to `CANCELLED` and that `409` applies only to `SHIPPED` and `DELIVERED`.
- Should a repeated (idempotent) call also write an audit log entry, or only the first cancellation?

## 02-db-soft-delete.md

### Title
Replace hard deletion of users with soft delete and 30-day restore in Identity DB

### Description
Currently `DELETE FROM users` loses related records in `audit_events` and `orders` through cascades, makes it impossible to restore an account at the customer's request within 30 days (company policy), and loses the fact that the account existed, which Legal requires for audit. We switch to soft deletion: add `users.deleted_at` (TIMESTAMPTZ NULL) and `users.deleted_by` (UUID NULL, FK to `users(id)`), a partial index `idx_users_active`, and replace the unique index on `email` with `UNIQUE (email) WHERE deleted_at IS NULL`. `UserRepository.delete()` sets `deleted_at = now()` and `deleted_by` without removing the row, read queries (`findById`, `findByEmail`, `list`) exclude deleted rows by default (admin API gets `includeDeleted=true`), a deleted user's login returns the same `401` as a wrong password, and a new endpoint `POST /admin/users/{id}/restore` undoes the deletion. A daily job at 03:00 UTC physically removes users deleted more than 30 days ago, keeping an anonymized `audit_events` record. The migration must not block writes, and the 3 places in the billing-reports module that query `users` bypassing the repository must be moved to it.

### AC
1. Given an active user, when `UserRepository.delete()` is called, then the row remains in `users` with `deleted_at` set to the current time and `deleted_by` set to the deleting user's id.
2. Given a deleted user, when `findById`, `findByEmail` or `list` is called, then the deleted user is not returned by default, and it is returned only in the admin API with `includeDeleted=true`.
3. Given a deleted user, when they try to log in, then the response is `401`, identical to the response for a wrong password.
4. Given a deleted user whose e-mail is not used by an active user, when an admin calls `POST /admin/users/{id}/restore`, then `deleted_at` and `deleted_by` are reset to NULL.
5. Given a deleted user whose e-mail is already taken by an active user, when an admin calls `POST /admin/users/{id}/restore`, then the response is `409` and the user stays deleted.
6. Given a deleted user, when a new user registers with the same e-mail, then the registration is not rejected by the unique constraint on `email`.
7. Given users with `deleted_at` older than 30 days, when the daily job runs at 03:00 UTC, then those users and their personal data are physically deleted and their `audit_events` records remain with `user_id` kept and `email` and `name` set to `NULL`.
8. The migration creates the index with `CREATE INDEX CONCURRENTLY`, does not block writes and completes in ≤ 5 minutes in prod, with `deleted_at` = NULL for all existing rows.
9. A rollback script for the migration exists and is verified to revert the schema change.
10. The 3 queries in the billing-reports module that access `users` directly go through `UserRepository`, so no query to `users` bypasses the soft-delete filter.

### Open questions
- `deleted_by` references `users(id)`: what happens to this reference (and to the cascades on `orders`) when the physical cleanup job removes a user, given that the goal is to keep `orders` and `audit_events` records?
- Restoration is described for "within 30 days", and the job removes users "older than 30 days". Should `/restore` explicitly reject users past 30 days that have not yet been cleaned up?

## 03-ui-report-export.md

### Title
Add filters and CSV export to the Transactions Report page

### Description
Analysts currently export data with SQL queries against the replica, which is unsafe and requires help from developers, and the page at `/reports/transactions` shows only the last 100 transactions without filters. We add a filter panel (Period, Status, Amount, Currency with "Apply" and "Reset" buttons, stored in URL query parameters), a paginated and sortable table, and an "Export to CSV" button for the roles `finance_analyst` and `finance_admin`. The export contains all records matching the current filters in UTF-8 with BOM, delimiter `;`, ISO-8601 dates, dot as decimal separator, file name `transactions_{from}_{to}.csv`, limited to 100,000 rows.
Out of scope: export to XLSX, saving filter presets, scheduled exports.

### AC
1. Given the page is opened or "Reset" is clicked, when the filter panel is shown, then Period is the last 7 days (required) and all four Status values (`Completed`, `Pending`, `Failed`, `Refunded`) are selected.
2. Given a Period longer than 92 days, when it is selected, then the error "Period cannot exceed 92 days" is shown and the "Apply" button is disabled.
3. Given Amount "from" is greater than "to", when the values are entered, then an error is shown at the "to" field.
4. Given applied filters, when the page URL is opened by another user, then the same filter values are restored from the URL query parameters.
5. The table shows 50 rows per page, is sorted by "Date" descending by default, can be sorted by "Amount", and shows the total number of found records above it.
6. Given a user with the role `finance_analyst` or `finance_admin`, when the page is opened, then the "Export to CSV" button is visible.
7. Given filters that match more than one page, when the user exports, then the CSV contains all matching records in UTF-8 with BOM, delimiter `;`, ISO-8601 dates, dot as decimal separator, named `transactions_{from}_{to}.csv`.
8. Given the filters match more than 100,000 records, when the user clicks export, then the message "More than 100,000 records found, refine the filters" is shown and no file is generated.
9. Given the export is in progress, then the button is inactive and shows a loading indicator, and for exports of up to 10,000 rows the file is generated in ≤ 10 seconds.
10. Given the filters return an empty result set, then the "Export to CSV" button is inactive.

### Open questions
- What date format should `{from}` and `{to}` in the file name use (ISO-8601 `YYYY-MM-DD` is assumed but not stated)?
- The Currency filter is optional; should the Amount filter and the exported amounts be interpreted across mixed currencies when no currency is selected?

## 04-nfr-login-rate-limit.md

### Title
Protect the login endpoint against brute force with per-account and per-IP limits

### Description
The pentest (finding F-04, Medium) made about 40,000 brute-force attempts on a single account within 10 minutes on `POST /auth/login` in Auth Service; none was blocked and none triggered an alert. We add a per-account lock (5 consecutive failed attempts within a sliding 15-minute window locks the account for 15 minutes), a per-IP limit (30 attempts per minute), uniform `401` responses for wrong login and wrong password, counters stored in Redis with a TTL equal to the window (fail-open when Redis is unavailable), logging and alerting for account locks, and an admin endpoint `DELETE /admin/auth/locks/{userId}` for the role `security_admin` to remove a lock early.
Out of scope at this stage: CAPTCHA, MFA, locking by device fingerprint.

### AC
1. Given 5 consecutive failed login attempts for one account within a sliding 15-minute window, then the account is locked for 15 minutes.
2. Given a locked account, when a login is attempted (even with the correct password), then the response is `429 Too Many Requests` with a `Retry-After` header in seconds.
3. Given an account with failed attempts, when a login succeeds, then its failed-attempt counter is reset.
4. Given more than 30 login attempts from one IP address within a minute (any accounts), when another attempt is made, then the response is `429` with a `Retry-After` header.
5. Given a wrong login and a wrong password, when each is submitted, then both return `401` with the same body and a comparable response time `[clarify: maximum allowed difference in response time]`.
6. Given Redis is unavailable, when a login is attempted, then login is not blocked (fail-open), an ERROR-level event is written and the metric `auth_ratelimit_backend_errors_total` is incremented.
7. Given an account lock, then an `ACCOUNT_LOCKED` event is logged without the password and with the IP hash.
8. Given more than 20 accounts locked within 5 minutes, then an alert is sent to the #security-alerts channel.
9. Given a locked account, when a user with the role `security_admin` calls `DELETE /admin/auth/locks/{userId}`, then the lock is removed before the 15 minutes expire.
10. A repeated pentest does not find the possibility of more than 5 attempts per account within 15 minutes (closing criterion for F-04).

### Open questions
- R3 requires that existing accounts cannot be enumerated, yet a locked account returns `429` while an unknown login returns `401`. Should attempts against non-existent logins also be counted and locked so the responses stay indistinguishable?
- How is "comparable response time" measured (maximum allowed difference)?
- Are the 5 attempts "consecutive failed" or any failed within the sliding window (a success resets the counter per R1)? Confirm the counting semantics.

## 05-integration-payment-webhooks.md

### Title
Receive PayGate payment webhooks in Order Service instead of polling

### Description
Order Service polls PayGate every 60 seconds for each pending payment (about 2,000 at peak), which loads both sides and delays order confirmation by up to a minute. We switch to push notifications with the public endpoint `POST /integrations/paygate/webhook`. Each request is verified by HMAC-SHA256 over the raw body (header `X-PayGate-Signature`, hex) and by `X-PayGate-Timestamp` (replay protection), with the secret kept in the secrets manager and rotatable without downtime. Events `payment.succeeded`, `payment.failed`, `payment.refunded` are validated, persisted to an inbox table with a `200` response, and processed asynchronously (order status update, publishing `OrderPaid` / `OrderPaymentFailed`), idempotently by `eventId` and in order by `occurredAt`. The polling job stays behind the feature flag `paygate.polling.enabled` and is disabled after one week of stable webhook operation; metrics `paygate_webhook_received_total{type,result}`, `paygate_inbox_lag_seconds` and `paygate_inbox_dead_letter_total` are exposed.
Out of scope: removing the polling code.

### AC
1. Given a request with a missing or invalid `X-PayGate-Signature`, when it is received, then the response is `401` and the event is not processed.
2. Given a request with `X-PayGate-Timestamp` older than 5 minutes, when it is received, then the response is `400`.
3. Given two secrets are active during rotation, when requests signed with either secret arrive, then both are accepted.
4. Given an event type other than `payment.succeeded`, `payment.failed`, `payment.refunded`, when it is received, then the response is `200`, the event is ignored and logged at DEBUG.
5. Given an `eventId` already processed (kept for 7 days), when the event is received again, then the response is `200` and the state is not changed again.
6. Given a valid event, when it is received, then it is persisted to the inbox table and `200` is returned in under 2 seconds.
7. Given an inbox record, when it is processed asynchronously, then the order status is updated and `OrderPaid` or `OrderPaymentFailed` is published.
8. Given an event with an older `occurredAt` than the one already applied, when it is processed, then it does not overwrite the state set by the newer event.
9. Given a temporary DB failure, when a webhook is received, then the endpoint returns `5xx`.
10. Given asynchronous processing of an inbox record fails, then it is retried 5 times (after 1 min, 5 min, 15 min, 1 h, 6 h) and after that goes to dead-letter status and an alert is fired.

### Open questions
- What should `payment.refunded` do in Order Service, and is any event published for it? Only `OrderPaid` and `OrderPaymentFailed` are named.
- While the polling job and webhooks both run (up to one week), how are conflicting updates to the same payment resolved?
