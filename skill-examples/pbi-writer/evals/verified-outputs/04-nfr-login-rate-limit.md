### Title
Limit the number of login attempts on `POST /auth/login` to protect against password brute-forcing

### Description
The Q3 pentest (finding F-04, Medium) showed that the endpoint does not limit login attempts: ~40,000 brute-force attempts were made for a single account over 10 minutes without a lock and without an alert. In Auth Service, introduce a per-account limit (5 failed attempts within a sliding 15 minutes → lock for 15 minutes) and a per-IP limit (30 attempts per minute), identical responses to a wrong login and a wrong password, counters in Redis with TTL (fail-open when Redis is unavailable), logging of locks with an alert, and an admin endpoint for early unlocking. The finding is considered closed if a repeated pentest cannot make more than 5 attempts per account within 15 minutes.
Out of scope: CAPTCHA, MFA, locking by device fingerprint.

### AC
1. Given 5 consecutive failed login attempts for one account within a 15-minute window, Then the account is locked for 15 minutes.
2. Given the account is locked, When a login arrives (including with the correct password), Then the response is `429` with a `Retry-After` header in seconds.
3. Given a successful login, Then the account's failed-attempt counter is reset.
4. Given more than 30 login attempts from a single IP per minute (any accounts), Then requests over the limit get a `429` response with `Retry-After`.
5. Responses for a non-existent login and for a wrong password are identical: `401`, the same body, comparable response time.
6. Counters are stored in Redis with a TTL equal to the window; Given Redis is unavailable, Then login keeps working (fail-open), an ERROR-level event is written and the metric `auth_ratelimit_backend_errors_total` grows.
7. Every account lock is logged as `ACCOUNT_LOCKED` without the password and with the IP hash.
8. Given more than 20 account locks within 5 minutes, Then an alert is sent to the #security-alerts channel.
9. When `security_admin` calls `DELETE /admin/auth/locks/{userId}`, Then the lock is removed early; access is denied for other roles `[clarify: response code for non-security_admin]`.
10. A repeated pentest cannot make more than 5 attempts per account within 15 minutes.
