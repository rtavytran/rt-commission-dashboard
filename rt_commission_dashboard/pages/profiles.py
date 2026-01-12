from nicegui import ui, app
from rt_commission_dashboard.ui.theme import Theme
from rt_commission_dashboard.ui.layout import layout
from rt_commission_dashboard.core.db_handler import get_db_handler
from rt_commission_dashboard.core.i18n import t

@layout
def profiles_page():
    db = get_db_handler(app.storage.user.get('supabase_token'))
    user = app.storage.user.get('user_info', {})

    # Title
    with ui.row().classes('items-center mb-6'):
        ui.icon('badge', size='md', color=Theme.SECONDARY)
        Theme.title('Dashboard Profiles')

    Theme.subtitle('Manage dashboard access for RealTimeX users')

    with Theme.card():
        def load_rows():
            profiles = db.get_all_profiles()
            users = db.get_all_users()

            # Create user lookup
            user_lookup = {u['id']: f"{u.get('full_name') or ''} <{u.get('username') or u.get('email', '')}>" for u in users}

            rows_local = []
            for p in profiles:
                row = dict(p)
                row['status_display'] = p['status'].upper() if p.get('status') else 'PENDING'
                row['role_display'] = t(f"role.{p['role']}") if p.get('role') else 'ctv'
                row['user_link_display'] = user_lookup.get(p.get('user_id'), p.get('user_id') or '(No Link)')
                rows_local.append(row)
            return rows_local

        rows = load_rows()

        columns = [
            {'name': 'email', 'label': 'Email', 'field': 'email', 'sortable': True, 'align': 'left'},
            {'name': 'full_name', 'label': 'Full Name', 'field': 'full_name', 'sortable': True, 'align': 'left'},
            {'name': 'role', 'label': 'Role', 'field': 'role_display', 'sortable': True, 'align': 'left'},
            {'name': 'status', 'label': 'Status', 'field': 'status_display', 'sortable': True, 'align': 'left'},
            {'name': 'user_link', 'label': 'Linked User', 'field': 'user_link_display', 'align': 'left'},
            {'name': 'created_at', 'label': 'Created At', 'field': 'created_at', 'sortable': True, 'align': 'right'},
            {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'},
        ]

        # Search Filter
        with ui.row().classes('w-full mb-4 justify-end'):
            search = ui.input(placeholder='Search...').props('outlined dense append-icon=search').classes('w-64 rt-input')
            ui.button('Reload', on_click=lambda: table.update_rows(load_rows())).props('unelevated color=indigo-600').classes('ml-2')

        table = ui.table(
            columns=columns,
            rows=rows,
            row_key='id',
            pagination=10
        ).classes('w-full').props('flat bordered')

        # Bind search filter
        table.bind_filter_from(search, 'value')

        # Add edit functionality
        def edit_profile(row):
            """Edit profile details."""
            profile_id = row['id']

            with ui.dialog() as dialog, ui.card().classes('w-96'):
                ui.label(f"Edit Profile: {row['email']}").classes('text-xl font-bold mb-4')

                # Get all users for linking
                users = db.get_all_users()
                user_options = {None: '(No Link)'}
                user_options.update({u['id']: f"{u.get('full_name') or ''} ({u.get('email') or u.get('username')})" for u in users})

                # Role selector
                role_select = ui.select(
                    options={'ctv': 'CTV', 'affiliate': 'Affiliate', 'admin': 'Admin'},
                    value=row.get('role', 'ctv'),
                    label='Role'
                ).props('outlined dense').classes('w-full mb-4')

                # Status selector
                status_select = ui.select(
                    options={'pending': 'Pending', 'approved': 'Approved', 'blocked': 'Blocked'},
                    value=row.get('status', 'pending'),
                    label='Status'
                ).props('outlined dense').classes('w-full mb-4')

                # User link selector
                user_link_select = ui.select(
                    options=user_options,
                    value=row.get('user_id'),
                    label='Link to User (for data access)'
                ).props('outlined dense use-input fill-input').classes('w-full mb-4')

                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('Cancel', on_click=dialog.close).props('flat')

                    def save_changes():
                        updates = {
                            'role': role_select.value,
                            'status': status_select.value,
                            'user_id': user_link_select.value
                        }

                        # If approving, set approved_by and approved_at
                        if status_select.value == 'approved' and row.get('status') != 'approved':
                            success = db.approve_profile(profile_id, user['id'])
                        else:
                            success = db.update_profile(profile_id, updates)

                        if success:
                            ui.notify('Profile updated successfully!', type='positive')
                            table.update_rows(load_rows())
                            dialog.close()
                        else:
                            ui.notify('Failed to update profile', type='negative')

                    ui.button('Save', on_click=save_changes).props('unelevated color=indigo-600')

            dialog.open()

        # Add action buttons to each row
        table.add_slot('body-cell-actions', '''
            <q-td :props="props" class="text-center">
                <q-btn flat dense icon="edit" color="primary" size="sm" @click="$parent.$emit('edit', props.row)" />
            </q-td>
        ''')

        table.on('edit', lambda e: edit_profile(e.args))
