import pytest
import asyncio
from config_manager import ConfigManager
from redis_client import RedisClient
from short_term_memory import ShortTermMemory
from chat_log import ChatLog

@pytest.mark.asyncio
async def test_config_manager():
    config = ConfigManager("config/config.yaml")
    assert config.get("app.name") == "智能客服后端"
    assert "providers" in config._config
    assert "models" in config._config
    print("ConfigManager test passed")

@pytest.mark.asyncio
async def test_short_term_memory_prune():
    config = ConfigManager("config/config.yaml")
    redis_client = RedisClient(config)
    try:
        await redis_client.connect()
        short_term_memory = ShortTermMemory(config, redis_client)
        
        session_id = "test_session"
        await short_term_memory.clear(session_id)
        
        for i in range(35):
            await short_term_memory.write(session_id, "user", f"Message {i}")
        
        memory = await short_term_memory.get_all(session_id)
        assert len(memory) == 30, f"Expected 30, got {len(memory)}"
        print("ShortTermMemory prune test passed")
    finally:
        await redis_client.disconnect()

@pytest.mark.asyncio
async def test_chat_log():
    config = ConfigManager("config/config.yaml")
    redis_client = RedisClient(config)
    try:
        await redis_client.connect()
        chat_log = ChatLog(redis_client)
        
        session_id = "test_chat_log"
        await chat_log.append(session_id, "user1", "user", "Hello")
        await chat_log.append(session_id, "user1", "agent", "Hi there!")
        
        messages = await chat_log.get_all_messages(session_id)
        assert len(messages) == 2
        assert messages[0]["sender"] == "user"
        assert messages[1]["sender"] == "agent"
        print("ChatLog test passed")
    finally:
        await redis_client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_config_manager())
    asyncio.run(test_short_term_memory_prune())
    asyncio.run(test_chat_log())
    print("All tests passed!")
