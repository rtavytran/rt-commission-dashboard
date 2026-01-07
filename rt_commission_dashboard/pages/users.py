from nicegui import ui, app
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.ui.layout import layout
from rt_commission_dashboard.core.db_handler import get_db_handler
from rt_commission_dashboard.core.i18n import t

@layout
def users_page():
    db = get_db_handler()
    
    # Title
    with ui.row().classes('items-center mb-6'):
        ui.icon('group', size='md', color=Theme.SECONDARY)
        Theme.title(t('user.title'))
        
    Theme.subtitle(t('user.subtitle'))
    
    with Theme.card():
        # Fetch data
        users = db.get_all_users()
        
        # Process for display
        rows = []
        for u in users:
            row = dict(u)
            # Dynamic Role Mapping based on I18n
            row['role_display'] = t(f"role.{u['role']}")
            rows.append(row)

        columns = [
            {'name': 'full_name', 'label': t('user.name'), 'field': 'full_name', 'sortable': True, 'align': 'left'},
            {'name': 'email', 'label': t('user.email'), 'field': 'email', 'sortable': True, 'align': 'left'},
            {'name': 'role', 'label': t('user.role'), 'field': 'role_display', 'sortable': True, 'align': 'left'},
            {'name': 'parent_id', 'label': t('user.upline'), 'field': 'parent_id', 'align': 'left'},
            {'name': 'created_at', 'label': t('user.joined'), 'field': 'created_at', 'sortable': True, 'align': 'right'},
        ]
        
        # Custom slot not needed for basic text, but we could add chips in future.
        # Search Filter
        # Search Filter
        with ui.row().classes('w-full mb-4 justify-end'):
            search = ui.input(placeholder='Search...').props('outlined dense dark append-icon=search').classes('w-64')

        table = ui.table(
            columns=columns, 
            rows=rows, 
            row_key='id', 
            pagination=10
        ).classes('w-full').props('flat bordered').bind_filter_from(search, 'value')
