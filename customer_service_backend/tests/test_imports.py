import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    print("Testing imports...")

    try:
        from app.config import ConfigManager, get_config_manager
        print("✓ Config module imported successfully")
    except Exception as e:
        print(f"✗ Config module import failed: {e}")
        return False

    try:
        from app.providers import Provider, ProviderManager
        print("✓ Providers module imported successfully")
    except Exception as e:
        print(f"✗ Providers module import failed: {e}")
        return False

    try:
        from app.tasks import TaskExecutor
        print("✓ Tasks module imported successfully")
    except Exception as e:
        print(f"✗ Tasks module import failed: {e}")
        return False

    try:
        from app.memory import (
            Memory,
            RedisShortTermMemory,
            SessionManager,
            ConversationHistory,
            RedisConversationHistory
        )
        print("✓ Memory module imported successfully")
    except Exception as e:
        print(f"✗ Memory module import failed: {e}")
        return False

    try:
        from app.security import PreGuard, PostGuard
        print("✓ Security module imported successfully")
    except Exception as e:
        print(f"✗ Security module import failed: {e}")
        return False

    try:
        from app.knowledge import KnowledgeRetriever, DifyRetriever
        print("✓ Knowledge module imported successfully")
    except Exception as e:
        print(f"✗ Knowledge module import failed: {e}")
        return False

    try:
        from app.routing import MessageForwarder, RouteState
        print("✓ Routing module imported successfully")
    except Exception as e:
        print(f"✗ Routing module import failed: {e}")
        return False

    try:
        from app.agents import CustomerServiceAgent
        print("✓ Agents module imported successfully")
    except Exception as e:
        print(f"✗ Agents module import failed: {e}")
        return False

    try:
        from app.admin import router
        print("✓ Admin module imported successfully")
    except Exception as e:
        print(f"✗ Admin module import failed: {e}")
        return False

    try:
        from app.utils import setup_logger, format_history
        print("✓ Utils module imported successfully")
    except Exception as e:
        print(f"✗ Utils module import failed: {e}")
        return False

    print("\n✓ All imports successful!")
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
