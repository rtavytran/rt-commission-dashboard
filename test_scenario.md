# Test Scenario Scenarios

## 1. User Hierarchy (Affiliate System)
The system focuses on a 3-tier structure with some edge cases (orphans).

### **Mermaid Relationship Chart**
```mermaid
graph TD
    A[Admin (u_admin)]
    
    %% Level 1
    B[Affiliate A (u_aff1)] --> A
    C[Orphan User (u_orphan)] -. No Parent .- A
    
    %% Level 2
    D[Affiliate B (u_aff2)] --> B
    E[CTV Y (u_ctv2)] --> B
    
    %% Level 3
    F[CTV X (u_ctv1)] --> D
    
    %% Styling
    style A fill:#f9f,stroke:#333
    style C fill:#eee,stroke:#999,stroke-dasharray: 5 5
```

### **Users Table**
| ID | Email | Role | Full Name | Parent ID | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `u_admin` | `admin@rt.local` | `admin` | Super Admin | `NULL` | Root user. Sees ALL. |
| `u_aff1` | `daily1@rt.local` | `affiliate` | Đại lý A | `u_admin` | Direct under Admin. |
| `u_aff2` | `daily2@rt.local` | `affiliate` | Đại lý B | `u_aff1` | Child of Đại lý A. |
| `u_ctv1` | `ctv1@rt.local` | `ctv` | CTV X | `u_aff2` | Child of Đại lý B. |
| `u_ctv2` | `ctv2@rt.local` | `ctv` | CTV Y | `u_aff1` | Another direct child of A. |
| `u_orphan` | `orphan@rt.local` | `affiliate` | Độc Lập | `NULL` | **Edge Case**: No parent (should not break tree). |

**Note**: Email domains are configurable in `config.yaml`

---

## 2. Order & Transaction Data
We simulate a mix of standard flows and edge cases.

### **Transactions Table**
| ID | User ID | Type | Amount | Status | Logic / Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Standard Retail** |||||
| `tx_1` | `u_ctv1` | `retail_sales` | $500.00 | `approved` | **Retail**: CTV X sells "Combo Giày". |
| `tx_2` | `u_aff2` | `retail_sales` | $1200.00 | `approved` | **Retail**: Đại lý B sells "Suit Cao Cấp". |
| **Commissions (Flow Up)** |||||
| `tx_3` | `u_aff2` | `commission_sharing` | $50.00 | `paid` | **Share**: Đại lý B gets 10% from CTV X (`tx_1`). |
| `tx_4` | `u_aff1` | `commission_sharing` | $120.00 | `paid` | **Share**: Đại lý A gets 10% from Đại lý B (`tx_2`). |
| **Rewards & Bonuses** |||||
| `tx_5` | `u_aff1` | `kpi_reward` | $5000.00 | `approved` | **Reward**: QA Bonus for meeting targets. |
| **Edge Cases** |||||
| `tx_6` | `u_orphan` | `retail_sales` | $300.00 | `approved` | **Orphan Sale**: No commission generated upwards. |
| `tx_7` | `u_ctv2` | `retail_sales` | $100.00 | `refunded` | **Refund**: Should NOT count towards Total Revenue. |
| `tx_8` | `u_aff1` | `retail_sales` | $50.00 | `pending` | **Pending**: Pending order, shouldn't show in charts yet. |

---

## 3. Permission & Visibility Matrix

### **Verification Checklist**
This matrix ensures that visibility scope is correctly enforced.

| Viewer | Can See User? | Can See Transaction? | Success Criteria |
| :--- | :--- | :--- | :--- |
| **Admin** | **ALL** | **ALL** | Sees `u_orphan`, `u_ctv1`, `tx_1`... everything. |
| **Affiliate A** | `u_aff2`, `u_ctv1`, `u_ctv2` | `tx_1`, `tx_2` (via downstream) | Sees own sub-tree. **Cannot** see `u_orphan`. |
| **Affiliate B** | `u_ctv1` | `tx_1` | Sees only CTV X. **Cannot** see `u_ctv2`. |
| **CTV X** | `None` (Leaf) | `tx_1` (Own) | Sees only self. |
| **Orphan** | `None` (Leaf) | `tx_6` (Own) | Sees only self. Tree view is empty or self-only. |

### **Testing Flows**
1.  **Affiliate View (`daily1`)**:
    *   **Revenue**: Own Revenue (0) + Commission ($120).
    *   **Tree**: Expands to see `daily2` -> `ctv1`.
    *   **Edge Case**: Should NOT see `u_orphan`.

2.  **Orphan View (`orphan`)**:
    *   **Tree**: Should render just self or empty message (No parents, no children).

3.  **Refund Logic**:
    *   Check Reports for `u_ctv2`. Ensure `tx_7` (Refunded) is NOT included in "Total Revenue" sum.
