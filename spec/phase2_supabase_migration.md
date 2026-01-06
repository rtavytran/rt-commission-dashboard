# Phase 2: Supabase Migration Plan

## Overview
Migrate from local SQLite database to cloud-based Supabase (PostgreSQL) with production-grade authentication and real-time capabilities.

## 1. Supabase Project Setup

### Step 1.1: Create Supabase Project
1. Sign up at [https://supabase.com](https://supabase.com)
2. Create new project: `rt-commission-dashboard`
3. Choose region (closest to your users)
4. Note down:
   - Project URL: `https://xxxxx.supabase.co`
   - Project ID: `dwdcpxinaiknskvpeqcq`
   - Anon Public Key: `eyJhbG...`
   - Service Role Key: `eyJhbG...` (keep secret!)

### Step 1.2: Environment Configuration
Create `.env` file in project root:
```bash
# Supabase Credentials
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbG...
SUPABASE_SERVICE_KEY=eyJhbG...

# Database Selection
DATABASE_TYPE=supabase  # or 'sqlite' for local development

# App Settings
SECRET_KEY=your-secret-key-here
ENVIRONMENT=production  # or 'development'
```

Update `config.yaml`:
```yaml
database:
  type: supabase  # or 'sqlite'
  supabase:
    url: ${SUPABASE_URL}
    anon_key: ${SUPABASE_ANON_KEY}
    service_key: ${SUPABASE_SERVICE_KEY}
  sqlite:
    filename: "rt_commission_dashboard_v2.db"
```

---

## 2. Database Schema Migration

### Step 2.1: Create Tables in Supabase
Execute in Supabase SQL Editor:

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR UNIQUE NOT NULL,
    full_name VARCHAR,
    role VARCHAR DEFAULT 'ctv' CHECK (role IN ('admin', 'affiliate', 'ctv')),
    permissions JSONB DEFAULT '[]'::jsonb,
    parent_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on parent_id for tree queries
CREATE INDEX idx_users_parent ON users(parent_id);
CREATE INDEX idx_users_email ON users(email);

-- Transactions Table
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(15, 2) NOT NULL,
    type VARCHAR NOT NULL CHECK (type IN ('retail_sales', 'commission_sharing', 'kpi_reward')),
    status VARCHAR DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'paid', 'refunded')),
    reference_id UUID REFERENCES transactions(id),
    shared_with_id UUID REFERENCES users(id),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_transactions_user ON transactions(user_id);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_created ON transactions(created_at);
CREATE INDEX idx_transactions_shared ON transactions(shared_with_id);

-- Monthly Stats Table
CREATE TABLE monthly_stats (
    id TEXT PRIMARY KEY, -- user_id::text || '_' || YYYY-MM
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month VARCHAR(7) NOT NULL, -- YYYY-MM format
    personal_sales_volume NUMERIC(15, 2) DEFAULT 0,
    shared_out_volume NUMERIC(15, 2) DEFAULT 0,
    received_volume NUMERIC(15, 2) DEFAULT 0,
    f1_sales_volume NUMERIC(15, 2) DEFAULT 0,
    tier_rate NUMERIC(5, 4) DEFAULT 0,
    comm_direct NUMERIC(15, 2) DEFAULT 0,
    comm_shared NUMERIC(15, 2) DEFAULT 0,
    comm_received NUMERIC(15, 2) DEFAULT 0,
    comm_override NUMERIC(15, 2) DEFAULT 0,
    total_commission NUMERIC(15, 2) DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, month)
);

