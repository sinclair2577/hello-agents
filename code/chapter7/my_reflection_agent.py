# my_reflection_agent.py
"""
自定义反思型智能体 MyReflectionAgent

继承自 hello_agents 框架的 ReflectionAgent，扩展功能包括：
1. 支持自定义提示词模板
2. 质量评分机制（每次反思后对输出打分，低于阈值才继续优化）
3. 完整的输出追踪与日志
4. 与框架消息系统的集成
"""

from typing import Optional, Dict, Any
from hello_agents import ReflectionAgent, HelloAgentsLLM, Config, Message
from hello_agents.agents.reflection_agent import Memory

# ──────────────────────────────────────────────
# 默认提示词模板（与框架一致，留作自定义的基准）
# ──────────────────────────────────────────────
DEFAULT_PROMPTS = {
    "initial": """
请根据以下要求完成任务：

任务: {task}

请提供一个完整、准确的回答。
""",
    "reflect": """
请仔细审查以下回答，并找出可能的问题或改进空间：

# 原始任务:
{task}

# 当前回答:
{content}

请分析这个回答的质量，指出不足之处，并提出具体的改进建议。
如果回答已经很好，请回答"无需改进"。
""",
    "refine": """
请根据反馈意见改进你的回答：

# 原始任务:
{task}

# 上一轮回答:
{last_attempt}

# 反馈意见:
{feedback}

请提供一个改进后的回答。
"""
}


class MyReflectionAgent(ReflectionAgent):
    """
    自定义反思型智能体 - 具备质量评分机制

    相比框架基类增加的增强功能：
    - quality_threshold: 质量评分阈值，低于此值才继续迭代（默认 7/10）
    - custom_prompts: 更灵活的自定义提示词
    - 详细的步骤日志输出
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_iterations: int = 3,
        custom_prompts: Optional[Dict[str, str]] = None,
        quality_threshold: float = 7.0,
    ):
        """
        初始化 MyReflectionAgent

        Args:
            name: Agent 名称
            llm: LLM 实例
            system_prompt: 系统提示词
            config: 配置对象
            max_iterations: 最大反思迭代次数
            custom_prompts: 自定义提示词模板 {"initial": ..., "reflect": ..., "refine": ...}
            quality_threshold: 质量评分阈值（0-10），低于此值才继续优化
        """
        super().__init__(name, llm, system_prompt, config, max_iterations, custom_prompts)
        self.quality_threshold = quality_threshold
        print(f"✅ {name} 初始化完成，最大迭代: {max_iterations}，质量阈值: {quality_threshold}")

    def run(self, input_text: str, **kwargs) -> str:
        """
        运行反思型智能体（带质量评分）

        Args:
            input_text: 任务描述
            **kwargs: 其他参数

        Returns:
            最终优化后的结果
        """
        print(f"\n🤖 {self.name} 开始处理任务: {input_text}")
        self.memory = Memory()  # 重置记忆

        # ── 第 1 步：初始执行 ──
        print("\n─── 正在进行初始尝试 ───")
        initial_prompt = self.prompts["initial"].format(task=input_text)
        initial_result = self._get_llm_response(initial_prompt, **kwargs)
        self.memory.add_record("execution", initial_result)
        print(f"\n📝 初始结果:\n{initial_result}")

        # ── 第 2 步：迭代反思与优化 ──
        for i in range(self.max_iterations):
            print(f"\n─── 第 {i+1}/{self.max_iterations} 轮迭代 ───")

            # 2a. 反思
            print("\n→ 正在进行反思...")
            last_result = self.memory.get_last_execution()
            reflect_prompt = self.prompts["reflect"].format(
                task=input_text,
                content=last_result
            )
            feedback = self._get_llm_response(reflect_prompt, **kwargs)
            self.memory.add_record("reflection", feedback)
            print(f"\n💡 反思反馈:\n{feedback}")

            # 2b. 检查是否需要停止（无改进空间）
            if "无需改进" in feedback or "no need for improvement" in feedback.lower():
                print("\n✅ 反思认为结果已无需改进，任务完成。")
                break

            # 2c. ★ 质量评分：让 LLM 对当前版本打分
            quality_score = self._evaluate_quality(input_text, last_result, **kwargs)
            print(f"\n📊 当前质量评分: {quality_score:.1f}/10")

            if quality_score >= self.quality_threshold:
                print(f"✅ 质量评分 {quality_score:.1f} ≥ 阈值 {self.quality_threshold}，停止迭代。")
                break

            # 2d. 优化
            print(f"\n→ 正在进行优化（质量评分 {quality_score:.1f} < {self.quality_threshold}）...")
            refine_prompt = self.prompts["refine"].format(
                task=input_text,
                last_attempt=last_result,
                feedback=feedback
            )
            refined_result = self._get_llm_response(refine_prompt, **kwargs)
            self.memory.add_record("execution", refined_result)
            print(f"\n📝 优化后结果:\n{refined_result}")

        final_result = self.memory.get_last_execution()
        print(f"\n─── 任务完成 ───\n最终结果:\n{final_result}")

        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_result, "assistant"))

        return final_result

    def _evaluate_quality(self, task: str, content: str, **kwargs) -> float:
        """
        对当前输出进行质量评分（0-10）

        Args:
            task: 原始任务
            content: 当前回答

        Returns:
            质量评分 (0-10)
        """
        eval_prompt = f"""
请对以下回答进行质量评分（0-10分）。
评分标准：
- 准确性（0-3分）：回答是否正确、无事实错误
- 完整性（0-3分）：是否全面覆盖了任务要求
- 清晰度（0-2分）：表达是否清晰、有条理
- 实用性（0-2分）：是否具有实际参考价值

# 原始任务:
{task}

# 回答:
{content}

请只输出一个数字（0-10之间的整数或一位小数），不要输出其他内容。
"""
        messages = [{"role": "user", "content": eval_prompt}]
        score_text = self.llm.invoke(messages, **kwargs) or "5"

        try:
            # 提取数字
            import re
            numbers = re.findall(r"\d+\.?\d*", score_text.strip())
            score = float(numbers[0]) if numbers else 5.0
            return max(0.0, min(10.0, score))
        except (ValueError, IndexError):
            return 5.0  # 默认中间分
