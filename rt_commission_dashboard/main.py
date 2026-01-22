import os
import argparse
import yaml
from rt_commission_dashboard.core.paths import get_data_dir, get_config_path

# Ensure NiceGUI storage uses a writable, per-process location before NiceGUI imports (avoid Windows file locks)
storage_base = get_data_dir() / '.nicegui' / str(os.getpid())
os.environ.setdefault('NICEGUI_STORAGE_PATH', str(storage_base))
storage_base.mkdir(parents=True, exist_ok=True)

from nicegui import ui, app
from rt_commission_dashboard.core.config import config
from rt_commission_dashboard.pages.login import login_page
from rt_commission_dashboard.pages.setup import setup_page
from rt_commission_dashboard.pages.signup import signup_page
from rt_commission_dashboard.pages.check_email import check_email_page
from rt_commission_dashboard.pages.email_confirmed import email_confirmed_page
from rt_commission_dashboard.pages.dashboard import dashboard_page
from rt_commission_dashboard.pages.affiliates import affiliates_page
from rt_commission_dashboard.pages.reports import reports_page
from rt_commission_dashboard.pages.settings import settings_page

# --- Routes (Global Scope) ---
# Ensure pages are registered at module level for multiprocessing

@ui.page('/login')
def login_route():
    login_page()

@ui.page('/setup')
def setup_route():
    setup_page()

@ui.page('/signup')
def signup_route():
    signup_page()

@ui.page('/check-email')
def check_email_route():
    check_email_page()

@ui.page('/email-confirmed')
def email_confirmed_route():
    email_confirmed_page()

from rt_commission_dashboard.pages.users import users_page
from rt_commission_dashboard.pages.profiles import profiles_page

ui.page('/')(dashboard_page)
ui.page('/affiliates')(affiliates_page)
ui.page('/reports')(reports_page)
ui.page('/admin/users')(users_page)
ui.page('/admin/profiles')(profiles_page)
ui.page('/admin/settings')(settings_page)

from rt_commission_dashboard.ui.layout import layout
from rt_commission_dashboard.core.i18n import t

@ui.page('/admin/contracts')
@layout
def admin_contracts_page():
    ui.label(t('contracts.title')).classes('text-2xl font-bold rt-title mb-4')
    ui.label(t('contracts.coming_soon')).classes('rt-muted')

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

    # Check if database configuration provided via command-line
    cli_db_configured = args.db_type or args.supabase_url or args.supabase_anon_key

    # Try to load saved configuration
    settings_file = get_config_path()
    saved_config = None
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                saved_config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"⚠️  Warning: Could not load settings file: {e}")

    # Set database configuration from command-line arguments (priority)
    if cli_db_configured:
        cli_db_type = args.db_type or 'supabase'

        if cli_db_type:
            os.environ['DATABASE_TYPE'] = cli_db_type
            print(f"📦 Database type: {cli_db_type}")

        if args.supabase_url:
            os.environ['SUPABASE_URL'] = args.supabase_url
            print(f"🔗 Supabase URL: {args.supabase_url}")

        if args.supabase_anon_key:
            os.environ['SUPABASE_ANON_KEY'] = args.supabase_anon_key
            print(f"🔑 Supabase Anon Key: {'*' * 20}... (hidden)")

        if args.supabase_service_key:
            os.environ['SUPABASE_SERVICE_KEY'] = args.supabase_service_key
            print(f"🔐 Supabase Service Key: {'*' * 20}... (hidden)")

    # If no CLI args, try to use saved configuration
    elif saved_config and 'database' in saved_config:
        db_config = saved_config['database']
        db_type = db_config.get('type', 'sqlite')
        os.environ['DATABASE_TYPE'] = db_type
        print(f"📦 Database type (from saved config): {db_type}")

        if db_type == 'supabase' and 'supabase' in db_config:
            supabase_cfg = db_config['supabase']
            if supabase_cfg.get('url'):
                os.environ['SUPABASE_URL'] = supabase_cfg['url']
                print(f"🔗 Supabase URL (from saved config): {supabase_cfg['url']}")
            if supabase_cfg.get('anon_key'):
                os.environ['SUPABASE_ANON_KEY'] = supabase_cfg['anon_key']
                print(f"🔑 Supabase Anon Key (from saved config): {'*' * 20}... (hidden)")
            if supabase_cfg.get('service_key'):
                os.environ['SUPABASE_SERVICE_KEY'] = supabase_cfg['service_key']
                print(f"🔐 Supabase Service Key (from saved config): {'*' * 20}... (hidden)")
    else:
        print("⚠️  No database configuration found. Setup page will be shown on first access.")

    # Configure NiceGUI storage path to use writable, per-process data directory (avoids handle locks on Windows)
    storage_path = get_data_dir() / '.nicegui' / str(os.getpid())
    storage_path.mkdir(parents=True, exist_ok=True)
    os.environ['NICEGUI_STORAGE_PATH'] = str(storage_path)

    # Store runtime port in environment for access in page handlers
    os.environ['RUNTIME_PORT'] = str(args.port)

    print(f"🚀 Starting {config.get_app_title()} on port {args.port}")
    try:
        ui.run(
            title=config.get_app_title(),
            port=args.port,
            dark=None,  # Let theme system handle dark/light mode
            storage_secret=config.get_secret_key(),
            reload=False,
            show=False  # do not auto-open browser; user can open manually
        )
    except KeyboardInterrupt:
        print("\n👋 Server interrupted by user. Shutting down gracefully...")

if __name__ in {"__main__", "__mp_main__"}:
    main()
