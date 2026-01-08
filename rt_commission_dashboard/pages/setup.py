from nicegui import ui, app
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.core.paths import get_config_path
import yaml
import os

def setup_page():
    Theme.apply_global_styles()

    # Center container
    with ui.column().classes('absolute-center w-full max-w-2xl'):
        # Logo/Brand
        ui.label('RT Commission Dashboard').classes('text-3xl font-bold text-center w-full mb-4')
        ui.label('Initial Setup').classes('text-xl rt-subtitle text-center w-full mb-8')

        with Theme.card():
            ui.label('Database Configuration').classes('text-xl font-bold mb-4')
            ui.label('Please configure your database connection to continue.').classes('rt-muted mb-6')

            # Database Type Selector
            db_type_select = ui.select(
                options={'sqlite': 'SQLite (Local)', 'supabase': 'Supabase (Cloud)'},
                value='supabase',
                label='Database Type'
            ).props('outlined dense').classes('w-full mb-4 rt-input')

            # Supabase Configuration
            supabase_container = ui.column().classes('w-full gap-4')

            with supabase_container:
                ui.label('Supabase Configuration').classes('text-lg font-semibold mb-2')

                supabase_url = ui.input(
                    label='Supabase URL',
                    placeholder='https://your-project.supabase.co',
                    value=os.environ.get('SUPABASE_URL', '')
                ).props('outlined dense').classes('w-full rt-input')

                supabase_anon_key = ui.input(
                    label='Supabase Anon Key',
                    placeholder='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                    value=os.environ.get('SUPABASE_ANON_KEY', '')
                ).props('outlined dense type=password').classes('w-full rt-input')

                supabase_service_key = ui.input(
                    label='Supabase Service Key (Optional)',
                    placeholder='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                    value=os.environ.get('SUPABASE_SERVICE_KEY', '')
                ).props('outlined dense type=password').classes('w-full rt-input')

            # Show/hide Supabase config based on selection
            def update_visibility():
                supabase_container.set_visibility(db_type_select.value == 'supabase')

            db_type_select.on_value_change(update_visibility)
            update_visibility()

            # Save configuration
            def save_config():
                settings_file = get_config_path()
                settings_file.parent.mkdir(parents=True, exist_ok=True)

                # Load existing settings or create new
                if settings_file.exists():
                    with open(settings_file, 'r') as f:
                        settings = yaml.safe_load(f) or {}
                else:
                    settings = {}

                # Update database configuration
                if db_type_select.value == 'supabase':
                    if not supabase_url.value or not supabase_anon_key.value:
                        ui.notify('Please enter Supabase URL and Anon Key', type='negative')
                        return

                    settings['database'] = {
                        'type': 'supabase',
                        'supabase': {
                            'url': supabase_url.value,
                            'anon_key': supabase_anon_key.value,
                            'service_key': supabase_service_key.value if supabase_service_key.value else ''
                        }
                    }

                    # Set environment variables
                    os.environ['DATABASE_TYPE'] = 'supabase'
                    os.environ['SUPABASE_URL'] = supabase_url.value
                    os.environ['SUPABASE_ANON_KEY'] = supabase_anon_key.value
                    if supabase_service_key.value:
                        os.environ['SUPABASE_SERVICE_KEY'] = supabase_service_key.value
                else:
                    settings['database'] = {'type': 'sqlite'}
                    os.environ['DATABASE_TYPE'] = 'sqlite'

                # Save to file
                with open(settings_file, 'w') as f:
                    yaml.dump(settings, f, default_flow_style=False)

                # Mark setup as complete
                app.storage.general['setup_complete'] = True
                app.storage.general['db_configured'] = True

                ui.notify('Configuration saved successfully!', type='positive')

                # Auto-authenticate as admin
                app.storage.user['authenticated'] = True
                app.storage.user['user_info'] = {
                    'id': 1,
                    'full_name': 'Administrator',
                    'email': 'admin@rt.local',
                    'role': 'admin'
                }

                # Redirect to dashboard
                ui.navigate.to('/')

            ui.button('Save Configuration & Continue', on_click=save_config).props('unelevated color=indigo-600').classes('w-full h-10 mt-4')

        # Information Card
        with Theme.card().classes('mt-6'):
            ui.label('Quick Start Guide').classes('text-lg font-bold mb-3')
            with ui.column().classes('gap-2 rt-muted'):
                ui.label('1. Choose your database type (SQLite for local development, Supabase for cloud)')
                ui.label('2. If using Supabase, enter your project credentials from https://supabase.com')
                ui.label('3. Click "Save Configuration & Continue" to start using the dashboard')
                ui.label('4. You can change these settings later in the Settings page')
