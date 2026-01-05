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
                    metadata TEXT, -- JSON for Customer info, Product details
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
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
            
            # Seed transactions
            transactions = [
                # Retail Sales
                ('tx_1', 'u_ctv1', 500.00, 'retail_sales', 'approved', None, json.dumps({'customer': 'Khách Hàng A', 'product': 'Combo Giày'})),
                ('tx_2', 'u_aff2', 1200.00, 'retail_sales', 'approved', None, json.dumps({'customer': 'Khách Hàng B', 'product': 'Suit Cao Cấp'})),
                
                # Commissions (Sharing)
                # Affiliate 2 gets commission from CTV 1
                ('tx_3', 'u_aff2', 50.00, 'commission_sharing', 'paid', 'tx_1', json.dumps({'note': 'Hoa hồng từ CTV X'})),
                
                # Affiliate 1 gets commission from Affiliate 2
                ('tx_4', 'u_aff1', 120.00, 'commission_sharing', 'paid', 'tx_2', json.dumps({'note': 'Hoa hồng gián tiếp từ Đại lý B'})),
                
                # Rewards
                ('tx_5', 'u_aff1', 5000.00, 'kpi_reward', 'approved', None, json.dumps({'period': 'Jan 2026', 'note': 'Thưởng Quý'})),
                
                # Edge Cases
                ('tx_6', 'u_orphan', 300.00, 'retail_sales', 'approved', None, json.dumps({'customer': 'Khách Hàng C', 'product': 'Áo Thun'})),
                ('tx_7', 'u_ctv2', 100.00, 'retail_sales', 'refunded', None, json.dumps({'customer': 'Khách Hàng D', 'reason': 'Faulty'})),
                ('tx_8', 'u_aff1', 50.00, 'retail_sales', 'pending', None, json.dumps({'customer': 'Khách Hàng E', 'status': 'Payment Pending'})),
            ]
            cursor.executemany('''
                INSERT INTO transactions (id, user_id, amount, type, status, reference_id, metadata) 
                VALUES (?,?,?,?,?,?,?)
            ''', transactions)
            conn.commit()

    def create_retail_sale(self, user_id, amount, metadata={}):
        """Creates a retail sale and automatically generates upline commissions."""
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Create the retail sale
            sale_id = f"sale_{datetime.now().timestamp()}"
            cursor.execute('''
                INSERT INTO transactions (id, user_id, amount, type, status, metadata, created_at)
                VALUES (?, ?, ?, 'retail_sales', 'approved', ?, CURRENT_TIMESTAMP)
            ''', (sale_id, user_id, amount, json.dumps(metadata)))

            # 2. Auto-generate commissions up the tree
            self._generate_upline_commissions(cursor, user_id, sale_id, amount)

            conn.commit()
            return sale_id

    def _generate_upline_commissions(self, cursor, seller_id, sale_id, sale_amount):
        """Automatically creates commission transactions for upline."""
        import json
        
        # Get configuration values
        max_levels = config.get_max_commission_levels()
        commission_rates = config.get_commission_rates()
        
        # Get seller's upline chain
        cursor.execute('''
            WITH RECURSIVE upline AS (
                SELECT parent_id, 1 as level FROM users WHERE id = ?
                UNION ALL
                SELECT u.parent_id, up.level + 1 
                FROM users u JOIN upline up ON u.id = up.parent_id
                WHERE up.level < ?  -- Max configurable levels
            )
            SELECT parent_id as user_id, level FROM upline WHERE parent_id IS NOT NULL
        ''', (seller_id, max_levels))

        for row in cursor.fetchall():
            upline_id, level = row
            if level in commission_rates:
                commission_amount = sale_amount * commission_rates[level]
                comm_id = f"comm_{datetime.now().timestamp()}_{level}"

                cursor.execute('''
                    INSERT INTO transactions (id, user_id, amount, type, status, reference_id, metadata, created_at)
                    VALUES (?, ?, ?, 'commission_sharing', 'approved', ?, ?, CURRENT_TIMESTAMP)
                ''', (comm_id, upline_id, commission_amount, sale_id,
                        json.dumps({'level': level, 'rate': commission_rates[level]})))

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

    def get_kpi_stats(self, user_id):
        """Calculates core KPIs: Revenue, Commission, Network Size, New Customers."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Revenue (Retail Sales)
            cursor.execute('''
                SELECT SUM(amount) FROM transactions 
                WHERE user_id = ? AND type = 'retail_sales' AND status = 'approved'
            ''', (user_id,))
            revenue = cursor.fetchone()[0] or 0.0
            
            # 2. Commission Sharing (Direct Commissions)
            cursor.execute('''
                SELECT SUM(amount) FROM transactions 
                WHERE user_id = ? AND type = 'commission_sharing' AND status IN ('approved', 'paid')
            ''', (user_id,))
            commission_share = cursor.fetchone()[0] or 0.0

            # 3. KPI Rewards (Bonuses)
            cursor.execute('''
                SELECT SUM(amount) FROM transactions 
                WHERE user_id = ? AND type = 'kpi_reward' AND status IN ('approved', 'paid')
            ''', (user_id,))
            kpi_reward = cursor.fetchone()[0] or 0.0
            
            # 4. New Customers
            cursor.execute('''
                SELECT COUNT(*) FROM transactions 
                WHERE user_id = ? AND type = 'retail_sales' AND metadata LIKE '%customer%'
            ''', (user_id,))
            new_customers = cursor.fetchone()[0] or 0
            
            # 5. Network Size
            network_size = len(self.get_downline_flat(user_id))
            
            return {
                'revenue': revenue,
                'commission': commission_share + kpi_reward, # Total for legacy cards
                'commission_share': commission_share,
                'kpi_reward': kpi_reward,
                'new_customers': new_customers,
                'network_size': network_size
            }

    def get_monthly_sales(self, user_id):
        """Aggregates approved retail sales by month."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT strftime('%Y-%m', created_at) as month, SUM(amount) 
                FROM transactions 
                WHERE user_id = ? AND type = 'retail_sales' AND status = 'approved'
                GROUP BY month
                ORDER BY month
            ''', (user_id,))
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
