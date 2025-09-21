"""Demonstration of wiring MemoryReaderVertex, LLMVertex, and MemVertex in a workflow."""

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


class DemoChatModel:
    """Minimal chat model stub for demo purposes."""

    def __init__(self, responses=None):
        self.responses = list(responses or ["收到，我们会持续跟进。"])

    def chat(self, messages, option=None, tools=None):  # pragma: no cover - simple stub for demo
        content = self.responses.pop(0) if self.responses else "收到，我们会持续跟进。"
        return SimpleNamespace(message=SimpleNamespace(content=content), finish_reason="stop")


def build_memory_enabled_workflow(memory: InnerMemory) -> Workflow:
    workflow = Workflow()

    source = SourceVertex(id="source", task=lambda inputs, context=None: inputs)

    reader = MemoryReaderVertex(
        id="memory_reader",
        memory=memory,
        ctx_keys=["goal_summary"],
        history_len=10,
    )
    reader.add_variables([{SOURCE_SCOPE: "source", SOURCE_VAR: "user_id", LOCAL_VAR: "user_id"}])

    conversation_model = DemoChatModel(["了解，我们已经更新OKR计划。"])
    llm_vertex = LLMVertex(id="llm", params={MODEL: conversation_model, SYSTEM: "你是一个助理", USER: []})
    llm_vertex.add_variables(
        [
            {SOURCE_SCOPE: "memory_reader", SOURCE_VAR: CONVERSATION_HISTORY, LOCAL_VAR: CONVERSATION_HISTORY},
            {SOURCE_SCOPE: "source", SOURCE_VAR: "current_message", LOCAL_VAR: "current_message"},
        ]
    )

    summary_model = DemoChatModel(["总结：用户正在跟进OKR目标。"])
    mem_vertex = MemVertex(
        id="memory_writer",
        memory=memory,
        model=summary_model,
        rules=[
            SummaryRule(
                name="goal_summary",
                memory_key="goal_summary",
                prompt_template="请总结对话要点：\n{context}",
            )
        ],
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

    return workflow


def main():  # pragma: no cover - manual demo
    memory = InnerMemory()
    user_id = "demo-user"

    memory.append_history(user_id, "user", "text", {"text": "之前的对话"})
    memory.append_history(user_id, "assistant", "text", {"text": "已经记录"})
    memory.ctx_set(user_id, "goal_summary", {"summary": "之前的总结"})

    workflow = build_memory_enabled_workflow(memory)
    workflow.execute_workflow({"user_id": user_id, "current_message": "我们需要更新OKR"}, stream=False)

    recent = memory.recent_history(user_id, n=2)
    updated_summary = memory.ctx_get(user_id, "goal_summary")

    print("Latest history entries:")
    for entry in recent:
        print(f"- {entry['role']}: {entry['content']['text']}")

    print("\nSummary:")
    print(updated_summary["summary"])


if __name__ == "__main__":
    main()
