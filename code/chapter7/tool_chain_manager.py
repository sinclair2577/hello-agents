# tool_chain_manager.py
"""
工具链管理器 - 支持多个工具的顺序执行与编排

实现 7.5.4 节中描述的工具链式调用机制。
通过将多个工具串联为可复用的工作流，让 Agent 能够完成更复杂的任务。
"""

from typing import List, Dict, Any, Optional
from hello_agents import ToolRegistry


class ToolChain:
    """
    工具链 - 支持多个工具的顺序执行

    允许将多个工具串联为一个可复用的工作流。
    每个步骤的输出可以作为后续步骤的输入（通过变量替换）。
    """

    def __init__(self, name: str, description: str):
        """
        初始化工具链

        Args:
            name: 工具链名称
            description: 工具链描述
        """
        self.name = name
        self.description = description
        self.steps: List[Dict[str, Any]] = []

    def add_step(self, tool_name: str, input_template: str, output_key: Optional[str] = None):
        """
        添加工具执行步骤

        Args:
            tool_name: 工具名称
            input_template: 输入模板，支持 {input}、{step_0_result} 等变量替换
            output_key: 输出结果的键名，用于后续步骤引用（默认自动生成）
        """
        self.steps.append({
            "tool_name": tool_name,
            "input_template": input_template,
            "output_key": output_key or f"step_{len(self.steps)}_result"
        })

    def execute(self, registry: ToolRegistry, initial_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        执行工具链

        Args:
            registry: 工具注册表
            initial_input: 初始输入
            context: 额外上下文变量

        Returns:
            最后一步的执行结果
        """
        context = context or {}
        context["input"] = initial_input

        print(f"\n🔗 开始执行工具链: {self.name}")
        print(f"📥 初始输入: {initial_input[:60]}...")

        for i, step in enumerate(self.steps):
            tool_name = step["tool_name"]
            input_template = step["input_template"]
            output_key = step["output_key"]

            # 替换模板中的变量
            try:
                tool_input = input_template.format(**context)
            except KeyError as e:
                error_msg = f"❌ 工具链执行失败: 模板变量 {e} 未找到"
                print(error_msg)
                return error_msg

            print(f"\n  步骤 {i+1}/{len(self.steps)}: 使用 [{tool_name}]")
            print(f"  输入: {tool_input[:80]}...")

            # 执行工具
            result = registry.execute_tool(tool_name, tool_input)
            context[output_key] = result

            print(f"  ✅ 步骤 {i+1} 完成，结果长度: {len(result)} 字符")

        final_result = context[self.steps[-1]["output_key"]]
        print(f"\n🎉 工具链 '{self.name}' 执行完成")
        return final_result


class ToolChainManager:
    """
    工具链管理器

    负责注册、管理和执行多个工具链。
    """

    def __init__(self, registry: ToolRegistry):
        """
        初始化工具链管理器

        Args:
            registry: 工具注册表
        """
        self.registry = registry
        self.chains: Dict[str, ToolChain] = {}

    def register_chain(self, chain: ToolChain):
        """
        注册工具链

        Args:
            chain: ToolChain 实例
        """
        self.chains[chain.name] = chain
        print(f"✅ 工具链 '{chain.name}' 已注册")

    def execute_chain(self, chain_name: str, input_data: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        执行指定的工具链

        Args:
            chain_name: 工具链名称
            input_data: 输入数据
            context: 额外上下文变量

        Returns:
            执行结果
        """
        if chain_name not in self.chains:
            return f"❌ 工具链 '{chain_name}' 不存在"

        chain = self.chains[chain_name]
        return chain.execute(self.registry, input_data, context)

    def list_chains(self) -> List[str]:
        """列出所有已注册的工具链"""
        return list(self.chains.keys())

    def remove_chain(self, chain_name: str) -> bool:
        """移除工具链"""
        if chain_name in self.chains:
            del self.chains[chain_name]
            print(f"🗑️ 工具链 '{chain_name}' 已移除")
            return True
        return False


# ──────────────────────────────────────────────
# 预置工具链示例
# ──────────────────────────────────────────────

def create_research_chain() -> ToolChain:
    """
    创建一个研究工具链: 搜索 → 计算 → 总结

    适用于需要先搜索信息再进行计算的场景。
    """
    chain = ToolChain(
        name="research_and_calculate",
        description="搜索信息并进行相关计算"
    )

    # 步骤 1: 搜索信息
    chain.add_step(
        tool_name="search",
        input_template="{input}",
        output_key="search_result"
    )

    # 步骤 2: 基于搜索结果进行计算
    chain.add_step(
        tool_name="my_calculator",
        input_template="根据搜索结果: {search_result}，计算相关数值: {input}",
        output_key="calculation_result"
    )

    return chain


def create_qa_chain() -> ToolChain:
    """
    创建一个问答工具链: 搜索 → 总结

    适用于需要搜索信息并给出简洁回答的场景。
    """
    chain = ToolChain(
        name="search_and_answer",
        description="搜索信息并给出简洁回答"
    )

    # 步骤 1: 搜索信息
    chain.add_step(
        tool_name="search",
        input_template="{input}",
        output_key="search_result"
    )

    return chain
