import os
from nicegui import ui, app
from supabase import create_client
import httpx
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.core.config import config


def signup_page():
    Theme.apply_global_styles()

    with ui.column().classes('absolute-center w-full max-w-sm'):
        ui.label('RT Commission Dashboard').classes('text-3xl font-bold text-center w-full mb-8')

        with Theme.card():
            ui.label('Create Account').classes('text-xl font-bold mb-6 text-center w-full')

            email = ui.input('Email').props('outlined dense type=email').classes('w-full mb-4 rt-input')
            password = ui.input('Password').props('outlined dense type=password').classes('w-full mb-4 rt-input')
            confirm = ui.input('Confirm Password').props('outlined dense type=password').classes('w-full mb-4 rt-input')
            otp_code = ui.input('OTP code (passwordless option)').props('outlined dense inputmode=numeric pattern=\\d* maxlength=6').classes('w-full mb-6 rt-input')

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
                base_url = os.environ.get('APP_BASE_URL')
                if base_url:
                    base_url = base_url.rstrip('/')
                else:
                    # Fallback to localhost default port; users can override APP_BASE_URL
                    base_url = f"http://localhost:{config.get_app_port()}"
                email_redirect = f"{base_url}/login"
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
                        ui.notify('Signup initiated. Check your email to confirm. Then wait for admin approval.', type='positive')
                    ui.navigate.to(f"/check-email?email={email.value}")
                except httpx.RequestError:
                    ui.notify('Cannot reach Supabase. Check URL/anon key or network/proxy and try again.', type='negative')
                    ui.navigate.to('/setup')
                except Exception as exc:  # noqa: BLE001
                    ui.notify(f'Signup failed: {exc}', type='negative')

            def send_signup_otp():
                if not email.value:
                    ui.notify('Please enter email to receive an OTP.', type='warning')
                    return
                client = get_supabase_client()
                if client is None:
                    return
                try:
                    client.auth.sign_in_with_otp({
                        'email': email.value,
                        'options': {'should_create_user': True}
                    })
                    ui.notify('OTP sent. Check your email to finish signup.', type='positive')
                except httpx.RequestError:
                    ui.notify('Cannot reach Supabase. Check URL/anon key or network/proxy and try again.', type='negative')
                    ui.navigate.to('/setup')
                except Exception as exc:  # noqa: BLE001
                    ui.notify(f'Failed to send OTP: {exc}', type='negative')

            def verify_signup_otp():
                if not email.value:
                    ui.notify('Please enter email before verifying.', type='warning')
                    return
                if not otp_code.value:
                    ui.notify('Enter the OTP code sent to your email.', type='warning')
                    return
                client = get_supabase_client()
                if client is None:
                    return
                try:
                    client.auth.verify_otp({
                        'email': email.value,
                        'token': otp_code.value,
                        'type': 'email'
                    })
                    ui.notify('OTP verified. Account created/pending approval. You can log in after approval.', type='positive')
                    ui.navigate.to(f"/check-email?email={email.value}")
                except httpx.RequestError:
                    ui.notify('Cannot reach Supabase. Check URL/anon key or network/proxy and try again.', type='negative')
                    ui.navigate.to('/setup')
                except Exception as exc:  # noqa: BLE001
                    ui.notify(f'OTP verification failed: {exc}', type='negative')

            ui.button('Sign Up', on_click=handle_signup).props('unelevated color=indigo-600').classes('w-full h-10 mb-2')
            with ui.row().classes('w-full gap-2'):
                ui.button('Send OTP', on_click=send_signup_otp).props('outline color=indigo-600').classes('flex-1 h-10')
                ui.button('Verify OTP & Register', on_click=verify_signup_otp).props('unelevated color=indigo-600').classes('flex-1 h-10')
            ui.link('Back to Login', '/login').classes('block text-center mt-3 text-sm text-indigo-500')
