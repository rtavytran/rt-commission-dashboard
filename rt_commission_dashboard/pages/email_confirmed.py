from nicegui import ui
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.core.i18n import t


def email_confirmed_page():
    """Page displayed after successful email confirmation from Supabase."""
    Theme.apply_global_styles()

    with ui.column().classes('absolute-center w-full max-w-md gap-6'):
        # Success icon
        with ui.row().classes('w-full justify-center'):
            ui.icon('check_circle', size='80px').classes('text-green-500')

        # Title
        ui.label(t('auth.email_confirmed_title')).classes('text-3xl font-bold text-center w-full')

        with Theme.card().classes('text-center'):
            ui.label(t('auth.email_confirmed_msg')).classes('rt-muted text-lg mb-6')

            # Return button - for users who opened in browser
            ui.button(t('auth.return_to_app'), on_click=lambda: ui.navigate.to('/login')).props('unelevated color=indigo-600').classes('w-full h-12')

            # Alternative: close window message
            with ui.row().classes('w-full justify-center mt-4'):
                ui.label(t('auth.or')).classes('rt-muted text-sm')
            ui.label(t('auth.close_window_hint')).classes('rt-muted text-sm text-center mt-2')
