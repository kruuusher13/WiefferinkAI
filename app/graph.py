import os
from datetime import datetime
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.graph.message import add_messages

# Import our WinCar + RDW tools
from app.tools import (
    # WinCar tools
    identify_customer,
    check_werkorder_status,
    check_part_stock,
    generate_payment_link,
    schedule_appointment,
    # RDW tools (Dutch vehicle authority)
    lookup_vehicle_rdw,
    check_apk_status,
    get_vehicle_recalls,
    # General tools
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
    # RDW tools (use these first when customer provides kenteken)
    lookup_vehicle_rdw,
    check_apk_status,
    get_vehicle_recalls,
    # WinCar tools
    identify_customer,
    check_werkorder_status,
    check_part_stock,
    generate_payment_link,
    schedule_appointment,
    # General tools
    web_search,
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
- You speak clearly and concisely (max 2 sentences per response).
- If the user speaks Dutch, reply in Dutch. If English, reply in English.

CONVERSATION FLOW:
1. GREETING: Start with a friendly greeting and ask "How can I help you?".
2. IDENTIFY PROBLEM: Listen to the user's issue FIRST.
   - Do NOT ask for customer identification immediately unless needed.
   - If the user just wants information, answer it directly.
3. KENTEKEN (LICENSE PLATE) - YOUR SUPERPOWER:
   - When a customer mentions their kenteken (license plate), IMMEDIATELY use `lookup_vehicle_rdw`.
   - This gives you instant knowledge about their car: make, model, year, APK status.
   - After looking up, personalize: "Ik zie dat u een [merk] [model] heeft..."
   - PROACTIVELY check APK: If APK expires within 60 days, mention it and offer to schedule.
   - Also check for recalls with `get_vehicle_recalls` if discussing safety or service.
4. IDENTIFY CUSTOMER (Contextual):
   - Ask for phone number only if you need WinCar data (appointments, history, work orders).
   - If they provide kenteken first, use that for vehicle info before asking for phone.

APK INTELLIGENCE:
- If APK is expired: URGENT - tell them they cannot legally drive, offer immediate appointment.
- If APK expires in <30 days: Strongly recommend scheduling now.
- If APK expires in 30-60 days: Mention it as a helpful reminder, offer to schedule.
- If APK is fine (>60 days): No need to mention unless they ask.

CRITICAL SAFETY RULES:
- If the user mentions "burning smell", "smoke", "brakes failing", or "red warning light", STOP.
- Tell them this sounds like an EMERGENCY.
- Advise: stop the car safely, call roadside assistance or 112 if necessary.
- Do NOT upsell until safety is addressed.

TOOLS:
- `lookup_vehicle_rdw`: Get vehicle info from kenteken (make, model, APK date). USE THIS FIRST when they give kenteken.
- `check_apk_status`: Detailed APK status check with urgency levels.
- `get_vehicle_recalls`: Check for manufacturer recalls (terugroepacties).
- `identify_customer`: Find customer in garage system by phone number.
- `check_werkorder_status`: Check status of ongoing work.
- `check_part_stock`: Check parts availability and price.
- `schedule_appointment`: Book a new appointment.
- `web_search`: For general car questions not in our system.

EXAMPLE FLOW:
Customer: "Ik wil een afspraak maken, mijn kenteken is AB-123-CD"
You: [Call lookup_vehicle_rdw with AB-123-CD]
You: "Ik zie dat u een Volkswagen Golf uit 2019 rijdt. Uw APK verloopt over 3 weken.
      Zal ik direct een APK-afspraak voor u inplannen?"

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
