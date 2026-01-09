import os
from nicegui import ui, app
from supabase import create_client
import httpx
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.core.db_handler import get_db_handler
from rt_commission_dashboard.core.config import config

def login_page():
    Theme.apply_global_styles()

    # Center container
    with ui.column().classes('absolute-center w-full max-w-sm'):
        # Logo/Brand
        ui.label('RT Commission Dashboard').classes('text-3xl font-bold text-center w-full mb-8')

        with Theme.card():
            ui.label('Sign In').classes('text-xl font-bold mb-6 text-center w-full')

            email = ui.input('Email').props('outlined dense').classes('w-full mb-4 rt-input')
            password = ui.input('Password').props('outlined dense type=password').classes('w-full mb-4 rt-input')
            otp_code = ui.input('One-time code (OTP)').props('outlined dense inputmode=numeric pattern=\\d* maxlength=6').classes('w-full mb-6 rt-input')

            def get_supabase_client():
                supabase_url = config.get_supabase_url()
                supabase_anon = config.get_supabase_anon_key()
                if not supabase_url or not supabase_anon:
                    ui.notify('Supabase not configured. Please complete setup.', type='warning')
                    ui.navigate.to('/setup')
                    return None
                return create_client(supabase_url, supabase_anon)

            def complete_login(auth_response, client):
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
                    'email': profile.get('email') if profile else email.value,
                    'role': effective_role,
                    'full_name': (profile or {}).get('full_name', ''),
                    'data_user_id': data_user_id
                }
                app.storage.user['supabase_token'] = token
                ui.notify('Welcome back!', type='positive')
                ui.navigate.to('/')

            def handle_login():
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
                        complete_login(auth_response, client)
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

            def send_otp():
                if not email.value:
                    ui.notify('Please enter your email to receive an OTP.', type='warning')
                    return
                client = get_supabase_client()
                if client is None:
                    return
                try:
                    client.auth.sign_in_with_otp({
                        'email': email.value,
                        'options': {'should_create_user': False}
                    })
                    ui.notify('OTP sent. Check your email for the code.', type='positive')
                except httpx.RequestError:
                    ui.notify('Cannot reach Supabase. Check URL/anon key or network/proxy and try again.', type='negative')
                    ui.navigate.to('/setup')
                except Exception as exc:  # noqa: BLE001
                    ui.notify(f'Failed to send OTP: {exc}', type='negative')

            def handle_otp_login():
                if not email.value:
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
                        'email': email.value,
                        'token': otp_code.value,
                        'type': 'email'
                    })
                    complete_login(auth_response, client)
                except httpx.RequestError:
                    ui.notify('Cannot reach Supabase. Check URL/anon key or network/proxy and try again.', type='negative')
                    ui.navigate.to('/setup')
                except Exception as exc:  # noqa: BLE001
                    ui.notify(f'OTP verification failed: {exc}', type='negative')

            ui.button('Login', on_click=handle_login).props('unelevated color=indigo-600').classes('w-full h-10 mb-2')
            with ui.row().classes('w-full gap-2'):
                ui.button('Send OTP', on_click=send_otp).props('outline color=indigo-600').classes('flex-1 h-10')
                ui.button('Login with OTP', on_click=handle_otp_login).props('unelevated color=indigo-600').classes('flex-1 h-10')
            ui.link('Create account', '/signup').classes('block text-center mt-3 text-sm text-indigo-500')
