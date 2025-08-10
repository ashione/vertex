"""Example usage of Vertexflow Memory module."""

import time

from vertex_flow.memory import FileMemory, InnerMemory


def demo_inmemory():
    """Demonstrate InnerMemory usage."""
    print("=== InnerMemory Demo ===")

    # Initialize memory
    memory = InnerMemory(hist_maxlen=10)
    user_id = "demo_user"

    # 1. Deduplication demo
    print("\n1. Deduplication:")
    key = "message_123"
    print(f"First seen '{key}': {memory.seen(user_id, key)}")
    print(f"Second seen '{key}': {memory.seen(user_id, key)}")

    # 2. History demo
    print("\n2. History:")
    for i in range(5):
        memory.append_history(user_id, "user", "text", {"text": f"Hello message {i}", "id": i})

    history = memory.recent_history(user_id, n=3)
    print(f"Recent 3 messages: {len(history)} items")
    for msg in history:
        print(f"  - {msg['content']['text']}")

    # 3. Context demo
    print("\n3. Context storage:")
    memory.ctx_set(user_id, "user_preference", {"theme": "dark", "lang": "en"})
    memory.ctx_set(user_id, "session_data", {"login_time": time.time()}, ttl_sec=3600)

    pref = memory.ctx_get(user_id, "user_preference")
    session = memory.ctx_get(user_id, "session_data")
    print(f"User preference: {pref}")
    print(f"Session data: {session}")

    # 4. Ephemeral demo
    print("\n4. Ephemeral storage:")
    memory.set_ephemeral(user_id, "temp_token", "abc123", ttl_sec=2)
    print(f"Temp token: {memory.get_ephemeral(user_id, 'temp_token')}")

    print("Waiting 2.5 seconds for expiration...")
    time.sleep(2.5)
    print(f"Temp token after expiration: {memory.get_ephemeral(user_id, 'temp_token')}")

    # 5. Rate limiting demo
    print("\n5. Rate limiting:")
    for i in range(5):
        count = memory.incr_rate(user_id, "api_calls", ttl_sec=60)
        print(f"API call #{count}")


def demo_file_memory():
    """Demonstrate FileMemory usage."""
    print("\n\n=== FileMemory Demo ===")

    # Initialize file-based memory
    memory = FileMemory(storage_dir="./demo_memory", hist_maxlen=10)
    user_id = "file_demo_user"

    # Store some data
    print("\n1. Storing data to files:")
    memory.ctx_set(user_id, "config", {"version": "1.0", "features": ["a", "b"]})
    memory.append_history(user_id, "user", "text", {"text": "Persistent message"})

    # Retrieve data
    config = memory.ctx_get(user_id, "config")
    history = memory.recent_history(user_id, n=1)

    print(f"Retrieved config: {config}")
    print(f"Retrieved history: {history[0]['content']['text'] if history else 'None'}")

    print("\nData is now persisted to files in ./demo_memory/")


def demo_multiple_users():
    """Demonstrate multi-user isolation."""
    print("\n\n=== Multi-user Demo ===")

    memory = InnerMemory()

    # Different users with same keys
    users = ["alice", "bob", "charlie"]

    for user in users:
        memory.ctx_set(user, "name", user.title())
        memory.ctx_set(user, "score", len(user) * 10)
        memory.append_history(user, "user", "text", {"text": f"Hello from {user}"})

    print("\nUser data isolation:")
    for user in users:
        name = memory.ctx_get(user, "name")
        score = memory.ctx_get(user, "score")
        history = memory.recent_history(user, n=1)
        msg = history[0]["content"]["text"] if history else "No messages"

        print(f"  {user}: name={name}, score={score}, last_msg='{msg}'")


if __name__ == "__main__":
    # Run all demos
    demo_inmemory()
    demo_file_memory()
    demo_multiple_users()

    print("\n=== Demo completed ===")
