from nicegui import ui, app
import argparse
from rt_commission_dashboard.core.config import config
from rt_commission_dashboard.pages.login import login_page
from rt_commission_dashboard.pages.dashboard import dashboard_page
from rt_commission_dashboard.pages.affiliates import affiliates_page
from rt_commission_dashboard.pages.reports import reports_page

# --- Routes (Global Scope) ---
# Ensure pages are registered at module level for multiprocessing

@ui.page('/login')
def login_route():
    login_page()

from rt_commission_dashboard.pages.users import users_page

ui.page('/')(dashboard_page)
ui.page('/affiliates')(affiliates_page)
ui.page('/reports')(reports_page)
ui.page('/admin/users')(users_page)

from rt_commission_dashboard.ui.layout import layout
@ui.page('/admin/contracts')

@ui.page('/admin/contracts')
@layout
def admin_contracts_page():
    ui.label('Contract Management').classes('text-2xl font-bold text-white mb-4')
    ui.label('Coming Soon in Phase 2').classes('text-gray-400')

def main():
    parser = argparse.ArgumentParser(description=config.get_app_title())
    parser.add_argument('--port', type=int, default=config.get_app_port(), help='Port to run the UI on')
    parser.add_argument('--ui', action='store_true', help='Start the UI') 
    args = parser.parse_args()

    print(f"🚀 Starting {config.get_app_title()} on port {args.port}")
    ui.run(
        title=config.get_app_title(), 
        port=args.port, 
        dark=True, 
        storage_secret=config.get_secret_key(), 
        reload=False
    )

if __name__ in {"__main__", "__mp_main__"}:
    main()
