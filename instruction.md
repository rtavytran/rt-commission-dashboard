# Updating Supabase Monthly Stats Trigger (Parent Upsert + F1 Volume)

This guide updates the Supabase trigger/procedure so that when a child user records their first retail sale, the parent’s `monthly_stats` row is auto-created (if missing) and `f1_sales_volume` is accumulated before recalculation.

## Prerequisites
- You are the project owner in Supabase.
- Your hierarchy is stored in `public.users` (with `parent_id`), and `monthly_stats.user_id` and `transactions.user_id` reference `public.users(id)`.
  - If you instead use `public.profiles` for the hierarchy, replace `public.users` with `public.profiles` in the SQL below before running.
- You have access to the Supabase SQL Editor.

## Steps (run in Supabase SQL Editor)
1) Open your Supabase project → SQL → New Query.
2) Paste and run the SQL below (adjust table names if your hierarchy uses `profiles`):

```sql
-- Helper: tier rate
create or replace function public.get_commission_rate(volume numeric)
returns numeric as $$
begin
    if volume > 2000000000 then return 0.35;
    elsif volume > 1000000000 then return 0.30;
    elsif volume > 400000000 then return 0.25;
    elsif volume > 200000000 then return 0.22;
    else return 0.20;
    end if;
end;
$$ language plpgsql immutable;

-- Recalculate stats; upsert parent row + F1 volume, then recurse
create or replace procedure public.recalculate_monthly_stats(p_user_id uuid, p_month text)
language plpgsql as $$
declare
    v_total_vol numeric;
    v_new_rate numeric;
    v_stat_id text := p_user_id::text || '_' || p_month;
    v_parent_id uuid;
begin
    select coalesce(personal_sales_volume + shared_out_volume + received_volume, 0)
      into v_total_vol
      from public.monthly_stats
     where id = v_stat_id;

    v_new_rate := get_commission_rate(coalesce(v_total_vol,0));

    update public.monthly_stats
       set tier_rate = v_new_rate,
           total_commission = (personal_sales_volume * v_new_rate),
           last_updated = now()
     where id = v_stat_id;

    -- propagate to parent: ensure row exists and add F1 volume
    select parent_id into v_parent_id from public.users where id = p_user_id;
    if v_parent_id is not null then
        insert into public.monthly_stats (id, user_id, month, f1_sales_volume, last_updated)
        values (v_parent_id::text || '_' || p_month, v_parent_id, p_month, v_total_vol, now())
        on conflict (id) do update
          set f1_sales_volume = public.monthly_stats.f1_sales_volume + excluded.f1_sales_volume,
              last_updated = now();
        call public.recalculate_monthly_stats(v_parent_id, p_month);
    end if;
end;
$$;

-- Trigger function: upsert seller row, then recurse (which handles parents)
create or replace function public.handle_new_transaction()
returns trigger as $$
declare
    v_month text;
    v_stat_id text;
begin
    if new.type = 'retail_sales' then
        v_month := to_char(new.created_at, 'YYYY-MM');
        v_stat_id := new.user_id::text || '_' || v_month;

        insert into public.monthly_stats (id, user_id, month, personal_sales_volume, last_updated)
        values (v_stat_id, new.user_id, v_month, new.amount, now())
        on conflict (id) do update
        set personal_sales_volume = public.monthly_stats.personal_sales_volume + excluded.personal_sales_volume,
            last_updated = now();

        call public.recalculate_monthly_stats(new.user_id, v_month);
    end if;
    return new;
end;
$$ language plpgsql;

-- Recreate trigger to use the updated function
drop trigger if exists on_transaction_insert on public.transactions;
create trigger on_transaction_insert
after insert on public.transactions
for each row execute function public.handle_new_transaction();
```

3) Click “Run”.

## Notes
- This only fires for `transactions.type = 'retail_sales'`. Add more logic if you want other types to affect stats.
- If you store the hierarchy in `public.profiles` instead of `public.users`, swap the parent lookup to `public.profiles` and ensure FKs match.
- Existing data is untouched; future inserts will upsert parent rows and accumulate `f1_sales_volume`.
