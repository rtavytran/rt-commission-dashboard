from nicegui import ui, app
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.ui.layout import layout
from rt_commission_dashboard.core.config import config
from rt_commission_dashboard.core.paths import get_app_dir
import yaml
import os

@layout
def settings_page():
    """Settings page for database configuration."""

    # Check if user is admin
    user = app.storage.user.get('user_info', {})
    if user.get('role') != 'admin':
        ui.label('Access Denied').classes('text-2xl font-bold text-red-500')
        ui.label('Only administrators can access settings.').classes('text-gray-400')
        return

    # Title
    with ui.row().classes('items-center mb-6'):
        ui.icon('settings', size='md', color=Theme.SECONDARY)
        Theme.title('Settings')

    Theme.subtitle('Configure database connection and application settings')

    # Database Settings Card
    with Theme.card():
        ui.label('Database Configuration').classes('text-xl font-bold mb-4')

        # Load current settings
        config_file = get_app_dir() / 'config.yaml'
        current_settings = {}
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    current_settings = yaml.safe_load(f) or {}
            except Exception as e:
                ui.notify(f'Error loading config: {e}', type='negative')

        # Get current database type
        db_config = current_settings.get('database', {})
        current_db_type = db_config.get('type', 'sqlite')

        # Database Type Selector
        db_type_select = ui.select(
            options={'sqlite': 'SQLite (Local)', 'supabase': 'Supabase (Cloud)'},
            value=current_db_type,
            label='Database Type'
        ).props('outlined dense dark').classes('w-full mb-4')

        # Supabase Configuration Container
        supabase_container = ui.column().classes('w-full gap-4')

        with supabase_container:
            ui.label('Supabase Configuration').classes('text-lg font-semibold mb-2')

            # Get current Supabase settings
            supabase_config = db_config.get('supabase', {})

            supabase_url = ui.input(
                label='Supabase URL',
                placeholder='https://your-project.supabase.co',
                value=supabase_config.get('url', config.get_supabase_url())
            ).props('outlined dense dark').classes('w-full')

            supabase_anon_key = ui.input(
                label='Supabase Anon Key',
                placeholder='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                value=supabase_config.get('anon_key', config.get_supabase_anon_key())
            ).props('outlined dense dark type=password').classes('w-full')

            supabase_service_key = ui.input(
                label='Supabase Service Key (Optional)',
                placeholder='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                value=supabase_config.get('service_key', config.get_supabase_service_key())
            ).props('outlined dense dark type=password').classes('w-full')

        # Show/hide Supabase config based on selection
        def update_visibility():
            supabase_container.set_visibility(db_type_select.value == 'supabase')

        db_type_select.on_value_change(update_visibility)
        update_visibility()

        # Save Button
        def save_settings():
            try:
                # Prepare config data
                new_config = current_settings.copy()

                # Update database settings
                if 'database' not in new_config:
                    new_config['database'] = {}

                new_config['database']['type'] = db_type_select.value

                if db_type_select.value == 'supabase':
                    new_config['database']['supabase'] = {
                        'url': supabase_url.value,
                        'anon_key': supabase_anon_key.value,
                        'service_key': supabase_service_key.value
                    }

                # Ensure config directory exists
                config_dir = get_app_dir() / 'config'
                config_dir.mkdir(parents=True, exist_ok=True)

                # Write to config.yaml in the app directory
                config_path = config_dir / 'settings.yaml'
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(new_config, f, default_flow_style=False, sort_keys=False)

                # Also update environment variables for immediate effect
                if db_type_select.value == 'supabase':
                    os.environ['DATABASE_TYPE'] = 'supabase'
                    os.environ['SUPABASE_URL'] = supabase_url.value
                    os.environ['SUPABASE_ANON_KEY'] = supabase_anon_key.value
                    if supabase_service_key.value:
                        os.environ['SUPABASE_SERVICE_KEY'] = supabase_service_key.value
                else:
                    os.environ['DATABASE_TYPE'] = 'sqlite'

                ui.notify('Settings saved! Please restart the application for changes to take effect.', type='positive')

            except Exception as e:
                ui.notify(f'Error saving settings: {e}', type='negative')

        with ui.row().classes('w-full mt-6 gap-4'):
            ui.button('Save Settings', on_click=save_settings).props('unelevated color=indigo-600')
            ui.button('Cancel', on_click=lambda: ui.navigate.to('/')).props('flat')

    # Information Card
    with Theme.card().classes('mt-6'):
        ui.label('Important Notes').classes('text-lg font-bold mb-3')
        with ui.column().classes('gap-2 text-gray-400'):
            ui.label('• After changing database settings, you must restart the application.')
            ui.label('• Make sure your Supabase project has the correct schema and tables.')
            ui.label('• The service key is optional but recommended for admin operations.')
            ui.label('• Settings are stored in the config/settings.yaml file.')
