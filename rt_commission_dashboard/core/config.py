"""
Configuration management for RT Commission Dashboard.
Loads settings from config.yaml and provides centralized access.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

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
        # Look for config.yaml in the project root
        config_paths = [
            Path(__file__).parent.parent.parent / "config.yaml",  # Project root
            Path.cwd() / "config.yaml",  # Current working directory
            Path(__file__).parent / "config.yaml",  # Same directory as this file
        ]
        
        config_file = None
        for path in config_paths:
            if path.exists():
                config_file = path
                break
        
        if config_file is None:
            # Use default configuration if no config file found
            self._config_data = self._get_default_config()
            return
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load config file {config_file}: {e}")
            self._config_data = self._get_default_config()
    
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
    
    def get_commission_rates(self) -> Dict[int, float]:
        """Get commission rates by level."""
        rates = self.get('commission.rates', {})
        return {
            1: rates.get('level_1', 0.10),
            2: rates.get('level_2', 0.05),  
            3: rates.get('level_3', 0.02)
        }
    
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


# Global config instance
config = Config()