CREATE INDEX idx_monthly_stats_user ON monthly_stats(user_id);
CREATE INDEX idx_monthly_stats_month ON monthly_stats(month);
```

### Step 2.2: Implement Automatic Commission Triggers (Optional)
For server-side commission calculation (reduces Python dependencies):

```sql
-- Function: Calculate tier rate from volume
CREATE OR REPLACE FUNCTION get_commission_rate(volume NUMERIC)
RETURNS NUMERIC AS $$
BEGIN
    IF volume >= 2000000000 THEN RETURN 0.35;
    ELSIF volume >= 1000000000 THEN RETURN 0.30;
    ELSIF volume >= 400000000 THEN RETURN 0.25;
    ELSIF volume >= 200000000 THEN RETURN 0.22;
    ELSE RETURN 0.20;
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Trigger: Auto-update monthly_stats on new transaction
-- (Detailed implementation from database_schema.md lines 160-190)
```

### Step 2.3: Row Level Security (RLS)
Protect data access at database level:

```sql
-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_stats ENABLE ROW LEVEL SECURITY;

-- Policy: Users can read their own data
CREATE POLICY "Users can view own profile"
    ON users FOR SELECT
    USING (auth.uid()::text = id::text);

-- Policy: Admins can see all users
CREATE POLICY "Admins can view all users"
    ON users FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE id::text = auth.uid()::text
            AND role = 'admin'
        )
    );

-- Policy: Users can see their own transactions
CREATE POLICY "Users can view own transactions"
    ON transactions FOR SELECT
    USING (user_id::text = auth.uid()::text);

-- Policy: Admins can see all transactions
CREATE POLICY "Admins can view all transactions"
    ON transactions FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE id::text = auth.uid()::text
            AND role = 'admin'
        )
    );

-- Similar policies for monthly_stats
CREATE POLICY "Users can view own stats"
    ON monthly_stats FOR SELECT
    USING (user_id::text = auth.uid()::text);

CREATE POLICY "Admins can view all stats"
    ON monthly_stats FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE id::text = auth.uid()::text
            AND role = 'admin'
        )
    );
```

---

## 3. Code Implementation

### Step 3.1: Install Dependencies
Update `pyproject.toml`:
```toml
[project]
dependencies = [
    "nicegui>=1.4.0",
    "plotly>=5.0.0",
    "pandas>=2.0.0",
    "pyyaml>=6.0.0",
    "python-dotenv>=1.0.0",
    "faker>=20.0.0",
    "supabase>=2.0.0",  # Add this
]
```

Run:
```bash
uv sync
```

### Step 3.2: Create SupabaseHandler
Create new file: `rt_commission_dashboard/core/supabase_handler.py`

```python
from supabase import create_client, Client
from datetime import datetime
import os
from rt_commission_dashboard.core.config import config

class SupabaseHandler:
    """Supabase-based database handler (same interface as DBHandler)."""

    def __init__(self):
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')

        if not url or not key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

        self.client: Client = create_client(url, key)
        self._init_db()

    def _init_db(self):
        """Check if tables exist, seed if empty."""
        # Tables are created via SQL (Step 2.1)
        # Just check if we need to seed
        result = self.client.table('users').select('id').limit(1).execute()

        if len(result.data) == 0:
            self._seed_mock_data()

    def _seed_mock_data(self):
        """Seeds the database with test data."""
        # Implementation similar to DBHandler._seed_mock_data
        # Use self.client.table('users').insert(...).execute()
        pass

    def create_retail_sale(self, user_id, amount, metadata={}, created_at=None):
        """Creates a retail sale transaction."""
        if created_at is None:
            created_at = datetime.now().isoformat()

        # Insert transaction
        result = self.client.table('transactions').insert({
            'user_id': user_id,
            'amount': amount,
            'type': 'retail_sales',
            'status': 'approved',
            'metadata': metadata,
            'created_at': created_at
        }).execute()

        # Trigger monthly stats update
        tx_month = created_at[:7] if isinstance(created_at, str) else created_at.strftime('%Y-%m')
        self._propagate_monthly_updates(user_id, tx_month)

        return result.data[0]['id']

    def create_shared_opportunity(self, receiver_id, sharer_id, amount, metadata={}, created_at=None):
        """Creates a shared opportunity sale."""
        if created_at is None:
            created_at = datetime.now().isoformat()

        metadata['shared_type'] = 'opportunity'

        result = self.client.table('transactions').insert({
            'user_id': receiver_id,
            'amount': amount,
            'type': 'retail_sales',
            'status': 'approved',
            'metadata': metadata,
            'shared_with_id': sharer_id,
            'created_at': created_at
        }).execute()

        tx_month = created_at[:7] if isinstance(created_at, str) else created_at.strftime('%Y-%m')
        self._propagate_monthly_updates(receiver_id, tx_month)
        self._propagate_monthly_updates(sharer_id, tx_month)

        return result.data[0]['id']

    def _propagate_monthly_updates(self, start_user_id, month):
        """Recursively recalculates monthly stats."""
        # Implementation similar to DBHandler
        # Use Supabase client instead of SQL cursor
        pass

    def get_user(self, email):
        """Fetch user by email."""
        result = self.client.table('users')\
            .select('*')\
            .eq('email', email)\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    # ... Implement all other methods from DBHandler ...
    # get_all_users(), get_kpi_stats(), get_monthly_sales(), etc.
