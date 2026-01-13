# Migration Guide: Transactions Table UUID to TEXT

## Overview
This migration changes the `transactions` table columns from UUID to TEXT types:
- `id`: uuid → text
- `reference_id`: uuid → text

## Pre-Migration Checklist

### 1. Check for existing data
```sql
SELECT COUNT(*) FROM transactions;
SELECT id, reference_id FROM transactions LIMIT 5;
```

### 2. Check for foreign key constraints
```sql
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND (ccu.table_name = 'transactions' AND ccu.column_name = 'id');
```

### 3. Check for indexes
```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'transactions';
```

## Migration Options

### Option A: Safe Migration (Recommended if you have existing data)

1. **Backup your data first!**
```sql
-- Create a backup table
CREATE TABLE transactions_backup AS SELECT * FROM transactions;
```

2. **Run the migration**
   - Use the SQL in `alter_transactions_to_text.sql`
   - Or manually run in Supabase SQL Editor

3. **Verify the migration**
```sql
-- Check column types
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'transactions'
  AND column_name IN ('id', 'reference_id');

-- Verify data integrity
SELECT COUNT(*) FROM transactions;
SELECT id, reference_id FROM transactions LIMIT 5;
```

### Option B: Fresh Start (If table is empty or test environment)

If your transactions table is empty or this is a dev/test environment:

```sql
-- Drop and recreate the table
DROP TABLE IF EXISTS transactions CASCADE;

CREATE TABLE transactions (
    id text PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id),
    amount numeric NOT NULL,
    type varchar NOT NULL CHECK (type IN ('retail_sales', 'commission', 'kpi_reward')),
    status varchar NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved')),
    reference_id text,
    shared_with_id uuid REFERENCES users(id),
    metadata jsonb,
    created_at timestamptz NOT NULL DEFAULT NOW()
);

-- Add indexes
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_reference_id ON transactions(reference_id);
CREATE INDEX idx_transactions_created_at ON transactions(created_at);
```

## Post-Migration Steps

### 1. Update your application code
Make sure your application generates TEXT IDs instead of UUIDs for transactions:

**Before:**
```javascript
const transactionId = crypto.randomUUID(); // UUID v4
```

**After:**
```javascript
// Option 1: Use a custom format (e.g., TXN_timestamp_random)
const transactionId = `TXN_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// Option 2: Use nanoid for shorter IDs
import { nanoid } from 'nanoid';
const transactionId = nanoid();

// Option 3: Use ulid for sortable IDs
import { ulid } from 'ulid';
const transactionId = ulid();
```

### 2. Test the trigger
```sql
-- Insert a test transaction
INSERT INTO transactions (id, user_id, amount, type, status, created_at)
VALUES ('TEST_001', '00000000-0000-0000-0000-000000000001', 1000000, 'retail_sales', 'approved', NOW());

-- Check if monthly_stats was updated
SELECT * FROM monthly_stats WHERE user_id = '00000000-0000-0000-0000-000000000001';

-- Clean up test
DELETE FROM transactions WHERE id = 'TEST_001';
```

### 3. Drop backup table (after confirming everything works)
```sql
DROP TABLE transactions_backup;
```

## Rollback Plan

If something goes wrong:

```sql
-- Restore from backup
DROP TABLE transactions;
ALTER TABLE transactions_backup RENAME TO transactions;

-- Recreate triggers and indexes
-- (Run your original trigger creation scripts)
```

## Notes

- **Downtime**: Plan for a brief maintenance window during the migration
- **Data Conversion**: PostgreSQL handles UUID → TEXT conversion automatically using `USING id::text`
- **Performance**: TEXT primary keys may have slightly different performance characteristics than UUIDs, but for most use cases the difference is negligible
- **Application Updates**: Update all code that generates transaction IDs to use TEXT format instead of UUIDs
