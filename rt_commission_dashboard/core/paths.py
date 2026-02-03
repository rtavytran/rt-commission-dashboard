import os
import sys
from pathlib import Path

def get_package_dir():
    """Returns the directory where the package is installed."""
    # This returns the directory containing this file (core/)
    # Then we go up one level to get rt_commission_dashboard/
    return Path(__file__).parent.parent

def get_data_dir():
    """Returns the directory where data should be stored."""
    # Check for env var override
    env_dir = os.getenv('RT_COMMISSION_DATA_DIR')
    if env_dir:
        # Expand environment variables in the path
        expanded_dir = os.path.expandvars(env_dir)
        path = Path(expanded_dir)
        # Create parent directories if needed
        parent_dir = os.path.dirname(str(path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        os.makedirs(str(path), exist_ok=True)
        return path

    # Default to current working directory (like crm-automator)
    path = Path(os.getcwd()) / 'data'
    os.makedirs(str(path), exist_ok=True)
    return path

def get_app_dir():
    """Returns the root directory of the application for user data."""
    # Use parent of data directory
    return get_data_dir().parent

def get_db_path():
    """Returns the path to the SQLite database."""
    from rt_commission_dashboard.core.config import config
    return get_data_dir() / config.get_database_filename()

def get_config_path():
    """Returns the path to the config file."""
    return get_app_dir() / 'config' / 'settings.yaml'

def get_locales_path():
    """Returns the path to the locales directory inside the package."""
    # Locales are part of the installed package
    return get_package_dir() / 'locales'
