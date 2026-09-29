## 01-api-order-cancel.md

### Title
Add customer order cancellation endpoint

### Description
Customers currently can only cancel orders through support (averaging 14 hours to process), which generates ~9% of support inquiries. We will implement a POST endpoint that allows customers to cancel their own orders in statuses NEW, PAID, or PACKING with a required reason (CHANGED_MIND, FOUND_CHEAPER, DELIVERY_TOO_LONG, OTHER) and optional comment up to 500 characters. Cancellations trigger full refunds via Payment Service and release stock synchronously within the same transaction. The operation is idempotent to prevent errors on client retries.

Out of scope: partial cancellation of individual order items, mobile app interface.

### AC
1. Endpoint POST /api/v2/orders/{orderId}/cancel requires Bearer JWT token with customer role
2. Customer can only cancel their own orders; attempting to cancel another customer's order returns 403
3. Request body with missing/invalid reason or comment > 500 chars returns 400
4. Cancellation of orders in NEW, PAID, or PACKING status succeeds with 200
5. Cancellation of orders in SHIPPED, DELIVERED, or CANCELLED status returns 409
6. When cancelling PAID or PACKING order, RefundRequested event sent to Payment Service and stock released synchronously in same transaction
7. Repeated cancellation of already-cancelled order returns 200 with current state instead of error
8. Every cancellation written to audit log with who, when, reason, and previous status
9. P95 response time ≤ 300 ms
10. Successful response body includes orderId, status=CANCELLED, cancelledAt (ISO-8601 UTC), refundStatus (NONE|PENDING)

---

## 02-db-soft-delete.md

### Title
Implement soft delete for users table

### Description
Currently, deleting users with DELETE cascades to related records in audit_events and orders, losing data and preventing account restoration within the company's 30-day recovery policy. Legal requires maintaining the audit trail. We will implement soft deletion by adding deleted_at and deleted_by columns, updating all read queries to exclude soft-deleted users by default, adding an admin API parameter includeDeleted and restore endpoint, and scheduling daily cleanup of records older than 30 days.

Out of scope: None mentioned. Note: existing queries in billing-reports module (3 places found) bypass the repository and must be refactored as part of this change.

### AC
1. Schema: users table adds deleted_at (TIMESTAMPTZ NULL) and deleted_by (UUID NULL FK to users.id)
2. Index idx_users_active created on (id) WHERE deleted_at IS NULL
3. Email unique constraint becomes partial: UNIQUE (email) WHERE deleted_at IS NULL
4. UserRepository.delete() sets deleted_at=now() and deleted_by without deleting the row
5. Read queries (findById, findByEmail, list) exclude rows with deleted_at IS NOT NULL by default
6. Admin API supports includeDeleted=true parameter to retrieve soft-deleted users
7. Login attempt for deleted user returns 401 with same error response as wrong password, not revealing account existence
8. POST /admin/users/{id}/restore endpoint resets deleted_at and deleted_by to NULL
9. Restore fails with 409 if email is already taken by an active user
10. Daily job at 03:00 UTC physically deletes users with deleted_at > 30 days; audit_events anonymized with user_id kept, email and name replaced with NULL
11. Migration uses non-blocking index creation (CREATE INDEX CONCURRENTLY), expected runtime ≤ 5 minutes in production with rollback script provided

---

## 03-ui-report-export.md

### Title
Add filters and CSV export to transactions report page

### Description
Finance analysts currently export transaction data through unsafe SQL queries to the replica, requiring developer help. The transactions report displays only the last 100 transactions without filtering. We will add a filter panel with period, status, amount, and currency filters, implement 50-row pagination with sorting, and provide CSV export for all filtered records up to 100,000 rows in UTF-8 with BOM format.

Out of scope: XLSX export, filter presets, scheduled exports.

