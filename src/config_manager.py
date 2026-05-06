import os
import re
import time
import yaml
from typing import Any, Dict, Optional
from threading import Thread
from pathlib import Path

class ConfigManager:
    def __init__(self, config_path: str = "config/config.yaml", reload_interval: int = 5):
        self.config_path = Path(config_path)
        self.reload_interval = reload_interval
        self._config: Dict[str, Any] = {}
        self._last_modified = 0
        self._reload_thread: Optional[Thread] = None
        self._stop_reload = False
        self.load_config()
        self.start_auto_reload()

    def _replace_env_vars(self, value: str) -> str:
        if isinstance(value, str):
            return re.sub(
                r"\$\{(\w+)\}",
                lambda m: os.environ.get(m.group(1), m.group(0)),
                value
            )
        return value

    def _replace_env_vars_in_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self._replace_env_vars_in_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._replace_env_vars_in_dict(item) if isinstance(item, dict) 
                    else self._replace_env_vars(item) 
                    for item in value
                ]
            else:
                result[key] = self._replace_env_vars(value)
        return result

    def load_config(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)
        
        self._config = self._replace_env_vars_in_dict(raw_config)
        self._last_modified = self.config_path.stat().st_mtime

    def get(self, path: str, default: Any = None) -> Any:
        keys = path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, path: str, value: Any):
        keys = path.split('.')
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
        self._save_config()

    def _save_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)

    def get_raw_yaml(self) -> str:
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return f.read()

    def set_raw_yaml(self, raw_yaml: str):
        parsed = yaml.safe_load(raw_yaml)
        if parsed is not None:
            self._config = self._replace_env_vars_in_dict(parsed)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(raw_yaml)
            self._last_modified = self.config_path.stat().st_mtime

    def _reload_loop(self):
        while not self._stop_reload:
            try:
                current_modified = self.config_path.stat().st_mtime
                if current_modified > self._last_modified:
                    self.load_config()
            except Exception:
                pass
            time.sleep(self.reload_interval)

    def start_auto_reload(self):
        if self._reload_thread is None or not self._reload_thread.is_alive():
            self._stop_reload = False
            self._reload_thread = Thread(target=self._reload_loop, daemon=True)
            self._reload_thread.start()

    def stop_auto_reload(self):
        self._stop_reload = True
        if self._reload_thread is not None:
            self._reload_thread.join()

    def get_desensitized_config(self) -> Dict[str, Any]:
        def desensitize(obj):
            if isinstance(obj, dict):
                result = {}
                for key, value in obj.items():
                    if 'key' in key.lower() or 'secret' in key.lower():
                        result[key] = '***'
                    else:
                        result[key] = desensitize(value)
                return result
            elif isinstance(obj, list):
                return [desensitize(item) for item in obj]
            return obj
        return desensitize(self._config)

    def __contains__(self, path: str) -> bool:
        keys = path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return False
        return True
