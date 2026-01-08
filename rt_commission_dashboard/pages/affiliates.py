from nicegui import ui, app
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.ui.layout import layout
from rt_commission_dashboard.core.db_handler import get_db_handler
from rt_commission_dashboard.core.i18n import t

@layout
def affiliates_page():
    user = app.storage.user.get('user_info', {})
    db = get_db_handler()
    
    with ui.row().classes('items-center mb-6'):
        ui.icon('hub', size='md', color=Theme.SECONDARY)
        Theme.title(t('nav.affiliates'))
        
    Theme.subtitle(f"Downline for {user['full_name']}")
    
    with Theme.card():
        # Tree Construction - Using Nested Data
        if user.get('role') == 'admin':
            hierarchy = db.get_entire_network_nested()
        else:
            hierarchy = db.get_downline_nested(user['id'])
        
        def build_tree_nodes(nodes):
            tree_nodes = []
            for n in nodes:
                # Recursive Children
                children = build_tree_nodes(n['children'])
                
                # Icon based on role
                icon = 'person'
                if n['role'] == 'affiliate':
                    icon = 'business'
                elif n['role'] == 'ctv':
                    icon = 'badge'
                    
                # Role Label (Translated)
                role_label = t(f"role.{n['role']}")
                    
                tree_nodes.append({
                    'id': n['id'],
                    'label': f"{n['full_name']} ({role_label})",
                    'icon': icon,
                    'children': children
                })
            return tree_nodes
            
        tree_data = build_tree_nodes(hierarchy)
        
        # If empty (no downlines), showing nothing might be confusing, so maybe show self?
        # But get_downline_nested usually returns user themselves as root if we implemented it that way.
        # Let's check DBHandler implementation. Assuming it returns list of root nodes (usually just the user).
        
        ui.tree(tree_data, label_key='label', children_key='children').expand().classes('text-lg').style('color: var(--text)')

        if not tree_data:
             # Even if just self, tree_data usually has 1 node if get_downline_nested includes root
             ui.label('No downlines found yet. Start recruiting!').classes('rt-muted italic mt-4')
