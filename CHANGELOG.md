# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.25] - 2026-01-22
### Fixed
- User filters on Dashboard/Reports now use NiceGUI defaults (no `emit-value/map-options`) with input filtering to prevent `'int' object is not subscriptable` errors when searching or selecting users.
- User avatar menu text now respects light theme colors so email and "Đăng Xuất" stay visible.

## [1.2.19] - 2026-01-12
### Added
- JWT token validation in layout decorator to catch expired tokens and redirect to login with proper message instead of showing 500 error.
- New "Dashboard Profiles" admin page to manage RealTimeX dashboard access (profiles table).
- Profile management interface for admins to view and edit user profiles (role, status, linked user).
- Inline editing for profiles with ability to update role, status, and user linkage.
- Profile approval workflow with proper tracking of approved_by and approved_at timestamps.

### Fixed
- Session expiration now properly redirects to login page with "Your session has expired" message instead of showing 500 error.
- JWT tokens are now validated on each page load to ensure they haven't expired.

## [1.2.0] - 2026-01-09
### Added
- Supabase auth-first flow with `profiles` tied to `auth.users`, approval gating on `status='approved'`, and external actor support (`actor_code`/`actor_name`, nullable `user_id`).
- Signup/login UI wired to Supabase (anon key only), with profile approval checks; settings/setup only collect URL + anon key.
- Auto monthly stats trigger/procedure adapted to UUID `user_id`/profiles.

### Changed
- RLS policies now require approved profiles; admins can see external-actor rows (null `user_id`).
- Spec rewritten for fresh Supabase setup (no legacy migrations), plus clear owner steps for auth/invite and RLS.

### Fixed
- Removed service-key prompts from UI; secrets stay server-side. Login no longer bypasses auth in the layout.

## [1.2.18] - 2026-01-10
### Changed
- Redesigned login page with tabbed interface: separate "Password" and "OTP Login" tabs for clearer UX.
- Password and OTP login methods now have dedicated, focused interfaces instead of showing all fields at once.

### Added
- 60-second cooldown timer on "Send OTP Code" button to prevent spam and match Supabase rate limits.
- Real-time countdown display showing "Resend in Xs..." during cooldown period.
- Button automatically re-enables after cooldown expires.

### Improved
- Better mobile experience with less clutter on small screens.
- Clearer user flow - users see one login method at a time.
- Visual feedback during OTP request cooldown.

## [1.2.17] - 2026-01-10
### Changed
- Simplified signup page to password-based registration only (removed OTP options from signup flow).
- OTP login is now exclusively available on the login page, keeping signup flow clean and straightforward.

### Added
- SUPABASE_OTP_SETUP.md documentation guide for configuring Supabase to send actual 6-digit OTP codes instead of magic links.

## [1.2.16] - 2026-01-10
### Fixed
- Supabase OTP/magic link emails now redirect to the correct port when using custom `--port` argument (e.g., port 8001) instead of defaulting to localhost:3000.
- Email redirect URL detection now uses: 1) APP_BASE_URL env var, 2) runtime request base URL, or 3) runtime port from command-line args.
- Post-signup messaging clarified to guide users through email confirmation and admin approval flow.

## [1.2.14] - 2026-01-10
### Added
- OTP-based login and registration alongside password auth using Supabase email OTP send/verify flows.
### Changed
- Login/Signup share a Supabase client helper and reuse approval/profile checks for OTP and password paths.
- Reload buttons on Dashboard and Reports now read “Reload” for consistency.

## [1.2.1] - 2026-01-09
### Changed
- Improved signup/login UX messaging: pending profiles and approval communicated explicitly; signup warns to confirm email (if enabled) and wait for approval.
- Login refuses access if profile is missing or not approved, with clear notifications.

## [1.2.2] - 2026-01-09
### Changed
- Supabase runtime no longer requires service key: handler can use anon key + user session JWT; service key remains only for owner/admin tasks.
- Pages pass the user’s Supabase JWT into the DB handler for RLS-aligned access.
- Seeding with service key is skipped in JWT-only mode to avoid schema mismatch.

