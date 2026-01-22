from nicegui import ui, app
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.core.paths import get_config_path
from rt_commission_dashboard.core.i18n import t
import yaml
import os

def setup_page():
    Theme.apply_global_styles()

    # Center container
    with ui.column().classes('absolute-center w-full max-w-2xl'):
        # Logo/Brand
        ui.label(t('app.name')).classes('text-3xl font-bold text-center w-full mb-4')
        ui.label(t('setup.title')).classes('text-xl rt-subtitle text-center w-full mb-8')

        def normalize_supabase_url(url_or_id: str) -> str:
            """Convert project ID or URL to full Supabase URL."""
            if not url_or_id:
                return ''
            url_or_id = url_or_id.strip()
            # Already a full URL
            if url_or_id.startswith('http://') or url_or_id.startswith('https://'):
                return url_or_id.rstrip('/')
            # Just project ID - convert to URL
            return f'https://{url_or_id}.supabase.co'

        with Theme.card():
            ui.label(t('setup.db_config')).classes('text-xl font-bold mb-4')
            ui.label(t('setup.db_config_desc')).classes('rt-muted mb-6')

            # Database Type Selector
            db_type_select = ui.select(
                options={'sqlite': 'SQLite (Local)', 'supabase': 'Supabase (Cloud)'},
                value='supabase',
                label=t('setup.db_type')
            ).props('outlined dense').classes('w-full mb-4 rt-input')

            # Supabase Configuration
            supabase_container = ui.column().classes('w-full gap-4')

            with supabase_container:
                ui.label(t('setup.supabase_config')).classes('text-lg font-semibold mb-2')

                supabase_url = ui.input(
                    label=t('setup.supabase_url'),
                    placeholder=t('setup.supabase_url_hint'),
                    value=os.environ.get('SUPABASE_URL', '')
                ).props('outlined stack-label').classes('w-full rt-input')

                supabase_anon_key = ui.input(
                    label=t('setup.supabase_anon_key'),
                    placeholder=t('setup.supabase_anon_key_hint'),
                    value=os.environ.get('SUPABASE_ANON_KEY', '')
                ).props('outlined stack-label type=password').classes('w-full rt-input')

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
                        ui.notify('Please enter Supabase URL/Project ID and Anon Key', type='negative')
                        return

                    # Normalize URL (accept project ID or full URL)
                    normalized_url = normalize_supabase_url(supabase_url.value)

                    settings['database'] = {
                        'type': 'supabase',
                        'supabase': {
                            'url': normalized_url,
                            'anon_key': supabase_anon_key.value
                        }
                    }

                    # Set environment variables
                    os.environ['DATABASE_TYPE'] = 'supabase'
                    os.environ['SUPABASE_URL'] = normalized_url
                    os.environ['SUPABASE_ANON_KEY'] = supabase_anon_key.value
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

                # Redirect to login for proper auth
                ui.navigate.to('/login')

            ui.button(t('setup.save_continue'), on_click=save_config).props('unelevated color=indigo-600').classes('w-full h-10 mt-4')

        # Information Card
        with Theme.card().classes('mt-6'):
            ui.label(t('setup.quick_start')).classes('text-lg font-bold mb-3')
            with ui.column().classes('gap-2 rt-muted'):
                ui.label(t('setup.step1'))
                ui.label(t('setup.step2'))
                ui.label(t('setup.step3'))
                ui.label(t('setup.step4'))
