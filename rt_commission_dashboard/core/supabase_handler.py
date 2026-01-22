"""
Supabase database handler for RT Commission Dashboard.
Implements the same interface as DBHandler but uses Supabase (PostgreSQL) backend.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from rt_commission_dashboard.core.config import config


class SupabaseHandler:
    """Supabase-based database handler (same interface as DBHandler)."""

    def __init__(self, session_token: Optional[str] = None):
        """Initialize Supabase client. Prefer service key if available; otherwise use anon + session JWT."""
        url = config.get_supabase_url()
        service_key = config.get_supabase_service_key()
        anon_key = config.get_supabase_anon_key()

        if not url or not (service_key or anon_key):
            raise ValueError("Missing Supabase credentials: SUPABASE_URL and SUPABASE_ANON_KEY required.")

        key = service_key or anon_key
        self.using_service_key = bool(service_key)

        self.client: Client = create_client(url, key)
        if session_token:
            try:
                # set_session requires a refresh_token string; we only have access_token.
                # Use empty string to satisfy type validation.
                self.client.auth.set_session(session_token, "")
            except Exception as e:
                logging.warning(f"Could not set Supabase session token via set_session: {e}")
                try:
                    # Fallback: directly set auth header for postgrest
                    self.client.postgrest.auth(session_token)
                except Exception as e2:
                    logging.error(f"Failed to set Supabase auth token: {e2}")

        logging.info(f"Connected to Supabase at {url} (service_key={self.using_service_key})")

        # Check if we need to seed mock data (service key only)
        if self.using_service_key:
            self._check_and_seed()

    def _check_and_seed(self):
        """Check if database is empty and seed with mock data if needed."""
        # Skip seeding in JWT-only mode; legacy seeding expected a service key and older schema.
        if not config.is_mock_data_enabled():
            return
        try:
            result = self.client.table('profiles').select('id').limit(1).execute()
            if len(result.data) == 0:
                logging.info("Supabase empty. Skipping seed (requires service key and matching schema).")
        except Exception as e:
            logging.error(f"Error checking database: {e}")

    def _seed_mock_data(self):
        """Seeds the database with test data using custom usernames."""
        import json
        from datetime import timedelta

        logging.info("Seeding Supabase with mock data...")
        domain = config.get_sample_domain()
        admin_email = config.get_admin_email()

        # Get role permissions from config
        admin_perms = json.dumps(config.get_role_permissions('admin'))
        affiliate_perms = json.dumps(config.get_role_permissions('affiliate'))
        ctv_perms = json.dumps(config.get_role_permissions('ctv'))

        # Insert admin first (no parent) - using custom username
        self.client.table('users').insert({
            'id': 'rta_admin',
            'email': admin_email,
            'full_name': 'Super Admin',
            'role': 'admin',
            'permissions': admin_perms,
            'parent_id': None
        }).execute()

        # Insert affiliates with custom usernames
        self.client.table('users').insert({
            'id': 'rta_vytran',
            'email': f'vytran@{domain}',
            'full_name': 'Vy Tran',
            'role': 'affiliate',
            'permissions': affiliate_perms,
            'parent_id': 'rta_admin'
        }).execute()

        self.client.table('users').insert({
            'id': 'rta_traphan',
            'email': f'traphan@{domain}',
            'full_name': 'Tra Phan',
            'role': 'affiliate',
            'permissions': affiliate_perms,
            'parent_id': 'rta_vytran'
        }).execute()

        # Insert CTVs with custom usernames
        self.client.table('users').insert({
            'id': 'rta_minhnguyen',
            'email': f'minhnguyen@{domain}',
            'full_name': 'Minh Nguyen',
            'role': 'ctv',
            'permissions': ctv_perms,
            'parent_id': 'rta_traphan'
        }).execute()

        self.client.table('users').insert({
            'id': 'rta_hangle',
            'email': f'hangle@{domain}',
            'full_name': 'Hang Le',
            'role': 'ctv',
            'permissions': ctv_perms,
            'parent_id': 'rta_vytran'
        }).execute()

        # Insert orphan
        self.client.table('users').insert({
            'id': 'rta_orphan',
            'email': f'orphan@{domain}',
            'full_name': 'Độc Lập',
            'role': 'affiliate',
            'permissions': ctv_perms,
            'parent_id': None
        }).execute()

        # Seed transactions for last 3 months
        # Using millions (VND) to demonstrate different tier rates
        now = datetime.now()
        months_offsets = [0, 1, 2]

        for offset in months_offsets:
            base_date = now - timedelta(days=30 * offset)
            month_str = base_date.strftime('%Y-%m')

            logging.info(f"Seeding transactions for {month_str}...")

            # Create retail sales with varied amounts to trigger different tiers
            # rta_minhnguyen: 50M VND (stays at 20% tier)
            self.create_retail_sale('rta_minhnguyen', 50_000_000.00,
                {'customer': f'Customer A ({month_str})', 'product': 'Enterprise Software License'},
                created_at=base_date.isoformat())

            # rta_hangle: 120M VND (stays at 20% tier)
            self.create_retail_sale('rta_hangle', 120_000_000.00,
                {'customer': f'Customer B ({month_str})', 'product': 'Cloud Services'},
                created_at=base_date.isoformat())

            # rta_traphan: 250M VND (personal 250M + F1 50M from minhnguyen = 300M total → 22% tier)
            self.create_retail_sale('rta_traphan', 250_000_000.00,
                {'customer': f'Customer C ({month_str})', 'product': 'IT Infrastructure'},
                created_at=base_date.isoformat())

            # rta_vytran: 500M VND (personal 500M + F1 370M from traphan/hangle = 870M total → 25% tier)
            self.create_retail_sale('rta_vytran', 500_000_000.00,
                {'customer': f'Customer D ({month_str})', 'product': 'Digital Transformation Project'},
                created_at=base_date.isoformat())

            # === Share-Receive Examples ===

            # Example 1: Same tier sharing (20% tier)
            # rta_hangle brings opportunity, rta_minhnguyen executes the sale
            # Sharer (hangle): Gets 100% of 80M for tier ranking, 50% commission rate
            # Receiver (minhnguyen): Gets 0% for tier ranking, 50% commission rate
            self.create_shared_opportunity('rta_minhnguyen', 'rta_hangle', 80_000_000.00,
                {'customer': f'Customer E ({month_str})', 'product': 'Shared Deal - Training Program', 'note': 'Brought by hangle, executed by minhnguyen'},
                created_at=base_date.isoformat())

            # Example 2: Different tier sharing
            # rta_vytran (25% tier) brings opportunity, rta_traphan (22% tier) executes
            # Sharer (vytran): Gets 100% of 200M for tier ranking → boosts to higher volume
            # Receiver (traphan): Gets 0% for tier ranking, but gets 11% commission (22% * 0.5)
            # Sharer (vytran): Gets 12.5% commission (25% * 0.5)
            self.create_shared_opportunity('rta_traphan', 'rta_vytran', 200_000_000.00,
                {'customer': f'Customer F ({month_str})', 'product': 'Shared Deal - Enterprise Solution', 'note': 'Brought by vytran, executed by traphan'},
                created_at=base_date.isoformat())

        logging.info("Mock data seeding complete!")

    # ========== Transaction Creation Methods ==========

    def create_retail_sale(self, user_id: str, amount: float, metadata: Dict = None, created_at: Optional[str] = None):
        """Creates a standard retail sale."""
        if metadata is None:
            metadata = {}
        if created_at is None:
            created_at = datetime.now().isoformat()

        # Insert transaction - database triggers will handle commission calculation
        result = self.client.table('transactions').insert({
            'user_id': user_id,
            'amount': amount,
            'type': 'retail_sales',
            'status': 'approved',
            'metadata': metadata,
            'created_at': created_at
        }).execute()

        return result.data[0]['id']

    def create_shared_opportunity(self, receiver_id: str, sharer_id: str, amount: float, metadata: Dict = None, created_at: Optional[str] = None):
        """Creates a shared opportunity sale."""
        if metadata is None:
            metadata = {}
        metadata['shared_type'] = 'opportunity'

        if created_at is None:
            created_at = datetime.now().isoformat()

        # Insert transaction - database triggers will handle commission calculation for both users
        result = self.client.table('transactions').insert({
            'user_id': receiver_id,
            'amount': amount,
            'type': 'retail_sales',
            'status': 'approved',
            'metadata': metadata,
            'shared_with_id': sharer_id,
            'created_at': created_at
        }).execute()

        return result.data[0]['id']

    # ========== Commission Calculation Methods ==========
    # NOTE: These methods are DEPRECATED for Supabase
    # Commission calculations are handled by PostgreSQL triggers (see scripts/supabase_setup.sql)
    # Keeping these for reference/backward compatibility only

    def _propagate_monthly_updates(self, start_user_id: str, month: str):
        """Recursively recalculates monthly stats for user and upline."""
        # Update the starting user
        self._update_user_monthly_stats(start_user_id, month)

        # Get parent to propagate
        result = self.client.table('users').select('parent_id').eq('id', start_user_id).execute()
        if result.data and result.data[0]['parent_id']:
            parent_id = result.data[0]['parent_id']
            # Recursively update parent
            self._propagate_monthly_updates(parent_id, month)

    def _update_user_monthly_stats(self, user_id: str, month: str):
        """Recalculates stats for a user in a specific month."""
        # Fetch relevant transactions
        result = self.client.table('transactions')\
            .select('amount, user_id, shared_with_id, created_at')\
            .or_(f'user_id.eq.{user_id},shared_with_id.eq.{user_id}')\
            .eq('type', 'retail_sales')\
            .eq('status', 'approved')\
            .execute()

        # Filter by month (since Supabase doesn't have strftime directly)
        txs = [tx for tx in result.data if tx.get('created_at', '')[:7] == month]

        personal_ranking_vol = 0.0
        vol_pure_retail = 0.0
        vol_shared_out = 0.0
        vol_received = 0.0

        for tx in txs:
            amount = tx['amount']
            tx_user_id = tx['user_id']
            tx_shared_id = tx.get('shared_with_id')

            if tx_user_id == user_id:
                if tx_shared_id is None:
                    # Pure retail
                    personal_ranking_vol += amount
                    vol_pure_retail += amount
                else:
                    # Receiver
                    vol_received += amount
            elif tx_shared_id == user_id:
                # Sharer
                personal_ranking_vol += amount
                vol_shared_out += amount

        # Calculate F1 volume
        f1_result = self.client.table('users').select('id').eq('parent_id', user_id).execute()
        f1_ids = [u['id'] for u in f1_result.data]

        f1_ranking_vol = 0.0
        if f1_ids:
            # Get monthly stats for F1
            stats_ids = [f"{fid}_{month}" for fid in f1_ids]
            stats_result = self.client.table('monthly_stats')\
                .select('personal_sales_volume')\
                .in_('id', stats_ids)\
                .execute()

            for stat in stats_result.data:
                f1_ranking_vol += stat.get('personal_sales_volume', 0)

        # Determine tier rate
        total_ranking_vol = personal_ranking_vol + f1_ranking_vol
        tier_rate = self._calculate_tier_rate(user_id, total_ranking_vol)

        # Calculate commissions
        received_rate = tier_rate * 0.5 if tier_rate > 0 else 0.04

        c_retail = vol_pure_retail * tier_rate
        c_shared = vol_shared_out * (tier_rate * 0.5)
        c_received = vol_received * received_rate

        # Calculate override
        override_comm = 0.0
        for child_id in f1_ids:
            stat_id = f"{child_id}_{month}"
            child_stat_result = self.client.table('monthly_stats')\
                .select('tier_rate, personal_sales_volume, f1_sales_volume')\
                .eq('id', stat_id)\
                .execute()

            if child_stat_result.data:
                child_stat = child_stat_result.data[0]
                child_rate = child_stat.get('tier_rate', 0)

                # Calculate child's leg commission volume
                leg_comm_vol = self._get_leg_commission_volume(child_id, month)

                differential = tier_rate - child_rate
                if differential > 0:
                    override_comm += leg_comm_vol * differential

        total_comm = c_retail + c_shared + c_received + override_comm

        # Upsert monthly stats
        stat_id = f"{user_id}_{month}"
        stat_data = {
            'id': stat_id,
            'user_id': user_id,
            'month': month,
            'personal_sales_volume': personal_ranking_vol,
            'shared_out_volume': vol_shared_out,
            'received_volume': vol_received,
            'f1_sales_volume': f1_ranking_vol,
            'tier_rate': tier_rate,
            'comm_direct': c_retail,
            'comm_shared': c_shared,
            'comm_received': c_received,
            'comm_override': override_comm,
            'total_commission': total_comm
        }

        # Upsert (insert or update)
        self.client.table('monthly_stats').upsert(stat_data).execute()

    def _get_leg_commission_volume(self, root_id: str, month: str) -> float:
        """Recursively sums commissionable volume for a user's entire downline."""
        # Get root's transactions
        result = self.client.table('transactions')\
            .select('amount, shared_with_id, created_at')\
            .or_(f'user_id.eq.{root_id},shared_with_id.eq.{root_id}')\
            .eq('type', 'retail_sales')\
            .eq('status', 'approved')\
            .execute()

        # Filter by month
        txs = [tx for tx in result.data if tx.get('created_at', '')[:7] == month]

        vol = 0.0
        for tx in txs:
            vol += (tx['amount'] / 2) if tx.get('shared_with_id') else tx['amount']

        # Get children
        children_result = self.client.table('users').select('id').eq('parent_id', root_id).execute()
        for child in children_result.data:
            vol += self._get_leg_commission_volume(child['id'], month)

        return vol

    def _calculate_tier_rate(self, user_id: str, total_volume: float) -> float:
        """Calculate tier rate from volume."""
        # Check role
        user_result = self.client.table('users').select('role').eq('id', user_id).execute()
        role = user_result.data[0]['role'] if user_result.data else 'ctv'

        role_rates = config.get_role_rates()
        if role == 'strategic_partner' or role in role_rates:
            return role_rates.get('strategic_partner', 0.35)

        # Lookup tier
        tiers = config.get_commission_tiers()
        sorted_tiers = sorted(tiers, key=lambda x: x['threshold'], reverse=True)

        for tier in sorted_tiers:
            if total_volume > tier['threshold']:
                return tier['rate']
        return 0.0

    # ========== User Methods ==========

    def get_user(self, email: str) -> Optional[Dict]:
        """Fetch user by email."""
        result = self.client.table('users').select('*').eq('email', email).limit(1).execute()
        return result.data[0] if result.data else None

    def get_all_users(self) -> List[Dict]:
        """Fetches all users for admin management."""
        result = self.client.table('users').select('*').order('created_at', desc=True).execute()
        return result.data

    # ========== Profile Methods ==========

    def get_all_profiles(self) -> List[Dict]:
        """Fetches all profiles for admin management."""
        result = self.client.table('profiles').select('*').order('created_at', desc=True).execute()
        return result.data

    def update_profile(self, profile_id: str, updates: Dict) -> bool:
        """Update a profile's details."""
        try:
            self.client.table('profiles').update(updates).eq('id', profile_id).execute()
            return True
        except Exception as e:
            logging.error(f"Failed to update profile {profile_id}: {e}")
            return False

    def approve_profile(self, profile_id: str, approver_id: str) -> bool:
        """Approve a profile and set approved_by and approved_at."""
        from datetime import datetime
        try:
            self.client.table('profiles').update({
                'status': 'approved',
                'approved_by': approver_id,
                'approved_at': datetime.now().isoformat()
            }).eq('id', profile_id).execute()
            return True
        except Exception as e:
            logging.error(f"Failed to approve profile {profile_id}: {e}")
            return False

    # ========== Stats Methods ==========

    def get_kpi_stats(self, user_id: str, month: Optional[int] = None, year: Optional[int] = None) -> Dict:
        """Calculate core KPIs with optional Month/Year filter."""
        # Build month filter
        month_filter = None
        if year and month:
            month_filter = f"{year}-{int(month):02d}"
        elif year:
            month_filter = f"{year}-"  # Will use LIKE for year prefix

        # Handle 'global' case for admin (all users)
        is_global = (user_id == 'global')

        # 1. Revenue (Retail Sales)
        revenue_query = self.client.table('transactions')\
            .select('amount, created_at')\
            .eq('type', 'retail_sales')\
            .eq('status', 'approved')

        if not is_global:
            revenue_query = revenue_query.eq('user_id', user_id)

        if month_filter:
            revenue_data = revenue_query.execute().data
            # Filter by month in Python since Supabase doesn't have strftime
            if year and month:
                revenue_data = [tx for tx in revenue_data if tx.get('created_at', '')[:7] == month_filter]
            else:
                revenue_data = [tx for tx in revenue_data if tx.get('created_at', '').startswith(month_filter)]
            revenue = sum(tx['amount'] for tx in revenue_data)
        else:
            revenue_data = revenue_query.execute().data
            revenue = sum(tx['amount'] for tx in revenue_data)

        # 2. Commission (from monthly_stats)
        if month_filter and not month_filter.endswith('-'):
            # Exact month
            stats_query = self.client.table('monthly_stats')\
                .select('comm_direct, comm_shared, comm_received, comm_override, total_commission')\
                .eq('month', month_filter)
            if not is_global:
                stats_query = stats_query.eq('user_id', user_id)
            stats_result = stats_query.execute()
        elif month_filter:
            # Year prefix
            stats_query = self.client.table('monthly_stats')\
                .select('comm_direct, comm_shared, comm_received, comm_override, total_commission, month')
            if not is_global:
                stats_query = stats_query.eq('user_id', user_id)
            stats_result = stats_query.execute()
            stats_result.data = [s for s in stats_result.data if s.get('month', '').startswith(month_filter)]
        else:
            # All time
            stats_query = self.client.table('monthly_stats')\
                .select('comm_direct, comm_shared, comm_received, comm_override, total_commission')
            if not is_global:
                stats_query = stats_query.eq('user_id', user_id)
            stats_result = stats_query.execute()

        c_direct = sum(s.get('comm_direct', 0) for s in stats_result.data)
        c_shared = sum(s.get('comm_shared', 0) for s in stats_result.data)
        c_received = sum(s.get('comm_received', 0) for s in stats_result.data)
        c_override = sum(s.get('comm_override', 0) for s in stats_result.data)
        total_comm = sum(s.get('total_commission', 0) for s in stats_result.data)

        # 3. KPI Rewards
        kpi_query = self.client.table('transactions')\
            .select('amount, created_at')\
            .eq('type', 'kpi_reward')\
            .in_('status', ['approved', 'paid'])

        if not is_global:
            kpi_query = kpi_query.eq('user_id', user_id)

        kpi_data = kpi_query.execute().data
        if month_filter and not month_filter.endswith('-'):
            kpi_data = [tx for tx in kpi_data if tx.get('created_at', '')[:7] == month_filter]
        elif month_filter:
            kpi_data = [tx for tx in kpi_data if tx.get('created_at', '').startswith(month_filter)]
        kpi_reward = sum(tx['amount'] for tx in kpi_data)

        # 4. New Customers (count transactions with customer metadata)
        customers_query = self.client.table('transactions')\
            .select('id, created_at')\
            .eq('type', 'retail_sales')

        if not is_global:
            customers_query = customers_query.eq('user_id', user_id)

        cust_data = customers_query.execute().data
        if month_filter and not month_filter.endswith('-'):
            cust_data = [tx for tx in cust_data if tx.get('created_at', '')[:7] == month_filter]
        elif month_filter:
            cust_data = [tx for tx in cust_data if tx.get('created_at', '').startswith(month_filter)]
        new_customers = len(cust_data)

        # 5. Network Size (snapshot - always total)
        if is_global:
            # For global stats, count all users
            all_users = self.client.table('users').select('id').execute()
            network_size = len(all_users.data)
        else:
            network_size = len(self.get_downline_flat(user_id))

        return {
            'revenue': revenue,
            'commission': total_comm + kpi_reward,
            'commission_share': total_comm,
            'comm_direct': c_direct,
            'comm_shared': c_shared,
            'comm_received': c_received,
            'comm_override': c_override,
            'kpi_reward': kpi_reward,
            'new_customers': new_customers,
            'network_size': network_size
        }

    def get_global_stats(self, month: Optional[int] = None, year: Optional[int] = None) -> Dict:
        """Calculate system-wide KPIs for admins."""
        # Build month filter
        month_filter = None
        if year and month:
            month_filter = f"{year}-{int(month):02d}"
        elif year:
            month_filter = f"{year}-"

        # 1. Revenue (Retail Sales, Approved)
        rev_query = self.client.table('transactions')\
            .select('amount, created_at')\
            .eq('type', 'retail_sales')\
            .eq('status', 'approved')
        
        rev_data = rev_query.execute().data
        if month_filter:
            rev_data = [tx for tx in rev_data if tx.get('created_at', '').startswith(month_filter)]
        
        revenue = sum(tx['amount'] for tx in rev_data)

        # 2. Commission (from monthly_stats)
        # Note: monthly_stats ID is user_id + '_' + month (YYYY-MM)
        # We can query by month column directly if we have exact month
        
        stats_query = self.client.table('monthly_stats')\
            .select('comm_direct, comm_shared, comm_received, comm_override, total_commission, month')
            
        if month_filter and not month_filter.endswith('-'):
             stats_query = stats_query.eq('month', month_filter)
        
        stats_result = stats_query.execute()
        stats_data = stats_result.data
        
        # If year-only filter, we have to filter in code or use 'like' if supported on 'month' column
        # efficient to filter in code for now as dataset isn't massive yet
        if month_filter and month_filter.endswith('-'):
             stats_data = [s for s in stats_data if s.get('month', '').startswith(month_filter)]

        c_direct = sum(s.get('comm_direct', 0) for s in stats_data)
        c_shared = sum(s.get('comm_shared', 0) for s in stats_data)
        c_received = sum(s.get('comm_received', 0) for s in stats_data)
        c_override = sum(s.get('comm_override', 0) for s in stats_data)
        total_comm = sum(s.get('total_commission', 0) for s in stats_data)

        # 3. KPI Rewards
        kpi_query = self.client.table('transactions')\
            .select('amount, created_at')\
            .eq('type', 'kpi_reward')\
            .in_('status', ['approved', 'paid'])
            
        kpi_data = kpi_query.execute().data
        if month_filter:
             kpi_data = [tx for tx in kpi_data if tx.get('created_at', '').startswith(month_filter)]
             
        kpi_reward = sum(tx['amount'] for tx in kpi_data)

        # 4. New Customers
        cust_query = self.client.table('transactions')\
            .select('id, created_at')\
            .eq('type', 'retail_sales')\
            .neq('metadata', '{}') # Simple check, ideally filter by metadata->>customer exists
            
        # Since metadata filtering is tricky without complex postgrest, we'll fetch retail sales and check if they have customer data
        # actually, existing get_kpi_stats logic just checked retail sales count mainly, or specific metadata. 
        # Let's align with logic: count retail sales that are "new customers". 
        # For now, let's assume all retail sales might imply customer activity, but the previous SQL used `metadata LIKE '%customer%'`
        # We'll replicate fetching and checking.
        cust_data = cust_query.execute().data
        if month_filter:
             cust_data = [tx for tx in cust_data if tx.get('created_at', '').startswith(month_filter)]
        
        # Approximate "metadata has customer" check in python
        # We need to fetch metadata to check it. 
        # Refetching with metadata
        cust_full_query = self.client.table('transactions')\
            .select('metadata, created_at')\
            .eq('type', 'retail_sales')\
            .eq('status', 'approved') # Only approved sales count as customer acquisition usually?
            
        cust_full_data = cust_full_query.execute().data
        if month_filter:
             cust_full_data = [tx for tx in cust_full_data if tx.get('created_at', '').startswith(month_filter)]
             
        new_customers = sum(1 for tx in cust_full_data if 'customer' in tx.get('metadata', {}))

        # 5. Network Size
        # Count all users
        all_users_count = self.client.table('users').select('id', count='exact', head=True).execute().count

        return {
            'revenue': revenue,
            'commission': total_comm + kpi_reward,
            'commission_share': total_comm,
            'comm_direct': c_direct,
            'comm_shared': c_shared,
            'comm_received': c_received,
            'comm_override': c_override,
            'kpi_reward': kpi_reward,
            'new_customers': new_customers,
            'network_size': all_users_count if all_users_count is not None else 0
        }

    def get_monthly_sales(self, user_id: str, year: Optional[int] = None) -> List[tuple]:
        """Get monthly sales aggregated."""
        # Handle 'global' case
        if user_id == 'global':
            return self.get_global_monthly_sales(year)

        # Get all transactions for this user
        query = self.client.table('transactions')\
            .select('amount, created_at')\
            .eq('user_id', user_id)\
            .eq('type', 'retail_sales')\
            .eq('status', 'approved')

        txs = query.execute().data

        # Filter by year if specified
        if year:
            year_str = str(year)
            txs = [tx for tx in txs if tx.get('created_at', '').startswith(year_str)]

        # Group by month
        from collections import defaultdict
        by_month = defaultdict(float)

        for tx in txs:
            month = tx.get('created_at', '')[:7]  # YYYY-MM
            by_month[month] += tx['amount']

        # Return as sorted list of tuples
        return sorted(by_month.items())

    def get_global_monthly_sales(self, year: Optional[int] = None) -> List[tuple]:
        """Get global monthly sales (all users combined)."""
        # Get all transactions
        query = self.client.table('transactions')\
            .select('amount, created_at')\
            .eq('type', 'retail_sales')\
            .eq('status', 'approved')

        txs = query.execute().data

        # Filter by year if specified
        if year:
            year_str = str(year)
            txs = [tx for tx in txs if tx.get('created_at', '').startswith(year_str)]

        # Group by month
        from collections import defaultdict
        by_month = defaultdict(float)

        for tx in txs:
            month = tx.get('created_at', '')[:7]  # YYYY-MM
            by_month[month] += tx['amount']

        # Return as sorted list of tuples
        return sorted(by_month.items())

    def get_transactions_filtered(self, user_id: Optional[str], month: Optional[int] = None, year: Optional[int] = None, type_filter: Optional[str] = None, is_admin: bool = False) -> List[Dict]:
        """Fetch transactions with optional filters.

        Args:
            user_id: Filter by this user. If None and is_admin=True, returns all transactions.
            is_admin: If True and user_id is None, skips user filtering (admin sees all).
        """
        query = self.client.table('transactions').select('*')

        # User filtering: admin with user_id=None sees all, otherwise filter by user
        if user_id is not None:
            # Filter by user_id OR shared_with_id
            query = query.or_(f"user_id.eq.{user_id},shared_with_id.eq.{user_id}")
        elif not is_admin:
            # Non-admin with no user_id should see nothing
            return []
        
        # Date Filter
        # Supabase doesn't support complex date part filtering easily in one go without custom functions or ranges.
        # We'll fetch and filter in Python if needed, OR use text match for starters (YYYY-MM)
        
        # Note: 'created_at' is ISO string. 
        if year and month:
            # Filter by YYYY-MM
            start_date = f"{year}-{int(month):02d}-01"
            # Calculate next month for upper bound
            if int(month) == 12:
                end_date = f"{int(year)+1}-01-01"
            else:
                end_date = f"{year}-{int(month)+1:02d}-01"
            
            query = query.gte('created_at', start_date).lt('created_at', end_date)
            
        elif year:
            start_date = f"{year}-01-01"
            end_date = f"{int(year)+1}-01-01"
            query = query.gte('created_at', start_date).lt('created_at', end_date)
            
        # Type Filter
        if type_filter and type_filter != 'All':
            db_type_map = {
                'Retail': 'retail_sales',
                'Share': 'commission_sharing', # Note: In Supabase/New Schema we handle split logic differently, but 'type' column still exists.
                # Actually, in Supabase schema we treat everything as 'retail_sales' mostly?
                # Let's check schema/seed. Seed uses 'retail_sales' for everything. 
                # 'commission_sharing' might not be used in new engine?
                # DB Schema says: CHECK (type IN ('retail_sales', 'commission_sharing', 'kpi_reward'))
                # Seed uses 'retail_sales' even for Shared Opps.
                # So filtering by "Share" might yield nothing if we only look for 'commission_sharing'.
                # But let's stick to map for now.
                'Receive': 'commission_sharing', 
                'Reward': 'kpi_reward'
            }
            mapped_type = db_type_map.get(type_filter)
            if mapped_type:
                query = query.eq('type', mapped_type)
        
        query = query.order('created_at', desc=True)
        
        result = query.execute()
        return result.data

    # ========== Network Methods ==========

    def get_downline_flat(self, root_user_id: str) -> List[Dict]:
        """Get downline as flat list using recursive query."""
        # For Supabase, we'll do iterative traversal
        # (Could also create a PostgreSQL recursive CTE function)
        result = []
        queue = [root_user_id]
        visited = set()

        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue

            visited.add(current_id)

            # Get this user
            user_result = self.client.table('users')\
                .select('id, full_name, role, parent_id')\
                .eq('id', current_id)\
                .execute()

            if user_result.data:
                user = user_result.data[0]
                result.append(user)

                # Get children
                children_result = self.client.table('users')\
                    .select('id')\
                    .eq('parent_id', current_id)\
                    .execute()

                for child in children_result.data:
                    queue.append(child['id'])

        return result

    def get_downline_nested(self, root_user_id: str) -> List[Dict]:
        """Get downline as nested tree."""
        flat_list = self.get_downline_flat(root_user_id)
        
        # Build tree from flat list
        nodes_by_id = {u['id']: {**u, 'children': []} for u in flat_list}
        tree = []
        
        for u in flat_list:
            node = nodes_by_id[u['id']]
            
            # If current node is the root we asked for OR its parent is not in our list, it's a top-level node for this view
            if u['id'] == root_user_id:
                tree.append(node)
                continue
                
            parent_id = u.get('parent_id')
            if parent_id and parent_id in nodes_by_id:
                nodes_by_id[parent_id]['children'].append(node)
            else:
                # Should not happen in a strict tree from get_downline_flat(root), 
                # but if we have broken links or it's a root:
                # If parent not found, treated as root of this subgraph
                pass 
                
        # If the root_user_id wasn't in the list (e.g. strict strict), we might rely on the logic above.
        # But get_downline_flat typically includes the root. 
        
        return tree

    def get_entire_network_nested(self) -> List[Dict]:
        """Get entire network for admins."""
        # Fetch all users
        result = self.client.table('users').select('*').execute()
        flat_list = result.data
        
        nodes_by_id = {u['id']: {**u, 'children': []} for u in flat_list}
        forest = []
        
        for u in flat_list:
            node = nodes_by_id[u['id']]
            parent_id = u.get('parent_id')
            
            if parent_id and parent_id in nodes_by_id:
                nodes_by_id[parent_id]['children'].append(node)
            else:
                # No parent, or parent not in DB -> Root of a tree
                forest.append(node)
                
        return forest

    def get_viewable_users(self, user_id: str, role: str) -> List[Dict]:
        """Get users viewable by current user."""
        results = []
        if role == 'admin':
            # Admins see all users
            all_users = self.client.table('users').select('id, full_name, role').order('created_at', desc=True).execute()
            results = all_users.data
        else:
            # Regular users see themselves
            self_user = self.client.table('users').select('id, full_name, role').eq('id', user_id).execute()
            if self_user.data:
                results.append(self_user.data[0])

            # Plus their downline
            downline = self.get_downline_flat(user_id)
            results.extend(downline)

        return [dict(id=u['id'], label=f"{u['full_name']} ({u['role']})", role=u['role']) for u in results]

    # --- KPI helpers ---
    def _filter_month_year(self, rows, month=None, year=None, date_key='created_at'):
        if not month and not year:
            return rows
        out = []
        for r in rows:
            dt = r.get(date_key)
            if not dt:
                continue
            if isinstance(dt, str):
                if year and month:
                    if not dt.startswith(f"{year}-{int(month):02d}"):
                        continue
                elif year:
                    if not dt.startswith(f"{year}-"):
                        continue
            out.append(r)
        return out

    def _sum_field(self, rows, field):
        return sum(float(r.get(field) or 0) for r in rows)

    def get_kpi_stats(self, user_id: str, month: Optional[int] = None, year: Optional[int] = None) -> Dict:
        month_val = str(month) if month else None
        year_val = str(year) if year else None
        # Transactions for revenue/shared
        tx_query = self.client.table('transactions').select('*').eq('type', 'retail_sales').eq('status', 'approved')\
            .or_(f"user_id.eq.{user_id},shared_with_id.eq.{user_id}")
        tx_rows = tx_query.execute().data or []
        tx_rows = self._filter_month_year(tx_rows, month_val, year_val)

        revenue = sum(t.get('amount') or 0 for t in tx_rows if t.get('user_id') == user_id)
        shared_out_amount = sum(t.get('amount') or 0 for t in tx_rows if t.get('shared_with_id') == user_id)
        shared_received_amount = sum(t.get('amount') or 0 for t in tx_rows if t.get('user_id') == user_id and t.get('shared_with_id'))

        # monthly_stats for commissions/tier/ranking
        ms_query = self.client.table('monthly_stats').select('*').eq('user_id', user_id)
        if year_val and month_val:
            ms_query = ms_query.eq('month', f"{year_val}-{int(month_val):02d}")
        elif year_val:
            ms_query = ms_query.like('month', f"{year_val}-%")
        ms_rows = ms_query.execute().data or []

        c_direct = self._sum_field(ms_rows, 'comm_direct')
        c_shared = self._sum_field(ms_rows, 'comm_shared')
        c_received = self._sum_field(ms_rows, 'comm_received')
        c_override = self._sum_field(ms_rows, 'comm_override')
        total_comm = self._sum_field(ms_rows, 'total_commission')
        ranking_volume = self._sum_field(ms_rows, 'personal_sales_volume') + self._sum_field(ms_rows, 'shared_out_volume') + self._sum_field(ms_rows, 'f1_sales_volume')
        tier_rate = max((float(r.get('tier_rate') or 0) for r in ms_rows), default=0.0)

        # KPI rewards
        kpi_tx = [t for t in tx_rows if t.get('type') == 'kpi_reward' and t.get('status') in ('approved', 'paid')]
        kpi_reward = sum(t.get('amount') or 0 for t in kpi_tx)

        # New customers: metadata contains 'customer'
        new_customers = 0
        for t in tx_rows:
            meta = t.get('metadata') or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            if isinstance(meta, dict) and 'customer' in meta:
                new_customers += 1

        network_size = len(self.get_downline_flat(user_id))

        return {
            'revenue': revenue,
            'shared_out_amount': shared_out_amount,
            'shared_received_amount': shared_received_amount,
            'commission': total_comm + kpi_reward,
            'commission_share': total_comm,
            'comm_direct': c_direct,
            'comm_shared': c_shared,
            'comm_received': c_received,
            'comm_override': c_override,
            'tier_rate': tier_rate,
            'ranking_volume': ranking_volume,
            'kpi_reward': kpi_reward,
            'new_customers': new_customers,
            'network_size': network_size
        }

    def get_global_stats(self, month: Optional[int] = None, year: Optional[int] = None) -> Dict:
        month_val = str(month) if month else None
        year_val = str(year) if year else None

        tx_query = self.client.table('transactions').select('*').eq('type', 'retail_sales').eq('status', 'approved')
        tx_rows = self._filter_month_year(tx_query.execute().data or [], month_val, year_val)
        revenue = sum(t.get('amount') or 0 for t in tx_rows)
        shared_out_amount = sum(t.get('amount') or 0 for t in tx_rows if t.get('shared_with_id'))
        shared_received_amount = shared_out_amount

        ms_query = self.client.table('monthly_stats').select('*')
        if year_val and month_val:
            ms_query = ms_query.eq('month', f"{year_val}-{int(month_val):02d}")
        elif year_val:
            ms_query = ms_query.like('month', f"{year_val}-%")
        ms_rows = ms_query.execute().data or []

        def ms_sum(field):
            return sum(float(r.get(field) or 0) for r in ms_rows)

        c_direct = ms_sum('comm_direct')
        c_shared = ms_sum('comm_shared')
        c_received = ms_sum('comm_received')
        c_override = ms_sum('comm_override')
        total_comm = ms_sum('total_commission')
        ranking_volume = ms_sum('personal_sales_volume') + ms_sum('shared_out_volume') + ms_sum('f1_sales_volume')
        tier_rate = max((float(r.get('tier_rate') or 0) for r in ms_rows), default=0.0)

        kpi_tx = [t for t in tx_rows if t.get('type') == 'kpi_reward' and t.get('status') in ('approved', 'paid')]
        kpi_reward = sum(t.get('amount') or 0 for t in kpi_tx)

        new_customers = 0
        for t in tx_rows:
            meta = t.get('metadata') or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            if isinstance(meta, dict) and 'customer' in meta:
                new_customers += 1

        users_count = self.client.table('users').select('id', count='exact', head=True).execute().count or 0

        return {
            'revenue': revenue,
            'shared_out_amount': shared_out_amount,
            'shared_received_amount': shared_received_amount,
            'commission': total_comm + kpi_reward,
            'commission_share': total_comm,
            'comm_direct': c_direct,
            'comm_shared': c_shared,
            'comm_received': c_received,
            'comm_override': c_override,
            'ranking_volume': ranking_volume,
            'tier_rate': tier_rate,
            'kpi_reward': kpi_reward,
            'new_customers': new_customers,
            'network_size': users_count
        }

    def get_monthly_sales(self, user_id: str, year: Optional[int] = None) -> List[tuple]:
        """Aggregates approved retail sales by month for a user."""
        if user_id == 'global':
            return self.get_global_monthly_sales(year)

        query = self.client.table('transactions')\
            .select('amount, created_at')\
            .eq('user_id', user_id)\
            .eq('type', 'retail_sales')\
            .eq('status', 'approved')
        txs = query.execute().data or []
        if year:
            txs = [tx for tx in txs if tx.get('created_at', '').startswith(f"{year}-")]

        from collections import defaultdict
        monthly = defaultdict(float)
        for tx in txs:
            month = tx.get('created_at', '')[:7]
            monthly[month] += tx.get('amount') or 0
        return sorted(monthly.items(), key=lambda x: x[0])

    def get_global_monthly_sales(self, year: Optional[int] = None) -> List[tuple]:
        query = self.client.table('transactions')\
            .select('amount, created_at')\
            .eq('type', 'retail_sales')\
            .eq('status', 'approved')
        txs = query.execute().data or []
        if year:
            txs = [tx for tx in txs if tx.get('created_at', '').startswith(f"{year}-")]
        from collections import defaultdict
        monthly = defaultdict(float)
        for tx in txs:
            month = tx.get('created_at', '')[:7]
            monthly[month] += tx.get('amount') or 0
        return sorted(monthly.items(), key=lambda x: x[0])
