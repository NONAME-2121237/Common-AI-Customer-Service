
import time
import logging
from pathlib import Path
from threading import Thread, Event
from typing import Optional

logger = logging.getLogger(__name__)

class ConfigHotReloader:
    def __init__(self, config_path: str, callback, check_interval: float = 1.0):
        self._config_path = config_path
        self._callback = callback
        self._check_interval = check_interval
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._last_mtime: float = 0
        self._enabled = True
    
    def start(self) -> None:
        config_file = Path(self._config_path)
        if config_file.exists():
            self._last_mtime = config_file.stat().st_mtime
        
        self._thread = Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logger.info(f"Hot reload started for {self._config_path}")
    
    def _watch_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if self._enabled:
                    self._check_for_changes()
            except Exception as e:
                logger.error(f"Error checking config changes: {e}")
            self._stop_event.wait(self._check_interval)
    
    def _check_for_changes(self) -> None:
        config_file = Path(self._config_path)
        if not config_file.exists():
            return
        
        current_mtime = config_file.stat().st_mtime
        if current_mtime > self._last_mtime:
            logger.info(f"Config file changed, reloading...")
            self._last_mtime = current_mtime
            try:
                self._callback()
            except Exception as e:
                logger.error(f"Error reloading config: {e}")
    
    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Hot reload stopped")
    
    def enable(self) -> None:
        self._enabled = True
    
    def disable(self) -> None:
        self._enabled = False
