import os
from langchain_core.messages import HumanMessage
from graph import app as agent_app, get_initial_messages

def main():
    print("🚗 GarageAI Logic Tester (Direct Graph Interface)")
    print("-----------------------------------------------")
    
    # Init state with a fake thread ID
    thread_id = "cli-test-user"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Initialize history if empty
    state = agent_app.get_state(config)
    if not state.values:
        print("⚙️  Initializing Conversation...")
        initial_input = {"messages": get_initial_messages()}
        agent_app.invoke(initial_input, config=config)
    
    print("💬 You can start chatting. Type 'quit' to exit.")
    
    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit"]:
                break
                
            print("🤖 Agent is thinking...")
            inputs = {"messages": [HumanMessage(content=user_input)]}
            
            # Stream the events from the graph
            for event in agent_app.stream(inputs, config=config):
                for node_name, value in event.items():
                    print(f"--- Node: {node_name} ---")
                    if "messages" in value:
                        last_msg = value["messages"][-1]
                        
                        # Print Tool Calls (from Agent)
                        if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                            for tc in last_msg.tool_calls:
                                print(f"🛠️  Call: {tc['name']} ({tc['args']})")
                        
                        # Print Content (from Agent or Tool)
                        if last_msg.content:
                            prefix = "🤖 Agent" if node_name == "agent" else "🔧 Tool Output"
                            print(f"{prefix}: {last_msg.content}")
                            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
