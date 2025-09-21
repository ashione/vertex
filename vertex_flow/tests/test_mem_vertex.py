from types import SimpleNamespace

from vertex_flow.memory.inmem_store import InnerMemory
from vertex_flow.workflow.vertex.mem_vertex import MemVertex, SummaryRule
from vertex_flow.workflow.workflow import Workflow


class DummyModel:
    def __init__(self, response: str = ""):
        self.response = response or "总结：用户希望完成年度计划。"
        self.calls = []

    def chat(self, messages, option=None, tools=None):  # pragma: no cover - simple stub
        self.calls.append({"messages": messages, "option": option})
        return SimpleNamespace(message=SimpleNamespace(content=self.response), finish_reason="stop")


def _make_workflow(vertex: MemVertex) -> Workflow:
    workflow = Workflow()
    workflow.add_vertex(vertex)
    return workflow


def test_mem_vertex_appends_history():
    memory = InnerMemory()
    vertex = MemVertex(id="mem_history", memory=memory, rules=None)
    workflow = _make_workflow(vertex)

    inputs = {
        "user_id": "user-1",
        "records": [
            {"role": "user", "content": "你好，帮我记录目标"},
            {"role": "assistant", "content": {"text": "当然，可以。"}},
        ],
    }

    output = vertex.execute(inputs=inputs, context=workflow.flow_context)

    assert output["records_written"] == 2
    history = memory.recent_history("user-1", n=2)
    assert len(history) == 2
    assert history[0]["content"]["text"] == "当然，可以。"
    assert history[1]["content"]["text"] == "你好，帮我记录目标"


def test_mem_vertex_summary_rule_and_context_storage():
    memory = InnerMemory()
    model = DummyModel("用户年度目标：完成 OKR")
    rule = SummaryRule(
        name="user_goal",
        memory_key="goal_summary",
        prompt_template="请基于以下对话提炼长期目标：\n{context}",
        match=["目标"],
    )

    vertex = MemVertex(id="mem_summary", memory=memory, model=model, rules=[rule])
    workflow = _make_workflow(vertex)

    inputs = {
        "user_id": "user-2",
        "records": [
            {"role": "user", "content": "我的目标是完成今年的 OKR 计划"},
            {"role": "assistant", "content": "收到，我会帮助你跟踪"},
        ],
    }

    output = vertex.execute(inputs=inputs, context=workflow.flow_context)

    stored = memory.ctx_get("user-2", "goal_summary")
    assert stored is not None
    assert stored["summary"] == "用户年度目标：完成 OKR"
    assert output["summaries"][0]["summary"] == "用户年度目标：完成 OKR"
    assert model.calls, "LLM 模型应被调用生成总结"
