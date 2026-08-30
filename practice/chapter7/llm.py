# 从零到一构建一个智能体框架，从使用框架者到自我构建框架者，其中的区别在于对Agent开发的掌握程度以及能力复用性上的价值产出

# 构建HelloAgents框架

# 设计理念：解决现有框架的痛点
# 核心：如何让学习者既能快速上手，又能深入理解Agent的工作原理？

# HelloAgentsLLM进行迭代升级，改造成更具适应性的模型调用中枢：
# 1. 多提供商支持：通过配置ModelScope提供商配置不同的模型
# 2. 本地模型集成：本地构建模型不限制在云端API调用形式，主流部署方式有vLLM和Ollama
# 3. 自动检测机制：减少用户配置自动检测服务商和根据推断结果完成具体的参数配置

import os
from dotenv import load_dotenv

from typing import Optional
from openai import OpenAI
from hello_agents import HelloAgentsLLM

load_dotenv()


class MyLLM(HelloAgentsLLM):
    """
    自定义的LLM客户端，重写HelloAgentsLLM类
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = "auto",
        **kwargs,
    ):
        # ★ 当 provider 为 "auto" 时，先触发自动检测，然后传入检测到的具体值
        if provider == "auto":
            detected = self._auto_detect_provider(api_key, base_url)
            print(f"🔍 自动检测到 provider: {detected}")
            # 如果检测到具体值就传具体值，否则传 "auto" 让父类走通用分支
            provider = detected if detected != "auto" else "auto"

        if provider == "modelscope":
            print("正在使用自定义的 ModelScope Provider")
            self.provider = "modelscope"

            # 解析 ModelScope的凭证：api_key和base_url
            self.api_key = api_key or os.getenv("MODELSCOPE_API_KEY")
            self.base_url = base_url or "https://api-inference.modelscope.cn/v1/"

            if not self.api_key:
                raise ValueError(
                    "ModelScope API key not found. Please set MODELSCOPE_API_KEY enviroment variable."
                )

            # 设置默认模型和其他参数
            self.model = (
                model or os.getenv("LLM_MODEL_ID") or "Qwen/Qwen2.5-VL-72B-Instruct"
            )
            self.temperature = kwargs.get("temperature", 0.7)
            self.max_tokens = kwargs.get("max_tokens")
            self.timeout = kwargs.get("timeout", 60)

            # 使用获取的参数创建OpenAI客户端实例
            self._client = OpenAI(
                api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
            )

        else:
            # 如果不是 modelscope，则完全使用父类的原始逻辑来处理
            super().__init__(
                model=model,
                api_key=api_key,
                base_url=base_url,
                provider=provider,
                **kwargs,
            )

    def _auto_detect_provider(
        self, api_key: Optional[str], base_url: Optional[str]
    ) -> str:
        """
        自动检测LLM服务商
        """
        # 1. 检查特定提供商的环境变量 (最高优先级)
        if os.getenv("MODELSCOPE_API_KEY"):
            return "modelscope"
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        if os.getenv("ZHIPU_API_KEY"):
            return "zhipu"

        # 获取通用的环境变量
        actual_api_key = api_key or os.getenv("LLM_API_KEY")
        actual_base_url = base_url or os.getenv("LLM_BASE_URL")

        # 2. 根据 base_url 判断
        if actual_base_url:
            base_url_lower = actual_base_url.lower()
            if "api-inference.modelscope.cn" in base_url_lower:
                return "modelscope"
            if "open.bigmodel.cn" in base_url_lower:
                return "zhipu"
            if "localhost" in base_url_lower or "127.0.0.1" in base_url_lower:
                if ":11434" in base_url_lower:
                    return "ollama"
                if ":8000" in base_url_lower:
                    return "vllm"
                return "local"  # 其他本地端口

        # 3. 根据 API 密钥格式辅助判断
        if actual_api_key:
            if actual_api_key.startswith("ms-"):
                return "modelscope"

        # 4. 兜底：委托父类的完整检测逻辑
        return super()._auto_detect_provider(api_key, base_url)

    def _resolve_credentials(
        self, api_key: Optional[str], base_url: Optional[str]
    ) -> tuple[str, str]:
        """
        根据 provider 解析 API 密钥和 base_url
        """
        if self.provider == "openai":
            resolved_api_key = (
                api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
            )
            resolved_base_url = (
                base_url or os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
            )
            return resolved_api_key, resolved_base_url
        elif self.provider == "modelscope":
            resolved_api_key = (
                api_key or os.getenv("MODELSCOPE_API_KEY") or os.getenv("LLM_API_KEY")
            )
            resolved_base_url = (
                base_url
                or os.getenv("LLM_BASE_URL")
                or "https://api-inference.modelscope.cn/v1/"
            )
            return resolved_api_key, resolved_base_url

        else:
            # 其他未特殊处理的 provider（auto / deepseek 等），委托给父类
            return super()._resolve_credentials(api_key, base_url)
