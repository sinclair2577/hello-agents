# my_plan_solve_agent.py
"""
自定义规划执行智能体 MyPlanAndSolveAgent

继承自 hello_agents 框架的 PlanAndSolveAgent，扩展功能包括：
1. 完善的 custom_prompts 支持
2. 更鲁棒的 Planner 计划输出解析
3. 流式输出规划与执行过程
4. 执行结果汇总（不仅仅是最后一步）
"""

from typing import Optional, List, Dict, Any
from hello_agents import PlanAndSolveAgent, HelloAgentsLLM, Config, Message
from hello_agents.agents.plan_solve_agent import Planner, Executor


class MyPlanAndSolveAgent(PlanAndSolveAgent):
    """
    自定义规划执行智能体

    扩展了框架的 PlanAndSolveAgent，提供了：
    - 更灵活的自定义提示词支持（通过 custom_prompts 传入）
    - 增强的计划解析（多种格式兼容）
    - 执行结果汇总（将各步骤结果合并为完整答案）
    - 详细的步骤日志输出
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        custom_prompts: Optional[Dict[str, str]] = None,
    ):
        """
        初始化 MyPlanAndSolveAgent

        Args:
            name: Agent 名称
            llm: LLM 实例
            system_prompt: 系统提示词
            config: 配置对象
            custom_prompts: 自定义提示词模板 {"planner": ..., "executor": ...}
        """
        super().__init__(name, llm, system_prompt, config, custom_prompts)
        print(f"✅ {name} 初始化完成")

        # 如果传入了 custom_prompts，重新初始化 Planner 和 Executor
        if custom_prompts:
            planner_prompt = custom_prompts.get("planner")
            executor_prompt = custom_prompts.get("executor")
            self.planner = EnhancedPlanner(self.llm, planner_prompt)
            self.executor = EnhancedExecutor(self.llm, executor_prompt)

    def run(self, input_text: str, **kwargs) -> str:
        """
        运行 Plan and Solve Agent

        Args:
            input_text: 要解决的问题
            **kwargs: 其他参数

        Returns:
            最终答案（包含各步骤汇总）
        """
        print(f"\n🤖 {self.name} 开始处理问题: {input_text}")

        # 1. 生成计划
        plan = self.planner.plan(input_text, **kwargs)
        if not plan:
            final_answer = "无法生成有效的行动计划，任务终止。"
            print(f"\n─── 任务终止 ───\n{final_answer}")
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(final_answer, "assistant"))
            return final_answer

        print(f"\n📋 执行计划（共 {len(plan)} 步）:")
        for idx, step in enumerate(plan, 1):
            print(f"  步骤 {idx}: {step}")

        # 2. 执行计划
        final_answer = self.executor.execute(input_text, plan, **kwargs)

        # 3. 汇总结果（用 LLM 做一次整合）
        summary = self._summarize_results(input_text, plan, final_answer, **kwargs)
        print(f"\n─── 任务完成 ───\n最终答案:\n{summary}")

        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(summary, "assistant"))

        return summary

    def _summarize_results(self, question: str, plan: List[str], last_result: str, **kwargs) -> str:
        """
        将执行结果汇总为完整的最终答案
        """
        plan_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(plan)])
        summary_prompt = f"""
请根据以下执行结果，给出一个完整的最终答案：

# 原始问题:
{question}

# 执行计划:
{plan_str}

# 最后一步结果:
{last_result}

请给出一个完整的、有条理的最终答案。
"""
        messages = [{"role": "user", "content": summary_prompt}]
        return self.llm.invoke(messages, **kwargs) or last_result


class EnhancedPlanner(Planner):
    """增强版规划器 - 支持更灵活的计划输出格式解析"""

    def plan(self, question: str, **kwargs) -> List[str]:
        """
        生成执行计划（增强版）

        支持多种格式解析:
        - ```python [...] ```
        - ``` [...] ```
        - 纯列表文本 [...]
        """
        prompt = self.prompt_template.format(question=question)
        messages = [{"role": "user", "content": prompt}]

        print("\n─── 正在生成计划 ───")
        response_text = self.llm_client.invoke(messages, **kwargs) or ""
        print(f"✅ 计划已生成\n{response_text}")

        # 尝试多种方式解析计划
        plan = self._parse_plan(response_text)
        if not plan:
            print("⚠️ 未能解析出有效计划，尝试直接使用 LLM 重新生成...")
            retry_prompt = f"""
请将以下问题分解为2-5个执行步骤，每个步骤用一句话描述。
只输出一个 Python 列表，例如: ["步骤1", "步骤2", "步骤3"]

问题: {question}
"""
            messages = [{"role": "user", "content": retry_prompt}]
            response_text = self.llm_client.invoke(messages, **kwargs) or ""
            plan = self._parse_plan(response_text)

        return plan if isinstance(plan, list) else []

    def _parse_plan(self, text: str) -> Optional[List[str]]:
        """从 LLM 响应中解析计划列表"""
        import ast
        import re

        # 方法1: 提取 ```python ... ``` 代码块
        match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            try:
                plan = ast.literal_eval(match.group(1).strip())
                if isinstance(plan, list):
                    return plan
            except (ValueError, SyntaxError):
                pass

        # 方法2: 提取 ``` ... ``` 代码块
        match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            try:
                plan = ast.literal_eval(match.group(1).strip())
                if isinstance(plan, list):
                    return plan
            except (ValueError, SyntaxError):
                pass

        # 方法3: 查找 [...] 列表形式
        match = re.search(r"\[.*?\]", text, re.DOTALL)
        if match:
            try:
                plan = ast.literal_eval(match.group(0))
                if isinstance(plan, list):
                    return plan
            except (ValueError, SyntaxError):
                pass

        return None


class EnhancedExecutor(Executor):
    """增强版执行器 - 支持更详细的步骤输出"""

    def execute(self, question: str, plan: List[str], **kwargs) -> str:
        """
        按计划执行任务（增强版）

        增加功能：
        - 每个步骤的详细日志
        - 步骤间上下文传递
        """
        history = ""
        step_results = []
        final_answer = ""

        print("\n─── 正在执行计划 ───")
        for i, step in enumerate(plan, 1):
            print(f"\n→ 步骤 {i}/{len(plan)}: {step}")

            prompt = self.prompt_template.format(
                question=question,
                plan=plan,
                history=history if history else "无",
                current_step=step
            )
            messages = [{"role": "user", "content": prompt}]

            response_text = self.llm_client.invoke(messages, **kwargs) or ""

            history += f"步骤 {i}: {step}\n结果: {response_text}\n\n"
            step_results.append(response_text)
            final_answer = response_text
            print(f"  ✅ 步骤 {i} 完成")

        # 汇总各步骤结果
        if len(step_results) > 1:
            summary_prompt = f"""
问题: {question}
执行计划: {plan}

请将以下各步骤的执行结果整合为最终的完整答案:

{history}

请给出最终的完整答案:
"""
            messages = [{"role": "user", "content": summary_prompt}]
            final_answer = self.llm_client.invoke(messages, **kwargs) or final_answer

        return final_answer