## [1.2.13] - 2026-01-10
### Changed
- Removed dev hints from Login page; added user menu with logout in the header.

## [1.2.12] - 2026-01-10
### Fixed
- Supabase session now sets auth with an empty refresh token (and postgrest fallback) to avoid validation errors when only an access token is available.

## [1.2.11] - 2026-01-10
### Added
- Users table spec adds `username`; Admin > Users now shows upline as `Full Name <username/email>` and includes a reload button.
- Added reload buttons to Dashboard and Reports pages.
- App no longer auto-opens a browser window on start.
### Fixed
- Spec reflects new `username` column; minor cleanups.

## [1.2.10] - 2026-01-10
### Fixed
- Login profile fetch now tolerates empty/blocked responses (204/missing response) by treating the profile as pending instead of throwing.
- Spec updated: RLS policies now use helper functions to avoid recursion on `profiles` checks.

## [1.2.9] - 2026-01-10
### Changed
- Signup now sends users to a “check email” page with instructions; Supabase email confirmation redirect is set to the app login (via `APP_BASE_URL` or localhost fallback).
- Login error for invalid credentials now hints at email confirmation/approval.
- Added `/check-email` route/page to guide users post-signup.

## [1.2.8] - 2026-01-10
### Fixed
- Added Supabase connectivity check in the layout: if the project URL is unreachable, users are redirected to Setup with a clear message instead of hitting timeouts during login/data fetch.

## [1.2.7] - 2026-01-10
### Fixed
- Login/Signup now catch Supabase connect errors and redirect back to Setup with a clear message when the URL/anon key or network/proxy prevents reaching Supabase.

## [1.2.6] - 2026-01-10
### Fixed
- Login/Signup now redirect to Setup with a clear notice if Supabase URL/anon key are missing, avoiding timeouts when credentials aren’t entered yet.

## [1.2.5] - 2026-01-10
### Changed
- Login now captures the mapped data user (`profiles.user_id`) and uses it (or admin role) for data queries; role defaults from linked user when available.
- Dashboard, reports, affiliates pages gate data access on mapped data user id (unless admin) to align with profiles-as-access model.

## [1.2.4] - 2026-01-10
### Added
- Supabase spec now defines a `public.users` compatibility view mapped to `profiles` to keep current app queries working.

### Changed
- Clarified that inserts/approvals go through `profiles`; the `users` view is read-only and only for legacy reads.

## [1.2.3] - 2026-01-09
### Changed
- Supabase selection now requires only URL + anon key; service key is optional (owner/admin only).


## [1.1.0] - 2026-01-06

### Added
- **Phase 2: Supabase Backend**
  - Full PostgreSQL/Supabase integration with database triggers
  - Automatic commission calculation via PostgreSQL functions
  - Real-time commission updates on transaction insert/update
  - `get_commission_rate()` function for tier-based rates
  - `get_leg_commission_volume()` recursive function for downline volume calculation
  - `recalculate_monthly_stats()` function with automatic parent propagation
  - Database triggers: `on_transaction_insert` and `on_transaction_update`

- **TEXT User IDs**
  - Custom username format (e.g., `rta_vytran`, `rta_traphan`) instead of UUIDs
  - Human-readable and memorable user identifiers
  - Better for administrative tasks and support
  - Complete migration guide from UUID to TEXT IDs

- **Enhanced Test Data**
  - Realistic Vietnamese Dong (VND) amounts in millions
  - Multiple tier examples: 20%, 22%, 25%, 30%
  - Share-receive transaction examples demonstrating:
    - Same tier sharing (both 20% tier)
    - Different tier sharing (25% sharer, 22% receiver)
    - Tier upgrades from shared volume
  - 6 sample users across 3 hierarchical levels
  - 18 transactions spanning 3 months (Nov 2025 - Jan 2026)

