# Design Doc: Soft delete for the `users` table

**Component:** Identity DB (PostgreSQL 15) · **Type:** migration + logic change

## Context
Currently a user is deleted with the command `DELETE FROM users`. Because of cascades, related records in `audit_events` and `orders` are lost, and it is impossible to restore an account at the customer's request (within 30 days per company policy). Legal requires keeping the fact that the account existed for audit purposes.

## Solution
Switch to "soft" deletion.

### Schema
```sql
ALTER TABLE users ADD COLUMN deleted_at TIMESTAMPTZ NULL;
ALTER TABLE users ADD COLUMN deleted_by UUID NULL REFERENCES users(id);
CREATE INDEX idx_users_active ON users (id) WHERE deleted_at IS NULL;
```
The unique index on `email` is replaced with a partial one: `UNIQUE (email) WHERE deleted_at IS NULL`, so that the e-mail of a deleted user can be reused.

### Application changes
- `UserRepository.delete()` sets `deleted_at = now()` and `deleted_by`, without deleting the row.
- All read queries (`findById`, `findByEmail`, `list`) exclude rows with `deleted_at IS NOT NULL` by default. For the admin API, the parameter `includeDeleted=true` is added.
- Login of a deleted user returns the same error as for a wrong password (`401`), so as not to reveal the fact that the account exists.
- The new admin endpoint `POST /admin/users/{id}/restore` resets `deleted_at` and `deleted_by` to NULL. Restoration is impossible if the e-mail is already taken by an active user (response `409`).

### Physical cleanup
A daily job (03:00 UTC) physically deletes users with `deleted_at` older than 30 days together with personal data; an anonymized record remains in `audit_events` (`user_id` is kept, `email` and `name` are replaced with `NULL`).

### Migration
- Existing data does not change, `deleted_at` for all current rows = NULL.
- The migration must run without blocking writes (`CREATE INDEX CONCURRENTLY`), expected time in prod ≤ 5 minutes.
- A rollback script is mandatory.

## Risks
Forgotten places where queries to `users` bypass the repository (3 places found in the billing-reports module) — they need to be moved to the repository.
