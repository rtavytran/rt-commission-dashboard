from nicegui import ui
from rt_commission_dashboard.ui.theme import Theme


def check_email_page():
    Theme.apply_global_styles()
    # Get email from query if present
    try:
        email = ui.context.client.request.args.get('email', '')
    except Exception:
        email = ''

    with ui.column().classes('absolute-center w-full max-w-sm gap-4'):
        ui.label('Check your email').classes('text-3xl font-bold text-center w-full')
        with Theme.card():
            ui.label('Confirm your email to continue').classes('text-xl font-bold mb-4 text-center w-full')
            ui.label('We sent a confirmation link to your email. Click it, you will return to the login screen, then wait for admin approval.').classes('rt-muted mb-2 text-center')
            if email:
                ui.label(f'Email: {email}').classes('text-center text-sm rt-muted')
            ui.button('Back to Login', on_click=lambda: ui.navigate.to('/login')).props('unelevated color=indigo-600').classes('w-full h-10 mt-4')
