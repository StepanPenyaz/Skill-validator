### Title
Add a self-service order cancellation endpoint for customers in Order Service v2

### Description
Currently a customer can cancel an order only through support (on average 14 hours until it is processed), so ~9% of inquiries are about cancellation, and refunds start only after shipment. Implement `POST /api/v2/orders/{orderId}/cancel` for the role `customer` (Bearer JWT, own orders only). Request body: required `reason` (`CHANGED_MIND`, `FOUND_CHEAPER`, `DELIVERY_TOO_LONG`, `OTHER`) and optional `comment` (up to 500 characters). Cancellation is allowed in statuses `NEW`, `PAID`, `PACKING`; for `PAID`/`PACKING` a full refund is initiated via Payment Service (event `RefundRequested`), and stock reservations are released synchronously in the same transaction. The operation is idempotent.
Out of scope: partial cancellation of items, UI in the mobile app.

### AC
1. Given a customer's order in status `NEW`, `PAID` or `PACKING`, When the customer calls the endpoint with a valid `reason`, Then the response is `200` with the body `{orderId, status: "CANCELLED", cancelledAt (ISO-8601 UTC), refundStatus}`.
2. Given an order in status `PAID` or `PACKING`, When it is cancelled, Then the event `RefundRequested` for the full amount is published and `refundStatus = PENDING`; for status `NEW` `refundStatus = NONE`.
3. Given a successful cancellation, Then stock reservations are released in the same transaction as the status change.
4. Given an order in status `SHIPPED`, `DELIVERED` or `CANCELLED` (except a repeated call, see item 5), When cancellation is called, Then the response is `409` and the order state does not change.
5. Given an order is already cancelled, When a repeated call arrives, Then the response is `200` with the current order state, without a repeated refund and without releasing reservations again.
6. Given a request without `reason`, with an unknown `reason` value or with a `comment` longer than 500 characters, Then the response is `400`.
7. Given the token is missing or invalid — response `401`; Given the order belongs to another customer — `403`; Given the order does not exist — `404`.
8. Given any successful cancellation, Then the audit log records: user, time, reason and the previous order status.
9. p95 endpoint response time ≤ 300 ms.
