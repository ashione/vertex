from types import SimpleNamespace

from vertex_flow.memory.inmem_store import InnerMemory
from vertex_flow.workflow.constants import CONVERSATION_HISTORY, MODEL, SYSTEM, USER
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.vertex.mem_vertex import MemVertex
from vertex_flow.workflow.vertex.memory_reader_vertex import MemoryReaderVertex


class DummyModel:
    def __init__(self, response: str = "助手回复"):
        self.response = response
        self.calls = []

    def chat(self, messages, option=None, tools=None):  # pragma: no cover - simple stub
        self.calls.append(messages)
        return SimpleNamespace(message=SimpleNamespace(content=self.response), finish_reason="stop")


def test_memory_reader_vertex_outputs_conversation_and_context():
    memory = InnerMemory()
    user_id = "user-1"

    memory.append_history(user_id, "user", "text", {"text": "请帮我记录 OKR"})
    memory.append_history(user_id, "assistant", "text", {"text": "好的，我记住了"})
    memory.ctx_set(user_id, "goal_summary", {"summary": "完成 OKR"})

    vertex = MemoryReaderVertex(
        id="memory_reader",
        memory=memory,
        ctx_keys=["goal_summary"],
        history_len=5,
    )

    output = vertex.execute(inputs={"user_id": user_id}, context=WorkflowContext())

    assert output["user_id"] == user_id
    assert len(output["history_records"]) == 2
    messages = output[CONVERSATION_HISTORY]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"  # chronological order
    assert "OKR" in messages[0]["content"]
    assert output["context_values"]["goal_summary"]["summary"] == "完成 OKR"


def test_memory_read_write_cycle_with_llm_vertex():
    memory = InnerMemory()
    user_id = "user-2"

    # Existing context
    memory.append_history(user_id, "assistant", "text", {"text": "欢迎回来"})
    memory.ctx_set(user_id, "profile", {"name": "Alice"})

    reader = MemoryReaderVertex(
        id="memory_reader",
        memory=memory,
        ctx_keys=["profile"],
        history_len=10,
    )

    reader_output = reader.execute(inputs={"user_id": user_id}, context=WorkflowContext())
    conversation_history = reader_output[CONVERSATION_HISTORY]

    model = DummyModel("好的，我们继续")
    llm_vertex = LLMVertex(
        id="llm",
        params={MODEL: model, SYSTEM: "你是助理", USER: []},
    )

    llm_output = llm_vertex.chat(
        inputs={CONVERSATION_HISTORY: conversation_history, "current_message": "你好"},
        context=WorkflowContext(),
    )

    writer = MemVertex(id="memory_writer", memory=memory)
    writer.execute(
        inputs={
            "user_id": user_id,
            "records": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": llm_output},
            ],
        },
        context=WorkflowContext(),
    )

    updated_history = memory.recent_history(user_id, n=3)
    assert updated_history[0]["content"]["text"] == "好的，我们继续"
    assert updated_history[1]["content"]["text"] == "你好"
