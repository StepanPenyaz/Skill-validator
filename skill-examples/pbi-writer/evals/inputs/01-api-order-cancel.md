# API Spec: Order cancellation by the customer

**Service:** Order Service v2 · **Author:** Backend team · **Status:** Approved

## 1. Problem
Currently a customer can cancel an order only by contacting support (on average 14 hours until it is processed). This results in ~9% of inquiries being about "cancellation" and in refunds that start only after shipment.

## 2. Endpoint
`POST /api/v2/orders/{orderId}/cancel`

**Authorization:** Bearer JWT, role `customer`. A customer can cancel only their own orders.

**Request body (JSON):**
| Field | Type | Required | Description |
|---|---|---|---|
| `reason` | string (enum) | yes | `CHANGED_MIND`, `FOUND_CHEAPER`, `DELIVERY_TOO_LONG`, `OTHER` |
| `comment` | string (up to 500 characters) | no | Free-form comment |

## 3. Business rules
- Cancellation is allowed only in statuses `NEW`, `PAID`, `PACKING`.
- In statuses `SHIPPED`, `DELIVERED`, `CANCELLED` cancellation is forbidden.
- When cancelling an order in status `PAID` or `PACKING`, a full refund is initiated via Payment Service (event `RefundRequested`).
- Stock reservations in the warehouse are released synchronously within the same transaction.
- The operation is idempotent: a repeated call for an already cancelled order returns `200` with the current state, not an error.

## 4. Responses
| Code | Condition |
|---|---|
| 200 | Order cancelled (or was already cancelled earlier) |
| 400 | Invalid request body (no `reason`, unknown value, `comment` > 500) |
| 401 | Missing/invalid token |
| 403 | Order belongs to another customer |
| 404 | Order not found |
| 409 | Order status does not allow cancellation |

Successful response body: `{ "orderId": "...", "status": "CANCELLED", "cancelledAt": "ISO-8601 UTC", "refundStatus": "NONE | PENDING" }`

## 5. Non-functional requirements
- p95 response time ≤ 300 ms.
- Every cancellation is written to the audit log (who, when, reason, previous status).

## 6. Out of scope
Partial cancellation of order items, mobile app interface (a separate task).
