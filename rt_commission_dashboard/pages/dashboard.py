from nicegui import ui, app
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.ui.layout import layout
from rt_commission_dashboard.core.db_handler import DBHandler
from rt_commission_dashboard.core.i18n import t

@layout
def dashboard_page():
    user = app.storage.user.get('user_info', {})
    db = DBHandler()
    
    # Title
    with ui.row().classes('items-center mb-6'):
        ui.icon('dashboard', size='md', color=Theme.SECONDARY)
        Theme.title(t('dash.title'))
    
    # --- KPI Cards (Order Data) ---
    kpis = db.get_kpi_stats(user['id'])
    
    with ui.row().classes('w-full gap-4'):
        _kpi_card(t('dash.total_revenue'), f"${kpis['revenue']:,.2f}", 'attach_money', 'green')
        _kpi_card(t('dash.total_commission'), f"${kpis['commission']:,.2f}", 'payments', 'blue')
        _kpi_card(t('dash.new_customers'), str(kpis['new_customers']), 'person_add', 'orange')
        _kpi_card(t('dash.network_size'), str(kpis['network_size']), 'hub', 'purple')

    # --- Charts (Monthly Sales) ---
    monthly_data = db.get_monthly_sales(user['id'])
    months = [row[0] for row in monthly_data]
    sales = [row[1] for row in monthly_data]
    
    # Fallback for empty data to show structure
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
                'font': {'color': '#94a3b8'},
                'showlegend': True,
                'xaxis': {'showgrid': False},
                'yaxis': {'gridcolor': '#334155'}
            }
        }).classes('w-full h-80')

def _kpi_card(title, value, icon, color):
    with Theme.card().classes('flex-1 min-w-[200px]'):
        with ui.row().classes('items-center gap-4'):
            ui.icon(icon).classes(f'text-3xl text-{color}-500')
            with ui.column().classes('gap-0'):
                ui.label(title).classes('text-gray-400 text-sm')
                ui.label(value).classes('text-2xl font-bold')
