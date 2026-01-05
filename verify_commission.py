from rt_commission_dashboard.core.db_handler import DBHandler
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

db = DBHandler()

def verify_commissions():
    print("--- Verifying Auto-Commissions ---")
    
    # 1. Reset specific users for clean test (optional, but let's assume valid state from seed)
    # CTV1 is child of AFF2 (Daily 2). AFF2 is child of AFF1 (Daily 1). AFF1 is child of Admin.
    # Hierarchy: CTV1 -> AFF2 (L1) -> AFF1 (L2) -> Admin (L3)
    
    print("\n1. Creating Sale for CTV1 ($1000)...")
    sale_id = db.create_retail_sale('u_ctv1', 1000.00, {'product': 'Test Auto Comm'})
    print(f"Sale Created: {sale_id}")
    
    # 2. Verify Commissions
    print("\n2. Checking generated commissions...")
    
    # Check AFF2 (Level 1 Parent -> should get 10% = $100)
    txs_aff2 = db.get_transactions_filtered('u_aff2', type_filter='Share')
    comm_aff2 = next((t for t in txs_aff2 if t['reference_id'] == sale_id), None)
    
    if comm_aff2 and comm_aff2['amount'] == 100.00:
        print(f"✅ PASS: Level 1 (Affiliate 2) received $100.00 (10%)")
    else:
        print(f"❌ FAIL: Level 1 (Affiliate 2) expected $100.00, got {comm_aff2}")

    # Check AFF1 (Level 2 Parent -> should get 5% = $50)
    txs_aff1 = db.get_transactions_filtered('u_aff1', type_filter='Share')
    comm_aff1 = next((t for t in txs_aff1 if t['reference_id'] == sale_id), None)
    
    if comm_aff1 and comm_aff1['amount'] == 50.00:
        print(f"✅ PASS: Level 2 (Affiliate 1) received $50.00 (5%)")
    else:
        print(f"❌ FAIL: Level 2 (Affiliate 1) expected $50.00, got {comm_aff1}")
        
    # Check Admin (Level 3 Parent -> should get 2% = $20)
    # NOTE: Since Admin sees ALL transactions globally, we must filter by user_id explicitly in the result list
    txs_admin_view = db.get_transactions_filtered('u_admin', type_filter='Share')
    comm_admin = next((t for t in txs_admin_view if t['reference_id'] == sale_id and t['user_id'] == 'u_admin'), None)
    
    if comm_admin and comm_admin['amount'] == 20.00:
        print(f"✅ PASS: Level 3 (Admin) received $20.00 (2%)")
    else:
        print(f"❌ FAIL: Level 3 (Admin) expected $20.00, got {comm_admin}")

if __name__ == "__main__":
    verify_commissions()
