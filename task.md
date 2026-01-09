# Task: Align dashboard auth model with separate profiles and core data tables

## Context / Intent
- `profiles` = dashboard access control only (may include supervisors with no sales data).
- Core data tables stay as-is: `users`, `transactions`, `monthly_stats` all mapped to `users`.
- A `profile` may link to a `user` via `user_id` (or email-based mapping), but the sets are not identical (some profiles have no user row; some users have no profile).
- Profile roles default from linked `users.role` when mapped; otherwise set manually on approval.

## Plan (high level)
1) Schema design
   - Add/confirm `profiles.user_id` nullable FK to `users.id`.
   - Ensure `users/transactions/monthly_stats` remain unchanged and keep FK to `users`.
   - Define how to derive `profiles.role` (from mapped user or manual).
2) RLS/auth changes
   - RLS on `profiles` for dashboard access; base permissions on `auth.uid()` + `profiles`.
   - Keep data RLS tied to `users` table (not `profiles`), with admin override rules.
   - Document edge cases: profiles without users; users without profiles.
3) App flow updates
   - Adjust login/signup to work with profiles-only access; approval sets profile role/status.
   - Mapping flow: when approving a profile, allow linking to existing `users` by email/id.
   - UI cues for unmapped profiles vs mapped ones; role assignment rules.
4) Migration/docs
   - Update specs to reflect the split responsibility (profiles vs users).
   - Provide SQL for new/changed columns/indexes and RLS examples.
   - Test checklist for both mapped and unmapped scenarios.

## Open questions
- Should unmapped profiles be restricted from viewing any data, or allowed admin-only dashboards?
- How to handle profile role overrides when linked user.role differs?
- Need background sync (by email) from `users` to suggest mappings?***
