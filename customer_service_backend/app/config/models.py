
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class ProviderModel(BaseModel):
    name: str
    default_params: Optional[Dict[str, Any]] = None

class Provider(BaseModel):
    id: str
    type: str
    base_url: str
    api_key: str
    timeout: int = 30
    models: List[ProviderModel] = []

class ModelAlias(BaseModel):
    name: str

class TaskConfig(BaseModel):
    model: str
    fallback: Optional[str] = None
    timeout: int = 30

class MemoryConfig(BaseModel):
    provider: str
    config: Dict[str, Any]

class KnowledgeConfig(BaseModel):
    provider: str
    config: Dict[str, Any]

class TransferConfig(BaseModel):
    enabled: bool = True
    default_target_url: str
    method: str = "POST"
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    timeout: int = 5
    retry: int = 1
    auto_release_seconds: int = 600
    clear_memory_on_transfer: bool = True
    freeze_memory_during_transfer: bool = True

class RoutingConfig(BaseModel):
    transfer: TransferConfig

class SecurityConfig(BaseModel):
    enabled: bool = True
    rule_based_fallback: bool = True

class ResponseTemplates(BaseModel):
    escalate: str = "已为您转接人工客服。"
    rejection: str = "请遵守对话规范。"
    interrupt_limit: str = "您输入太快，请稍后重试。"

class AgentConfig(BaseModel):
    system_prompt_template: str
    response_templates: ResponseTemplates = ResponseTemplates()
    max_interrupt_count: int = 5
    escalate_keywords: List[str] = ["人工客服", "转人工"]
    think_prompt: str

class AppConfig(BaseModel):
    name: str = "智能客服后端"
    debug: bool = False
    max_agent_iterations: int = 5

class AdminConfig(BaseModel):
    api_key: str = ""
    log_file: str = "logs/app.log"

class LoggingConfig(BaseModel):
    file: str = "logs/app.log"
    level: str = "INFO"

class Config(BaseModel):
    app: AppConfig
    providers: List[Provider] = []
    models: Dict[str, str] = {}
    tasks: Dict[str, TaskConfig] = {}
    memory: MemoryConfig
    knowledge: Optional[KnowledgeConfig] = None
    routing: RoutingConfig
    security: SecurityConfig = SecurityConfig()
    agent: AgentConfig
    admin: AdminConfig = AdminConfig()
    logging: LoggingConfig = LoggingConfig()
