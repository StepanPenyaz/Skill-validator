### Title
Switch to soft deletion of users in the `users` table with the ability to restore within 30 days

### Description
Physical `DELETE FROM users` cascades and destroys related records in `audit_events` and `orders` and does not allow restoring an account at the customer's request (policy — 30 days); Legal requires keeping the fact that the account existed. Solution: add the columns `deleted_at` (TIMESTAMPTZ) and `deleted_by` (UUID, FK to `users.id`) to `users`, a partial index on active records, and replace the uniqueness of `email` with a partial one (`WHERE deleted_at IS NULL`). `UserRepository.delete()` sets `deleted_at`/`deleted_by` instead of deleting the row; reads exclude deleted users by default; the admin API gets `includeDeleted=true` and the endpoint `POST /admin/users/{id}/restore`. A daily job physically deletes records older than 30 days while anonymizing traces in `audit_events`. Three places in the billing-reports module that bypass the repository must be moved to it.

### AC
1. The migration adds `users.deleted_at` and `users.deleted_by`, creates the index `idx_users_active` (`WHERE deleted_at IS NULL`) via `CREATE INDEX CONCURRENTLY`; all existing rows have `deleted_at IS NULL`.
2. The migration runs without blocking writes and takes no more than 5 minutes in prod; a verified rollback script exists for it.
3. Given a user is deleted, When a new user with the same e-mail is created, Then creation succeeds (uniqueness applies only among `deleted_at IS NULL`).
4. When `UserRepository.delete()` is called, Then the row remains in the table, `deleted_at = now()`, `deleted_by` = ID of the initiator, and related records in `audit_events` and `orders` are not affected.
5. `findById`, `findByEmail` and `list` do not return deleted users; the admin API returns them with `includeDeleted=true`.
6. Given a deleted user, When they try to log in, Then the `401` response is identical to the response for a wrong password.
7. When an admin calls `POST /admin/users/{id}/restore` for a deleted user, Then `deleted_at` and `deleted_by` become NULL; if the e-mail is already taken by an active user — response `409`, the state does not change.
8. The daily job at 03:00 UTC physically deletes users with `deleted_at` older than 30 days; a record remains in `audit_events` with the preserved `user_id` and `email`/`name` = NULL.
9. The three places in the billing-reports module that accessed `users` bypassing the repository use `UserRepository` and do not return deleted users.
