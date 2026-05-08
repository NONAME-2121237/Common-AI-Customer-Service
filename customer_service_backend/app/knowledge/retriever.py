import logging
import httpx
from typing import List, Dict, Any, Optional

from ..config import get_config_manager

logger = logging.getLogger(__name__)

class KnowledgeRetriever:
    async def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        raise NotImplementedError

class DifyRetriever(KnowledgeRetriever):
    def __init__(self):
        self._config = get_config_manager()
        self._knowledge_config = self._config.get('knowledge.config', {})
        self._api_base = self._knowledge_config.get('api_base', 'http://localhost:5001/v1')
        self._api_key = self._knowledge_config.get('api_key', '')
        self._top_k = self._knowledge_config.get('retrieval_top_k', 3)
    
    async def retrieve(self, query: str, top_k: int = None) -> List[str]:
        effective_top_k = top_k if top_k is not None else self._top_k
        
        headers = {
            'Authorization': f'Bearer {self._api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'query': query,
            'top_k': effective_top_k
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f'{self._api_base}/retrieval',
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return self._parse_dify_response(result)
                else:
                    logger.warning(f"Dify API returned status {response.status_code}")
                    return []
                    
        except httpx.ConnectError:
            logger.warning(f"Cannot connect to Dify API at {self._api_base}")
            return []
        except Exception as e:
            logger.error(f"Error retrieving from Dify: {e}")
            return []
    
    def _parse_dify_response(self, result: Dict[str, Any]) -> List[str]:
        chunks = []
        
        if 'data' in result:
            data = result['data']
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        if 'content' in item:
                            chunks.append(item['content'])
                        elif 'text' in item:
                            chunks.append(item['text'])
            elif isinstance(data, dict) and 'segments' in data:
                for segment in data['segments']:
                    if 'content' in segment:
                        chunks.append(segment['content'])
        
        return chunks

class QdrantRetriever(KnowledgeRetriever):
    def __init__(self, url: str = "http://localhost:6333", collection: str = "knowledge"):
        self._url = url
        self._collection = collection
    
    async def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        headers = {'Content-Type': 'application/json'}
        
        payload = {
            'vector': [0.0] * 1536,
            'limit': top_k,
            'with_payload': True
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f'{self._url}/collections/{self._collection}/points/search',
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return self._parse_qdrant_response(result)
                else:
                    logger.warning(f"Qdrant API returned status {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error retrieving from Qdrant: {e}")
            return []
    
    def _parse_qdrant_response(self, result: Dict[str, Any]) -> List[str]:
        chunks = []
        
        if 'result' in result:
            for item in result['result']:
                if 'payload' in item and 'content' in item['payload']:
                    chunks.append(item['payload']['content'])
        
        return chunks
