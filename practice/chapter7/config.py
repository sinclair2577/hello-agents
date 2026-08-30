"""配置管理"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseModel


class Config(BaseModel):
    """
    HelloAgents配置类
    用于将代码中的硬编码配置参数集中，并支持从环境变量中读取
    """

    default_model: str = "deepseek-v4-pro"
    default_provider: str = "deepseek-ai"
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    debug: bool = False
    log_level: str = "INFO"

    max_history_length: int = 100

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量创建配置"""
        return cls(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=(
                int(os.getenv("MAX_TOKENS")) if os.getenv("MAX_TOKENS") else None
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
