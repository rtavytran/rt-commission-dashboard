import os
from nicegui import ui, app
from supabase import create_client
import httpx
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.core.db_handler import get_db_handler
from rt_commission_dashboard.core.config import config
from rt_commission_dashboard.core.i18n import t

def login_page():
    Theme.apply_global_styles()

    # Center container
    with ui.column().classes('absolute-center w-full max-w-sm'):
        # Logo/Brand
        ui.label(t('app.name')).classes('text-3xl font-bold text-center w-full mb-8')

        with Theme.card():
            ui.label(t('auth.sign_in')).classes('text-xl font-bold mb-6 text-center w-full')

            # Tabs for Password and OTP login
            with ui.tabs().classes('w-full') as tabs:
                password_tab = ui.tab(t('auth.password'))
                otp_tab = ui.tab(t('auth.otp_login'))

            # Helper functions
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

            def complete_login(auth_response, client, user_email):
                if not auth_response or not getattr(auth_response, 'user', None):
                    ui.notify('Login failed: missing user details in response.', type='negative')
                    return

                user_id = auth_response.user.id

                profile = None
                try:
                    profile_resp = client.table('profiles')\
                        .select('id,email,full_name,role,status,user_id')\
                        .eq('id', user_id)\
                        .limit(1)\
                        .execute()
                    if hasattr(profile_resp, 'data') and profile_resp.data:
                        profile = profile_resp.data[0] if isinstance(profile_resp.data, list) else profile_resp.data
                except Exception:
                    profile = None

                if profile is None:
                    ui.notify('Account pending approval (profile not yet created).', type='warning')
                    client.auth.sign_out()
                    return

                if profile.get('status') != 'approved':
                    ui.notify('Account pending approval. Please wait for admin approval.', type='warning')
                    client.auth.sign_out()
                    return

                # Determine effective role and data user mapping
                data_user_id = profile.get('user_id')
                data_user_role = None
                if data_user_id:
                    try:
                        user_row = client.table('users').select('id, role, full_name').eq('id', data_user_id).maybe_single().execute()
                        if hasattr(user_row, 'data') and user_row.data:
                            data_user_role = user_row.data.get('role')
                            if not profile.get('full_name') and user_row.data.get('full_name'):
                                profile['full_name'] = user_row.data.get('full_name')
                    except Exception:
                        pass

                effective_role = profile.get('role') or data_user_role or 'ctv'
                session = getattr(auth_response, 'session', None)
                token = getattr(session, 'access_token', None) if session else None
                if not token:
                    ui.notify('Login failed: missing session token.', type='negative')
                    client.auth.sign_out()
                    return

                app.storage.user['authenticated'] = True
                app.storage.user['user_info'] = {
                    'id': user_id,
                    'email': profile.get('email') if profile else user_email,
                    'role': effective_role,
                    'full_name': (profile or {}).get('full_name', ''),
                    'data_user_id': data_user_id
                }
                app.storage.user['supabase_token'] = token
                ui.notify('Welcome back!', type='positive')
                ui.navigate.to('/')

            with ui.tab_panels(tabs, value=password_tab).classes('w-full'):
                # Password Login Tab
                with ui.tab_panel(password_tab):
                    email = ui.input(t('auth.email')).props('outlined dense type=email').classes('w-full mb-4 rt-input')
                    password = ui.input(t('auth.password')).props('outlined dense type=password').classes('w-full mb-4 rt-input')

                    def handle_login():
                        if not email.value:
                            ui.notify('Please enter your email.', type='warning')
                            return
                        if not password.value:
                            ui.notify('Please enter your password.', type='warning')
                            return

                        # Supabase auth path (default)
                        if config.get_database_type() == 'supabase':
                            client = get_supabase_client()
                            if client is None:
                                return

                            try:
                                auth_response = client.auth.sign_in_with_password({
                                    'email': email.value,
                                    'password': password.value
                                })
                                complete_login(auth_response, client, email.value)
                                return
                            except httpx.RequestError:
                                ui.notify('Cannot reach Supabase. Check URL/anon key or network/proxy and try again.', type='negative')
                                ui.navigate.to('/setup')
                                return
                            except Exception as exc:  # noqa: BLE001
                                msg = str(exc)
                                if 'Invalid login credentials' in msg:
                                    ui.notify('Invalid credentials or email not confirmed. Please confirm your email and ensure admin approval.', type='negative')
                                else:
                                    ui.notify(f'Login failed: {exc}', type='negative')
                                return

                        # SQLite fallback (legacy)
                        db = get_db_handler()
                        user = db.get_user(email.value)
                        if user:
                            app.storage.user['authenticated'] = True
                            app.storage.user['user_info'] = user
                            ui.notify('Welcome back!', type='positive')
                            ui.navigate.to('/')
                        else:
                            ui.notify('Invalid email (Try: admin@rt.local)', type='negative')

                    ui.button(t('auth.login'), on_click=handle_login).props('unelevated color=indigo-600').classes('w-full h-10')

                # OTP Login Tab
                with ui.tab_panel(otp_tab):
                    email_otp = ui.input(t('auth.email')).props('outlined dense type=email').classes('w-full mb-4 rt-input')

                    # OTP cooldown state
                    otp_state = {'cooldown': 0}

                    def update_send_button():
                        """Update send button based on cooldown state."""
                        if otp_state['cooldown'] > 0:
                            send_btn.text = f"Resend in {otp_state['cooldown']}s"
                            send_btn.props('disable')
                        else:
                            send_btn.text = "Send OTP Code"
                            send_btn.props(remove='disable')

                    def start_cooldown():
                        """Start 60-second cooldown."""
                        otp_state['cooldown'] = 60
                        update_send_button()

                        def tick():
                            if otp_state['cooldown'] > 0:
                                otp_state['cooldown'] -= 1
                                update_send_button()

                        timer = ui.timer(1.0, tick)
                        ui.timer(60.0, lambda: timer.cancel(), once=True)

                    def send_otp():
                        if not email_otp.value:
                            ui.notify('Please enter your email to receive an OTP.', type='warning')
                            return

                        client = get_supabase_client()
                        if client is None:
                            return
                        base_url = get_base_url()
                        email_redirect = f"{base_url}/email-confirmed"
                        try:
                            client.auth.sign_in_with_otp({
                                'email': email_otp.value,
                                'options': {
                                    'should_create_user': False,
                                    'email_redirect_to': email_redirect
                                }
                            })
                            ui.notify('OTP sent. Check your email for the code.', type='positive')
                            start_cooldown()
                        except httpx.RequestError:
                            ui.notify('Cannot reach Supabase. Check URL/anon key or network/proxy and try again.', type='negative')
                            ui.navigate.to('/setup')
                        except Exception as exc:  # noqa: BLE001
                            ui.notify(f'Failed to send OTP: {exc}', type='negative')

                    send_btn = ui.button(t('auth.send_otp'), on_click=send_otp).props('outline color=indigo-600').classes('w-full h-10 mb-4')

                    otp_code = ui.input(t('auth.otp_code')).props('outlined dense inputmode=numeric pattern=\\d* maxlength=6').classes('w-full mb-4 rt-input')

                    def handle_otp_login():
                        if not email_otp.value:
                            ui.notify('Please enter your email.', type='warning')
                            return
                        if not otp_code.value:
                            ui.notify('Enter the OTP code sent to your email.', type='warning')
                            return
                        client = get_supabase_client()
                        if client is None:
                            return
                        try:
                            auth_response = client.auth.verify_otp({
                                'email': email_otp.value,
                                'token': otp_code.value,
                                'type': 'email'
                            })
                            complete_login(auth_response, client, email_otp.value)
                        except httpx.RequestError:
                            ui.notify('Cannot reach Supabase. Check URL/anon key or network/proxy and try again.', type='negative')
                            ui.navigate.to('/setup')
                        except Exception as exc:  # noqa: BLE001
                            ui.notify(f'OTP verification failed: {exc}', type='negative')

                    ui.button(t('auth.login_with_otp'), on_click=handle_otp_login).props('unelevated color=indigo-600').classes('w-full h-10')

            ui.link(t('auth.create_account_link'), '/signup').classes('block text-center mt-3 text-sm text-indigo-500')
