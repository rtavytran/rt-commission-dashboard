from nicegui import ui, app
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.ui.layout import layout
from rt_commission_dashboard.core.db_handler import DBHandler
import pandas as pd

from rt_commission_dashboard.core.i18n import t

@layout
def reports_page():
    user = app.storage.user.get('user_info', {})
    db = DBHandler()
    
    with ui.row().classes('items-center mb-6'):
        ui.icon('bar_chart', size='md', color=Theme.SECONDARY)
        Theme.title(t('rep.title'))
        
    Theme.subtitle(f"{t('rep.subtitle')} {user['full_name']}")
    
    # --- Income Breakdown (Doanh thu & Thưởng) ---
    stats = db.get_kpi_stats(user['id'])
    
    with ui.grid(columns=3).classes('w-full gap-4 mb-6'):
        with Theme.card().classes('bg-slate-800 border-l-4 border-blue-500'):
            ui.label(t('rep.retail_rev')).classes('text-xs text-gray-400 uppercase')
            ui.label(f"${stats['revenue']:,.2f}").classes('text-2xl font-bold text-white')
            
        with Theme.card().classes('bg-slate-800 border-l-4 border-green-500'):
            ui.label(t('rep.comm_share')).classes('text-xs text-gray-400 uppercase')
            ui.label(f"${stats['commission_share']:,.2f}").classes('text-2xl font-bold text-white')
            
        with Theme.card().classes('bg-slate-800 border-l-4 border-purple-500'):
            ui.label(t('rep.kpi_reward')).classes('text-xs text-gray-400 uppercase')
            ui.label(f"${stats['kpi_reward']:,.2f}").classes('text-2xl font-bold text-white')

    with Theme.card():
        # --- Filters ---
        from datetime import datetime
        current_year = datetime.now().year
        
        with ui.row().classes('w-full gap-4 items-center mb-6'):
            year_select = ui.select(
                options=[str(y) for y in range(current_year, current_year-5, -1)], 
                value=str(current_year), 
                label=t('rep.year')
            ).classes('w-32').props('outlined dense dark')
            
            month_select = ui.select(
                options={f"{m:02d}": datetime(2000, m, 1).strftime('%B') for m in range(1, 13)}, 
                value=None, 
                label=t('rep.month')
            ).classes('w-40').props('outlined dense dark clearable')
            
            type_select = ui.select(
                options=['All', 'Retail', 'Share', 'Reward'], 
                value='All', 
                label=t('rep.type')
            ).classes('w-40').props('outlined dense dark')
            
            ui.button(t('rep.apply'), on_click=lambda: update_table()).classes('h-10').props('unelevated color=indigo-600')

        # --- Data Table ---
        columns = [
            {'name': 'created_at', 'label': 'Date', 'field': 'created_at', 'sortable': True},
            {'name': 'type', 'label': 'Type', 'field': 'type', 'sortable': True},
            {'name': 'amount', 'label': 'Amount', 'field': 'amount', 'sortable': True},
            {'name': 'status', 'label': 'Status', 'field': 'status'},
            {'name': 'metadata', 'label': 'Details', 'field': 'metadata'},
        ]
        
        table = ui.table(columns=columns, rows=[], pagination=10).classes('w-full').props('flat bordered')
        
        def update_table():
            rows = db.get_transactions_filtered(
                user['id'], 
                month=month_select.value, 
                year=year_select.value, 
                type_filter=type_select.value
            )
            # Format rows for display
            formatted_rows = []
            for row in rows:
                row_dict = dict(row)
                row_dict['amount'] = f"${row_dict['amount']:,.2f}"
                row_dict['type'] = row_dict['type'].replace('_', ' ').title()
                
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
