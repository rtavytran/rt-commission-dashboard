from rt_commission_dashboard.core.db_handler import DBHandler
import logging
from datetime import datetime
import sqlite3

# Setup logging
logging.basicConfig(level=logging.ERROR) # Only show errors to keep output clean

db = DBHandler()

def setup_scenario():
    """
    Creates hierarchy: A -> B -> (C, D)
    And separate inactive user E (Child of A)
    """
    print("--- 1. Setting up Hierarchy: A -> B -> (C, D) + E (Inactive) ---")
    with db._get_connection() as conn:
        cursor = conn.cursor()
        # Clear existing data to avoid conflict
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM users")
        
        users = [
            ('admin', 'admin@rt.local', 'Administrator', 'admin', '["Q1","Q2","Q3","Q4"]', None),
            ('A', 'a@test.com', 'User A', 'affiliate', '[]', 'admin'),
            ('B', 'b@test.com', 'User B', 'affiliate', '[]', 'A'),
            ('C', 'c@test.com', 'User C', 'ctv', '[]', 'B'),
            ('D', 'd@test.com', 'User D', 'ctv', '[]', 'B'),
            ('E', 'e@test.com', 'User E', 'ctv', '[]', 'A'), # Inactive Check
        ]
        cursor.executemany("INSERT INTO users (id, email, full_name, role, permissions, parent_id) VALUES (?,?,?,?,?,?)", users)
        conn.commit()
    print("Hierarchy created (Admin -> A -> B -> C/D).")

def run_sales_scenario():
    print("\n--- 2. Executing Sales ---")
    
    # 1. Standard ScenarioSales
    # C: 100M Direct
    db.create_retail_sale('C', 100_000_000, {'desc': 'Direct Sale'})
    
    # D: 50M Direct
    db.create_retail_sale('D', 50_000_000, {'desc': 'Direct Sale'})
    
    # B: 200M Direct
    db.create_retail_sale('B', 200_000_000, {'desc': 'Direct Sale'})
    
    # A: 200M Direct
    db.create_retail_sale('A', 200_000_000, {'desc': 'Direct Sale'})
    
    # C shares 50M with D (Opportunity)
    # D (Receiver) has 50M personal already -> Ranking > 0 -> Rate 50% of Tier
    print("-> C shares 50M with D")
    db.create_shared_opportunity(receiver_id='D', sharer_id='C', amount=50_000_000, metadata={'desc': 'Shared C->D'})
    
    # 2. Inactive User E
    # A shares 50M with E
    # E has 0 personal volume -> Tier 0% -> Rate 4% (Fixed)
    print("-> A shares 50M with E (Inactive)")
    db.create_shared_opportunity(receiver_id='E', sharer_id='A', amount=50_000_000, metadata={'desc': 'Shared A->E'})

def print_results():
    print("\n--- 3. Verifying Results (Stored Monthly Stats Breakdown) ---")
    
    users = ['E', 'D', 'C', 'B', 'A']
    current_month = datetime.now().strftime('%Y-%m')
    
    # Headers
    headers = f"{'User':<5} | {'Role':<8} | {'Rank Vol':<12} | {'Rate':<5} | {'Direct':<12} | {'Shared':<12} | {'Recv':<12} | {'Ovrd':<12} | {'Total':<12}"
    print(headers)
    print("-" * len(headers))
    
    role_map = {'D': 'Child', 'C': 'Child', 'B': 'Parent', 'A': 'G-Parent', 'E': 'Inactive'}
    
    with db._get_connection() as conn:
        cursor = conn.cursor()
        for u in users:
            stat_id = f"{u}_{current_month}"
            # Select breakdown columns
            cursor.execute('''
                SELECT personal_sales_volume, f1_sales_volume, tier_rate, 
                       comm_direct, comm_shared, comm_received, comm_override, total_commission 
                FROM monthly_stats WHERE id=?
            ''', (stat_id,))
            row = cursor.fetchone()
            
            if row:
                personal_vol = row[0]
                f1_vol = row[1]
                rate = row[2]
                c_direct = row[3]
                c_shared = row[4]
                c_recv = row[5]
                c_ovrd = row[6]
                total_comm = row[7]
                
                # Ranking Volume
                rank_vol = personal_vol + f1_vol
                
                # Format
                def f(n): return f"{n:,.0f}"
                def p(n): return f"{int(n*100)}%"
                
                print(f"{u:<5} | {role_map[u]:<8} | {f(rank_vol):<12} | {p(rate):<5} | {f(c_direct):<12} | {f(c_shared):<12} | {f(c_recv):<12} | {f(c_ovrd):<12} | {f(total_comm):<12}")
                
            else:
                print(f"{u:<5} | MISSING")
    
    print("\n--- 4. Verifying Dashboard API (get_kpi_stats) ---")
    # Verify what the UI actually sees
    for u in ['A', 'B', 'C', 'D', 'E']:
        stats = db.get_kpi_stats(u)
        print(f"User {u} UI Stats:")
        print(f"  - Revenue (Retail): {stats['revenue']:,.0f}")
        print(f"  - Comm Total:       {stats['commission']:,.0f}")
        print(f"  - Breakdown:        Direct={stats['comm_direct']:,.0f}, Shared={stats['comm_shared']:,.0f}, Recv={stats['comm_received']:,.0f}, Ovrd={stats['comm_override']:,.0f}")
        print("-" * 40)
    
    print("\n--- 5. Verifying Global Stats (Admin View) ---")
    global_stats = db.get_global_stats()
    print("Global System Stats:")
    print(f"  - Total Revenue:    {global_stats['revenue']:,.0f}")
    print(f"  - Total Commission: {global_stats['commission']:,.0f}")
    print(f"  - Breakdown:        Direct={global_stats['comm_direct']:,.0f}, Shared={global_stats['comm_shared']:,.0f}, Recv={global_stats['comm_received']:,.0f}, Ovrd={global_stats['comm_override']:,.0f}")
    print(f"  - Network Size:     {global_stats['network_size']}")

    print("\n--- 6. Verifying Affiliates Tree (Admin View) ---")
    tree = db.get_entire_network_nested()
    print(f"Root Nodes Found: {len(tree)}")
    for node in tree:
        print(f"  - Root: {node['full_name']} ({node['role']}) has {len(node['children'])} children")
        for child in node['children']:
             print(f"    -> Child: {child['full_name']}")

if __name__ == "__main__":
    setup_scenario()
    run_sales_scenario()
    print_results()
