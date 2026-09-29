# Security Requirement SR-017: Protecting the login endpoint against password brute-forcing

**Source:** Q3 pentest results, finding F-04 (Medium) · **Component:** Auth Service · **Endpoint:** `POST /auth/login`

## Observation
The endpoint does not limit the number of login attempts. During the pentest, ~40,000 brute-force attempts were made for a single account over 10 minutes; none was blocked and none triggered an alert.

## Requirements

**R1. Per-account limit.** After 5 consecutive failed login attempts within a sliding 15-minute window, the account is locked for 15 minutes. While locked, the response to a login (even with the correct password) is `429 Too Many Requests` with a `Retry-After` header (in seconds). A successful login resets the counter.

**R2. Per-IP limit.** No more than 30 login attempts from a single IP address per minute (any accounts). Exceeding it → `429` with `Retry-After`.

**R3. Uniform responses.** The response to a wrong login and to a wrong password is identical (`401`, the same body, comparable response time), so that existing accounts cannot be enumerated.

**R4. Counter storage.** Counters are stored in Redis with a TTL equal to the window. Redis unavailability must not block login: the service operates in fail-open mode, but writes an ERROR-level event and increments the metric `auth_ratelimit_backend_errors_total`.

**R5. Logging and alerts.** Every account lock is logged as an `ACCOUNT_LOCKED` event (without the password, with the IP hash). If more than 20 accounts are locked within 5 minutes, an alert fires to the #security-alerts channel.

**R6. Unlocking.** An administrator with the role `security_admin` can remove a lock early via `DELETE /admin/auth/locks/{userId}`.

## Not required at this stage
CAPTCHA, MFA, locking by device fingerprint.

## Closing criterion for finding F-04
A repeated pentest must not find the possibility of more than 5 attempts per account within 15 minutes.
