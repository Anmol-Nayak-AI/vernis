from typing import Annotated, Sequence, TypedDict, Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from app.tools.art_tools import domain_tools

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

SYSTEM_PROMPT = (
    "You are an AI Master Painter & Art Director. For ANY canvas request, you MUST execute all 3 tools: "
    "1) generate_color_palette 2) calculate_grid_anchors 3) generate_canvas_painting."
)

def execute_langgraph_agent(query: str) -> Dict[str, Any]:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    llm_with_tools = llm.bind_tools(domain_tools)

    def chatbot_node(state: AgentState):
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(tools=domain_tools)

    def route_decision(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", chatbot_node)
    workflow.add_node("tools", tool_node)

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", route_decision, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    compiled_graph = workflow.compile()

    state_transitions: List[Dict[str, Any]] = []
    initial_input = {
        "messages": [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=query)
        ]
    }

    for step in compiled_graph.stream(initial_input, stream_mode="updates"):
        for node_id, node_update in step.items():
            serialized_messages = []
            for m in node_update.get("messages", []):
                msg_dict: Dict[str, Any] = {
                    "type": getattr(m, "type", "message"),
                    "content": str(m.content)
                }
                if hasattr(m, "tool_calls") and m.tool_calls:
                    msg_dict["tool_calls"] = m.tool_calls
                serialized_messages.append(msg_dict)

            state_transitions.append({
                "node_executed": node_id,
                "state_emitted": serialized_messages
            })

    final_result = compiled_graph.invoke(initial_input)["messages"][-1].content
    return {
        "final_output": str(final_result),
        "graph_steps": state_transitions,
        "execution_type": "LangGraph StateGraph + ToolNode"
    }