```

### Step 3.3: Database Factory Pattern
Update `rt_commission_dashboard/core/db_handler.py`:

```python
def get_db_handler():
    """Factory function to return appropriate DB handler."""
    db_type = config.get_database_type()

    if db_type == 'supabase':
        from rt_commission_dashboard.core.supabase_handler import SupabaseHandler
        return SupabaseHandler()
    else:
        return DBHandler()
```

Update all imports in pages:
```python
# Before
from rt_commission_dashboard.core.db_handler import DBHandler
db = DBHandler()

# After
from rt_commission_dashboard.core.db_handler import get_db_handler
db = get_db_handler()
```

---

## 4. Authentication Migration

### Step 4.1: Enable Supabase Auth
In Supabase Dashboard:
1. Go to Authentication → Settings
2. Enable Email/Password provider
3. Enable Magic Link (optional)
4. Configure email templates

### Step 4.2: Update Login Page
Modify `rt_commission_dashboard/pages/login.py`:

```python
from supabase import create_client
import os

async def handle_login():
    email = email_input.value
    password = password_input.value

    if config.get_database_type() == 'supabase':
        # Supabase Auth
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')
        supabase = create_client(url, key)

        try:
            auth_response = supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })

            user_id = auth_response.user.id

            # Fetch user details
            user_data = supabase.table('users')\
                .select('*')\
                .eq('id', user_id)\
                .single()\
                .execute()

            # Store in session
            app.storage.user['id'] = user_data.data['id']
            app.storage.user['email'] = user_data.data['email']
            app.storage.user['role'] = user_data.data['role']
            app.storage.user['full_name'] = user_data.data['full_name']
            app.storage.user['supabase_token'] = auth_response.session.access_token

            ui.navigate.to('/dashboard')
        except Exception as e:
            ui.notify(f'Login failed: {str(e)}', type='negative')
    else:
        # SQLite mock auth (Phase 1)
        user = db.get_user(email)
        if user:
            app.storage.user.update(user)
            ui.navigate.to('/dashboard')
```

### Step 4.3: Signup Page (Optional)
Create `rt_commission_dashboard/pages/signup.py`:
```python
@ui.page('/signup')
def signup_page():
    # Email, password, confirm password
    # Call supabase.auth.sign_up()
    pass
```

---

## 5. Real-Time Features

### Step 5.1: Enable Real-Time in Supabase
In Supabase Dashboard:
1. Go to Database → Replication
2. Enable replication for `transactions` and `monthly_stats` tables

### Step 5.2: Subscribe to Changes
Update `rt_commission_dashboard/pages/dashboard.py`:

```python
from supabase import create_client
import asyncio

# Create real-time subscription
def setup_realtime():
    if config.get_database_type() != 'supabase':
        return

    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')
    supabase = create_client(url, key)

    # Subscribe to transaction changes
    def on_transaction_change(payload):
        print(f"New transaction: {payload}")
        # Refresh KPI cards
        kpi_container.refresh()

    supabase.table('transactions')\
        .on('INSERT', on_transaction_change)\
        .subscribe()
