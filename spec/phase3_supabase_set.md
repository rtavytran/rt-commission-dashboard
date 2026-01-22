# Phase 3: Supabase Setup (Fresh Project, Profiles = Dashboard Access Only)

Goal: brand-new Supabase project where:
- `users`, `transactions`, `monthly_stats` remain the core data tables (no schema change from the app’s expectations).
- `profiles` controls dashboard access (keyed to `auth.users`). A profile may link to a `users.id` (nullable) but the sets can differ.
- Roles for a profile default from the linked `users.role` when mapped; otherwise set manually on approval.
- App flow: user provides Supabase URL + anon key → signup/login → admin creates/approves profile (optionally links to a `users` row) → RLS allows access.

## 0) Prerequisites
- New Supabase project.
- Disable open signup if you want invite-only.
- Enable Email/Password auth provider and set email templates.

## 1) Core Schema (run in Supabase SQL)
Fresh create; no migrations/drops needed.
```sql
create extension if not exists "uuid-ossp";
create extension if not exists "citext";

-- Core data tables (unchanged, keyed to users)
create table if not exists public.users (
    id uuid primary key default uuid_generate_v4(),
    email citext unique not null,
    username text unique,
    full_name text,
    role text not null default 'ctv' check (role in ('admin','affiliate','ctv')),
    permissions jsonb,
    parent_id uuid references public.users(id) on delete set null,
    created_at timestamptz default now()
);
create index if not exists idx_users_parent on public.users(parent_id);

create table if not exists public.transactions (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid not null references public.users(id) on delete cascade,
    amount numeric(15,2) not null,
    type varchar not null check (type in ('retail_sales','commission_sharing','kpi_reward')),
    status varchar default 'pending' check (status in ('pending','approved','paid','refunded')),
    reference_id uuid references public.transactions(id),
    shared_with_id uuid references public.users(id),
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz default now()
);
create index if not exists idx_transactions_user on public.transactions(user_id);
create index if not exists idx_transactions_created on public.transactions(created_at);

create table if not exists public.monthly_stats (
    id text primary key, -- user_id::text || '_' || YYYY-MM
    user_id uuid not null references public.users(id) on delete cascade,
    month varchar(7) not null, -- YYYY-MM
    personal_sales_volume numeric(15,2) default 0,
    shared_out_volume numeric(15,2) default 0,
    received_volume numeric(15,2) default 0,
    f1_sales_volume numeric(15,2) default 0,
    tier_rate numeric(5,4) default 0,
    comm_direct numeric(15,2) default 0,
    comm_shared numeric(15,2) default 0,
    comm_received numeric(15,2) default 0,
    comm_override numeric(15,2) default 0,
    total_commission numeric(15,2) default 0,
    last_updated timestamptz default now(),
    unique (user_id, month)
);
create index if not exists idx_monthly_stats_user on public.monthly_stats(user_id);
create index if not exists idx_monthly_stats_month on public.monthly_stats(month);

-- Profiles = dashboard access (auth.users.id), optional link to core users.user_id
create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    email citext unique not null,
    full_name text,
    user_id uuid references public.users(id),
    role text not null default 'ctv' check (role in ('admin','affiliate','ctv')),
    status text not null default 'pending' check (status in ('pending','approved','blocked')),
    approved_by uuid references public.profiles(id),
    approved_at timestamptz,
    created_at timestamptz default now()
);
create index if not exists idx_profiles_user_id on public.profiles(user_id);
create index if not exists idx_profiles_status on public.profiles(status);
```

## 2) Row Level Security (auth-first via profiles; data via users)

### Helper functions to avoid recursion
```sql
create or replace function public.is_admin(uid uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1 from public.profiles p
        where p.id = uid and p.role = 'admin' and p.status = 'approved'
    );
$$;

create or replace function public.is_self(uid uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select uid = auth.uid();
$$;
```

### Policies
```sql
-- Enable
alter table public.profiles enable row level security;
alter table public.transactions enable row level security;
alter table public.monthly_stats enable row level security;
alter table public.users enable row level security;

-- Profiles: only owner sees self; admins see all
drop policy if exists "profiles.self.read" on public.profiles;
create policy "profiles.self.read"
  on public.profiles for select
  using (auth.uid() = id);

drop policy if exists "profiles.self.update" on public.profiles;
create policy "profiles.self.update"
  on public.profiles for update
  using (auth.uid() = id);

drop policy if exists "profiles.admin.manage" on public.profiles;
create policy "profiles.admin.manage"
  on public.profiles for all
  using (public.is_admin(auth.uid()));

-- Users table: admin only (prevent direct reads by non-admins)
drop policy if exists "users.admin.read" on public.users;
create policy "users.admin.read"
  on public.users for select
  using (public.is_admin(auth.uid()));

-- Transactions: self if mapped; admin all
drop policy if exists "transactions.self.readwrite" on public.transactions;
create policy "transactions.self.readwrite"
  on public.transactions for all
  using (
    exists (select 1 from public.profiles p where p.id = auth.uid() and p.status='approved' and p.user_id = public.transactions.user_id)
  )
  with check (
    exists (select 1 from public.profiles p where p.id = auth.uid() and p.status='approved' and p.user_id = public.transactions.user_id)
  );

drop policy if exists "transactions.admin.full" on public.transactions;
create policy "transactions.admin.full"
  on public.transactions for all
  using (public.is_admin(auth.uid()))
  with check (true);

-- Monthly stats: self if mapped; admin all
drop policy if exists "monthly_stats.self.read" on public.monthly_stats;
create policy "monthly_stats.self.read"
  on public.monthly_stats for select
  using (
    exists (select 1 from public.profiles p where p.id = auth.uid() and p.status='approved' and p.user_id = public.monthly_stats.user_id)
  );

drop policy if exists "monthly_stats.admin.read" on public.monthly_stats;
create policy "monthly_stats.admin.read"
  on public.monthly_stats for select
  using (public.is_admin(auth.uid()));
```