- **Database Factory Pattern**
  - `get_db_handler()` factory function for seamless SQLite/Supabase switching
  - Environment-based configuration via DATABASE_TYPE
  - Same interface for both backends

### Changed
- Database schema updated to use TEXT for user IDs
- All foreign key references updated (parent_id, user_id, shared_with_id)
- Commission calculations moved from Python to PostgreSQL triggers
- Seeding data now includes millions VND amounts for realistic testing
- Updated all page imports to use factory pattern

### Fixed
- Share/receive volume calculation now correctly implemented:
  - Sharer gets 100% of volume for tier ranking
  - Receiver gets 0% for tier ranking
  - Both get 50% commission rate based on their respective tiers
- Missing `created_at` field in transaction queries (was causing commission errors)

### Documentation
- Added MIGRATION_TEXT_USERIDS.md - Complete migration guide for UUID → TEXT transition
- Added SUPABASE_SETUP.md - Step-by-step Supabase setup instructions
- Created verification scripts for tier rates and share-receive logic
- Added development scripts and documentation organization

### Technical
- Supabase Python client integration (v2.0.0+)
- PostgreSQL trigger system for automatic calculations
- Factory pattern for database abstraction
- Environment variable configuration with python-dotenv
- Organized project structure (scripts/, docs/, tests/ in .gitignore)

## [1.0.0] - 2025-01-06

### Added
- **Phase 1: SQLite Backend**
  - Complete commission tracking system with volume-based tier rates
  - Multi-tier differential bonus calculation with stateful monthly recalculation
  - Shared opportunity mechanism (sharer gets 100% tier credit, 50% commission split)
  - Inactive user policy (4% fixed rate for users with no personal sales)
  - Hierarchical affiliate network with infinite-level support

- **Dashboard Features**
  - KPI cards: Total Revenue, Total Commission, New Customers, Network Size
  - Commission breakdown: Direct, Shared Out, Received, Override
  - Interactive monthly sales trend charts with Plotly
  - Filterable by user, year, and month

- **Affiliate Network Visualization**
  - Interactive tree view of downline network
  - Role-based access control (admin/affiliate/ctv)
  - Nested hierarchy display

- **Reports & Transactions**
  - Comprehensive transaction history with search and filters
  - Type filtering: Retail, Share, Receive, Reward
  - Pagination and date formatting

- **User Management**
  - Admin-only user management interface
  - Role and permission system (Q1-Q4 permissions)
  - User hierarchy management

- **Internationalization**
  - Full bilingual support (English/Vietnamese)
  - Session-based language switching
  - Comprehensive translation coverage

- **Configuration System**
  - Fully configurable via `config.yaml`
  - Commission tier configuration
  - Role and permission customization
  - Workspace branding settings
  - Currency support (VND/USD)

- **Database**
  - SQLite backend with optimized schema
  - `users` table with self-referencing hierarchy
  - `transactions` table for all financial events
  - `monthly_stats` table for performance aggregation
  - Automatic mock data seeding for testing

### Technical
- Built with NiceGUI 1.4.0+ for reactive UI
- Plotly integration for interactive charts
- Pandas for data processing and reporting
- Configuration management with PyYAML
- Mock data generation with Faker
- Python 3.10+ support

### Documentation
- Complete README with installation and usage instructions
- Detailed architecture specification
- Database schema documentation
- Phase 2 Supabase migration guide
- Comprehensive inline code comments

### Known Limitations (Phase 1)
- SQLite database (single-user, file-based)
- Mock authentication (email only, no passwords)
- No real-time updates
- Local deployment only

### Coming Soon (Phase 2)
- Supabase/PostgreSQL backend for production scalability
- Real authentication with Supabase Auth
- Real-time dashboard updates
- Multi-user concurrent access
- Cloud deployment support

---

## [Unreleased]

### Planned for Phase 2
- [ ] Supabase backend integration
- [ ] Password-based authentication
- [ ] Real-time transaction updates
- [ ] Email notifications
- [ ] Advanced reporting and analytics
- [ ] Mobile-responsive UI improvements
