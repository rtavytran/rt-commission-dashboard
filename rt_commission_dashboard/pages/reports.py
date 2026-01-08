from nicegui import ui, app
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.ui.layout import layout
from rt_commission_dashboard.core.db_handler import get_db_handler
import pandas as pd

from rt_commission_dashboard.core.i18n import t
from rt_commission_dashboard.core.currency import format_currency

@layout
def reports_page():
    user = app.storage.user.get('user_info', {})
    db = get_db_handler()
    
    # Title
    with ui.row().classes('items-center mb-6'):
        ui.icon('summarize', size='md', color=Theme.SECONDARY)
        Theme.title(t('rep.title'))
        
    # --- Data Table Section ---


    with Theme.card():
    # --- Filters ---
        from datetime import datetime
        current_year = datetime.now().year
        
        
        # User Filter (Admin or Parent), sorted by label
        viewable_users = sorted(db.get_viewable_users(user['id'], user.get('role', 'ctv')), key=lambda u: u['label'].lower())
        user_options = {u['id']: u['label'] for u in viewable_users}
        target_user_id = user['id'] # Default
        user_select = None
        
        with ui.row().classes('w-full gap-4 items-center mb-6'):
            # Show User Selector if >1 option (Self + Downline)
            if len(user_options) > 1:
                # Safe default value
                default_val = user['id']
                if default_val not in user_options:
                     default_val = list(user_options.keys())[0] if user_options else None
                
                user_select = ui.select(
                    options=user_options,
                    value=default_val,
                    label=t('nav.users')
                ).classes('w-72 rt-input').props('outlined dense use-input fill-input input-debounce=0 filter clearable popup-content-class=rt-input')

            year_select = ui.select(
                options=[str(y) for y in range(current_year, current_year-5, -1)],
                value=str(current_year),
                label=t('rep.year')
            ).classes('w-32 rt-input').props('outlined dense')

            month_select = ui.select(
                options={f"{m:02d}": datetime(2000, m, 1).strftime('%B') for m in range(1, 13)},
                value=None,
                label=t('rep.month')
            ).classes('w-40 rt-input').props('outlined dense clearable')

            type_select = ui.select(
                options=['All', 'Retail', 'Share', 'Reward'],
                value='All',
                label=t('rep.type')
            ).classes('w-40 rt-input').props('outlined dense')

            ui.button(t('rep.apply'), on_click=lambda: update_table()).classes('h-10').props('unelevated color=indigo-600')

            ui.space()
            search_input = ui.input(placeholder='Search...').props('outlined dense append-icon=search').classes('w-48 rt-input')

        # --- Data Table ---
        columns = [
            {'name': 'created_at', 'label': 'Date', 'field': 'created_at', 'sortable': True, 'align': 'left'},
            {'name': 'type', 'label': 'Type', 'field': 'type', 'sortable': True, 'align': 'left'},
            {'name': 'amount', 'label': 'Amount', 'field': 'amount', 'sortable': True, 'align': 'right'},
            {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'center'},
            {'name': 'metadata', 'label': 'Details', 'field': 'metadata', 'align': 'left'},
        ]
        
        table = ui.table(columns=columns, rows=[], pagination=10).classes('w-full').props('flat bordered').bind_filter_from(search_input, 'value')
        
        def update_table():
            # Determine target user
            filter_user_id = user_select.value if user_select else user['id']
            
            rows = db.get_transactions_filtered(
                filter_user_id, 
                month=month_select.value, 
                year=year_select.value, 
                type_filter=type_select.value
            )
            # Format rows for display
            from datetime import datetime
            formatted_rows = []
            for row in rows:
                row_dict = dict(row)
                row_dict['amount'] = format_currency(row_dict['amount'])
                
                # Custom Type Display
                display_type = row_dict['type'].replace('_', ' ').title()
                if row_dict.get('shared_with_id'):
                    if row_dict.get('shared_with_id') == filter_user_id:
                        display_type = "Shared (Received)"
                    elif row_dict.get('user_id') == filter_user_id:
                        display_type = f"Shared (Given)"
                
                row_dict['type'] = display_type
                
                # Format Date
                try:
                    dt = datetime.strptime(row_dict['created_at'], '%Y-%m-%d %H:%M:%S')
                    row_dict['created_at'] = dt.strftime('%d/%m/%Y %H:%M')
                except Exception:
                    pass # Keep original if parse fails
                
                # Clean up metadata display
                if row_dict.get('metadata'):
                    import json
                    try:
                        meta = json.loads(row_dict['metadata'])
                        if 'customer' in meta: 
                            row_dict['metadata'] = f"{meta.get('customer')} ({meta.get('product', '')})"
                        elif 'note' in meta: 
                            row_dict['metadata'] = meta.get('note')
                    except: pass
                else:
                    row_dict['metadata'] = '-'
                
                formatted_rows.append(row_dict)
                    
            table.rows = formatted_rows
            table.update()

        # Initial Load
        update_table()
