import json
from nicegui import app
from rt_commission_dashboard.core.paths import get_locales_path

TRANSLATIONS = {}

def load_translations():
    """Loads translations from JSON files in the locales directory."""
    global TRANSLATIONS
    locales_dir = get_locales_path()
    
    # Load supported languages
    for lang in ['en', 'vi']:
        try:
            file_path = locales_dir / f'{lang}.json'
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    TRANSLATIONS[lang] = json.load(f)
            else:
                print(f"Warning: Locale file not found: {file_path}")
                TRANSLATIONS[lang] = {}
        except Exception as e:
            print(f"Error loading {lang} translation: {e}")
            TRANSLATIONS[lang] = {}

# Load on module import
load_translations()

def t(key):
    """Fetches the translation for the given key based on user's selected language."""
    # Default to 'vi' if not set
    lang = app.storage.user.get('lang', 'vi') 
    
    # Fallback logic: Try selected lang -> Try 'vi' (default) -> Return key
    if lang in TRANSLATIONS and key in TRANSLATIONS[lang]:
        return TRANSLATIONS[lang][key]
    elif 'vi' in TRANSLATIONS and key in TRANSLATIONS['vi']:
        return TRANSLATIONS['vi'][key]
    
    return key

def get_current_lang():
    return app.storage.user.get('lang', 'vi')

def set_lang(lang_code):
    if lang_code in TRANSLATIONS:
        app.storage.user['lang'] = lang_code
