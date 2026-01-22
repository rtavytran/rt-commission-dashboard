from nicegui import ui, app
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.ui.layout import layout
from rt_commission_dashboard.core.db_handler import get_db_handler
from rt_commission_dashboard.core.i18n import t

@layout
def users_page():
    db = get_db_handler(app.storage.user.get('supabase_token'))
    
    # Title
    with ui.row().classes('items-center mb-6'):
        ui.icon('group', size='md', color=Theme.SECONDARY)
        Theme.title(t('user.title'))
        
    Theme.subtitle(t('user.subtitle'))
    
    with Theme.card():
        def load_rows():
            users = db.get_all_users()
            id_lookup = {}
            rows_local = []
            for u in users:
                row = dict(u)
                row['role_display'] = t(f"role.{u['role']}")
                id_lookup[u['id']] = f"{u.get('full_name') or ''} <{u.get('username') or u.get('email', '')}>"
                rows_local.append(row)
            # Fill parent display
            for row in rows_local:
                pid = row.get('parent_id')
                row['parent_display'] = id_lookup.get(pid, pid or '')
            return rows_local

        rows = load_rows()

        columns = [
            {'name': 'full_name', 'label': t('user.name'), 'field': 'full_name', 'sortable': True, 'align': 'left'},
            {'name': 'email', 'label': t('user.email'), 'field': 'email', 'sortable': True, 'align': 'left'},
            {'name': 'role', 'label': t('user.role'), 'field': 'role_display', 'sortable': True, 'align': 'left'},
            {'name': 'parent_display', 'label': t('user.upline'), 'field': 'parent_display', 'align': 'left'},
            {'name': 'created_at', 'label': t('user.joined'), 'field': 'created_at', 'sortable': True, 'align': 'right'},
        ]
        
        # Custom slot not needed for basic text, but we could add chips in future.
        # Search Filter
        with ui.row().classes('w-full mb-4 justify-end'):
            search = ui.input(placeholder=t('common.search')).props('outlined dense append-icon=search').classes('w-64 rt-input')
            ui.button(t('common.reload'), on_click=lambda: table.update_rows(load_rows())).props('unelevated color=indigo-600').classes('ml-2')

        table = ui.table(
            columns=columns, 
            rows=rows, 
            row_key='id', 
            pagination=10
        ).classes('w-full').props('flat bordered').bind_filter_from(search, 'value')
