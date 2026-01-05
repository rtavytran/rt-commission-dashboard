from nicegui import ui, app
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.core.i18n import t, set_lang, get_current_lang

def layout(content_func):
    """Decorator to wrap pages in the standard dashboard layout."""
    
    @ui.page(content_func.__name__ if hasattr(content_func, '__name__') else None)
    def wrapper():
        # Apply global styles
        Theme.apply_global_styles()
        
        # Check Auth (Phase 1: Simple check)
        if not app.storage.user.get('authenticated', False):
            return ui.navigate.to('/login')

        user = app.storage.user.get('user_info', {'full_name': 'Guest', 'role': 'Visitor'})

        # --- Header ---
        with ui.header().classes('items-center h-16 px-6'):
            ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white dense')
            ui.label('APP NAGEN').classes('text-xl font-bold ml-4 tracking-wider')
            
            ui.space()
            
            # Application Language Switcher
            def toggle_lang():
                new_lang = 'en' if get_current_lang() == 'vi' else 'vi'
                set_lang(new_lang)
                ui.open(app.storage.user.get('referrer_path', '/')) # Reload current page

            current_lang = get_current_lang()
            lang_label = 'VI' if current_lang == 'vi' else 'EN'
            ui.button(f"{lang_label}", on_click=toggle_lang).props('flat text-color=white dense').classes('mr-4 font-bold border border-white/20 rounded-md px-2')

            # User Menu
            with ui.row().classes('items-center gap-2 cursor-pointer'):
                ui.label(user['full_name']).classes('text-sm font-medium')
                ui.avatar(icon='person', color=Theme.PRIMARY, text_color='white').props('size=sm')
                
                with ui.menu():
                    ui.menu_item(t('logout'), on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login')))

        # --- Sidebar ---
        with ui.left_drawer(value=True).classes('py-6 px-2') as left_drawer:
            def nav_link(label, icon, target):
                with ui.item(on_click=lambda: ui.navigate.to(target)).classes('rounded-lg hover:bg-slate-800 mb-1'):
                    with ui.item_section().props('avatar'):
                        ui.icon(icon, color=Theme.SECONDARY)
                    with ui.item_section():
                        ui.label(label).classes('text-gray-300')
            
            ui.label('MAIN').classes('text-xs font-bold text-gray-500 ml-4 mb-2 mt-2')
            nav_link(t('nav.dashboard'), 'dashboard', '/')
            nav_link(t('nav.affiliates'), 'hub', '/affiliates')
            nav_link(t('nav.reports'), 'bar_chart', '/reports')
            
            if user['role'] == 'admin':
                ui.label('ADMIN').classes('text-xs font-bold text-gray-500 ml-4 mb-2 mt-4')
                nav_link(t('nav.users'), 'group', '/admin/users')
                nav_link(t('nav.contracts'), 'description', '/admin/contracts')

        # --- Main Content ---
        # Store current path for reload
        app.storage.user['referrer_path'] = '/'
        
        with ui.column().classes('w-full p-6'):
            content_func()

    return wrapper
