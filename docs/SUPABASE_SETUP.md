# Supabase Setup Guide

This guide walks you through setting up the RT Commission Dashboard with Supabase backend.

## Prerequisites

- Supabase account (sign up at https://supabase.com)
- Project created on Supabase
- Environment variables configured in `.env`

## Step 1: Configure Environment Variables

Ensure your `.env` file has the following:

```bash
# Supabase Credentials
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Database Selection
DATABASE_TYPE=supabase  # Use 'supabase' for production, 'sqlite' for dev

# App Settings
SECRET_KEY=your-secret-key
ENVIRONMENT=production
```

## Step 2: Create Database Tables

Run the table creation SQL (from `spec/phase2_supabase_migration.md` Section 2.1):

1. Go to your Supabase project
2. Click **SQL Editor** in the sidebar
3. Create a new query
4. Copy and paste the schema from Section 2.1 (users, transactions, monthly_stats tables)
5. Click **Run**

## Step 3: Set Up Automatic Commission Calculations

**IMPORTANT:** This is the key step that makes commission calculations automatic!

1. In Supabase SQL Editor, create a new query
2. Copy the ENTIRE contents of `scripts/supabase_setup.sql`
3. Run the script

This will create:
- ✅ `get_commission_rate()` - Calculates tier rate from volume
- ✅ `get_leg_commission_volume()` - Recursively sums downline volume
- ✅ `recalculate_monthly_stats()` - Recalculates all commissions for a user/month
- ✅ `handle_new_transaction()` - Trigger function for new transactions
- ✅ `handle_transaction_update()` - Trigger function for status changes
- ✅ `on_transaction_insert` - Trigger that fires on INSERT
- ✅ `on_transaction_update` - Trigger that fires on UPDATE

## Step 4: Verify Triggers Are Active

Check that triggers were created:

```sql
SELECT trigger_name, event_manipulation, event_object_table
FROM information_schema.triggers
WHERE trigger_schema = 'public'
AND event_object_table = 'transactions';
```

You should see:
- `on_transaction_insert` (INSERT trigger)
- `on_transaction_update` (UPDATE trigger)

## Step 5: Test the Setup

Insert a test transaction:

```sql
-- Get a user ID first
SELECT id, email FROM users LIMIT 1;

-- Insert a test sale (replace with actual user ID)
INSERT INTO transactions (user_id, amount, type, status, metadata)
VALUES ('your-user-id-here', 1000, 'retail_sales', 'approved', '{"product": "Test"}');

-- Check monthly_stats was auto-calculated
SELECT * FROM monthly_stats ORDER BY last_updated DESC LIMIT 5;
```

You should see:
- New row in `monthly_stats`
- `personal_sales_volume` = 1000
- `tier_rate` = 0.20 (20%)
- `comm_direct` = 200 (1000 × 20%)
- `total_commission` = 200

## Step 6: Optional - Recalculate Existing Data

If you already have transactions in the database before setting up triggers:

```sql
-- Recalculate for a specific user and month
SELECT recalculate_monthly_stats('user-id'::uuid, '2026-01');

-- Or recalculate for all existing transactions
DO $$
DECLARE
    tx RECORD;
BEGIN
    FOR tx IN
        SELECT DISTINCT user_id, to_char(created_at, 'YYYY-MM') as month
        FROM transactions
        WHERE type = 'retail_sales' AND status = 'approved'
    LOOP
        PERFORM recalculate_monthly_stats(tx.user_id, tx.month);
    END LOOP;
END $$;
```

## How It Works

### Automatic Commission Calculation Flow

1. **Transaction Inserted:**
   ```sql
   INSERT INTO transactions (user_id, amount, type, status, ...)
   VALUES (user_id, 1000, 'retail_sales', 'approved', ...);
   ```

2. **Trigger Fires:** `on_transaction_insert` trigger detects the INSERT

3. **Trigger Function Executes:** `handle_new_transaction()` is called

4. **Commission Calculation:** `recalculate_monthly_stats()` is called
   - Calculates personal volume
   - Calculates shared/received volumes
   - Calculates F1 volume from children
   - Determines tier rate
   - Calculates commissions (direct, shared, received, override)
   - Updates `monthly_stats` table

5. **Recursive Propagation:** Parent's stats are recalculated automatically

### Share/Receive Logic

For shared opportunities:

```sql
-- User B (receiver) sells, User A (sharer) gets credit
INSERT INTO transactions (user_id, shared_with_id, amount, type, status)
VALUES (user_b_id, user_a_id, 10000, 'retail_sales', 'approved');
```

Trigger automatically:
- User A (sharer): +10000 to `shared_out_volume` (100% for tier ranking)
- User B (receiver): +10000 to `received_volume` (0% for tier ranking)
- Both: 50% commission split using their respective tier rates

## Troubleshooting

### Commissions Not Calculating

1. **Check triggers exist:**
   ```sql
   SELECT * FROM information_schema.triggers WHERE event_object_table = 'transactions';
   ```

2. **Check function exists:**
   ```sql
   SELECT routine_name FROM information_schema.routines
   WHERE routine_type = 'FUNCTION' AND routine_name LIKE '%commission%';
   ```

3. **Check for errors in trigger execution:**
   ```sql
   -- Supabase doesn't have error logs, so test manually:
   SELECT recalculate_monthly_stats('user-id'::uuid, '2026-01');
   ```

### Data Type Errors

If you get UUID errors, ensure:
- User IDs are proper UUIDs (not TEXT)
- Use `::uuid` casting if needed: `'user-id'::uuid`

### Performance Issues

For large datasets:
- Triggers are synchronous and can slow down INSERTs
- Consider batch processing or async triggers for production scale
- Monitor query performance in Supabase Dashboard > Performance

## Next Steps

- ✅ Test the application: `uv run rt-commission-dashboard --ui`
- ✅ Login with test accounts (admin@rt.local, etc.)
- ✅ Create test transactions and verify commissions calculate automatically
- ✅ Monitor the `monthly_stats` table for real-time updates

## Support

If you encounter issues:
1. Check Supabase logs in Dashboard > Logs
2. Review `scripts/supabase_setup.sql` for trigger definitions
3. Test functions manually in SQL Editor
