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
    db = get_db_handler(app.storage.user.get('supabase_token'))
    data_user_id = user.get('data_user_id')
    is_admin = user.get('role') == 'admin'
    if not data_user_id and not is_admin:
        ui.notify('Account not linked to a data user yet. Please contact an admin.', type='warning')
        return
    
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
        viewable_users = sorted(
            db.get_viewable_users(data_user_id, user.get('role', 'ctv')) if data_user_id or is_admin else [],
            key=lambda u: u['label'].lower()
        )
        user_options = {u['id']: u['label'] for u in viewable_users}

        # Add "All" option for admins to see all transactions
        if is_admin:
            user_options = {'__all__': t('rep.all_users'), **user_options}

        user_select = None

        with ui.row().classes('w-full gap-4 items-center mb-6'):
            # Show User Selector if >1 option (Self + Downline) or admin
            if len(user_options) > 1 or is_admin:
                # Safe default value
                default_val = '__all__' if is_admin else data_user_id
                if default_val not in user_options:
                     default_val = list(user_options.keys())[0] if user_options else None

                user_select = ui.select(
                    options=user_options,
                    value=default_val,
                    label=t('nav.users'),
                    with_input=True,
                ).classes('w-96 rt-input text-base').props('outlined dense popup-content-class=rt-input behavior=menu')

            year_select = ui.select(
                options=[str(y) for y in range(current_year, current_year-5, -1)],
                value=str(current_year),
                label=t('rep.year')
            ).classes('w-32 rt-input').props('outlined dense popup-content-class=rt-input behavior=menu')

            # Month options with translations
            month_keys = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
            month_options = {f"{m:02d}": t(f'month.{month_keys[m-1]}') for m in range(1, 13)}
            month_select = ui.select(
                options=month_options,
                value=None,
                label=t('rep.month')
            ).classes('w-44 rt-input').props('outlined dense clearable popup-content-class=rt-input behavior=menu')

            # Type filter with translations
            type_options = {
                'All': t('type.all'),
                'Retail': t('type.retail'),
                'Share': t('type.share'),
                'Reward': t('type.reward')
            }
            type_select = ui.select(
                options=type_options,
                value='All',
                label=t('rep.type')
            ).classes('w-40 rt-input').props('outlined dense popup-content-class=rt-input behavior=menu')

            ui.button(t('rep.apply'), on_click=lambda: update_table()).classes('h-10').props('unelevated color=indigo-600')
            ui.button(t('common.reload'), on_click=lambda: update_table()).classes('h-10').props('unelevated')

            ui.space()
            search_input = ui.input(placeholder=t('common.search')).props('outlined dense append-icon=search').classes('w-48 rt-input')

        # --- Data Table ---
        columns = [
            {'name': 'created_at', 'label': t('table.date'), 'field': 'created_at', 'sortable': True, 'align': 'left'},
            {'name': 'type', 'label': t('table.type'), 'field': 'type', 'sortable': True, 'align': 'left'},
            {'name': 'amount', 'label': t('table.amount'), 'field': 'amount', 'sortable': True, 'align': 'right'},
            {'name': 'status', 'label': t('table.status'), 'field': 'status', 'align': 'center'},
            {'name': 'metadata', 'label': t('table.details'), 'field': 'metadata', 'align': 'left'},
        ]
        
        table = ui.table(columns=columns, rows=[], pagination=10).classes('w-full').props('flat bordered').bind_filter_from(search_input, 'value')
        
        def update_table():
            # Determine target user
            selected_value = user_select.value if user_select else data_user_id
            # __all__ means admin wants to see all transactions (pass None)
            filter_user_id = None if selected_value == '__all__' else selected_value

            rows = db.get_transactions_filtered(
                filter_user_id,
                month=month_select.value,
                year=year_select.value,
                type_filter=type_select.value,
                is_admin=is_admin
            )
            # Format rows for display
            from datetime import datetime
            formatted_rows = []
            for row in rows:
                row_dict = dict(row)
                row_dict['amount'] = format_currency(row_dict['amount'])

                # Custom Type Display with translations
                raw_type = row_dict['type']
                if raw_type == 'retail_sales':
                    display_type = t('type.retail_sales')
                elif raw_type == 'kpi_reward':
                    display_type = t('type.kpi_reward')
                else:
                    display_type = raw_type.replace('_', ' ').title()

                # Check for shared transactions
                if row_dict.get('shared_with_id'):
                    if row_dict.get('shared_with_id') == filter_user_id:
                        display_type = t('type.shared_received')
                    elif row_dict.get('user_id') == filter_user_id:
                        display_type = t('type.shared_given')

                row_dict['type'] = display_type

                # Translate status
                raw_status = row_dict.get('status', '')
                status_map = {
                    'pending': t('status.pending'),
                    'approved': t('status.approved'),
                    'paid': t('status.paid'),
                    'blocked': t('status.blocked')
                }
                row_dict['status'] = status_map.get(raw_status, raw_status.title() if raw_status else '-')

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
