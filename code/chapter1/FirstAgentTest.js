/**
 * 自动化旅游规划智能体 — JavaScript 实现
 *
 * 本脚本是对 FirstAgentTest.py 的 JavaScript 重写，使用完全相同的逻辑：
 *   1. ReAct 循环（Thought → Action → Observation）
 *   2. wttr.in API 查询天气
 *   3. Tavily Search API 推荐景点
 *   4. OpenAI 兼容接口调用大语言模型
 *
 * 运行方式:
 *   export TAVILY_API_KEY="tvly-..."
 *   node code/chapter1/FirstAgentTest.js
 */

// ============================================================
// 1. 系统提示词（与 Python 版本完全一致）
// ============================================================
const AGENT_SYSTEM_PROMPT = `
你是一个智能旅行助手。你的任务是分析用户的请求，并使用可用工具一步步地解决问题。

# 可用工具:
- \`get_weather(city: str)\`: 查询指定城市的实时天气。
- \`get_attraction(city: str, weather: str)\`: 根据城市和天气搜索推荐的旅游景点。

# 输出格式要求:
你的每次回复必须严格遵循以下格式，包含一对Thought和Action：

Thought: [你的思考过程和下一步计划]
Action: [你要执行的具体行动]

Action的格式必须是以下之一：
1. 调用工具：function_name(arg_name="arg_value")
2. 结束任务：Finish[最终答案]

# 重要提示:
- 每次只输出一对Thought-Action
- Action必须在同一行，不要换行
- 当收集到足够信息可以回答用户问题时，必须使用 Action: Finish[最终答案] 格式结束

请开始吧！
`;

// ============================================================
// 2. 工具函数
// ============================================================

/**
 * 通过 wttr.in API 查询指定城市的实时天气
 */
async function getWeather({ city }) {
  const url = `https://wttr.in/${encodeURIComponent(city)}?format=j1`;

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();

    const currentCondition = data.current_condition[0];
    const weatherDesc = currentCondition.weatherDesc[0].value;
    const tempC = currentCondition.temp_C;

    return `${city}当前天气：${weatherDesc}，气温${tempC}摄氏度`;
  } catch (err) {
    if (err instanceof TypeError) {
      return `错误：查询天气时遇到网络问题 - ${err.message}`;
    }
    return `错误：解析天气数据失败，可能是城市名称无效 - ${err.message}`;
  }
}

/**
 * 根据城市和天气，使用 Tavily Search API 搜索景点推荐
 */
async function getAttraction({ city, weather }) {
  const apiKey = process.env.TAVILY_API_KEY;
  if (!apiKey) {
    return "错误：未配置TAVILY_API_KEY。";
  }

  const query = `'${city}' 在'${weather}'天气下最值得去的旅游景点推荐及理由`;

  try {
    const response = await fetch("https://api.tavily.com/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        query,
        search_depth: "basic",
        include_answer: true,
      }),
    });

    if (!response.ok) {
      throw new Error(`Tavily API HTTP ${response.status}`);
    }

    const data = await response.json();

    // 如果有综合性回答，直接返回
    if (data.answer) {
      return data.answer;
    }

    // 否则格式化原始结果
    const results = data.results ?? [];
    if (results.length === 0) {
      return "抱歉，没有找到相关的旅游景点推荐。";
    }

    const formatted = results.map(
      (r) => `- ${r.title}: ${r.content}`
    );
    return "根据搜索，为您找到以下信息：\n" + formatted.join("\n");
  } catch (err) {
    return `错误：执行Tavily搜索时出现问题 - ${err.message}`;
  }
}

// 工具注册表（函数名 → 函数引用）
// 注意：key 必须与 LLM 系统提示词中的函数名一致（下划线命名）
const availableTools = {
  get_weather: getWeather,
  get_attraction: getAttraction,
};

// ============================================================
// 3. OpenAI 兼容客户端
// ============================================================
class OpenAICompatibleClient {
  constructor({ model, apiKey, baseUrl }) {
    this.model = model;
    this.apiKey = apiKey;
    this.baseUrl = baseUrl.replace(/\/+$/, ""); // 去掉末尾斜杠
  }

