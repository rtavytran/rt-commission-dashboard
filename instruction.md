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
# Default: $100 to u_aff1 (10%) and $50 to u_admin (5%)
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

### Default Commission Rates
| Level | Relationship | Rate | Calculation |
| :--- | :--- | :--- | :--- |
| **Level 1** | Direct Parent | **10%** | `Sale Amount * 0.10` |
| **Level 2** | Grandparent | **5%** | `Sale Amount * 0.05` |
| **Level 3** | Great-Grandparent | **2%** | `Sale Amount * 0.02` |

### Customizing Commission Rates
Edit `config.yaml` to change rates:
```yaml
commission:
  rates:
    level_1: 0.15  # 15% instead of 10%
    level_2: 0.08  # 8% instead of 5%
    level_3: 0.03  # 3% instead of 2%
  max_levels: 5    # Maximum hierarchy levels
```

**Note**: Commissions are only generated for `retail_sales`.