```

---

## 6. Data Migration

### Step 6.1: Export SQLite Data
Create `scripts/export_sqlite_to_json.py`:
```python
import sqlite3
import json

conn = sqlite3.connect('data/rt_commission_dashboard_v2.db')
conn.row_factory = sqlite3.Row

# Export users
cursor = conn.cursor()
cursor.execute('SELECT * FROM users')
users = [dict(row) for row in cursor.fetchall()]

with open('data/users_export.json', 'w') as f:
    json.dump(users, f, indent=2)

# Export transactions
cursor.execute('SELECT * FROM transactions')
transactions = [dict(row) for row in cursor.fetchall()]

with open('data/transactions_export.json', 'w') as f:
    json.dump(transactions, f, indent=2)

print("Export complete!")
```

### Step 6.2: Import to Supabase
Create `scripts/import_to_supabase.py`:
```python
from supabase import create_client
import json
import os

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

# Import users
with open('data/users_export.json') as f:
    users = json.load(f)

for user in users:
    # Convert id to UUID if needed
    supabase.table('users').insert(user).execute()

print("Import complete!")
```

---

## 7. Testing Strategy

### Step 7.1: Test Checklist
- [ ] User authentication (login/logout)
- [ ] Retail sale creation
- [ ] Shared opportunity creation
- [ ] Commission calculations (verify against SQLite results)
- [ ] Tier rate updates
- [ ] Monthly stats accuracy
- [ ] Dashboard KPIs display correctly
- [ ] Affiliate tree visualization
- [ ] Reports filtering
- [ ] Real-time updates (if enabled)

### Step 7.2: Performance Testing
- [ ] Test with 1000+ users
- [ ] Test with 10,000+ transactions
- [ ] Measure dashboard load time
- [ ] Measure commission calculation speed

---

## 8. Deployment

### Step 8.1: Update Config
Set environment variables on hosting platform:
```bash
export DATABASE_TYPE=supabase
export SUPABASE_URL=https://xxxxx.supabase.co
export SUPABASE_ANON_KEY=eyJhbG...
export SUPABASE_SERVICE_KEY=eyJhbG...
export ENVIRONMENT=production
```

### Step 8.2: Deploy Application
```bash
# Install dependencies
uv sync

# Run production server
uv run rt-commission-dashboard --ui --port 8080
```

---

## 9. Rollback Plan

If issues occur during migration:

1. Switch back to SQLite:
   ```bash
   export DATABASE_TYPE=sqlite
   ```

2. Restore SQLite backup:
   ```bash
   cp data/rt_commission_dashboard_v2.db.backup data/rt_commission_dashboard_v2.db
   ```

3. Application automatically uses SQLite handler

---

## 10. Monitoring & Maintenance

### Key Metrics to Monitor:
- API response times
- Database query performance
- Real-time subscription health
- Commission calculation accuracy
- User authentication success rate

### Supabase Dashboard:
- Monitor database size
- Check query performance in Database → Performance
- Review auth logs
- Set up database backups (automatic in Supabase)

---

## Summary Timeline

| Phase | Task | Estimated Time |
|-------|------|----------------|
| 1 | Supabase setup & schema | 2-4 hours |
| 2 | SupabaseHandler implementation | 8-12 hours |
| 3 | Authentication migration | 4-6 hours |
| 4 | Real-time features | 4-6 hours |
| 5 | Testing & validation | 6-8 hours |
| 6 | Data migration | 2-3 hours |
| 7 | Deployment | 2-3 hours |

**Total:** ~30-45 hours

---

## Next Immediate Steps

1. ✅ Create Supabase account and project
2. ✅ Set up `.env` file with credentials
3. ✅ Execute SQL schema in Supabase SQL Editor
4. ✅ Install `supabase` Python package
5. ✅ Start implementing `SupabaseHandler` class
