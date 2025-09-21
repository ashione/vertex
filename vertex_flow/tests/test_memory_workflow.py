from types import SimpleNamespace

from vertex_flow.memory.inmem_store import InnerMemory
from vertex_flow.workflow.constants import (
    CONVERSATION_HISTORY,
    LOCAL_VAR,
    MODEL,
    SOURCE_SCOPE,
    SOURCE_VAR,
    SYSTEM,
    USER,
)
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.vertex.mem_vertex import MemVertex, SummaryRule
from vertex_flow.workflow.vertex.memory_reader_vertex import MemoryReaderVertex
from vertex_flow.workflow.vertex.vertex import SinkVertex, SourceVertex
from vertex_flow.workflow.workflow import Workflow


class DummyChatModel:
    def __init__(self, responses=None):
        self.responses = list(responses or ["好的，我们会继续跟进。"])
        self.calls = []

    def chat(self, messages, option=None, tools=None):  # pragma: no cover - deterministic stub
        self.calls.append(messages)
        content = self.responses.pop(0) if self.responses else "好的，我们会继续跟进。"
        return SimpleNamespace(message=SimpleNamespace(content=content), finish_reason="stop")


def test_workflow_memory_read_and_write_cycle():
    memory = InnerMemory()
    user_id = "workflow-user"

    # Seed existing memory so reader has context to pull.
    memory.append_history(user_id, "user", "text", {"text": "之前的问题"})
    memory.append_history(user_id, "assistant", "text", {"text": "之前的回答"})
    memory.ctx_set(user_id, "goal_summary", {"summary": "之前的OKR目标"})

    workflow = Workflow()

    source = SourceVertex(id="source", task=lambda inputs, context=None: inputs)

    reader = MemoryReaderVertex(
        id="memory_reader",
        memory=memory,
        ctx_keys=["goal_summary"],
        history_len=5,
    )
    reader.add_variables([{SOURCE_SCOPE: "source", SOURCE_VAR: "user_id", LOCAL_VAR: "user_id"}])

    chat_model = DummyChatModel(["收到，我们已记录最新计划"])
    llm_vertex = LLMVertex(
        id="llm",
        params={MODEL: chat_model, SYSTEM: "你是一个助理", USER: []},
    )
    llm_vertex.add_variables(
        [
            {SOURCE_SCOPE: "memory_reader", SOURCE_VAR: CONVERSATION_HISTORY, LOCAL_VAR: CONVERSATION_HISTORY},
            {SOURCE_SCOPE: "source", SOURCE_VAR: "current_message", LOCAL_VAR: "current_message"},
        ]
    )

    summary_model = DummyChatModel(["总结：用户计划制定新的OKR。"])
    summary_rule = SummaryRule(
        name="goal_summary",
        memory_key="goal_summary",
        prompt_template="请总结关键信息：\n{context}",
    )
    mem_vertex = MemVertex(
        id="memory_writer",
        memory=memory,
        model=summary_model,
        rules=[summary_rule],
    )
    mem_vertex.add_variables(
        [
            {SOURCE_SCOPE: "source", SOURCE_VAR: "user_id", LOCAL_VAR: "user_id"},
            {SOURCE_SCOPE: "source", SOURCE_VAR: "current_message", LOCAL_VAR: "latest_user_message"},
            {SOURCE_SCOPE: "llm", SOURCE_VAR: None, LOCAL_VAR: "latest_assistant_message"},
        ]
    )

    sink = SinkVertex(id="sink", task=lambda inputs, context: inputs.get("memory_writer"))

    for vertex in (source, reader, llm_vertex, mem_vertex, sink):
        workflow.add_vertex(vertex)

    source | reader
    source | llm_vertex
    reader | llm_vertex
    source | mem_vertex
    llm_vertex | mem_vertex
    mem_vertex | sink

    workflow.execute_workflow({"user_id": user_id, "current_message": "我想更新OKR进度"}, stream=False)

    # Validate LLM consumed memory-provided history
    assert chat_model.calls, "主对话模型应被调用"
    history_messages = chat_model.calls[0]
    assert any("之前的问题" in (msg.get("content") or "") for msg in history_messages)

    # Validate memory writer recorded both sides of the exchange
    recent = memory.recent_history(user_id, n=3)
    assert recent[0]["content"]["text"] == "收到，我们已记录最新计划"
    assert recent[1]["content"]["text"] == "我想更新OKR进度"

    # Summary should be refreshed by MemVertex rule
    summary = memory.ctx_get(user_id, "goal_summary")
    assert summary["summary"].startswith("总结：")

    # Sink receives mem vertex output for further chaining if needed
    sink_output = workflow.context.get_output("sink")
    assert sink_output["user_id"] == user_id
    assert sink_output["records_written"] == 2
