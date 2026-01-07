# RT Commission Dashboard

**Multi-tier Sales & Commission Tracking Dashboard**

A high-performance commission dashboard for managing affiliate networks with hierarchical commission structures. Built with **NiceGUI** and **Python**.

## 🚀 Features
- **Multi-tier Commission System**: Automatic commission calculation across unlimited hierarchy levels
- **Volume-based Tier Ranking**: Dynamic commission rates based on monthly sales performance
- **Admin Panel**: User management, financial oversight, and system settings
- **Affiliate Tools**: Network tree visualization, commission tracking, and shared sales
- **Dual Backend Support**:
  - **SQLite**: Zero-setup local database (default)
  - **Supabase**: Cloud PostgreSQL for production deployments
- **Bilingual**: Full support for English and Vietnamese (EN/VI)

## 🛠️ Installation & Usage

### Quick Start (Recommended)

Run directly with `uvx` (no installation needed):

```bash
# SQLite (local database)
uvx rt-commission-dashboard --ui --port 8000

# Supabase (cloud database)
uvx rt-commission-dashboard --ui --port 8000 \
  --db-type supabase \
  --supabase-url https://your-project.supabase.co \
  --supabase-anon-key your-anon-key \
  --supabase-service-key your-service-key
```

### For Development

```bash
# Clone and install
git clone https://github.com/rtavytran/rt-commission-dashboard.git
cd rt-commission-dashboard
uv sync

# Run locally
uv run rt-commission-dashboard --ui
```

## ⚙️ Configuration

### Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--port` | Port to run the dashboard | `8000` |
| `--ui` | Start the web UI | - |
| `--db-type` | Database type: `sqlite` or `supabase` | `sqlite` |
| `--supabase-url` | Supabase project URL | - |
| `--supabase-anon-key` | Supabase anonymous key | - |
| `--supabase-service-key` | Supabase service role key | - |

### Configuration File

Optional: Create `config.yaml` to customize workspace settings, commission tiers, and application behavior. See [config.yaml](config.yaml) for the full template.

### Admin Settings Page

Administrators can configure database settings through the web UI:
1. Login as admin (`admin@rt.local`)
2. Navigate to **Settings** in the admin menu
3. Configure Supabase credentials or switch database types

## 🔐 Default Login

The dashboard comes with a pre-configured admin account for testing:

- **Email**: `admin@rt.local`
- **Password**: Any password (authentication is simplified for Phase 1)

Access the dashboard at `http://localhost:8000` after starting the application.

## 💰 Financial Mechanics
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

## 📚 Documentation & Resources

- **[CHANGELOG.md](CHANGELOG.md)**: Version history and release notes
- **[spec/dashboard_spec.md](spec/dashboard_spec.md)**: Full architecture and system requirements
- **User Guides**:
  - [English Guide](docs/user-guide-en.md)
  - [Vietnamese Guide](docs/user-guide-vi.md)

## 🛠️ Development

### Setting Up Supabase (Optional)

If you want to use Supabase instead of SQLite:

1. Create a project at [supabase.com](https://supabase.com)
2. Get your project credentials from **Settings** → **API**
3. Run the SQL schema from `spec/supabase_schema.sql` in the SQL editor
4. Use the `--supabase-*` arguments when starting the dashboard

### Running Tests

```bash
uv run pytest tests/
```

## 📦 PyPI Package

Published on PyPI: [rt-commission-dashboard](https://pypi.org/project/rt-commission-dashboard/)

```bash
pip install rt-commission-dashboard
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋 Support

- **Issues**: [GitHub Issues](https://github.com/rtavytran/rt-commission-dashboard/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rtavytran/rt-commission-dashboard/discussions)

---

Built with ❤️ by [RealTimeX Team](https://realtimex.ai)