### AC
1. Period filter: date range picker, required, default last 7 days, maximum range 92 days; exceeding 92 days shows error "Period cannot exceed 92 days" and disables Apply button
2. Status filter: multi-select dropdown (Completed, Pending, Failed, Refunded), all selected by default
3. Amount filter: two numeric fields "from" and "to" with 2 decimal places; from > to shows error at "to" field
4. Currency filter: optional dropdown (EUR, USD, PLN, GBP)
5. Apply and Reset buttons; Reset returns all defaults; filters stored in URL query parameters for sharing
6. Table pagination: 50 rows per page, sortable by Date (default, descending) and Amount columns; total record count displayed above table
7. Export to CSV button visible only to finance_analyst and finance_admin roles
8. CSV export includes all records matching current filters (not just current page), up to 100,000 rows maximum
9. Export exceeding 100,000 rows shows error "More than 100,000 records found, refine the filters", file not generated
10. CSV format: UTF-8 with BOM, semicolon delimiter, ISO-8601 dates, dot decimal separator; filename transactions_{from}_{to}.csv
11. During export generation, button becomes inactive with loading indicator; generation time ≤ 10 seconds for up to 10,000 rows
12. Export button inactive when result set is empty

---

## 04-nfr-login-rate-limit.md

### Title
Add login rate limiting and account lockout protection

### Description
Pentest found that the login endpoint allows unlimited brute-force attempts (~40,000 in 10 minutes without blocking). We will implement per-account and per-IP rate limits with account lockout, uniform error responses to prevent account enumeration, and Redis-backed counters with fail-open behavior. Exceeding limits returns 429 with Retry-After header. All account locks are logged; mass locking events (>20 accounts in 5 minutes) trigger a security alert to #security-alerts.

Out of scope: CAPTCHA, MFA, locking by device fingerprint.

### AC
1. After 5 consecutive failed login attempts within sliding 15-minute window, account locked for 15 minutes
2. Login to locked account returns 429 Too Many Requests with Retry-After header in seconds, even with correct password
3. Successful login resets failed attempt counter for the account
4. Per-IP limit: maximum 30 login attempts per minute from single IP (any accounts); exceeding returns 429 with Retry-After
5. Wrong login and wrong password responses are identical (401, same body, comparable response time) to prevent account enumeration
6. Rate limit counters stored in Redis with TTL equal to the rate-limit window
7. Redis unavailability does not block login; service operates in fail-open mode, writes ERROR-level event, and increments auth_ratelimit_backend_errors_total metric
8. Every account lock logged as ACCOUNT_LOCKED event with IP hash and no password
9. Alert fires to #security-alerts when more than 20 accounts are locked within 5 minutes
10. Administrator with security_admin role can remove lock early via DELETE /admin/auth/locks/{userId}

### Open questions
- What is the exact format and content of the `Retry-After` header (seconds vs. RFC-1123 date)?

---

## 05-integration-payment-webhooks.md

### Title
Implement PayGate webhook integration for payment status updates

### Description
Order Service currently polls PayGate every 60 seconds for payment status on ~2,000 pending payments at peak, creating load on both sides and delaying order confirmation by up to 1 minute. PayGate offers webhooks. We will implement a webhook endpoint to receive payment events, verify signatures with HMAC-SHA256, process events idempotently with out-of-order delivery protection, and maintain polling behind a feature flag during transition period.

Out of scope: removing polling code after transition.

### AC
1. Endpoint POST /integrations/paygate/webhook (public, no user auth) receives PayGate payment events
2. Each request signed with HMAC-SHA256 over raw body; signature in X-PayGate-Signature header (hex); missing/invalid signature rejected with 401
3. X-PayGate-Timestamp older than 5 minutes rejected with 400 for replay attack prevention; shared secret stored in secrets manager and rotatable without downtime
4. Handled event types: payment.succeeded, payment.failed, payment.refunded; other types acknowledged with 200 and ignored (logged at DEBUG level)
5. Each event has unique eventId; duplicate eventId acknowledged with 200 without state change; processed IDs retained 7 days
6. Endpoint validates, persists event to inbox table, responds with 200 in under 2 seconds; async processing updates order status and publishes OrderPaid/OrderPaymentFailed events
7. Events processed idempotently; out-of-order events do not overwrite newer state (compared by occurredAt timestamp)
8. Temporary failure returns 5xx for PayGate retry; async processing retries 5 times (1 min, 5 min, 15 min, 1 hour, 6 hours), then dead-letter status with alert
9. Polling job remains enabled behind feature flag paygate.polling.enabled, disabled after one week of stable webhook operation
10. Metrics collected: paygate_webhook_received_total{type,result}, paygate_inbox_lag_seconds, paygate_inbox_dead_letter_total
