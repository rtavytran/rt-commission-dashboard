-- Migration: Change transactions table ID columns from UUID to TEXT
-- WARNING: This will require downtime and may affect existing data
-- Run this during a maintenance window

-- Step 1: Drop the trigger temporarily (if it exists)
DROP TRIGGER IF EXISTS on_transaction_insert ON transactions;

-- Step 2: Drop foreign key constraints
-- The reference_id column references transactions.id (self-referencing FK)
ALTER TABLE transactions
  DROP CONSTRAINT IF EXISTS transactions_reference_id_fkey;

-- Drop any other foreign key constraints that reference transactions.id
-- (Check output from pre-migration query to see if there are others)

-- Step 3: Alter the column types
-- Note: PostgreSQL can convert UUID to TEXT automatically
ALTER TABLE transactions
  ALTER COLUMN id TYPE text USING id::text;

ALTER TABLE transactions
  ALTER COLUMN reference_id TYPE text USING reference_id::text;

-- Step 4: Recreate the foreign key constraint
ALTER TABLE transactions
  ADD CONSTRAINT transactions_reference_id_fkey
  FOREIGN KEY (reference_id) REFERENCES transactions(id)
  ON DELETE SET NULL;

-- Step 4: Recreate the trigger (if it was using UUID types)
CREATE OR REPLACE FUNCTION handle_new_transaction()
RETURNS TRIGGER AS $$
DECLARE
    v_month TEXT;
    v_stat_id TEXT;
BEGIN
    IF NEW.type = 'retail_sales' THEN
        v_month := to_char(NEW.created_at, 'YYYY-MM');
        v_stat_id := NEW.user_id || '_' || v_month;

        -- 1. Upsert Initial Volume
        INSERT INTO monthly_stats (id, user_id, month, personal_sales_volume, last_updated)
        VALUES (v_stat_id, NEW.user_id, v_month, NEW.amount, NOW())
        ON CONFLICT (id) DO UPDATE
        SET personal_sales_volume = monthly_stats.personal_sales_volume + EXCLUDED.personal_sales_volume,
            last_updated = NOW();

        -- 2. Trigger Recalculation Chain
        CALL recalculate_monthly_stats(NEW.user_id, v_month);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_transaction_insert
AFTER INSERT ON transactions
FOR EACH ROW EXECUTE FUNCTION handle_new_transaction();

-- Step 5: Verify the changes
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'transactions'
  AND column_name IN ('id', 'reference_id');
