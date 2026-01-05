import os
import sys
from pathlib import Path

def get_app_dir():
    """Returns the root directory of the application."""
    # Determine if running as a script or frozen exe
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(os.getcwd())

def get_data_dir():
    """Returns the directory where data should be stored."""
    # Check for env var override
    env_dir = os.getenv('RT_COMMISSION_DATA_DIR')
    if env_dir:
        path = Path(env_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    # Default to local directory for portability during dev
    path = get_app_dir() / 'data'
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_db_path():
    """Returns the path to the SQLite database."""
    from rt_commission_dashboard.core.config import config
    return get_data_dir() / config.get_database_filename()

def get_config_path():
    """Returns the path to the config file."""
    return get_app_dir() / 'config' / 'settings.yaml'

def get_locales_path():
    """Returns the path to the locales directory."""
    # Assuming locales is inside the package (i.e. sibling to core, ui, etc.)
    # We are in core/paths.py, so parent is rt_commission_dashboard
    # Actually get_app_dir usually points to root of project (d:\RTA\GitHub\rt-commission-dashboard)
    # The new folder was created at d:\RTA\GitHub\rt-commission-dashboard\rt_commission_dashboard\locales
    return get_app_dir() / 'rt_commission_dashboard' / 'locales'
