
import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from functools import lru_cache
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self._config_path = config_path
        self._config: Dict[str, Any] = {}
        self._raw_config: str = ""
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._lock = Lock()
        self._loaded = False
    
    def load(self) -> Dict[str, Any]:
        with self._lock:
            config_file = Path(self._config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Config file not found: {self._config_path}")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self._raw_config = f.read()
            
            self._config = yaml.safe_load(self._raw_config)
            self._config = self._replace_env_vars(self._config)
            self._loaded = True
            logger.info(f"Configuration loaded from {self._config_path}")
            
            return self._config
    
    def _replace_env_vars(self, config: Any) -> Any:
        if isinstance(config, dict):
            return {k: self._replace_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._replace_env_vars(item) for item in config]
        elif isinstance(config, str):
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, config)
            for match in matches:
                env_value = os.environ.get(match, '')
                config = config.replace(f'${{{match}}}', env_value)
            return config
        return config
    
    def get(self, path: str, default: Any = None) -> Any:
        if not self._loaded:
            self.load()
        
        keys = path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value
    
    def set(self, path: str, value: Any) -> None:
        with self._lock:
            keys = path.split('.')
            config = self._config
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            config[keys[-1]] = value
    
    def save_config(self, updates: Dict[str, Any]) -> None:
        with self._lock:
            for path, value in updates.items():
                self.set(path, value)
            
            self._save_to_file()
            logger.info(f"Configuration updated: {list(updates.keys())}")
    
    def _save_to_file(self) -> None:
        with open(self._config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)
    
    def reload(self) -> Dict[str, Any]:
        logger.info("Reloading configuration...")
        self._loaded = False
        return self.load()
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._callbacks.append(callback)
    
    def notify_callbacks(self) -> None:
        for callback in self._callbacks:
            try:
                callback(self._config)
            except Exception as e:
                logger.error(f"Error in config callback: {e}")
    
    def get_raw(self) -> str:
        if not self._loaded:
            self.load()
        return self._raw_config
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded

@lru_cache(maxsize=1)
def get_config_manager(config_path: str = "config.yaml") -> ConfigManager:
    manager = ConfigManager(config_path)
    manager.load()
    return manager
