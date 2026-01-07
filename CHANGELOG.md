# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
