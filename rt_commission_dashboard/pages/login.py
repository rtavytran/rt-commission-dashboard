from nicegui import ui, app
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.core.db_handler import DBHandler

def login_page():
    Theme.apply_global_styles()
    
    # Center container
    with ui.column().classes('absolute-center w-full max-w-sm'):
        # Logo/Brand
        ui.label('RT Commission Dashboard').classes('text-3xl font-bold text-center w-full mb-8 text-indigo-500')
        
        with Theme.card():
            ui.label('Sign In').classes('text-xl font-bold mb-6 text-center w-full')
            
            email = ui.input('Email').props('outlined dense dark').classes('w-full mb-4')
            password = ui.input('Password').props('outlined dense dark type=password').classes('w-full mb-6')
            
            def handle_login():
                db = DBHandler()
                user = db.get_user(email.value)
                
                # Phase 1: Any password works if email exists
                if user:
                    app.storage.user['authenticated'] = True
                    app.storage.user['user_info'] = user
                    ui.notify('Welcome back!', type='positive')
                    ui.navigate.to('/')
                else:
                    ui.notify('Invalid email (Try: admin@rt.local)', type='negative')

            ui.button('Login', on_click=handle_login).props('unelevated color=indigo-600').classes('w-full h-10')
            
        # Helper for Phase 1 testing
        with ui.expansion('Dev Hints', icon='code').classes('w-full mt-4 text-gray-500 text-sm'):
            with ui.column().classes('gap-1'):
                ui.label('Test Accounts:')
                ui.label('admin@rt.local (Admin)')
                ui.label('daily1@rt.local (Affiliate)')
                ui.label('ctv1@rt.local (CTV)')
                ui.label('Pass: admin')
