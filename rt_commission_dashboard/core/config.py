"""
Configuration management for RT Commission Dashboard.
Loads settings from config.yaml and provides centralized access.
Also loads environment variables from .env file for Supabase credentials.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    _instance: Optional['Config'] = None
    _config_data: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Load configuration from config.yaml file."""
        # Start with default configuration
        self._config_data = self._get_default_config()

        # Look for config.yaml in the project root
        config_paths = [
            Path(__file__).parent.parent.parent / "config.yaml",  # Project root
            Path.cwd() / "config.yaml",  # Current working directory
            Path(__file__).parent / "config.yaml",  # Same directory as this file
        ]

        # Try to load base config
        for path in config_paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        base_config = yaml.safe_load(f) or {}
                        self._config_data.update(base_config)
                    break
                except Exception as e:
                    print(f"Warning: Could not load config file {path}: {e}")

        # Try to load user settings from config/settings.yaml
        from rt_commission_dashboard.core.paths import get_app_dir
        settings_path = get_app_dir() / 'config' / 'settings.yaml'
        if settings_path.exists():
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    user_settings = yaml.safe_load(f) or {}
                    # Deep merge user settings into config
                    self._deep_merge(self._config_data, user_settings)
            except Exception as e:
                print(f"Warning: Could not load settings file {settings_path}: {e}")

    def _deep_merge(self, base: dict, override: dict):
        """Deep merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration when no config file is available."""
        return {
            'workspace': {
                'name': 'RT Commission Dashboard',
                'company': 'RealTime',
                'domain': 'rt.local'
            },
            'database': {
                'filename': 'rt_commission_dashboard.db'
            },
            'commission': {
                'rates': {
                    'level_1': 0.10,
                    'level_2': 0.05,
                    'level_3': 0.02
                },
                'max_levels': 5
            },
            'roles': {
                'admin': {
                    'label': 'Administrator',
                    'permissions': ['Q1', 'Q2', 'Q3', 'Q4']
                },
                'affiliate': {
                    'label': 'Affiliate',
                    'permissions': ['Q1', 'Q2', 'Q3', 'Q4']
                },
                'ctv': {
                    'label': 'Collaborator',
                    'permissions': ['Q1', 'Q2']
                }
            },
            'app': {
                'title': 'RT Commission Dashboard',
                'port': 8000,
                'secret_key': 'rt_dashboard_secret_key_123',
                'theme': 'dark'
            },
            'mock_data': {
                'enabled': True,
                'admin_email': 'admin@rt.local',
                'sample_domain': 'rt.local'
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to the configuration key (e.g., 'workspace.name')
            default: Default value to return if key is not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self._config_data
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_workspace_name(self) -> str:
        """Get the workspace/company name."""
        return self.get('workspace.name', 'RT Commission Dashboard')
    
    def get_database_filename(self) -> str:
        """Get the database filename."""
        return self.get('database.filename', 'rt_commission_dashboard.db')
    
    def get_commission_tiers(self) -> list:
        """Get commission tiers."""
        return self.get('commission.tiers', [])
    
    def get_role_rates(self) -> Dict[str, float]:
        """Get fixed rates for specific roles."""
        return self.get('commission.role_rates', {})
    
    def get_max_commission_levels(self) -> int:
        """Get maximum commission levels."""
        return self.get('commission.max_levels', 5)
    
    def get_app_title(self) -> str:
        """Get the application title."""
        return self.get('app.title', 'RT Commission Dashboard')
    
    def get_app_port(self) -> int:
        """Get the application port."""
        return self.get('app.port', 8000)
    
    def get_secret_key(self) -> str:
        """Get the application secret key."""
        return self.get('app.secret_key', 'rt_dashboard_secret_key_123')

    def get_currency(self) -> str:
        """Get the application currency (usd/vnd)."""
        return self.get('app.currency', 'usd').lower()
    
    def get_sample_domain(self) -> str:
        """Get the sample domain for mock data."""
        return self.get('mock_data.sample_domain', 'rt.local')
    
    def get_admin_email(self) -> str:
        """Get the admin email for mock data."""
        return self.get('mock_data.admin_email', 'admin@rt.local')
    
    def is_mock_data_enabled(self) -> bool:
        """Check if mock data seeding is enabled."""
        return self.get('mock_data.enabled', True)
    
    def get_role_permissions(self, role: str) -> list:
        """Get permissions for a specific role."""
        return self.get(f'roles.{role}.permissions', [])
    
    def get_role_label(self, role: str) -> str:
        """Get display label for a specific role."""
        return self.get(f'roles.{role}.label', role.title())

    # ========== Environment Variable Methods (for Supabase) ==========

    def get_database_type(self) -> str:
        """Get database type from environment variable or config."""
        # First check environment variable
        db_type = os.getenv('DATABASE_TYPE')
        if db_type:
            db_type = db_type.lower()
        else:
            # Fall back to config.yaml/settings.yaml
            db_type = self.get('database.type', 'sqlite').lower()

        if db_type == 'supabase':
            # Verify credentials are present; otherwise fall back to sqlite
            url = self.get_supabase_url()
            anon = self.get_supabase_anon_key()
            missing = [name for name, value in [
                ('SUPABASE_URL', url),
                ('SUPABASE_ANON_KEY', anon),
            ] if not value]

            if missing:
                logging.warning(f"Supabase selected but missing credentials ({', '.join(missing)}); using SQLite until configured.")
                return 'sqlite'

        return db_type

    def get_supabase_url(self) -> str:
        """Get Supabase URL from environment variable."""
        url = os.getenv('SUPABASE_URL')
        if not url:
            # Try config.yaml as fallback
            url = self.get('database.supabase.url', '')
        return url

    def get_supabase_anon_key(self) -> str:
        """Get Supabase anon key from environment variable."""
        key = os.getenv('SUPABASE_ANON_KEY')
        if not key:
            # Try config.yaml as fallback
            key = self.get('database.supabase.anon_key', '')
        return key

    def get_supabase_service_key(self) -> str:
        """Get Supabase service key from environment variable."""
        key = os.getenv('SUPABASE_SERVICE_KEY')
        if not key:
            # Try config.yaml as fallback
            key = self.get('database.supabase.service_key', '')
        return key

    def get_environment(self) -> str:
        """Get environment (development/production) from environment variable."""
        return os.getenv('ENVIRONMENT', 'development').lower()


# Global config instance
config = Config()
