import anthropic
import os 
from dotenv import load_dotenv
load_dotenv()
client = anthropic.Anthropic(
    api_key=os.getenv("ZHIPUAI_API_KEY"),
    base_url=os.getenv("ZHIPUAI_API_BASE_URL")
)
MODEL="glm-4.5-flash"
tools=[
    {
        "name": "calculate",
        "description": "calculate the result of a mathematical expression",
        "input_schema":{
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to calculate"
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "get_weather",
        "description": "search for weather information on the internet in input city",
        "input_schema":{
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city for which to search weather information"
                }
            },
            "required": ["city"]
        }
    }
]
def calculate (expression):
    return str(eval(expression))

def get_weather (city):
    return f"{city}: sunny,25°C"

def execute_tool (name,tool_input): 
    if name == "calculate":
        return calculate(tool_input["expression"])
    elif name == "get_weather":
        return get_weather(tool_input["city"])
    else:
        return "未知工具"

def chat(user_message):
    messages =[{"role":"user","content": user_message}]
    while True:
        response = client.messages.create(
            model = MODEL,
            messages = messages,
            tools = tools,
            max_tokens = 1024
        )
        print(response)
        if response.stop_reason == "end_turn":
            print(response.content[0].text)
            return
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                ]})
if __name__ == "__main__":
    chat(input("""请输入消息: """))
