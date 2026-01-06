# Data Management Instructions

This guide explains how to populate the RT Commission Dashboard database with users and transactions, ensuring the automatic commission logic works correctly.

**Database**: Uses configurable filename from `config.yaml` (default: `rt_commission_dashboard.db`)

## 1. User Management (Roles & Hierarchy)

To create a valid affiliate tree, you must link users via `parent_id`.

### Roles
*   `admin`: Super Admin (Views all data).
*   `affiliate`: Agency/Partner (Deep hierarchy).
*   `ctv`: Collaborator (Leaf nodes, usually focused on sales).

### SQL Example
```sql
-- Create Root Admin
INSERT INTO users (id, email, role, full_name, parent_id) 
VALUES ('u_admin', 'admin@rt.local', 'admin', 'Super Admin', NULL);

-- Create Level 1 Affiliate (Directly under Admin)
INSERT INTO users (id, email, role, full_name, parent_id) 
VALUES ('u_aff1', 'daily1@rt.local', 'affiliate', 'Đại lý A', 'u_admin');

-- Create Level 2 CTV (Under Affiliate)
INSERT INTO users (id, email, role, full_name, parent_id) 
VALUES ('u_ctv1', 'ctv1@rt.local', 'ctv', 'CTV X', 'u_aff1');

-- Note: Email domains are configurable in config.yaml
```

---

## 2. Transaction Flow

### Retail Sales (Triggers Commissions)
Use the python method `db.create_retail_sale()` to ensure commissions are generated. If inserting manually via SQL, you **MUST** also calculate and insert the commission rows yourself.

**Recommended: Use Python Shell**
```bash
uv run python
```
```python
from rt_commission_dashboard.core.db_handler import DBHandler
db = DBHandler()

# Create a $1000 sale for CTV1
# This automatically gives commissions to upline based on config.yaml rates
# This automatically gives commissions to upline based on monthly volume (Differential)
# Example: Upline (Tier 22%) - Seller (Tier 20%) = 2% Commission
db.create_retail_sale('u_ctv1', 1000.00, {'product': 'Giày Nike', 'customer': 'Mr. Long'})
```

### Manual Transactions (Bonuses/Adjustments)
For non-automated transactions like KPI Rewards, insert directly via SQL or a future Admin UI.

**SQL Example (KPI Reward)**
```sql
INSERT INTO transactions (id, user_id, amount, type, status, created_at)
VALUES (
    'tx_bonus_001', 
    'u_aff1', 
    5000.00, 
    'kpi_reward', 
    'approved', 
    CURRENT_TIMESTAMP
);
```

---

## 3. Commission Logic Reference

**Note**: Commission rates are configurable in `config.yaml`

### Volume-Based Tier System
Commission rates are now determined by **Total Monthly Sales** (Personal + F1).

| Monthly Sales | Rate |
| :--- | :--- |
| > 0 | **20%** |
| > 200M | **22%** |
| > 400M | **25%** |
| > 1B | **30%** |
| > 2B | **35%** |

The system automatically calculates the **differential** between upline and downline rates.

### Customizing Tiers
Edit `config.yaml` to change thresholds:
```yaml
commission:
  tiers:
    - {threshold: 0, rate: 0.15}           # Base rate 15%
    - {threshold: 100000000, rate: 0.20}   # > 100M: 20%
```

### Shared Opportunity (Co-Selling)
When a sale is shared (e.g., User A is the "Sharer" and User B is the "Receiver"):
1.  **Volume for Tier Ranking**:
    *   **Sharer (User A)**: Gets **100% of the sale amount** counted toward their monthly tier ranking.
    *   **Receiver (User B)**: Gets **0% volume credit** for tier ranking (does not count).
2.  **Commission Split**: Both users earn commission on **50% of the sale value** using their respective tier rates:
    *   **Sharer**: Commission = (Sharer's Tier Rate) × 50% × Sale Amount
    *   **Receiver**: Commission = (Receiver's Tier Rate) × 50% × Sale Amount
3.  **Upline**: The upline of *each* user earns differential commission based on that user's respective volumes and tiers.

### Inactive User Logic (The "4% Rule")
*   **Condition**: If a user has **0 Personal Sales** in the current month (excluding received shares).
*   **Penalty**: Their commission rate is capped at **4%**.
*   **Effect**: 
    *   Direct Sales: 4% commission.
    *   Shared/Received: 4% commission on the split amount.
    *   **Override**: They generally do *not* receive override commissions from downlines if they are inactive (unless specific config allows).

---

## 4. Database Schema Reference

### `monthly_stats` Table
This table stores the stateful monthly performance for each user, allowing for instant reporting and historical snapshots.

```sql
CREATE TABLE monthly_stats (
    id TEXT PRIMARY KEY,          -- Format: {user_id}_{YYYY-MM}
    user_id TEXT NOT NULL,
    month TEXT NOT NULL,          -- Format: YYYY-MM
    
    -- Volume Columns (Used for Tier Ranking)
    personal_sales_volume REAL,   -- Direct Retail Sales
    shared_out_volume REAL,       -- Volume shared with others (50% of sale)
    received_volume REAL,         -- Volume received from others (50% of sale)
    f1_sales_volume REAL,         -- Volume from direct downlines (for future use)
    
    -- Financial Columns
    tier_rate REAL,               -- Effective Commission Rate (e.g. 0.20, 0.22)
    comm_direct REAL,             -- Commission from Personal Sales
    comm_shared REAL,             -- Commission from Shared-Out sales
    comm_received REAL,           -- Commission from Received sales
    comm_override REAL,           -- Commission from Downline differentials
    total_commission REAL,        -- Total Earnings
    
    last_updated DATETIME
);
```

**Key Note**: `tier_rate` is dynamically updated every time a transaction occurs, potentially recalculating `comm_direct` and `comm_override` for the entire month to reflect the new rate.