  /**
   * 调用 LLM API 生成回复
   */
  async generate(prompt, systemPrompt) {
    console.log("正在调用大语言模型...");
    try {
      const response = await fetch(`${this.baseUrl}/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          model: this.model,
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: prompt },
          ],
          stream: false,
        }),
      });

      if (!response.ok) {
        const errText = await response.text().catch(() => "");
        throw new Error(`HTTP ${response.status}: ${errText}`);
      }

      const data = await response.json();
      const answer = data.choices[0].message.content;
      console.log("大语言模型响应成功。");
      return answer;
    } catch (err) {
      console.error(`调用LLM API时发生错误: ${err.message}`);
      return "错误：调用语言模型服务时出错。";
    }
  }
}

// ============================================================
// 4. 主循环
// ============================================================
async function main() {
  // ---- 4.1 配置 ----
  // 请替换为你自己的 API Key 和地址
  const API_KEY = "sk-EfNU1TcffOIY4XOl47D397CfF2Fe4c49B832D48b15813eCa";
  const BASE_URL = "https://aihubmix.com/v1";
  const MODEL_ID = "coding-glm-5.2-free";

  const llm = new OpenAICompatibleClient({
    model: MODEL_ID,
    apiKey: API_KEY,
    baseUrl: BASE_URL,
  });

  // ---- 4.2 初始化 ----
  const userPrompt =
    "你好，请帮我查询一下今天北京的天气，然后根据天气推荐一个合适的旅游景点。";
  const promptHistory = [`用户请求: ${userPrompt}`];

  console.log(`用户输入: ${userPrompt}`);
  console.log("=".repeat(40));

  // ---- 4.3 ReAct 循环（最多 5 轮） ----
  for (let i = 0; i < 5; i++) {
    console.log(`--- 循环 ${i + 1} ---\n`);

    // 构建完整 prompt
    const fullPrompt = promptHistory.join("\n");

    // 调用 LLM
    let llmOutput = await llm.generate(fullPrompt, AGENT_SYSTEM_PROMPT);

    // 截断多余的 Thought-Action 对（模型可能一次输出多对）
    const match = llmOutput.match(
      /(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)/s
    );
    if (match) {
      const truncated = match[1].trim();
      if (truncated !== llmOutput.trim()) {
        llmOutput = truncated;
        console.log("已截断多余的 Thought-Action 对");
      }
    }
    console.log(`模型输出:\n${llmOutput}\n`);
    promptHistory.push(llmOutput);

    // 解析 Action
    const actionMatch = llmOutput.match(/Action: (.*)/s);
    if (!actionMatch) {
      const observation =
        "错误: 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。";
      const obsStr = `Observation: ${observation}`;
      console.log(`${obsStr}\n${"=".repeat(40)}`);
      promptHistory.push(obsStr);
      continue;
    }
    const actionStr = actionMatch[1].trim();

    // 处理 Finish
    if (actionStr.startsWith("Finish")) {
      const finishMatch = actionStr.match(/Finish\[(.*)\]/);
      const finalAnswer = finishMatch ? finishMatch[1] : "";
      console.log(`任务完成，最终答案: ${finalAnswer}`);
      break;
    }

    // 解析工具调用：function_name(arg1="val1", arg2="val2")
    const toolNameMatch = actionStr.match(/(\w+)\(/);
    const argsMatch = actionStr.match(/\(([\s\S]*)\)/);
    if (!toolNameMatch || !argsMatch) {
      const observation = `错误：无法解析 Action: ${actionStr}`;
      const obsStr = `Observation: ${observation}`;
      console.log(`${obsStr}\n${"=".repeat(40)}`);
      promptHistory.push(obsStr);
      continue;
    }

    const toolName = toolNameMatch[1];
    const argsStr = argsMatch[1];

    // 解析 key="value" 形式的参数
    const kwargs = {};
    const argRegex = /(\w+)="([^"]*)"/g;
    let argMatch;
    while ((argMatch = argRegex.exec(argsStr)) !== null) {
      kwargs[argMatch[1]] = argMatch[2];
    }

    // 执行工具（直接传入解构后的 kwargs）
    let observation;
    if (toolName in availableTools) {
      try {
        observation = await availableTools[toolName](kwargs);
      } catch (err) {
        observation = `错误：工具执行出错 - ${err.message}`;
      }
    } else {
      observation = `错误：未定义的工具 '${toolName}'`;
    }

    // 记录观察结果
    const obsStr = `Observation: ${observation}`;
    console.log(`${obsStr}\n${"=".repeat(40)}`);
    promptHistory.push(obsStr);
  }
}

main().catch(console.error);
