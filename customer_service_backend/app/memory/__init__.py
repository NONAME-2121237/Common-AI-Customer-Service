from .base import Memory
from .simple import SimpleMemory, SimpleConversationHistory, SimpleSessionManager

def RedisShortTermMemory(*args, **kwargs):
    raise ImportError("Redis not installed. Set USE_SIMPLE_MEMORY=true")

def RedisConversationHistory(*args, **kwargs):
    raise ImportError("Redis not installed. Set USE_SIMPLE_MEMORY=true")

def SessionManager(*args, **kwargs):
    raise ImportError("Redis not installed. Set USE_SIMPLE_MEMORY=true")

__all__ = [
    'Memory',
    'RedisShortTermMemory',
    'SessionManager',
    'SimpleMemory',
    'SimpleConversationHistory',
    'SimpleSessionManager'
]
