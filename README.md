# RT Commission Dashboard

**Sales & Commission Dashboard**

A high-performance, Python-based commission tracking dashboard built with **NiceGUI**.

## 🚀 Features
- **Admin Panel**: User management, Contract approval, Financial oversight.
- **Affiliate Capability**: Infinite-level Tree View, Link generation, Commission tracking.
- **Performance**: Realtime updates, instant page loads (SPA).
- **Backend Agnostic**:
    - **Phase 1**: Local SQLite (Zero-setup).
    - **Phase 2**: Supabase (Production).

## 🛠️ Installation

```bash
# Install with uv (recommended)
uv sync

# Run the dashboard
uv run rt-commission-dashboard --ui
```

## ⚙️ Configuration

The dashboard is fully configurable via `config.yaml` in the project root. You can customize:

### Workspace Settings
```yaml
workspace:
  name: "RT Commission Dashboard"  # Application title
  company: "RealTime"              # Company name
  domain: "rt.local"               # Email domain for mock data
```

### Commission Settings
```yaml
commission:
  rates:
    level_1: 0.10  # 10% for direct upline
    level_2: 0.05  # 5% for second level upline  
    level_3: 0.02  # 2% for third level upline
  max_levels: 5    # Maximum commission hierarchy levels
```

### Database & App Settings
```yaml
database:
  filename: "rt_commission_dashboard.db"  # Database filename

app:
  title: "RT Commission Dashboard"        # App title
  port: 8000                             # Default port
  secret_key: "rt_dashboard_secret_key_123"
```

### User Roles & Permissions
```yaml
roles:
  admin:
    label: "Administrator"
    permissions: ["Q1", "Q2", "Q3", "Q4"]
  affiliate:
    label: "Affiliate"  
    permissions: ["Q1", "Q2", "Q3", "Q4"]
  ctv:
    label: "Collaborator"
    permissions: ["Q1", "Q2"]
```

## 💰 **Financial Mechanics**
The system implements a configurable **Multi-Tier Automatic Commission** structure triggered by `retail_sales`.

### Volume-Based Commission Tiers
Commission rates are determined by **Total Monthly Sales** (Personal + F1).

| Monthly Sales | Rate |
| :--- | :--- |
| > 0 | **20%** |
| > 200M | **22%** |
| > 400M | **25%** |
| > 1B | **30%** |
| > 2B | **35%** |

### Differential Bonus (Stateful)
The system uses a **Stateful Monthly Recalculation** model.
-   **Step 1**: Every `retail_sales` transaction triggers a recalculation of the user's monthly volume and tier.
-   **Step 2**: The update propagates up the upline.
-   **Step 3**: Upline earns the **Differential** between their Tier Rate and the Downline's Tier Rate.
-   *Benefit*: Ensures "End-of-Month" consistency in real-time. If a user ranks up late in the month, their commission for the entire month is adjusted.

*Note: Commission rates can be customized in `config.yaml`*

### Shared Opportunity
*   **Mechanism**: A sale can be shared between two users (the "Sharer" who brings the opportunity and the "Receiver" who executes the sale).
*   **Volume for Tier Ranking**: The **FULL sales amount** counts toward the **Sharer's** tier ranking. The Receiver gets **0% volume credit** for tier ranking.
*   **Commission Split**: Both parties earn commission on **50% of the sale value** using their respective tier rates.
    *   **Sharer**: Commission = (Sharer's Tier Rate) × 50% × Sale Amount
    *   **Receiver**: Commission = (Receiver's Tier Rate) × 50% × Sale Amount

### Inactive User Policy
*   **Definition**: Users with **0 Personal Sales** in the current month.
*   **Rate**: They earn a fixed **4%** commission on sales (and 4% receive/share rate) instead of the standard tier rates.
*   **Motivation**: Encourages active selling to unlock higher tier rates (20%+).

### Transaction Types
*   **Retail Revenue**: Direct sales (Count towards Personal Revenue).
*   **Commission**: Passive income (Count towards Total Income).
*   **Rewards**: KPI Bonuses (Manual/Periodical).

## 📚 Data & Development
*   **[instruction.md](instruction.md)**: Guide on how to populate users and create transactions.
*   **[spec/dashboard_spec.md](spec/dashboard_spec.md)**: Full architecture and requirements.
*   **[test_scenario.md](test_scenario.md)**: Current testing hierarchy and edge cases.

## 📖 Documentation
See [spec/dashboard_spec.md](spec/dashboard_spec.md) for detailed requirements and architecture.
