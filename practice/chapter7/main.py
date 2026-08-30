import os
from dotenv import load_dotenv
from llm import MyLLM

load_dotenv()

# 无需传 provider，框架会自动检测
llm = MyLLM()

# 准备输入消息
messages = [{"role": "user", "content": "你好，请介绍一下你自己。"}]

response_stream = llm.think(messages)

print("ModelScope Response:")
for chunk in response_stream:
    pass
