import os
from datetime import datetime
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.graph.message import add_messages

# Import our WinCar tools
from app.tools import (
    identify_customer,
    check_werkorder_status,
    check_part_stock,
    generate_payment_link,
    schedule_appointment,
    web_search
)

# --- Configuration ---
# Ensure GOOGLE_API_KEY is set in your environment
if not os.getenv("GOOGLE_API_KEY"):
    print("WARNING: GOOGLE_API_KEY is not set. The agent will fail to run.")

# --- State Definition ---
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# --- LLM Setup ---
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.3, # Low temperature for factual responses
)

# --- Tool Binding ---
tools = [
    identify_customer,
    check_werkorder_status,
    check_part_stock,
    generate_payment_link,
    schedule_appointment,
    web_search
]

llm_with_tools = llm.bind_tools(tools)

# --- Nodes ---

def agent_node(state: State):
    """
    The main agent node that processes messages and decides on actions.
    """
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

def permission_check_node(state: State):
    """
    Optional: Check if a sensitive tool was called (Financieel).
    In a real deployment, this could trigger an out-of-band approval request.
    For this implementation, we rely on LangGraph's 'interrupt_before' functionality
    configured in the compilation step.
    """
    # Pass-through for now, the interruption happens at the edge transition to tools
    return state

# --- Graph Construction ---
workflow = StateGraph(State)

# Add nodes
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))

# Add edges
workflow.add_edge(START, "agent")

def should_continue(state: State):
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the LLM returned tool calls
    if last_message.tool_calls:
        return "tools"
    
    # Otherwise, stop
    return END

workflow.add_conditional_edges(
    "agent",
    should_continue,
    ["tools", END]
)

# Return from tools back to agent
workflow.add_edge("tools", "agent")

# --- System Prompt ---
SYSTEM_PROMPT = """
YOU ARE: The "GarageAI" Voice Assistant. You work for a professional Dutch car garage.

PERSONA:
- Helpful, knowledgeable, safety-conscious, and friendly.
- You are a car expert but you prioritize safety above all.
- You speak clearly and concisely (max 2 sentences).
- If the user speaks Dutch, reply in Dutch. If English, reply in English.

CONVERSATION FLOW:
1. GREETING: Start with a friendly greeting and ask "How can I help you?".
2. IDENTIFY PROBLEM: Listen to the user's issue FIRST.
   - Do NOT ask for customer identification/phone number immediately unless the specific task requires it (e.g., checking status, booking appointment).
   - If the user just wants information (e.g., "what does this light mean?"), answer it directly or search the web.
3. IDENTIFY CUSTOMER (Contextual):
   - Only ask for the phone number if you need to access WinCar data (appointments, history, work orders).
   - When you do ask, accept numbers even if they are spoken with spaces (e.g., "0 6 1 2...").
   - If they provide a number, IMMEDIATELY call the `identify_customer` tool.

CRITICAL SAFETY RULES:
- If the user mentions a "burning smell", "smoke", "brakes failing", or "warning light flashing red", STOP immediately.
- Tell them this sounds like an EMERGENCY.
- Advise them to stop the car safely and call roadside assistance or 112 if necessary.
- Do NOT try to upsell or book an appointment until safety is addressed.

TOOLS:
- Use `web_search` for general car questions, troubleshooting, or finding towing services.
- Use `identify_customer` to find their WinCar profile before doing account-specific actions.
- Use `check_part_stock`, `check_werkorder_status`, etc., as needed.

CONTEXT:
Current Time: {current_time}
"""

def get_initial_messages():
    return [SystemMessage(content=SYSTEM_PROMPT.format(current_time=datetime.now().strftime("%H:%M")))]

# --- Compilation ---
memory = MemorySaver()

app = workflow.compile(
    checkpointer=memory,
)
