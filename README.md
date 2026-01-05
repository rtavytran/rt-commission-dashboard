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

### Default Commission Rates (Configurable)
| Level | Role | Rate |
| :--- | :--- | :--- |
| **L1** | Direct Parent | **10%** |
| **L2** | Grandparent | **5%** |
| **L3** | Great-Grandparent | **2%** |

*Note: Commission rates can be customized in `config.yaml`*

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
