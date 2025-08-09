#!/usr/bin/env python3
"""
MCP Smart Strategy Example

This example demonstrates the default "smart" strategy for MCP context updates.
The smart strategy only updates MCP context when it actually changes,
providing optimal performance while maintaining functionality.
"""

from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.vertex.mcp_llm_vertex import create_mcp_llm_vertex


def demonstrate_smart_strategy():
    """Demonstrate the default smart strategy"""

    print("=== MCP Smart Strategy Demo ===\n")

    # Create vertex with default smart strategy
    vertex = create_mcp_llm_vertex(
        "smart_vertex", model_name="gpt-3.5-turbo", temperature=0.7  # Replace with your model
    )

    print(f"Created vertex with strategy: {vertex.get_mcp_context_update_strategy()}")
    print("Smart strategy: Only update MCP context when it changes\n")

    # Test multiple messages to see smart behavior
    test_messages = [
        "Hello, what can you do?",
        "Tell me about available tools",
        "What resources do you have access to?",
        "Can you help me with a task?",
    ]

    for i, message in enumerate(test_messages, 1):
        print(f"--- Message {i}: {message} ---")

        # Create workflow context
        context = WorkflowContext()

        # Process message
        inputs = {"message": message}
        vertex.messages_redirect(inputs, context)

        # Check if MCP context was added
        system_messages = [msg for msg in vertex.messages if msg.get("role") == "system"]
        if system_messages:
            content = system_messages[0]["content"]
            if "MCP Context:" in content:
                print("✓ MCP context found in system message")
                # Count lines in MCP context
                mcp_start = content.find("MCP Context:")
                if mcp_start != -1:
                    mcp_content = content[mcp_start:]
                    line_count = mcp_content.count("\n")
                    print(f"   MCP context has {line_count} lines")
            else:
                print("✗ No MCP context in system message")
        else:
            print("✗ No system message found")

        # Show MCP status
        status = vertex.get_mcp_status()
        print(f"   MCP available: {status['available']}")
        print(f"   Context strategy: {status['context_update_strategy']}")
        print()

    print("=== Smart Strategy Benefits ===")
    print("1. Performance: Only updates when MCP context changes")
    print("2. Efficiency: Reduces token usage by avoiding redundant context")
    print("3. Functionality: Maintains all MCP capabilities")
    print("4. Cache: Uses 5-minute TTL for MCP resource caching")

    print("\n=== Usage Tips ===")
    print("- Smart strategy is the default and recommended")
    print("- Use vertex.set_mcp_context_update_strategy('never') for tools-only mode")
    print("- Use vertex.set_mcp_context_update_strategy('always') for dynamic environments")
    print("- Adjust cache TTL with vertex.set_mcp_cache_ttl(seconds)")


def show_strategy_comparison():
    """Show comparison of different strategies"""

    print("\n=== Strategy Comparison ===")

    strategies = {
        "smart": {
            "description": "Default strategy - update only when context changes",
            "performance": "Optimal",
            "token_usage": "Minimal",
            "use_case": "Most scenarios",
        },
        "never": {
            "description": "Never add MCP context to messages",
            "performance": "Best",
            "token_usage": "Lowest",
            "use_case": "Tools-only usage",
        },
        "always": {
            "description": "Always update MCP context in every message",
            "performance": "Good",
            "token_usage": "Higher",
            "use_case": "Dynamic MCP environments",
        },
    }

    for strategy, info in strategies.items():
        print(f"\n[{strategy.upper()}]")
        print(f"  Description: {info['description']}")
        print(f"  Performance: {info['performance']}")
        print(f"  Token Usage: {info['token_usage']}")
        print(f"  Use Case: {info['use_case']}")


if __name__ == "__main__":
    try:
        demonstrate_smart_strategy()
        show_strategy_comparison()
    except Exception as e:
        print(f"Demo failed: {e}")
        print("Make sure MCP is properly configured and available")