Notes:
- If a profile has no linked `user_id`, they can log in but won’t see data unless they are an admin (who can see everything).
- Core data rows can exist without a profile (e.g., sales-only users). Admins can see them; unmapped profiles cannot.

## 3) Auth & Approval Flow
- App collects only Supabase URL + anon key from the user.
- User signs up (auth user created in `auth.users`).
- Admin action (owner task):
  1. Create/confirm a `users` row for that person (if they should see data).
  2. Insert/approve a `profiles` row for the auth user, optionally linking `profiles.user_id` to the `users.id`.
  3. Set `status='approved'` and, if linked, set `role` from `users.role` (or choose manually for unmapped).
- Until approved, RLS blocks data.

### (Optional) Auto-create pending profile on signup
To automatically add a pending profile when a new auth user is created:
```sql
create or replace function public.handle_new_auth_user()
returns trigger
security definer
set search_path = public
language plpgsql
as $$
begin
    insert into public.profiles (id, email, full_name, status)
    values (new.id, new.email, new.raw_user_meta_data->>'full_name', 'pending')
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_auth_user();
```
Owners still need to approve and (optionally) link `user_id` to a core `users` row.

## 4) Optional: Server-side monthly stats trigger (from database_schema)
Use if you want PostgreSQL to maintain `monthly_stats` automatically.
```sql
create or replace function get_commission_rate(volume NUMERIC)
returns NUMERIC as $$
begin
    if volume > 2000000000 then return 0.35;
    elsif volume > 1000000000 then return 0.30;
    elsif volume > 400000000 then return 0.25;
    elsif volume > 200000000 then return 0.22;
    else return 0.20;
    end if;
end;
$$ language plpgsql immutable;

create or replace procedure recalculate_monthly_stats(p_user_id uuid, p_month text)
language plpgsql as $$
declare
    v_total_vol numeric;
    v_new_rate numeric;
    v_stat_id text := p_user_id::text || '_' || p_month;
    v_parent_id uuid;
begin
    select coalesce(personal_sales_volume + shared_out_volume + received_volume, 0)
      into v_total_vol
      from monthly_stats where id = v_stat_id;

    v_new_rate := get_commission_rate(coalesce(v_total_vol,0));

    update monthly_stats
       set tier_rate = v_new_rate,
           total_commission = (personal_sales_volume * v_new_rate),
           last_updated = now()
     where id = v_stat_id;

    -- propagate up to parent: ensure row exists and accumulate F1 volume
    select parent_id into v_parent_id from public.users where id = p_user_id;
    if v_parent_id is not null then
        insert into monthly_stats (id, user_id, month, f1_sales_volume, last_updated)
        values (v_parent_id::text || '_' || p_month, v_parent_id, p_month, v_total_vol, now())
        on conflict (id) do update
          set f1_sales_volume = monthly_stats.f1_sales_volume + excluded.f1_sales_volume,
              last_updated = now();
        call recalculate_monthly_stats(v_parent_id, p_month);
    end if;
end;
$$;

create or replace function handle_new_transaction()
returns trigger as $$
declare
    v_month text;
    v_stat_id text;
begin
    if new.type = 'retail_sales' then
        v_month := to_char(new.created_at, 'YYYY-MM');
        v_stat_id := new.user_id::text || '_' || v_month;

        -- Upsert seller row (personal volume)
        insert into monthly_stats (id, user_id, month, personal_sales_volume, last_updated)
        values (v_stat_id, new.user_id, v_month, new.amount, now())
        on conflict (id) do update
        set personal_sales_volume = monthly_stats.personal_sales_volume + excluded.personal_sales_volume,
            last_updated = now();

        -- Recalculate chain (also upserts parent rows and F1 volume)
        call recalculate_monthly_stats(new.user_id, v_month);
    end if;
    return new;
end;
$$ language plpgsql;

drop trigger if exists on_transaction_insert on transactions;
create trigger on_transaction_insert
after insert on transactions
for each row execute function handle_new_transaction();
```

## 5) Quick Flow (Mermaid)
```mermaid
flowchart TD
  Start[User opens app] --> Setup[/Enter Supabase URL + anon key/]
  Setup --> Signup{Has account?}
  Signup -->|No| SignUp[User signs up (auth.users)]
  Signup -->|Yes| Login[User logs in]
  SignUp --> Wait[Pending approval]
  Login --> CheckProfile[Profile exists & approved?]
  CheckProfile -->|No| Wait
  Wait --> Admin[Admin creates/links profile, sets status=approved]
  Admin --> CheckProfile
  CheckProfile -->|Yes| Dashboard[Access dashboard data via RLS]
```

## 6) Owner checklist
- Run Section 1 SQL in Supabase.
- Configure Auth (invite-only if desired).
- For each user: ensure a `users` row if they need data; create/link a `profiles` row; approve it.
- If using triggers: run Section 4 SQL.
