import sqlite3
import logging
from datetime import datetime
from rt_commission_dashboard.core.paths import get_db_path
from rt_commission_dashboard.core.config import config

class DBHandler:
    def __init__(self, db_path=None):
        self.db_path = db_path if db_path else str(get_db_path())
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initializes the database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Users Table (Affiliates/Admins)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT,
                    role TEXT DEFAULT 'ctv', -- admin, partner, pro_agent, agent, ctv
                    permissions TEXT, -- JSON list of Q1-Q4
                    parent_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(parent_id) REFERENCES users(id)
                )
            ''')

            # Transactions Table (Commissions/Revenue)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    type TEXT NOT NULL, -- retail_sales, commission_sharing, kpi_reward
                    status TEXT DEFAULT 'pending', 
                    reference_id TEXT, -- Link to source transaction
                    shared_with_id TEXT, -- For Shared Opportunity: Link to the other beneficiary
                    metadata TEXT, -- JSON for Customer info, Product details
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(shared_with_id) REFERENCES users(id)
                )
            ''')
            # Monthly Stats Table (Stateful Report)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monthly_stats (
                    id TEXT PRIMARY KEY, -- user_id + '_' + month
                    user_id TEXT NOT NULL,
                    month TEXT NOT NULL, -- YYYY-MM
                    personal_sales_volume REAL DEFAULT 0, -- Direct retail sales (100% for tier ranking)
                    shared_out_volume REAL DEFAULT 0, -- Volume shared with others (100% for tier ranking)
                    received_volume REAL DEFAULT 0, -- Volume received from others (0% for tier ranking)
                    f1_sales_volume REAL DEFAULT 0,
                    tier_rate REAL DEFAULT 0,
                    comm_direct REAL DEFAULT 0, -- From Personal Retail
                    comm_shared REAL DEFAULT 0, -- From Shared-Out
                    comm_received REAL DEFAULT 0, -- From Received
                    comm_override REAL DEFAULT 0, -- From Downlines
                    total_commission REAL DEFAULT 0, -- Sum of above
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            conn.commit()
            
            # Check if empty
            cursor.execute('SELECT COUNT(*) FROM users')
            if cursor.fetchone()[0] == 0:
                self._seed_mock_data()
            else:
                self._clean_invalid_users(conn)

    def _clean_invalid_users(self, conn):
        """Removes users with legacy roles (Partner, Pro Agent, Agent)."""
        cursor = conn.cursor()
        # Roles NOT in the approved list
        cursor.execute('''
            DELETE FROM users 
            WHERE role NOT IN ('admin', 'affiliate', 'ctv')
        ''')
        if cursor.rowcount > 0:
            logging.info(f"Cleaned up {cursor.rowcount} invalid legacy users.")
            conn.commit()

    def _seed_mock_data(self):
        """Seeds the database with test data using configurable values."""
        import json
        from datetime import timedelta
        
        if not config.is_mock_data_enabled():
            return
            
        logging.info("Seeding DB with mock data...")
        domain = config.get_sample_domain()
        admin_email = config.get_admin_email()
        
        # Get role permissions from config
        admin_perms = json.dumps(config.get_role_permissions('admin'))
        affiliate_perms = json.dumps(config.get_role_permissions('affiliate'))  
        ctv_perms = json.dumps(config.get_role_permissions('ctv'))
        
        users = [
            ('u_admin', admin_email, 'Super Admin', 'admin', admin_perms, None),
            
            # Affiliate (Đại lý) - Level 1
            ('u_aff1', f'daily1@{domain}', 'Đại lý A', 'affiliate', affiliate_perms, 'u_admin'),
            
            # Affiliate (Đại lý) - Level 2 (Child of Affiliate 1)
            ('u_aff2', f'daily2@{domain}', 'Đại lý B', 'affiliate', affiliate_perms, 'u_aff1'),
            
            # Collaborator (CTV) - Child of Affiliate 2
            ('u_ctv1', f'ctv1@{domain}', 'CTV X', 'ctv', ctv_perms, 'u_aff2'),
            
            # Collaborator (CTV) - Direct Child of Affiliate 1
            ('u_ctv2', f'ctv2@{domain}', 'CTV Y', 'ctv', ctv_perms, 'u_aff1'),
            
            # Orphan User (No Parent)
            ('u_orphan', f'orphan@{domain}', 'Độc Lập', 'affiliate', ctv_perms, None),
        ]
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany('INSERT INTO users (id, email, full_name, role, permissions, parent_id) VALUES (?,?,?,?,?,?)', users)
            conn.commit()

        # Seed transactions for last 3 months
        now = datetime.now()
        months_offsets = [0, 1, 2] # Current, Last, 2-Prev
        
        for offset in months_offsets:
            # Approx logic (just subtract 30 days * offset)
            base_date = now - timedelta(days=30 * offset)
            month_str = base_date.strftime('%Y-%m') # For display logic only
            
            logging.info(f"Seeding for {month_str}...")
            
            # Use helpers to trigger calculation
            # Retail Sales
            self.create_retail_sale('u_ctv1', 500.00, {'customer': f'Cust A ({month_str})', 'product': 'Shoes'}, created_at=base_date)
            self.create_retail_sale('u_aff2', 1200.00, {'customer': f'Cust B ({month_str})', 'product': 'Suit'}, created_at=base_date)
            self.create_retail_sale('u_orphan', 300.00, {'customer': f'Cust C ({month_str})', 'product': 'T-Shirt'}, created_at=base_date)
            
            # Commissions (Sharing) - Manual for special types
            # Note: _create_transaction handles normal inserts. 
            # We can use helpers or direct manual insert if needed for specific 'commission_sharing' types not covered by create_retail_sale
            # But wait, create_retail_sale IS retail. 'commission_sharing' usually generated by engine. 
            # The previous seed manually inserted 'commission_sharing' transactions as 'tx_3', 'tx_4'. 
            # If we want realistic stats, we should rely on the engine (create_retail_sale triggers propagation).
            # But the engine writes to 'monthly_stats', it does NOT create 'commission_sharing' TRANSACTION records (those are typically payouts or ledger entries created later).
            # The Dashboard uses 'monthly_stats' primarily now.
            # So creating retail sales is enough to populate the graph and numbers.
            
            # Legacy/Manual transactions for variety (Refunds, etc)
            if offset == 0:
                 # Only current month has pending/refunds
                 self._create_transaction('u_ctv2', 100.00, 'retail_sales', {'customer': 'Cust D', 'reason': 'Faulty'}, created_at=base_date, status='refunded')
                 self._create_transaction('u_aff1', 50.00, 'retail_sales', {'customer': 'Cust E', 'status': 'Pending'}, created_at=base_date, status='pending')
                 
                 # Manual Reward
                 self._create_transaction('u_aff1', 5000.00, 'kpi_reward', {'period': month_str, 'note': 'Bonus'}, created_at=base_date)

    def create_retail_sale(self, user_id, amount, metadata={}, created_at=None):
        """Creates a standard retail sale."""
        return self._create_transaction(user_id, amount, 'retail_sales', metadata, shared_with_id=None, created_at=created_at)

    def create_shared_opportunity(self, receiver_id, sharer_id, amount, metadata={}, created_at=None):
        """Creates a shared opportunity sale (Ranking Vol doubled, Comm Vol split)."""
        metadata['shared_type'] = 'opportunity'
        return self._create_transaction(receiver_id, amount, 'retail_sales', metadata, shared_with_id=sharer_id, created_at=created_at)

    def _create_transaction(self, user_id, amount, type, metadata, shared_with_id=None, created_at=None, status='approved'):
        import json
        
        # Default to now if not provided
        if created_at is None:
            created_at = datetime.now()
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            sale_id = f"sale_{created_at.timestamp()}_{user_id}_{amount}"
            cursor.execute('''
                INSERT INTO transactions (id, user_id, amount, type, status, metadata, shared_with_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sale_id, user_id, amount, type, status, json.dumps(metadata), shared_with_id, created_at))
            conn.commit()
            
            # Trigger updates for BOTH parties if shared, ONLY if approved
            if status == 'approved':
                tx_month = created_at.strftime('%Y-%m')
                self._propagate_monthly_updates(user_id, tx_month)
                
                if shared_with_id:
                    self._propagate_monthly_updates(shared_with_id, tx_month)
                
            return sale_id

    def _propagate_monthly_updates(self, start_user_id, month):
        """Recursively recalculates monthly stats for user and upline."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Initial User (Seller)
            # Find their Upline Chain to propagate updates
            # (We could do this iteratively: Update user -> Update Parent -> Update Grandparent...)
            
            # 1. Update the starting user
            self._update_user_monthly_stats(cursor, start_user_id, month)
            conn.commit()
            
            # 2. Get Parent to propagate
            cursor.execute("SELECT parent_id FROM users WHERE id = ?", (start_user_id,))
            row = cursor.fetchone()
            if row and row[0]:
                parent_id = row[0]
                # Recursively update parent
                # (Ideally we queue this, but for Phase 1 synchronous is fine)
                self._propagate_monthly_updates(parent_id, month)

    def _update_user_monthly_stats(self, cursor, user_id, month):
        """Recalculates stats. Handles Shared Opportunity splitting."""
        
        # 1. Fetch relevant sales to calculate separate volumes
        # Logic Update per User Request:
        # - Ranking Volume: Include "Retail" (Pure) + "Shared-Out" (Where I am sharer).
        #   - EXCLUDE "Received" (Where I am receiver).
        # - Commission:
        #   - Pure Retail: 100% Rate
        #   - Shared-Out: 50% Rate
        #   - Received: 50% Rate
        
        cursor.execute('''
            SELECT amount, user_id, shared_with_id 
            FROM transactions 
            WHERE (user_id = ? OR shared_with_id = ?)
            AND type = 'retail_sales' AND status = 'approved'
            AND strftime('%Y-%m', created_at) = ?
        ''', (user_id, user_id, month))
        
        txs = cursor.fetchall()
        
        personal_ranking_vol = 0.0
        
        # Accumulators for Commission Calculation
        vol_pure_retail = 0.0
        vol_shared_out = 0.0 # I shared with someone (I am shared_with_id)
        vol_received = 0.0   # Someone shared with me (I am user_id, shared_with exists)
        
        for amount, tx_user_id, tx_shared_id in txs:
            if tx_user_id == user_id:
                if tx_shared_id is None:
                    # Pure Retail
                    personal_ranking_vol += amount
                    vol_pure_retail += amount
                else:
                    # I am Receiver (tx_user_id=Me, shared_id=Someone)
                    # ranking_vol: DO NOT COUNT
                    vol_received += amount
            elif tx_shared_id == user_id:
                # I am Sharer (tx_shared_id=Me)
                # ranking_vol: COUNT
                personal_ranking_vol += amount
                vol_shared_out += amount

        # 2. Calculate F1 Volume (Ranking Volume from Direct Downlines)
        # "Total personal sales from direct agents"
        # CRITICAL: For the Upline (Me), we must NOT double conflict shared sales.
        # Even though C and D both get 50M "Credit" for ranking, I (B) only see 50M actual volume flowing up.
        # So we sum the Transactions where the *Owner* (user_id) is an F1.
        
        cursor.execute("SELECT id FROM users WHERE parent_id = ?", (user_id,))
        f1_ids = [r[0] for r in cursor.fetchall()]
        
        f1_ranking_vol = 0.0
        
        if f1_ids:
            placeholders = ','.join('?' * len(f1_ids))
            ids_month = [f"{uid}_{month}" for uid in f1_ids]
            
            cursor.execute(f'''
                SELECT SUM(personal_sales_volume) 
                FROM monthly_stats 
                WHERE id IN ({','.join(['?']*len(ids_month))})
            ''', ids_month)
            res = cursor.fetchone()
            f1_ranking_vol = res[0] if res and res[0] else 0.0

        # 3. Determine Tier (Based on Ranking Volume)
        total_ranking_vol = personal_ranking_vol + f1_ranking_vol
        tier_rate = self._calculate_tier_rate(cursor, user_id, total_ranking_vol)
        
        # 4. Calculate Commission
        # Direct Commission
        # Rate: Based on Tier
        # - Retail: 100% of Rate
        # - Shared-Out: 50% of Rate
        # - Received: 
        #   - If Ranking Vol > 0: 50% of Rate
        #   - If Ranking Vol == 0: 4% (Fixed 'inactive' rate)
        
        received_rate = 0.0
        if tier_rate > 0:
            received_rate = tier_rate * 0.5
        else:
            # Fallback for 0-volume users receiving opportunity
            # Access config safely
            comm_config = getattr(config, 'config_data', {}).get('commission', {})
            received_rate = comm_config.get('inactive_received_rate', 0.04)

        c_retail = vol_pure_retail * tier_rate
        c_shared = vol_shared_out * (tier_rate * 0.5)
        c_received = vol_received * received_rate
        
        override_comm = 0.0
        
        for child_id in f1_ids:
            stat_id = f"{child_id}_{month}"
            cursor.execute("SELECT tier_rate, personal_sales_volume, f1_sales_volume FROM monthly_stats WHERE id = ?", (stat_id,))
            child_stat = cursor.fetchone()
            
            if child_stat:
                child_rate = child_stat[0]
                
                # Calculate Child's Leg Commission Volume recursively for differential
                leg_comm_vol = self._get_leg_commission_volume(cursor, child_id, month)
                
                differential = tier_rate - child_rate
                if differential > 0:
                    override_comm += leg_comm_vol * differential

        total_comm = c_retail + c_shared + c_received + override_comm

        # 5. Upsert
        stat_id = f"{user_id}_{month}"
        cursor.execute('''
            INSERT INTO monthly_stats (
                id, user_id, month, 
                personal_sales_volume, shared_out_volume, received_volume, 
                f1_sales_volume, tier_rate, 
                comm_direct, comm_shared, comm_received, comm_override,
                total_commission, last_updated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                personal_sales_volume=excluded.personal_sales_volume,
                shared_out_volume=excluded.shared_out_volume,
                received_volume=excluded.received_volume,
                f1_sales_volume=excluded.f1_sales_volume,
                tier_rate=excluded.tier_rate,
                comm_direct=excluded.comm_direct,
                comm_shared=excluded.comm_shared,
                comm_received=excluded.comm_received,
                comm_override=excluded.comm_override,
                total_commission=excluded.total_commission,
                last_updated=CURRENT_TIMESTAMP
        ''', (stat_id, user_id, month, personal_ranking_vol, vol_shared_out, vol_received, f1_ranking_vol, tier_rate, 
              c_retail, c_shared, c_received, override_comm, total_comm))

    def _get_leg_commission_volume(self, cursor, root_id, month):
        """Recursively sums commissionable volume for a user's entire downline."""
        # 1. Root Personal Comm Vol
        cursor.execute('''
            SELECT amount, shared_with_id 
            FROM transactions 
            WHERE (user_id = ? OR shared_with_id = ?)
            AND type = 'retail_sales' AND status = 'approved'
            AND strftime('%Y-%m', created_at) = ?
        ''', (root_id, root_id, month))
        
        vol = 0.0
        for amt, shared in cursor.fetchall():
            vol += (amt / 2) if shared else amt
            
        # 2. Children
        cursor.execute("SELECT id FROM users WHERE parent_id = ?", (root_id,))
        children = cursor.fetchall()
        for child in children:
            vol += self._get_leg_commission_volume(cursor, child[0], month)
            
        return vol

    def _calculate_tier_rate(self, cursor, user_id, total_volume):
        """Helper to lookup tier rate from config."""
        # 1. Check Role
        cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
        res = cursor.fetchone()
        role = res[0] if res else 'ctv'
        
        role_rates = config.get_role_rates()
        if role == 'strategic_partner' or role in role_rates:
             return role_rates.get('strategic_partner', 0.35)
             
        # 2. Lookup Tier
        tiers = config.get_commission_tiers()
        sorted_tiers = sorted(tiers, key=lambda x: x['threshold'], reverse=True)
        
        for tier in sorted_tiers:
            if total_volume > tier['threshold']:
                return tier['rate']
        return 0.0

    def get_user(self, email):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_users(self):
        """Fetches all users for admin management."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]

    def get_kpi_stats(self, user_id, month=None, year=None):
        """Calculates core KPIs with optional Month/Year filter."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Helper for transaction filters (created_at is DATETIME)
            date_filter = ""
            params_dates = []
            if year:
                date_filter += " AND strftime('%Y', created_at) = ?"
                params_dates.append(str(year))
            if month:
                date_filter += " AND strftime('%m', created_at) = ?"
                params_dates.append(f"{int(month):02d}")
            
            # 1. Revenue (Retail Sales)
            query_rev = f"SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'retail_sales' AND status = 'approved' {date_filter}"
            cursor.execute(query_rev, (user_id, *params_dates))
            revenue = cursor.fetchone()[0] or 0.0
            
            # 2. Commission (From monthly_stats where month column is YYYY-MM)
            comm_where = "WHERE user_id = ?"
            comm_params = [user_id]
            if year and month:
                # Exact YYYY-MM
                comm_where += " AND month = ?"
                comm_params.append(f"{year}-{int(month):02d}")
            elif year:
                # Year prefix match
                comm_where += " AND month LIKE ?"
                comm_params.append(f"{year}-%")
            # If only month provided (odd case), ignore or require year? 
            # Usually UI provides Year if Month is selected. Ignoring month-only filter for now to avoid cross-year sums if not desired.
                
            cursor.execute(f'''
                SELECT 
                    SUM(comm_direct), 
                    SUM(comm_shared), 
                    SUM(comm_received), 
                    SUM(comm_override),
                    SUM(total_commission)
                FROM monthly_stats 
                {comm_where}
            ''', tuple(comm_params))
            row = cursor.fetchone()
            
            c_direct = row[0] or 0.0
            c_shared = row[1] or 0.0
            c_received = row[2] or 0.0
            c_override = row[3] or 0.0
            total_comm = row[4] or 0.0
            
            # Legacy fallback only if NO filter is applied (historics) or if explicitly checking old data
            # Skipping legacy fallback complexity for filtered views to keep it simple. Assumes monthly_stats is populated.

            # 3. KPI Rewards
            query_kpi = f"SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'kpi_reward' AND status IN ('approved', 'paid') {date_filter}"
            cursor.execute(query_kpi, (user_id, *params_dates))
            kpi_reward = cursor.fetchone()[0] or 0.0
            
            # 4. New Customers
            query_cust = f"SELECT COUNT(*) FROM transactions WHERE user_id = ? AND type = 'retail_sales' AND metadata LIKE '%customer%' {date_filter}"
            cursor.execute(query_cust, (user_id, *params_dates))
            new_customers = cursor.fetchone()[0] or 0
            
            # 5. Network Size (Snapshot - always total)
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

    def get_global_stats(self, month=None, year=None):
        """Calculates System-Wide KPIs for Admins with optional filter."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            date_filter = ""
            params_dates = []
            if year:
                date_filter += " AND strftime('%Y', created_at) = ?"
                params_dates.append(str(year))
            if month:
                date_filter += " AND strftime('%m', created_at) = ?"
                params_dates.append(f"{int(month):02d}")
            
            # 1. Total Revenue
            query_rev = f"SELECT SUM(amount) FROM transactions WHERE type='retail_sales' AND status='approved' {date_filter}"
            cursor.execute(query_rev, params_dates)
            revenue = cursor.fetchone()[0] or 0.0
            
            # 2. Total Commission (monthly_stats.month is YYYY-MM)
            comm_where = ""
            comm_params = []
            if year and month:
                comm_where = "WHERE month = ?"
                comm_params.append(f"{year}-{int(month):02d}")
            elif year:
                comm_where = "WHERE month LIKE ?"
                comm_params.append(f"{year}-%")
                
            cursor.execute(f'''
                SELECT 
                    SUM(comm_direct), 
                    SUM(comm_shared), 
                    SUM(comm_received), 
                    SUM(comm_override),
                    SUM(total_commission)
                FROM monthly_stats
                {comm_where}
            ''', tuple(comm_params))
            
            row = cursor.fetchone()
            c_direct = row[0] or 0.0
            c_shared = row[1] or 0.0
            c_received = row[2] or 0.0
            c_override = row[3] or 0.0
            total_comm = row[4] or 0.0
            
            # 3. KPI Rewards
            query_kpi = f"SELECT SUM(amount) FROM transactions WHERE type='kpi_reward' AND status IN ('approved', 'paid') {date_filter}"
            cursor.execute(query_kpi, params_dates)
            kpi_reward = cursor.fetchone()[0] or 0.0
            
            # 4. New Customers
            query_cust = f"SELECT COUNT(*) FROM transactions WHERE type='retail_sales' AND metadata LIKE '%customer%' {date_filter}"
            cursor.execute(query_cust, params_dates)
            new_customers = cursor.fetchone()[0] or 0
            
            # 5. Total Users (Network Size)
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0] or 0
            
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
                'network_size': total_users
            }

    def get_monthly_sales(self, user_id, year=None):
        """Aggregates approved retail sales by month, optionally filtered by year."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            where_clause = "WHERE user_id = ? AND type = 'retail_sales' AND status = 'approved'"
            params = [user_id]
            
            if year:
                where_clause += " AND strftime('%Y', created_at) = ?"
                params.append(str(year))
                
            cursor.execute(f'''
                SELECT strftime('%Y-%m', created_at) as month, SUM(amount) 
                FROM transactions 
                {where_clause}
                GROUP BY month
                ORDER BY month
            ''', tuple(params))
            return cursor.fetchall()

    def get_global_monthly_sales(self, year=None):
        """Aggregates system-wide retail sales by month, optionally filtered by year."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            where_clause = "WHERE type = 'retail_sales' AND status = 'approved'"
            params = []
            
            if year:
                where_clause += " AND strftime('%Y', created_at) = ?"
                params.append(str(year))
                
            cursor.execute(f'''
                SELECT strftime('%Y-%m', created_at) as month, SUM(amount) 
                FROM transactions 
                {where_clause}
                GROUP BY month
                ORDER BY month
            ''', tuple(params))
            return cursor.fetchall()

    def get_transactions_filtered(self, user_id, month=None, year=None, type_filter=None):
        """Fetches transactions with optional filters."""
        # Check user role
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            role = row['role'] if row else 'ctv'

        # If Admin, show ALL transactions (unless filtered safely?)
        # Issue: The UI might need to know if it's admin mode.
        params = []
        if role == 'admin':
            query = "SELECT * FROM transactions WHERE 1=1"
        else:
            query = "SELECT * FROM transactions WHERE user_id = ?"
            params.append(user_id)
        
        if month and year:
            query += " AND strftime('%m', created_at) = ? AND strftime('%Y', created_at) = ?"
            params.extend([f"{int(month):02d}", str(year)])
        elif year:
            query += " AND strftime('%Y', created_at) = ?"
            params.append(str(year))
            
        if type_filter and type_filter != 'All':
            db_type_map = {
                'Retail': 'retail_sales',
                'Share': 'commission_sharing',
                'Receive': 'commission_sharing', 
                'Reward': 'kpi_reward'
            }
            if type_filter in db_type_map:
                query += " AND type = ?"
                params.append(db_type_map[type_filter])
                
        query += " ORDER BY created_at DESC"
        
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_downline_nested(self, root_user_id):
        """Returns the downline tree as a nested dictionary structure."""
        flat_list = self.get_downline_flat(root_user_id)
        
        # Create a map of items
        nodes_by_id = {u['id']: {**u, 'children': []} for u in flat_list}
        tree = []
        
        for u in flat_list:
            node = nodes_by_id[u['id']]
            if u['parent_id'] == root_user_id:
                # Direct child of requested user
                tree.append(node)
            elif u['parent_id'] in nodes_by_id:
                # Child of someone else in the downline
                nodes_by_id[u['parent_id']]['children'].append(node)
            elif u['id'] == root_user_id:
                # If the root user is in the list (get_downline_flat returns it), add to tree
                 tree.append(node)
                
        return tree

    def get_entire_network_nested(self):
        """For Admins: Returns the entire network forest."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            flat_list = [dict(row) for row in cursor.fetchall()]

        # Mappings
        nodes_by_id = {u['id']: {**u, 'children': []} for u in flat_list}
        forest = []

        for u in flat_list:
            node = nodes_by_id[u['id']]
            if u['parent_id'] and u['parent_id'] in nodes_by_id:
                 # Has valid parent in the list
                 nodes_by_id[u['parent_id']]['children'].append(node)
            else:
                 # Is a root node (no parent or parent not in DB)
                 forest.append(node)

        return forest

    def get_downline_flat(self, root_user_id):
        """Returns the entire downline tree as a flat list for visualization."""
        # SQLite recursive query to get tree
        query = '''
            WITH RECURSIVE downline AS (
                SELECT id, full_name, role, parent_id, 1 as level
                FROM users
                WHERE id = ?
                UNION ALL
                SELECT u.id, u.full_name, u.role, u.parent_id, d.level + 1
                FROM users u
                JOIN downline d ON u.parent_id = d.id
            )
            SELECT * FROM downline;
        '''
        results = []
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (root_user_id,))
            for row in cursor.fetchall():
                results.append(dict(row))
        return results

        return results

    def get_viewable_users(self, user_id, role):
        """
        Returns list of users allowed to be viewed by the current user.
        - Admin: All users.
        - Average User: Themselves + their entire downline.
        """
        results = []
        if role == 'admin':
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT id, full_name, role FROM users ORDER BY created_at DESC")
                results = [dict(row) for row in cursor.fetchall()]
        else:
            # Self
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT id, full_name, role FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    results.append(dict(id=row[0], full_name=row[1], role=row[2]))
            
            # Downline
            downline = self.get_downline_flat(user_id)
            results.extend(downline)
            
        return [dict(u=u['id'], label=f"{u['full_name']} ({u['role']})", role=u['role']) for u in results]
