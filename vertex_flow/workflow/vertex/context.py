from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic, Deque
from collections import deque
from dataclasses import dataclass, field
import time

T = TypeVar("T")

@dataclass
class StreamData:
    """流式数据包装器"""
    data: Any
    vertex_id: str
    timestamp: float = field(default_factory=lambda: time.time())
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

class StreamContext:
    """流式上下文，用于管理流式数据流"""
    def __init__(self):
        self.stream_buffers: Dict[str, Deque[StreamData]] = {}
        self.stream_callbacks: Dict[str, List[Callable[[StreamData], None]]] = {}
        self.final_outputs: Dict[str, Any] = {}
        self.is_streaming: bool = False

    def register_stream_callback(self, vertex_id: str, callback: Callable[[StreamData], None]):
        if vertex_id not in self.stream_callbacks:
            self.stream_callbacks[vertex_id] = []
        self.stream_callbacks[vertex_id].append(callback)

    def emit_stream_data(self, vertex_id: str, data: Any, is_final: bool = False, metadata: Optional[Dict[str, Any]] = None):
        stream_data = StreamData(
            data=data,
            vertex_id=vertex_id,
            is_final=is_final,
            metadata=metadata or {}
        )
        if vertex_id not in self.stream_buffers:
            self.stream_buffers[vertex_id] = deque(maxlen=1000)
        self.stream_buffers[vertex_id].append(stream_data)
        if vertex_id in self.stream_callbacks:
            for callback in self.stream_callbacks[vertex_id]:
                try:
                    callback(stream_data)
                except Exception as e:
                    print(f"Stream callback error for {vertex_id}: {e}")
        if is_final:
            self.final_outputs[vertex_id] = data

    def get_stream_buffer(self, vertex_id: str) -> Deque[StreamData]:
        return self.stream_buffers.get(vertex_id, deque())

    def get_final_output(self, vertex_id: str) -> Any:
        return self.final_outputs.get(vertex_id)

class WorkflowContext(Generic[T]):
    """工作流上下文，管理全局状态和输出"""
    def __init__(self):
        self.outputs: Dict[str, Any] = {}
        self.state: Dict[str, Any] = {}

    def set_output(self, vertex_id: str, output: Any):
        self.outputs[vertex_id] = output

    def get_output(self, vertex_id: str) -> Any:
        return self.outputs.get(vertex_id)

    def set_state(self, key: str, value: Any):
        self.state[key] = value

    def get_state(self, key: str) -> Any:
        return self.state.get(key)

class SubgraphContext(Generic[T]):
    """子图上下文，管理子图内部变量、输出和流式上下文"""
    def __init__(self, parent_context: Optional[WorkflowContext[T]] = None):
        self.parent_context = parent_context
        self.internal_outputs: Dict[str, Any] = {}
        self.exposed_variables: Dict[str, Any] = {}
        self.stream_context = StreamContext()

    def store_internal_output(self, vertex_id: str, output_data: Any):
        self.internal_outputs[vertex_id] = output_data

    def get_internal_output(self, vertex_id: str) -> Optional[Any]:
        return self.internal_outputs.get(vertex_id)

    def expose_variable(self, internal_vertex_id: str, variable_name: Optional[str], exposed_name: Optional[str] = None):
        exposed_name = exposed_name or variable_name
        if exposed_name is None:
            return
        if internal_vertex_id in self.internal_outputs:
            output = self.internal_outputs[internal_vertex_id]
            if isinstance(output, dict) and variable_name and variable_name in output:
                self.exposed_variables[exposed_name] = output[variable_name]
            elif variable_name is None:
                self.exposed_variables[exposed_name] = output

    def get_exposed_variables(self) -> Dict[str, Any]:
        return self.exposed_variables.copy() 