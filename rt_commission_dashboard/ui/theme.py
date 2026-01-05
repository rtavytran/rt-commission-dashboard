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
        """Injects global CSS for a refined look."""
        ui.add_head_html(f'''
            <style>
                body {{
                    background-color: {Theme.DARK_BG};
                    color: {Theme.TEXT_MAIN};
                    font-family: 'Inter', sans-serif;
                }}
                .q-drawer {{
                    background-color: {Theme.DARK_BG} !important;
                    border-right: 1px solid {Theme.BORDER};
                }}
                .q-header {{
                    background-color: {Theme.DARK_BG} !important;
                    border-bottom: 1px solid {Theme.BORDER};
                }}
                .rt-card {{
                    background-color: {Theme.DARK_SURFACE};
                    border: 1px solid {Theme.BORDER};
                    border-radius: 12px;
                    padding: 1.5rem;
                }}
                .rt-input .q-field__control {{
                    border-radius: 8px;
                }}
            </style>
        ''')

    @staticmethod
    def card():
        """Returns a stylized card container."""
        return ui.column().classes('rt-card w-full shadow-lg')

    @staticmethod
    def title(text):
        return ui.label(text).classes('text-2xl font-bold text-white mb-2')
        
    @staticmethod
    def subtitle(text):
        return ui.label(text).classes('text-sm text-gray-400 mb-4')
