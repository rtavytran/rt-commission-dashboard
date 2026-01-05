# RT Commission Dashboard Specification

## 1. Context & Reference
- **Source Material**: 
    - `research_dashboard_options.md` (Requirements & Features)
    - `email-archiver` (Codebase Reference for Structure & NiceGUI implementation)
- **Goal (Destination)**: Creates a high-performance, Python-based Sales & Commission Dashboard with configurable workspace settings.
- **Base Architecture**: Python 3.9+, NiceGUI (UI), SQLite (Phase 1) -> Supabase (Phase 2).

## 2. Phased Implementation Strategy

### 🟢 Phase 1: Local SQLite (Immediate MVP)
**Objective**: Build a fully functional, visually complete dashboard that runs locally without external dependencies.
**Database**: SQLite (configurable filename, default: `rt_commission_dashboard.db`) - Ported directly from `email-archiver`'s robust `DBHandler`.

**Deliverables**:
1.  **Project Structure**: Cloned from `email-archiver` but tailored for Dashboarding.
2.  **UI/UX**:
    - "Premium" Dark Mode Layout (Sidebar, Header, Account Menu).
    - **Dashboard**: KPI Cards (Revenue, Members).
    - **Affiliate Tree**: Interactive tree view of downlines.
    - **Reports**: Data tables with filtering.
### 3. Data Models (SQLite)
    - `users` (id, name, role, parent_id, permissions)
    - `transactions` (id, user_id, amount, type, status)

## 3. Financial Logic & Commissions
### 1. Revenue Sources
*   **Retail Revenue**: Income generated from direct sales to customers. This is the primary source of volume.
    *   *Recorded as*: `type='retail_sales'`, `status='approved'`
*   **Commission Sharing**: Passive income earned from downline sales.
    *   *Recorded as*: `type='commission_sharing'`, `status='approved'|'paid'`
    *   *Trigger*: Automatic creation whenever a downline member makes a `retail_sales` transaction.
*   **KPI Rewards**: Bonuses for meeting performance targets.
    *   *Recorded as*: `type='kpi_reward'`

### 2. Commission Structure (Auto-Calculated)
The system automatically calculates and distributes commissions up to **5 levels** when a retail sale occurs.
*   **Level 1 (Direct Parent)**: **10%** of Sale Amount.
*   **Level 2 (Grandparent)**: **5%** of Sale Amount.
*   **Level 3**: **2%** of Sale Amount.
*   *Levels 4-5*: Currently 0% (Reserved for future).

### 3. Data Visibility
*   **Admins**: View **ALL** transaction data globally.
*   **Users**: View **ONLY** their own transactions (Sales, Commissions Received, Rewards).

## 3. Business Rules & Roles (from Issue #4891)
- **Roles**:
    - **CTV (Collaborator)**: Permissions Q1 (Recruit), Q2 (Share Opp).
    - **Agent (Đại lý)**: Permissions Q1, Q2, Q4 (Retail).
    - **Pro Agent (Đại lý chuyên nghiệp)**: Q1, Q2, Q3 (Receive Opp), Q4.
    - **Strategic Partner (Đối tác chiến lược)**: Q1-Q4 (Business/Individual variations).
- **Modules**: Admin, Agent, CTV, GGS.
- **Data Source**: `llm_all_log` (for future Phase 2 sync).

### 🔵 Phase 2: Supabase Migration (Production)
**Objective**: Connect the working UI to the real cloud backend.
**Database**: Supabase (PostgreSQL).

**Deliverables**:
1.  **Auth**: Replace local mock auth with Supabase Auth (Email/Password, Magic Link).
2.  **DB Handler**: Create `SupabaseHandler` to implementing the same interface as the SQLite `DBHandler` for seamless switching.
3.  **Realtime**: Enable realtime updates for Dashboard KPIs.

## 3. Technical Requirements
- **Language**: Python 3.10+
- **UI Framework**: NiceGUI
- **Charts**: Plotly (integrated with NiceGUI)
- **Data**: Pandas (for report generation)
- **Package Manager**: `uv` (recommended) or `pip`

## 4. Directory Structure
```
rt-commission-dashboard/
├── config.yaml          # Configuration file
├── data/
├── rt_commission_dashboard/     # Main Package
│   ├── core/            # Logic (DB, Auth, Calculation)
│   ├── ui/              # UI Components (Layout, Cards, Tables)
│   ├── pages/           # Page Definitions
│   └── main.py          # Entry Point
├── spec/                # Specifications & Research
├── tests/               # Tests
├── pyproject.toml       # Dependencies
└── README.md
```
