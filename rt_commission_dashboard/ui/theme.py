from nicegui import ui

class Theme:
    # Color Palette (Premium Dark / Fintech)
    PRIMARY = '#4f46e5'      # Indigo 600
    SECONDARY = '#10b981'    # Emerald 500 (Growth/Money)
    ACCENT = '#8b5cf6'       # Violet 500
    DARK_BG = '#0f172a'      # Slate 900
    DARK_SURFACE = '#1e293b' # Slate 800
    TEXT_MAIN = '#f8fafc'    # Slate 50
    TEXT_MUTED = '#94a3b8'   # Slate 400

    # Border & Dividers
    BORDER = '#334155'       # Slate 700

    @staticmethod
    def apply_global_styles():
        """Injects global CSS with dark/light mode support."""
        ui.add_head_html('''
            <style>
                :root {
                    color-scheme: dark light;
                    --card-bg: #ffffff;
                    --card-border: #e2e8f0;
                    --muted: #64748b;
                    --text: #0f172a;
                    --accent: #0ea5e9;
                    --accent-soft: #e0f2fe;
                    --bg: #f8fafc;
                    --input-bg: #fff;
                    --input-border: #d1d5db;
                    --shadow: rgba(15,23,42,0.05);
                    --primary: #4f46e5;
                    --secondary: #10b981;
                    --text-muted: #6b7280;
                }

                /* Dark theme */
                .dark {
                    --card-bg: #1e293b;
                    --card-border: #334155;
                    --muted: #94a3b8;
                    --text: #f1f5f9;
                    --accent: #3b82f6;
                    --accent-soft: #1e3a5f;
                    --bg: #0f172a;
                    --input-bg: #0f172a;
                    --input-border: #475569;
                    --shadow: rgba(0,0,0,0.2);
                    --text-muted: #94a3b8;
                }

                body {
                    background: var(--bg);
                    color: var(--text);
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    transition: background 0.2s, color 0.2s;
                }

                .q-drawer {
                    background-color: var(--bg) !important;
                    border-right: 1px solid var(--card-border);
                }

                .q-header {
                    background-color: var(--bg) !important;
                    border-bottom: 1px solid var(--card-border);
                }

                .rt-card {
                    background-color: var(--card-bg);
                    border: 1px solid var(--card-border);
                    border-radius: 12px;
                    padding: 1.5rem;
                    box-shadow: 0 1px 3px var(--shadow);
                }

                .rt-input .q-field__control {
                    border-radius: 8px;
                    background: var(--input-bg);
                }

                /* Top navigation bar */
                .top-nav {
                    display: flex;
                    gap: 0.5rem;
                    align-items: center;
                }

                .top-nav-item {
                    padding: 0.5rem 1rem;
                    border-radius: 6px;
                    cursor: pointer;
                    transition: background 0.2s;
                    color: var(--text);
                    text-decoration: none;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                }

                .top-nav-item:hover {
                    background: var(--accent-soft);
                }

                .theme-toggle {
                    cursor: pointer;
                    padding: 0.5rem;
                    border-radius: 6px;
                    transition: background 0.2s;
                }

                .theme-toggle:hover {
                    background: var(--accent-soft);
                }

                /* Additional theme-aware styles */
                .q-field__label,
                .q-field__native,
                .q-field__control {
                    color: var(--text) !important;
                }

                .q-item__label {
                    color: var(--text);
                }

                .q-menu {
                    background: var(--card-bg) !important;
                    border: 1px solid var(--card-border);
                }

                /* User dropdown menu text (light/dark safe) */
                .rt-user-menu,
                .rt-user-menu *,
                .rt-user-menu__header,
                .rt-user-menu__item,
                .rt-user-menu__item .q-item__label {
                    color: var(--text) !important;
                }

                .q-table {
                    background: var(--card-bg);
                    color: var(--text);
                }

                .q-table thead tr,
                .q-table tbody td {
                    border-color: var(--card-border);
                }

                .q-btn {
                    color: var(--text);
                }

                /* Theme-aware text color utilities */
                .rt-title {
                    color: var(--text) !important;
                }

                .rt-subtitle,
                .rt-muted {
                    color: var(--text-muted) !important;
                }

                .rt-text {
                    color: var(--text) !important;
                }

                /* Fix tree component text color */
                .q-tree__node-header,
                .q-tree__node-body,
                .q-tree__node-header-content,
                .q-tree .q-tree__node-label {
                    color: var(--text) !important;
                }

                .q-tree .q-icon,
                .q-tree__icon {
                    color: var(--text) !important;
                }

                /* Override any nested tree text colors */
                .q-tree * {
                    color: inherit !important;
                }

                /* Fix table pagination styling */
                .q-table__bottom,
                .q-table__control {
                    background: var(--card-bg) !important;
                    color: var(--text) !important;
                }

                .q-table__bottom .q-btn,
                .q-table__bottom .q-select {
                    background: var(--input-bg) !important;
                    color: var(--text) !important;
                }

                .q-table__bottom .q-field__native,
                .q-table__bottom .q-field__label {
                    color: var(--text) !important;
                }

                .q-table__bottom .q-select .q-field__control {
                    background: var(--input-bg) !important;
                }

                /* Fix pagination select dropdown */
                .q-table .q-select__dropdown-icon {
                    color: var(--text) !important;
                }

                /* Fix search input text color in dark mode */
                .rt-input input,
                .rt-input .q-field__native,
                .rt-input .q-field__input,
                .q-field--outlined .q-field__native,
                .q-field--outlined input {
                    color: var(--text) !important;
                    caret-color: var(--text) !important;
                }

                .rt-input input::placeholder,
                .q-field--outlined input::placeholder {
                    color: var(--text-muted) !important;
                    opacity: 0.7;
                }

                /* Fix select dropdown item display */
                .q-item__label--caption {
                    color: var(--text-muted) !important;
                }

                .q-select__dropdown-icon {
                    color: var(--text) !important;
                }

                /* Fix chip/tag display in select */
                .q-chip {
                    background: var(--accent-soft) !important;
                    color: var(--text) !important;
                }

                /* Fix autocomplete/filter input in select */
                .q-select .q-field__input {
                    color: var(--text) !important;
                }

                .q-select--with-input .q-field__native {
                    color: var(--text) !important;
                }

                /* Admin dropdown menu text (light/dark safe) */
                .rt-admin-menu,
                .rt-admin-menu *,
                .rt-admin-menu .q-item__label {
                    color: var(--text) !important;
                }
            </style>

            <script>
                let currentTheme = null;

                function updateToggleIcon(theme) {
                    const icon = document.querySelector('.theme-toggle i');
                    if (!icon) return;
                    const isDark = (theme === 'dark') || document.body.classList.contains('dark');
                    icon.textContent = isDark ? 'light_mode' : 'dark_mode';
                }

                // Apply theme to body and html
                function applyTheme(theme, { broadcast = false, persist = true } = {}) {
                    if (theme !== 'dark' && theme !== 'light') return;
                    currentTheme = theme;
                    document.body.classList.remove('light', 'dark');
                    document.body.classList.add(theme);
                    document.documentElement.classList.remove('light', 'dark');
                    document.documentElement.classList.add(theme);
                    if (persist) {
                        localStorage.setItem('theme', theme);
                    }
                    if (broadcast) {
                        try {
                            window.parent.postMessage({ type: 'theme-change', theme }, '*');
                        } catch (e) {}
                    }
                    updateToggleIcon(theme);
                }

                // Toggle theme (local action, broadcast to parent)
                function toggleTheme() {
                    const currentTheme = document.body.classList.contains('dark') ? 'dark' : 'light';
                    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                    applyTheme(newTheme, { broadcast: true, persist: true });
                }

                // Initialize theme from localStorage or system preference
                function initTheme() {
                    const savedTheme = localStorage.getItem('theme');
                    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                    if (savedTheme) {
                        applyTheme(savedTheme, { broadcast: false, persist: true });
                    } else {
                        applyTheme(systemTheme, { broadcast: false, persist: false });
                    }
                    // Request theme from parent app (realtimex host)
                    try {
                        window.parent.postMessage({ type: 'get-theme' }, '*');
                    } catch (e) {}
                }

                // Listen for system theme changes
                window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                    if (!localStorage.getItem('theme')) {
                        applyTheme(e.matches ? 'dark' : 'light', { broadcast: false, persist: false });
                    }
                });

                // Listen for parent theme updates (realtimex host)
                window.addEventListener('message', (event) => {
                    const data = event.data || {};
                    if (data.type === 'theme-response' || data.type === 'theme-change') {
                        if (data.theme === 'dark' || data.theme === 'light') {
                            applyTheme(data.theme, { broadcast: false, persist: false });
                        }
                    }
                });

                // Fallback after 100ms if no theme applied yet
                setTimeout(() => {
                    if (!document.body.classList.contains('light') && !document.body.classList.contains('dark')) {
                        const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                        applyTheme(systemTheme, { broadcast: false, persist: false });
                    }
                }, 100);

                // Initialize on load
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', initTheme);
                } else {
                    initTheme();
                }
            </script>
        ''')

    @staticmethod
    def card():
        """Returns a stylized card container."""
        return ui.column().classes('rt-card w-full shadow-lg')

    @staticmethod
    def title(text):
        return ui.label(text).classes('text-2xl font-bold rt-title mb-2')

    @staticmethod
    def subtitle(text):
        return ui.label(text).classes('text-sm rt-subtitle mb-4')
