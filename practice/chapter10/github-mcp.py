from hello_agents.tools import MCPTool

github_tool = MCPTool(
    server_command=["npx", '-y', '@modelcontextprotocol/server-github']
)

print("📋 可用工具：")
result = github_tool.run({"action": "list_tools"})
print(result)

print("\n🔍 搜索仓库：")
result = github_tool.run({
    "action": "call_tool",
    "tool_name": "search_repositories",
    "arguments": {
        "query": "AI agents language:python",
        "page": 1,
        "perPage": 3
    }
})

print(result)