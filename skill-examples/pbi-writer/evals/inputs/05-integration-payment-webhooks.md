# Integration Design: Receiving payment webhooks from PayGate

**Owner:** Payments squad · **Consumer:** Order Service · **Status:** Draft v3

## Background
Order Service currently polls PayGate every 60 seconds for the status of each pending payment. With ~2,000 pending payments at peak this generates load on both sides and delays order confirmation by up to a minute. PayGate offers webhooks, so we will switch from polling to push notifications.

## Endpoint
`POST /integrations/paygate/webhook` (public, no user auth).

## Request verification
- PayGate signs each request with HMAC-SHA256 over the raw body using the shared secret; the signature is in the `X-PayGate-Signature` header (hex).
- Requests with a missing or invalid signature must be rejected with `401` and must not be processed.
- Requests with `X-PayGate-Timestamp` older than 5 minutes are rejected with `400` to prevent replay attacks.
- Secret is stored in the secrets manager, not in config files, and must be rotatable without downtime (two active secrets during rotation).

## Processing
- Handled event types: `payment.succeeded`, `payment.failed`, `payment.refunded`. Other types are acknowledged with `200` and ignored (logged at DEBUG).
- Each event has a unique `eventId`. Events must be processed **idempotently**: a duplicate `eventId` is acknowledged with `200` without changing state again. Processed IDs are kept for 7 days.
- The endpoint validates and persists the event to an inbox table, then responds `200` in under 2 seconds. Business processing (updating order status, publishing `OrderPaid` / `OrderPaymentFailed`) happens asynchronously from the inbox.
- Events may arrive out of order; an older event (by `occurredAt`) must not overwrite the state set by a newer one.

## Failure handling
- PayGate retries non-2xx responses for 24 hours with exponential backoff, so returning `5xx` on a temporary DB failure is the correct behaviour.
- If asynchronous processing of an inbox record fails, it is retried 5 times (1 min, 5 min, 15 min, 1 h, 6 h); after that it goes to a dead-letter status and an alert is fired.

## Migration plan
The polling job stays enabled behind the feature flag `paygate.polling.enabled` and is disabled after one week of stable webhook operation. Removing the polling code is out of scope.

## Monitoring
Metrics: `paygate_webhook_received_total{type,result}`, `paygate_inbox_lag_seconds`, `paygate_inbox_dead_letter_total`.
