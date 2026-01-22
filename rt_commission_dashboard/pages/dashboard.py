from nicegui import ui, app
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.ui.layout import layout
from rt_commission_dashboard.core.db_handler import get_db_handler
from rt_commission_dashboard.core.i18n import t
from rt_commission_dashboard.core.currency import format_currency

@layout
def dashboard_page():
    user = app.storage.user.get('user_info', {})
    db = get_db_handler(app.storage.user.get('supabase_token'))
    data_user_id = user.get('data_user_id')
    is_admin = user.get('role') == 'admin'

    if not data_user_id and not is_admin:
        ui.notify('Account not linked to a data user yet. Please contact an admin.', type='warning')
        return
    
    # ... (Title omitted for brevity if unchanged, but I need to make sure import works)
    
    # Title
    with ui.row().classes('items-center mb-6'):
        ui.icon('dashboard', size='md', color=Theme.SECONDARY)
        Theme.title(t('dash.title'))
    
    # --- Filter Logic ---
    from datetime import datetime
    current_year = datetime.now().year

    # Get viewable users (Self + Downline, or All if Admin), sorted by label
    # For admin, always fetch all users even if data_user_id is None
    if is_admin or data_user_id:
        viewable_users = sorted(
            db.get_viewable_users(data_user_id, user.get('role', 'ctv')),
            key=lambda u: u['label'].lower()
        )
    else:
        viewable_users = []
    user_options = {u['id']: u['label'] for u in viewable_users}

    if is_admin:
        user_options = {'global': t('dash.global_stats'), **user_options}
        default_target = 'global'
    else:
        default_target = data_user_id

    # Refreshable Content
    @ui.refreshable
    def render_dashboard_content(target_id, month, year):
        # Fetch Data
        if target_id == 'global':
            kpis = db.get_global_stats(month=month, year=year)
            monthly_data = db.get_global_monthly_sales(year=year)
        else:
            kpis = db.get_kpi_stats(target_id, month=month, year=year)
            monthly_data = db.get_monthly_sales(target_id, year=year)
            
        # --- KPI Cards ---
        with ui.column().classes('w-full gap-3'):
            with ui.row().classes('w-full gap-4'):
                _kpi_card(t('dash.total_revenue'), format_currency(kpis['revenue']), 'attach_money', 'green')
                _kpi_card(t('dash.total_commission'), format_currency(kpis['commission']), 'payments', 'blue')
                _kpi_card(t('dash.new_customers'), str(kpis['new_customers']), 'person_add', 'orange')
                _kpi_card(t('dash.network_size'), str(kpis['network_size']), 'hub', 'purple')
            with ui.row().classes('w-full gap-4'):
                _kpi_card(t('dash.ranking_volume'), format_currency(kpis.get('ranking_volume', 0)), 'stacked_line_chart', 'indigo')
                _kpi_card(t('dash.tier_rate'), f"{kpis.get('tier_rate', 0)*100:.2f}%", 'trending_up', 'cyan')
                _kpi_card(t('dash.shared_out'), format_currency(kpis.get('shared_out_amount', 0)), 'north_east', 'teal')
                _kpi_card(t('dash.shared_received'), format_currency(kpis.get('shared_received_amount', 0)), 'south_west', 'pink')

            # --- Commission Breakdown ---
            ui.label(t('dash.comm_breakdown')).classes('text-lg font-bold mt-6 mb-2 rt-subtitle')
            with ui.row().classes('w-full gap-4'):
                _kpi_card(t('dash.comm_direct'), format_currency(kpis['comm_direct']), 'store', 'teal')
                _kpi_card(t('dash.comm_override'), format_currency(kpis['comm_override']), 'group_work', 'pink')
                _kpi_card(t('dash.comm_shared'), format_currency(kpis['comm_shared']), 'share', 'cyan')
                _kpi_card(t('dash.comm_received'), format_currency(kpis['comm_received']), 'move_to_inbox', 'indigo')

            # --- Charts ---
            months = [row[0] for row in monthly_data]
            sales = [row[1] for row in monthly_data]
            
            if not months:
                months = ['Jan', 'Feb', 'Mar']
                sales = [0, 0, 0]

            with Theme.card().classes('w-full mt-6'):
                ui.label(t('dash.chart_title')).classes('text-xl font-bold mb-4')
                ui.plotly({
                    'data': [
                        {'x': months, 'y': sales, 'type': 'bar', 'name': 'Sales', 'marker': {'color': '#6366f1'}},
                        {'x': months, 'y': sales, 'type': 'scatter', 'mode': 'lines+markers', 'name': 'Trend', 'line': {'color': '#10b981'}}
                    ],
                    'layout': {
                        'margin': {'l': 40, 'r': 20, 't': 20, 'b': 40},
                        'plot_bgcolor': 'rgba(0,0,0,0)',
                        'paper_bgcolor': 'rgba(0,0,0,0)',
                        'showlegend': True,
                        'xaxis': {'showgrid': False, 'type': 'category'},
                        'yaxis': {'gridcolor': 'rgba(128,128,128,0.2)'}
                    }
                }).classes('w-full h-80')

    # --- Render Filters ---
    with ui.row().classes('mb-4 items-center gap-4'):
        
        # 1. User Selector (Only if > 1 option)
        target_select = None
        if len(user_options) > 0: # Always >0 (self)
             if len(user_options) > 1 or is_admin:
                target_select = ui.select(
                    options=user_options,
                    value=default_target,
                    label=t('nav.users'),
                    on_change=lambda: refresh_all(),
                    with_input=True,
                ).classes('w-96 rt-input text-base').props('outlined dense popup-content-class=rt-input behavior=menu')

        # 2. Year Selector
        year_select = ui.select(
            options=[str(y) for y in range(current_year, current_year-5, -1)],
            value=str(current_year),
            label=t('rep.year'),
            on_change=lambda: refresh_all()
        ).classes('w-32 rt-input').props('outlined dense popup-content-class=rt-input behavior=menu')

        # 3. Month Selector with translations
        month_keys = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        month_options = {f"{m:02d}": t(f'month.{month_keys[m-1]}') for m in range(1, 13)}
        month_select = ui.select(
            options=month_options,
            value=None,
            label=t('rep.month'),
            on_change=lambda: refresh_all()
        ).classes('w-44 rt-input').props('outlined dense clearable popup-content-class=rt-input behavior=menu')

        ui.button(t('common.reload'), on_click=lambda: refresh_all()).props('unelevated color=indigo-600').classes('h-10')
        def refresh_all():
            t_id = target_select.value if target_select else default_target
            m = month_select.value
            y = year_select.value
            render_dashboard_content.refresh(t_id, m, y)
            
    # Initial Render
    render_dashboard_content(default_target, None, str(current_year))

def _kpi_card(title, value, icon, color):
    with Theme.card().classes('flex-1 min-w-[200px]'):
        with ui.row().classes('items-center gap-4'):
            ui.icon(icon).classes(f'text-3xl text-{color}-500')
            with ui.column().classes('gap-0'):
                ui.label(title).classes('rt-muted text-sm')
                ui.label(value).classes('text-2xl font-bold rt-title')
