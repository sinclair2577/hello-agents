# async_tool_executor.py
"""
异步工具执行器 - 支持并行执行多个工具调用

实现 7.5.4 节中描述的异步工具执行支持。
通过线程池将耗时的工具调用异步化，显著提升多工具场景的执行效率。
"""

import asyncio
import concurrent.futures
from typing import Dict, Any, List, Callable, Optional
from hello_agents import ToolRegistry


class AsyncToolExecutor:
    """
    异步工具执行器

    支持：
    1. 单个工具的异步执行
    2. 多个工具的并行执行
    3. 超时控制和资源管理
    4. 执行结果收集与排序
    """

    def __init__(self, registry: ToolRegistry, max_workers: int = 4):
        """
        初始化异步工具执行器

        Args:
            registry: 工具注册表
            max_workers: 线程池最大工作线程数
        """
        self.registry = registry
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    async def execute_tool_async(self, tool_name: str, input_data: str) -> str:
        """
        异步执行单个工具

        Args:
            tool_name: 工具名称
            input_data: 输入参数

        Returns:
            工具执行结果
        """
        loop = asyncio.get_event_loop()

        def _execute():
            return self.registry.execute_tool(tool_name, input_data)

        try:
            result = await loop.run_in_executor(self.executor, _execute)
            return result
        except Exception as e:
            return f"❌ 工具 '{tool_name}' 异步执行失败: {str(e)}"

    async def execute_tools_parallel(self, tasks: List[Dict[str, str]]) -> List[str]:
        """
        并行执行多个工具

        Args:
            tasks: 任务列表，每个任务包含 {"tool_name": ..., "input_data": ...}

        Returns:
            所有工具的执行结果列表（与输入顺序一致）
        """
        print(f"🚀 开始并行执行 {len(tasks)} 个工具任务")

        # 创建异步任务
        async_tasks = []
        for task in tasks:
            tool_name = task["tool_name"]
            input_data = task["input_data"]
            async_task = self.execute_tool_async(tool_name, input_data)
            async_tasks.append(async_task)

        # 等待所有任务完成
        results = await asyncio.gather(*async_tasks, return_exceptions=True)

        # 处理异常结果
        final_results = []
        for i, (task, result) in enumerate(zip(tasks, results)):
            if isinstance(result, Exception):
                final_results.append(f"❌ {task['tool_name']} 执行异常: {result}")
            else:
                final_results.append(result)

        print(f"✅ 所有 {len(tasks)} 个工具任务执行完成")
        return final_results

    async def execute_with_timeout(self, tool_name: str, input_data: str, timeout: float = 30.0) -> str:
        """
        带超时控制的异步工具执行

        Args:
            tool_name: 工具名称
            input_data: 输入参数
            timeout: 超时秒数

        Returns:
            工具执行结果或超时提示
        """
        try:
            result = await asyncio.wait_for(
                self.execute_tool_async(tool_name, input_data),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            return f"❌ 工具 '{tool_name}' 执行超时（{timeout}秒）"

    def __del__(self):
        """清理资源"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)


# ──────────────────────────────────────────────
# 使用示例（同步入口）
# ──────────────────────────────────────────────

def run_parallel_tools(registry: ToolRegistry, tasks: List[Dict[str, str]]) -> List[str]:
    """
    同步入口：并行执行多个工具

    这是一个便捷的同步封装，在非异步环境中也能使用并行工具执行。

    Args:
        registry: 工具注册表
        tasks: 任务列表

    Returns:
        执行结果列表
    """
    async def _run():
        executor = AsyncToolExecutor(registry)
        return await executor.execute_tools_parallel(tasks)

    return asyncio.run(_run())
