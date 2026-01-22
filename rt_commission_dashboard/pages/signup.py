import os
from nicegui import ui, app
from supabase import create_client
import httpx
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.core.config import config
from rt_commission_dashboard.core.i18n import t


def signup_page():
    Theme.apply_global_styles()

    with ui.column().classes('absolute-center w-full max-w-sm'):
        ui.label(t('app.name')).classes('text-3xl font-bold text-center w-full mb-8')

        with Theme.card():
            ui.label(t('auth.create_account')).classes('text-xl font-bold mb-6 text-center w-full')

            email = ui.input(t('auth.email')).props('outlined dense type=email').classes('w-full mb-4 rt-input')
            password = ui.input(t('auth.password')).props('outlined dense type=password').classes('w-full mb-4 rt-input')
            confirm = ui.input(t('auth.confirm_password')).props('outlined dense type=password').classes('w-full mb-6 rt-input')

            def get_base_url():
                """Resolve the base URL to send in Supabase email redirects."""
                env_url = os.environ.get('APP_BASE_URL')
                if env_url:
                    return env_url.rstrip('/')
                try:
                    request = ui.context.client.request  # Provided by NiceGUI (Starlette Request)
                    if request and getattr(request, 'base_url', None):
                        return str(request.base_url).rstrip('/')
                except Exception:
                    # Fall back to localhost:runtime_port if request context is unavailable
                    pass
                # Use runtime port if available, otherwise use config default
                port = os.environ.get('RUNTIME_PORT') or config.get_app_port()
                return f"http://localhost:{port}"

            def get_supabase_client():
                supabase_url = config.get_supabase_url()
                supabase_anon = config.get_supabase_anon_key()
                if not supabase_url or not supabase_anon:
                    ui.notify('Supabase not configured. Please complete setup.', type='warning')
                    ui.navigate.to('/setup')
                    return None
                return create_client(supabase_url, supabase_anon)

            def handle_signup():
                if password.value != confirm.value:
                    ui.notify('Passwords do not match', type='negative')
                    return
                if not email.value:
                    ui.notify('Please enter email', type='negative')
                    return

                client = get_supabase_client()
                if client is None:
                    return
                base_url = get_base_url()
                email_redirect = f"{base_url}/email-confirmed"
                try:
                    resp = client.auth.sign_up(
                        {
                            'email': email.value,
                            'password': password.value,
                            'options': {
                                'email_redirect_to': email_redirect
                            }
                        }
                    )
                    if resp.user and resp.user.email_confirmed_at:
                        ui.notify('Account created. Pending approval.', type='positive')
                    else:
                        ui.notify('Signup initiated. Check your email inbox for the confirmation link. After you confirm, return here to log in.', type='positive')
                    ui.navigate.to(f"/check-email?email={email.value}")
                except httpx.RequestError:
                    ui.notify('Cannot reach Supabase. Check URL/anon key or network/proxy and try again.', type='negative')
                    ui.navigate.to('/setup')
                except Exception as exc:  # noqa: BLE001
                    ui.notify(f'Signup failed: {exc}', type='negative')

            ui.button(t('auth.sign_up'), on_click=handle_signup).props('unelevated color=indigo-600').classes('w-full h-10 mb-4')
            ui.link(t('auth.back_to_login'), '/login').classes('block text-center mt-3 text-sm text-indigo-500')
