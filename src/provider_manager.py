import asyncio
from typing import Any, Dict, List, Optional, Tuple
from openai import AsyncOpenAI
from config_manager import ConfigManager

class Provider:
    def __init__(self, provider_id: str, base_url: str, api_key: str, models: List[Dict[str, str]]):
        self.id = provider_id
        self.base_url = base_url
        self.api_key = api_key
        self.models = {model['name']: model for model in models}
        self._client: Optional[AsyncOpenAI] = None

    async def connect(self):
        self._client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

    async def disconnect(self):
        if self._client:
            await self._client.close()
            self._client = None

    async def chat_completion(self, messages: List[Dict[str, str]], model_name: str, **kwargs) -> str:
        if not self._client:
            await self.connect()
        
        response = await self._client.chat.completions.create(
            model=model_name,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content.strip()

    def get_model_names(self) -> List[str]:
        return list(self.models.keys())

class ProviderManager:
    def __init__(self, config: ConfigManager):
        self.config = config
        self._providers: Dict[str, Provider] = {}
        self._model_aliases: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def init_providers(self):
        providers_config = self.config.get("providers", [])
        models_config = self.config.get("models", {})
        
        async with self._lock:
            await self._disconnect_all()
            self._providers = {}
            
            for provider_config in providers_config:
                provider = Provider(
                    provider_id=provider_config['id'],
                    base_url=provider_config['base_url'],
                    api_key=provider_config.get('api_key', ''),
                    models=provider_config.get('models', [])
                )
                await provider.connect()
                self._providers[provider_config['id']] = provider
            
            self._model_aliases = models_config

    async def _disconnect_all(self):
        for provider in self._providers.values():
            await provider.disconnect()

    def get_provider(self, provider_id: str) -> Optional[Provider]:
        return self._providers.get(provider_id)

    def resolve_model(self, model_ref: str) -> Tuple[Optional[str], Optional[str]]:
        if model_ref in self._model_aliases:
            model_ref = self._model_aliases[model_ref]
        
        if '/' in model_ref:
            parts = model_ref.split('/')
            provider_id = parts[0]
            model_name = '/'.join(parts[1:])
            return provider_id, model_name
        
        return None, None

    async def chat_completion(self, messages: List[Dict[str, str]], model: str, **kwargs) -> str:
        provider_id, model_name = self.resolve_model(model)
        
        if not provider_id or not model_name:
            raise ValueError(f"Invalid model reference: {model}")
        
        provider = self.get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")
        
        return await provider.chat_completion(messages, model_name, **kwargs)

    def get_all_providers(self) -> List[Dict[str, Any]]:
        result = []
        for provider_id, provider in self._providers.items():
            result.append({
                'id': provider_id,
                'type': 'openai_compatible',
                'base_url': provider.base_url,
                'models': provider.get_model_names()
            })
        return result

    def get_all_models(self) -> Dict[str, str]:
        result = {}
        for provider_id, provider in self._providers.items():
            for model_name in provider.get_model_names():
                result[f"{provider_id}/{model_name}"] = f"{provider_id}/{model_name}"
        result.update(self._model_aliases)
        return result

    async def reload(self):
        await self.init_providers()
