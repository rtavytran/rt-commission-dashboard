from nicegui import ui
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.core.i18n import t


def check_email_page():
    Theme.apply_global_styles()
    # Get email from query if present
    try:
        email = ui.context.client.request.args.get('email', '')
    except Exception:
        email = ''

    with ui.column().classes('absolute-center w-full max-w-sm gap-4'):
        ui.label(t('auth.check_email')).classes('text-3xl font-bold text-center w-full')
        with Theme.card():
            ui.label(t('auth.confirm_email')).classes('text-xl font-bold mb-4 text-center w-full')
            ui.label(t('auth.email_sent')).classes('rt-muted mb-2 text-center')
            if email:
                ui.label(f'Email: {email}').classes('text-center text-sm rt-muted')
            ui.button(t('auth.back_to_login'), on_click=lambda: ui.navigate.to('/login')).props('unelevated color=indigo-600').classes('w-full h-10 mt-4')
