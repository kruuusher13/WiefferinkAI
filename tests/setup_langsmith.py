#!/usr/bin/env python3
"""
LangSmith Setup and Test Script
================================
This script helps you configure LangSmith for tracing and visualization.

Usage: python tests/setup_langsmith.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_langsmith_config():
    """Check current LangSmith configuration."""
    print("="*60)
    print("LangSmith Configuration Check")
    print("="*60)

    tracing = os.getenv("LANGCHAIN_TRACING_V2")
    api_key = os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGCHAIN_PROJECT", "default")
    endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

    print(f"\n📊 Current Configuration:")
    print(f"   LANGCHAIN_TRACING_V2: {tracing or '(not set)'}")
    print(f"   LANGCHAIN_API_KEY: {'***' + api_key[-4:] if api_key else '(not set)'}")
    print(f"   LANGCHAIN_PROJECT: {project}")
    print(f"   LANGCHAIN_ENDPOINT: {endpoint}")

    if tracing == "true" and api_key:
        print("\n✅ LangSmith is fully configured!")
        print(f"   View your traces at: https://smith.langchain.com")
        return True
    else:
        print("\n⚠️  LangSmith is NOT configured or incomplete.")
        return False


def show_setup_instructions():
    """Display setup instructions."""
    print("\n" + "="*60)
    print("Setup Instructions")
    print("="*60)

    print("""
To enable LangSmith tracing:

1. Create a LangSmith account at https://smith.langchain.com

2. Get your API key from Settings > API Keys

3. Set environment variables:

   # Option A: Export in terminal
   export LANGCHAIN_TRACING_V2=true
   export LANGCHAIN_API_KEY=your_api_key_here
   export LANGCHAIN_PROJECT=GarageAI

   # Option B: Add to .env file
   echo 'LANGCHAIN_TRACING_V2=true' >> .env
   echo 'LANGCHAIN_API_KEY=your_api_key_here' >> .env
   echo 'LANGCHAIN_PROJECT=GarageAI' >> .env

4. Run your application - traces will appear automatically!

What you'll see in LangSmith:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Agent execution flow
• Tool calls (inputs and outputs)
• LLM calls (prompts and responses)
• Token usage and costs
• Latency breakdown
• Error traces
""")


def run_traced_test():
    """Run a test with LangSmith tracing enabled."""
    print("\n" + "="*60)
    print("Running Traced Test")
    print("="*60)

    if not os.getenv("LANGCHAIN_API_KEY"):
        print("\n❌ LANGCHAIN_API_KEY not set. Cannot run traced test.")
        print("   Please set it first (see instructions above).")
        return False

    if not os.getenv("GOOGLE_API_KEY"):
        print("\n❌ GOOGLE_API_KEY not set. Cannot run agent test.")
        return False

    # Enable tracing if not already
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = "GarageAI"

    try:
        from app.graph import app, get_initial_messages
        from langchain_core.messages import HumanMessage

        print("\n🔄 Running traced agent conversation...")

        test_messages = [
            "Hallo, ik ben Jan de Vries",
            "Wat is de status van mijn auto met kenteken XX-99-XX?",
            "Hebben jullie remblokken op voorraad?",
        ]

        config = {"configurable": {"thread_id": "langsmith-test"}}

        # Initialize with system prompt
        inputs = {"messages": get_initial_messages()}

        for msg in test_messages:
            print(f"\n👤 User: {msg}")

            inputs["messages"].append(HumanMessage(content=msg))
            result = app.invoke(inputs, config=config)

            # Get the response
            response = result['messages'][-1].content
            if isinstance(response, list):
                response = ' '.join(
                    p.get('text', str(p)) if isinstance(p, dict) else str(p)
                    for p in response
                )

            print(f"🤖 Harry: {response[:200]}{'...' if len(response) > 200 else ''}")

            # Update inputs for next turn
            inputs = {"messages": result['messages']}

        print("\n" + "="*60)
        print("✅ Traced test complete!")
        print("="*60)
        print(f"\n📊 View your traces at:")
        print(f"   https://smith.langchain.com/projects/{os.getenv('LANGCHAIN_PROJECT', 'default')}")

        return True

    except Exception as e:
        print(f"\n❌ Error running traced test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    print("\n" + "🔬"*30)
    print("  LANGSMITH SETUP UTILITY")
    print("🔬"*30)

    # Check current configuration
    is_configured = check_langsmith_config()

    if not is_configured:
        show_setup_instructions()
        return

    # Ask if user wants to run a traced test
    print("\nWould you like to run a traced test? (y/n): ", end="")
    try:
        response = input().strip().lower()
        if response == 'y':
            run_traced_test()
    except EOFError:
        # Non-interactive mode
        print("Running traced test automatically...")
        run_traced_test()


if __name__ == "__main__":
    main()
