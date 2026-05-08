import logging
from typing import Dict, List, Optional, Tuple, Any
from functools import lru_cache

from .base import Provider
from .openai_compatible import OpenAICompatibleProvider
from .anthropic import AnthropicProvider
from ..config import get_config_manager

logger = logging.getLogger(__name__)

class ProviderManager:
    def __init__(self):
        self._providers: Dict[str, Provider] = {}
        self._model_aliases: Dict[str, str] = {}
        self._config = get_config_manager()
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        providers_config = self._config.get('providers', [])
        model_aliases = self._config.get('models', {})
        
        for provider_config in providers_config:
            provider_id = provider_config['id']
            provider_type = provider_config.get('type', 'openai_compatible')
            base_url = provider_config['base_url']
            api_key = provider_config.get('api_key', '')
            timeout = provider_config.get('timeout', 30)
            models = provider_config.get('models', [])
            
            if provider_type == 'openai_compatible':
                provider = OpenAICompatibleProvider(
                    provider_id=provider_id,
                    base_url=base_url,
                    api_key=api_key,
                    timeout=timeout,
                    models=models
                )
            elif provider_type == 'anthropic':
                provider = AnthropicProvider(
                    provider_id=provider_id,
                    base_url=base_url,
                    api_key=api_key,
                    timeout=timeout
                )
            else:
                logger.warning(f"Unknown provider type: {provider_type}, using OpenAI compatible")
                provider = OpenAICompatibleProvider(
                    provider_id=provider_id,
                    base_url=base_url,
                    api_key=api_key,
                    timeout=timeout,
                    models=models
                )
            
            self._providers[provider_id] = provider
            logger.info(f"Loaded provider: {provider_id} ({provider_type})")
        
        self._model_aliases = model_aliases
        logger.info(f"Loaded {len(self._model_aliases)} model aliases")
    
    def reload(self) -> None:
        logger.info("Reloading providers...")
        self._providers.clear()
        self._model_aliases.clear()
        self._initialize_providers()
    
    def get_model(self, model_id: str) -> Tuple[Provider, str, Dict[str, Any]]:
        if model_id in self._model_aliases:
            model_id = self._model_aliases[model_id]
        
        if '/' not in model_id:
            raise ValueError(f"Invalid model ID format: {model_id}. Expected format: provider_id/model_name")
        
        provider_id, model_name = model_id.split('/', 1)
        
        if provider_id not in self._providers:
            raise ValueError(f"Provider not found: {provider_id}")
        
        provider = self._providers[provider_id]
        model_config = provider.get_model_config(model_name) or {}
        
        return provider, model_name, model_config
    
    def get_provider(self, provider_id: str) -> Optional[Provider]:
        return self._providers.get(provider_id)
    
    def list_providers(self) -> List[Dict[str, Any]]:
        result = []
        for provider_id, provider in self._providers.items():
            result.append({
                "id": provider_id,
                "base_url": provider.base_url,
                "models": list(provider._models_config.keys()) if hasattr(provider, '_models_config') else []
            })
        return result
    
    def list_models(self) -> Dict[str, str]:
        return self._model_aliases.copy()
    
    async def health_check_all(self) -> Dict[str, bool]:
        results = {}
        for provider_id, provider in self._providers.items():
            try:
                results[provider_id] = await provider.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {provider_id}: {e}")
                results[provider_id] = False
        return results

@lru_cache(maxsize=1)
def get_provider_manager() -> ProviderManager:
    return ProviderManager()
