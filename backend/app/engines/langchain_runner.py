from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.callbacks import BaseCallbackHandler
from app.tools.art_tools import domain_tools

class TraceCaptureCallback(BaseCallbackHandler):
    def __init__(self):
        self.trace: List[Dict[str, Any]] = []

    def on_agent_action(self, action, **kwargs):
        self.trace.append({
            "stage": "THOUGHT_ACTION",
            "tool": action.tool,
            "tool_input": action.tool_input,
            "log": action.log.strip() if hasattr(action, 'log') else f"Executing {action.tool}"
        })

    def on_tool_end(self, output, **kwargs):
        self.trace.append({
            "stage": "OBSERVATION",
            "output": str(output)
        })

def execute_langchain_agent(query: str) -> Dict[str, Any]:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an AI Master Painter & Art Director. For ANY user request, you MUST invoke all three tools in order: "
                   "1. generate_color_palette (to identify the art movement and select 5 harmonic hex codes) "
                   "2. calculate_grid_anchors (for compositional balance) "
                   "3. generate_canvas_painting (to generate the actual high-resolution artwork)."),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm, domain_tools, prompt)
    cb = TraceCaptureCallback()
    executor = AgentExecutor(agent=agent, tools=domain_tools, callbacks=[cb], verbose=True)

    result = executor.invoke({"input": query})

    return {
        "final_output": result.get("output", "Execution completed"),
        "trace": cb.trace,
        "execution_type": "LangChain ReAct AgentExecutor"
    }