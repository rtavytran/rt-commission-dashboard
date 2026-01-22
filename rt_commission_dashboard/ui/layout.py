from nicegui import ui, app
import os
import yaml
import httpx
from supabase import create_client
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.core.i18n import t, set_lang, get_current_lang
from rt_commission_dashboard.core.paths import get_config_path
from rt_commission_dashboard.core.config import config

def validate_jwt_token(token: str) -> bool:
    """Validate if the JWT token is still valid."""
    if not token:
        return False

    try:
        supabase_url = config.get_supabase_url()
        supabase_anon = config.get_supabase_anon_key()

        if not supabase_url or not supabase_anon:
            return False

        client = create_client(supabase_url, supabase_anon)
        # Try to get user with the token
        response = client.auth.get_user(token)
        return response.user is not None
    except Exception as e:
        # Token is expired or invalid
        return False

def layout(content_func):
    """Decorator to wrap pages in the standard dashboard layout."""

    @ui.page(content_func.__name__ if hasattr(content_func, '__name__') else None)
    def wrapper():
        # Apply global styles
        Theme.apply_global_styles()

        # Check if database is configured using env first, then saved settings
        db_type = os.environ.get('DATABASE_TYPE')
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_ANON_KEY')

        saved_config = {}
        config_path = get_config_path()
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    saved_config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"⚠️  Warning: Could not load settings file: {e}")

        db_settings = saved_config.get('database', {}) if saved_config else {}

        # Apply saved settings to environment if CLI/env not provided
        if not db_type and db_settings.get('type'):
            db_type = db_settings['type']
            os.environ['DATABASE_TYPE'] = db_type

        if db_type and db_type.lower() == 'supabase':
            supabase_cfg = db_settings.get('supabase', {}) if db_settings else {}
            if not supabase_url and supabase_cfg.get('url'):
                supabase_url = supabase_cfg['url']
                os.environ['SUPABASE_URL'] = supabase_url
            if not supabase_key and supabase_cfg.get('anon_key'):
                supabase_key = supabase_cfg['anon_key']
                os.environ['SUPABASE_ANON_KEY'] = supabase_key

        # Determine whether DB is configured
        db_configured = False
        if db_type:
            if db_type.lower() == 'sqlite':
                db_configured = True
            elif db_type.lower() == 'supabase':
                db_configured = bool(supabase_url and supabase_key)

        # If not configured, redirect to setup
        if not db_configured:
            ui.navigate.to('/setup')
            return

        # Connectivity check for Supabase to fail fast and let user fix setup/network
        if db_type and db_type.lower() == 'supabase':
            try:
                httpx.get(f"{supabase_url.rstrip('/')}/auth/v1/health", timeout=5)
            except Exception:
                ui.notify('Cannot reach Supabase. Check URL/anon key or network/proxy and try again.', type='negative')
                ui.navigate.to('/setup')
                return

        # Require authentication
        if not app.storage.user.get('authenticated', False):
            ui.navigate.to('/login')
            return

        user = app.storage.user.get('user_info')
        if not user:
            ui.navigate.to('/login')
            return

        # Validate JWT token if using Supabase
        if db_type and db_type.lower() == 'supabase':
            token = app.storage.user.get('supabase_token')
            if token and not validate_jwt_token(token):
                # Token expired - clear session and redirect to login
                try:
                    app.storage.user.clear()
                except PermissionError:
                    # Fallback for Windows file locks on storage files
                    try:
                        app.storage.user._data = {}
                    except Exception:
                        pass
                ui.notify('Your session has expired. Please login again.', type='warning')
                ui.navigate.to('/login')
                return

        # --- Header with Navigation ---
        with ui.header().classes('items-center h-16 px-6'):
            # Logo/Brand
            ui.label('APP NAGEN').classes('text-xl font-bold tracking-wider rt-title')

            ui.space()

            # Top Navigation Menu
            with ui.row().classes('top-nav'):
                # Main navigation items
                with ui.button(icon='dashboard', on_click=lambda: ui.navigate.to('/')).props('flat dense'):
                    ui.label(t('nav.dashboard')).classes('ml-1')

                with ui.button(icon='hub', on_click=lambda: ui.navigate.to('/affiliates')).props('flat dense'):
                    ui.label(t('nav.affiliates')).classes('ml-1')

                with ui.button(icon='bar_chart', on_click=lambda: ui.navigate.to('/reports')).props('flat dense'):
                    ui.label(t('nav.reports')).classes('ml-1')

                # Admin navigation (dropdown)
                if user['role'] == 'admin':
                    with ui.button(icon='admin_panel_settings').props('flat dense'):
                        ui.label(t('nav.admin')).classes('ml-1')
                        with ui.menu().classes('rt-admin-menu'):
                            ui.menu_item(t('nav.users'), on_click=lambda: ui.navigate.to('/admin/users'))
                            ui.menu_item(t('nav.profiles'), on_click=lambda: ui.navigate.to('/admin/profiles'))
                            ui.menu_item(t('nav.contracts'), on_click=lambda: ui.navigate.to('/admin/contracts'))
                            ui.menu_item(t('nav.settings'), on_click=lambda: ui.navigate.to('/admin/settings'))

            ui.space()

            # Theme Toggle Button
            theme_btn = ui.button(icon='light_mode', on_click=lambda: ui.run_javascript('''
                toggleTheme();
                // Update icon
                const isDark = document.body.classList.contains('dark');
                const btn = document.querySelector('.theme-toggle');
                if (btn) {
                    const icon = btn.querySelector('i');
                    if (icon) {
                        icon.textContent = isDark ? 'light_mode' : 'dark_mode';
                    }
                }
            ''')).props('flat dense').classes('theme-toggle')

            # Update icon based on current theme
            ui.run_javascript('''
                setTimeout(() => {
                    const isDark = document.body.classList.contains('dark');
                    const btn = document.querySelector('.theme-toggle');
                    if (btn) {
                        const icon = btn.querySelector('i');
                        if (icon) {
                            icon.textContent = isDark ? 'light_mode' : 'dark_mode';
                        }
                    }
                }, 100);
            ''')

            # Application Language Switcher
            def toggle_lang():
                new_lang = 'en' if get_current_lang() == 'vi' else 'vi'
                set_lang(new_lang)
                ui.run_javascript('window.location.reload()')

            current_lang = get_current_lang()
            lang_label = 'VI' if current_lang == 'vi' else 'EN'
            ui.button(f"{lang_label}", on_click=toggle_lang).props('flat dense').classes('font-bold border rounded-md px-2')

            # User Menu with logout
            with ui.button(icon='person').props('flat dense round'):
                with ui.menu().classes('rt-user-menu'):
                    with ui.row().classes('p-4 gap-2 items-center rt-user-menu__header'):
                        ui.avatar(icon='person', color=Theme.PRIMARY, text_color='white').props('size=md')
                        ui.label(user.get('full_name') or user.get('email') or 'User').classes('font-medium')
                    ui.separator()
                    def logout():
                        app.storage.user.clear()
                        ui.navigate.to('/login')
                    ui.menu_item(t('logout'), on_click=logout).classes('rt-user-menu__item')

        # --- Main Content (No Sidebar) ---
        # Store current path for reload
        app.storage.user['referrer_path'] = '/'

        with ui.column().classes('w-full p-6'):
            content_func()

    return wrapper
