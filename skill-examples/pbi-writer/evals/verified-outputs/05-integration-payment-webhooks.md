### Title
Receive PayGate payment status updates via webhooks instead of polling in Order Service

### Description
Order Service polls PayGate every 60 seconds for each pending payment (~2,000 at peak), which loads both systems and delays order confirmation by up to a minute. Implement a public endpoint `POST /integrations/paygate/webhook` that verifies the HMAC-SHA256 signature (`X-PayGate-Signature`) and timestamp freshness, persists `payment.succeeded`, `payment.failed` and `payment.refunded` events to an inbox table and responds `200` within 2 seconds. Order status updates and publication of `OrderPaid` / `OrderPaymentFailed` are processed asynchronously from the inbox, idempotently by `eventId` and safely against out-of-order delivery. The existing polling job stays behind the feature flag `paygate.polling.enabled` as a fallback.
Out of scope: removing the polling code.

### AC
1. Given a request with a missing or invalid `X-PayGate-Signature` (HMAC-SHA256 over the raw body), Then the response is `401` and the event is not processed.
2. Given `X-PayGate-Timestamp` older than 5 minutes, Then the response is `400` and the event is not processed.
3. The shared secret is read from the secrets manager, and during rotation two active secrets are accepted without downtime.
4. Given a valid `payment.succeeded`, `payment.failed` or `payment.refunded` event, Then it is saved to the inbox and the endpoint responds `200` in under 2 seconds.
5. Given any other event type, Then the response is `200`, the event is ignored and logged at DEBUG.
6. Given a duplicate `eventId` (retained for 7 days), Then the response is `200` and order state is not changed again.
7. Given an event with `occurredAt` older than the one already applied to the order, Then it does not overwrite the newer state.
8. Given a temporary DB failure while saving, Then the endpoint returns `5xx` so PayGate retries.
9. Given asynchronous processing of an inbox record fails, Then it is retried 5 times (1 min, 5 min, 15 min, 1 h, 6 h); after the last failure the record gets dead-letter status and an alert is fired.
10. Metrics `paygate_webhook_received_total{type,result}`, `paygate_inbox_lag_seconds` and `paygate_inbox_dead_letter_total` are exposed.
11. The polling job is controlled by the flag `paygate.polling.enabled` and continues to work when the flag is on.
