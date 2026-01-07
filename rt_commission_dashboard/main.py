from nicegui import ui, app
import argparse
import os
from rt_commission_dashboard.core.config import config
from rt_commission_dashboard.core.paths import get_data_dir
from rt_commission_dashboard.pages.login import login_page
from rt_commission_dashboard.pages.dashboard import dashboard_page
from rt_commission_dashboard.pages.affiliates import affiliates_page
from rt_commission_dashboard.pages.reports import reports_page
from rt_commission_dashboard.pages.settings import settings_page

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
ui.page('/admin/settings')(settings_page)

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

    # Database configuration arguments
    parser.add_argument('--db-type', type=str, choices=['sqlite', 'supabase'],
                        help='Database type (sqlite or supabase)')
    parser.add_argument('--supabase-url', type=str,
                        help='Supabase project URL (e.g., https://your-project.supabase.co)')
    parser.add_argument('--supabase-anon-key', type=str,
                        help='Supabase anonymous key')
    parser.add_argument('--supabase-service-key', type=str,
                        help='Supabase service role key (optional)')

    args = parser.parse_args()

    # Set database configuration from command-line arguments
    if args.db_type:
        os.environ['DATABASE_TYPE'] = args.db_type
        print(f"📦 Database type: {args.db_type}")

    if args.supabase_url:
        os.environ['SUPABASE_URL'] = args.supabase_url
        print(f"🔗 Supabase URL: {args.supabase_url}")

    if args.supabase_anon_key:
        os.environ['SUPABASE_ANON_KEY'] = args.supabase_anon_key
        print(f"🔑 Supabase Anon Key: {'*' * 20}... (hidden)")

    if args.supabase_service_key:
        os.environ['SUPABASE_SERVICE_KEY'] = args.supabase_service_key
        print(f"🔐 Supabase Service Key: {'*' * 20}... (hidden)")

    # Configure NiceGUI storage path to use writable data directory
    storage_path = get_data_dir() / '.nicegui'
    storage_path.mkdir(parents=True, exist_ok=True)
    os.environ['NICEGUI_STORAGE_PATH'] = str(storage_path)

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
