from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.edge import (
    Edge,
)

from vertex_flow.workflow.vertex import (
    FunctionVertex,
    SinkVertex,
    IfElseVertex,
    Vertex,
    SourceVertex,
    LLMVertex,
)
from typing import (
    Generic,
    TypeVar,
    Dict,
    Any,
    Set,
    List,
)
from collections import deque
from vertex_flow.workflow.utils import timer_decorator
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from threading import Lock, Event
from vertex_flow.workflow.event_channel import EventChannel

logging = LoggerUtil.get_logger()

T = TypeVar("T")  # 泛型类型变量


class WorkflowContext(Generic[T]):
    """工作流上下文，用于存储环境参数和输出数据"""

    def __init__(
        self,
        env_parameters: Dict[str, Any] = None,
        user_parameters: Dict[str, Any] = None,
    ):
        self.env_parameters = env_parameters or {}
        self.user_parameters = user_parameters or {}
        self.outputs = {}  # 新增属性来存储顶点的输出

    def get_env_parameter(self, key: str, default: T = {}) -> T:
        return self.env_parameters.get(key, default)

    def get_env_parameters(self) -> Dict[str, Any]:
        return self.env_parameters

    def get_user_parameter(self, key: str, default: T = {}) -> T:
        return self.user_parameters.get(key, default)

    def get_user_parameters(self) -> Dict[str, Any]:
        return self.user_parameters

    def store_output(self, vertex_id: str, output_data: T):
        """存储顶点的输出数据"""
        self.outputs[vertex_id] = output_data

    def get_output(self, vertex_id: str) -> T:
        """从上下文中获取指定顶点的输出数据"""
        return self.outputs.get(vertex_id, None)

    def get_outputs(self) -> Dict[str, Any]:
        """从上下文中获取所有顶点的输出数据"""
        return self.outputs


def around_workflow(func):
    def on_workflow_finished(self):
        logging.info("on workflow finished.")
        for vertex in self.vertices.values():
            if vertex.is_executed:
                try:
                    vertex.on_workflow_finished()
                except BaseException as e:
                    logging.error(
                        f"Failed to execute vertex {vertex.id} workflow finished callback."
                    )

    def on_workflow_failed(self):
        logging.info("on workflow failed.")
        for vertex in self.vertices.values():
            if vertex.is_executed:
                try:
                    vertex.on_workflow_failed()
                except BaseException as e:
                    logging.error(
                        f"Failed to execute vertex {vertex.id} workflow failed callback."
                    )

    def wrapper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
            on_workflow_finished(self)
        except BaseException as e:
            on_workflow_failed(self)
            raise e
        return result

    return wrapper


class Workflow(Generic[T]):
    """工作流类，管理顶点和边，并提供执行工作流的方法"""

    def __init__(self, context: WorkflowContext[T] = None):
        self.vertices = {}
        self.edges = set()
        self.context = context or WorkflowContext[T]()
        self.topological_order: List[str] = []
        self.lock = Lock()
        self.executed = False
        # 新增事件通道
        self.event_channel = EventChannel()

    def emit_event(self, event_type: str, event_data: dict):
        self.event_channel.emit_event(event_type, event_data)

    def subscribe(self, event_type: str, callback):
        self.event_channel.subscribe(event_type, callback)

    async def astream(self, event_type: str):
        """代理到 EventChannel 的 astream 方法"""
        async for event_data in self.event_channel.astream(event_type):
            yield event_data

    def add_vertex(self, vertex: Vertex[T]) -> Vertex[T]:
        self.vertices[vertex.id] = vertex
        vertex.workflow = self
        return vertex

    def ensure_vertex_added(self, vertex: Vertex[T]) -> Vertex[T]:
        if vertex.id not in self.vertices:
            self.add_vertex(vertex)
        return vertex

    def __getstate__(self):
        # 返回一个字典，包含可以被序列化的状态
        state = self.__dict__.copy()
        del state["lock"]  # 排除不能被序列化的属性
        return state

    def __setstate__(self, state):
        # 恢复状态，并重新创建不能被序列化的属性
        self.__dict__.update(state)
        self.lock = Lock()

    @property
    def flow_context(self):
        return self.context

    def add_edge(self, edge: Edge[T]):
        if edge in self.edges:
            # 如果边已经存在，则不进行任何操作
            return
        if (
            edge.source_vertex.id not in self.vertices
            or edge.target_vertex.id not in self.vertices
        ):
            raise ValueError("Invalid vertices IDs for the edge.")

        # 检查源顶点的输出类型与目标顶点的输入类型是否兼容, 目前动态类型检查先跳过.
        # if edge.target_vertex.task_type != 'SINK' and \
        #   edge.source_vertex.output_type is not None and \
        #   edge.source_vertex.output_type != edge.target_vertex.input_type:
        #    raise TypeError(f"Incompatible types between vertex {edge.source_vertex.id} and {edge.target_vertex.id}")
        logging.info(f"Edge add {edge}.")
        self.edges.add(edge)
        self.vertices[edge.target_vertex.id].in_degree += 1  # 更新入度
        self.vertices[edge.target_vertex.id].dependencies.add(edge.source_vertex.id)
        # 更新出度
        self.vertices[edge.source_vertex.id].out_degree += 1

    def topological_sort(self):
        queue = deque(self.get_sources())
        self.topological_order = []
        logging.info(f"Source vertex length : {len(queue)}")
        while queue:
            vertex = queue.popleft()
            self.topological_order.append(vertex)
            logging.debug(f"Topological in {vertex}")
            for edge in self.edges:
                if edge.get_source_vertex().id == vertex.id:
                    target_vertex = edge.get_target_vertex()
                    target_vertex.in_degree -= 1
                    if target_vertex.in_degree == 0:
                        queue.append(target_vertex)

        if len(self.topological_order) != len(self.vertices):
            raise ValueError(
                f"Graph contains a cycle, cannot perform topological sort, size of topo order : {len(self.topological_order)}, orignal size : {len(self.vertices)}."
            )

    def validate_workflow(self):
        """
        验证工作流图的正确性。
        """
        if self.executed:
            raise RuntimeError(f"Workflow running duplicated.")
        # 1. 检查顶点上下游的输入输出类型是否匹配
        for edge in self.edges:
            source_vertex = edge.get_source_vertex()
            target_vertex = edge.get_target_vertex()
            # if source_vertex.output_type is not None and \
            #    source_vertex.output_type != target_vertex.input_type:
            #     raise TypeError(f"Incompatible types between vertex {source_vertex.id} and {target_vertex.id}")

        # 2. 检查workflow是否包含至少一个source和一个sink
        sources = [
            vertex for vertex in self.vertices.values() if vertex.task_type == "SOURCE"
        ]
        sinks = [
            vertex for vertex in self.vertices.values() if vertex.task_type == "SINK"
        ]
        if len(sources) < 1:
            raise ValueError("Workflow must contain at least one source vertex.")
        if len(sinks) < 1:
            raise ValueError("Workflow must contain at least one sink vertex.")

        # 3. 入度为0的顶点必须为source
        for vertex in self.vertices.values():
            if vertex.in_degree == 0 and vertex.task_type != "SOURCE":
                raise ValueError(
                    f"Vertex {vertex.id} has an in-degree of 0 but is not a source vertex."
                )

        # 4. 出度为0的必须为sink
        for vertex in self.vertices.values():
            logging.debug(f"check out degress : {vertex}, {vertex.out_degree}")
            if vertex.out_degree > 0 and vertex.task_type == "SINK":
                raise ValueError(
                    f"Vertex {vertex.id} has out-degree of 0 but is not a sink vertex."
                )
            if vertex.task_type == "SINK" and vertex.out_degree > 0:
                raise ValueError(f"Sink vertex {vertex.id} should not have any output.")

        # 5. 其它类型出度和入度必须大于0
        for vertex in self.vertices.values():
            if vertex.task_type not in ["SOURCE", "SINK"]:
                if vertex.in_degree <= 0:
                    raise ValueError(
                        f"Non-source/non-sink vertex {vertex.id} must have both in-degree and out-degree greater than 0."
                    )

    def find_subgraph(self, start_vertex_id: str) -> Set[Vertex[T]]:
        """
        找到给定顶点的所有子图（依赖于该顶点的顶点及其依赖关系）。

        参数:
        - start_vertex_id: 开始顶点的ID

        返回:
        - 包含所有相关顶点的集合。
        """
        if start_vertex_id not in self.vertices:
            raise ValueError(f"Vertex with ID {start_vertex_id} does not exist.")

        visited = set()  # 已访问过的顶点
        subgraph = set()  # 子图中的顶点

        queue = deque([self.vertices[start_vertex_id]])  # 初始化队列

        while queue:
            current_vertex = queue.popleft()
            if current_vertex in visited:
                continue
            visited.add(current_vertex)
            subgraph.add(current_vertex)

            # 获取当前顶点的所有邻居（依赖于当前顶点的顶点）
            neighbors = [
                edge.target_vertex
                for edge in self.edges
                if edge.source_vertex == current_vertex
            ]
            queue.extend(neighbors)

        return subgraph

    def mayebe_filter_subgraph(self, vertex: Vertex[T]) -> tuple[bool, Set[str]]:
        ifelse_deps = []
        for vertex_id in vertex.dependencies:
            deps_vertex = self.get_vertice_by_id(vertex_id)
            if isinstance(deps_vertex, IfElseVertex):
                ifelse_deps.append(deps_vertex)
        if not ifelse_deps:
            return (False, set())
        # 目前只有一个ifelse
        assert len(ifelse_deps) == 1
        ifelse_dep: IfElseVertex = ifelse_deps[0]
        ifedeg: Edge = list(
            filter(
                lambda x: x.source_vertex == ifelse_dep and x.target_vertex == vertex,
                self.edges,
            )
        )
        if ifedeg and not ifelse_dep.iftrue(ifedeg[0].edge_type.id):
            return (
                True,
                set([sub_vertex.id for sub_vertex in self.find_subgraph(vertex.id)]),
            )
        return (False, set())

    @around_workflow
    @timer_decorator
    def execute_workflow(
        self, source_inputs: Dict[str, Any] = {}, stream: bool = False
    ):
        self.validate_workflow()  # 在执行之前先验证图的正确性
        self.topological_sort()
        self.executed = True
        filtered_vertices: Set[str] = set()

        with ThreadPoolExecutor() as executor:
            futures = {}
            checked_futures = set()

            for vertex in self.topological_order:
                self.execute_vertex(
                    vertex,
                    source_inputs,
                    futures,
                    checked_futures,
                    filtered_vertices,
                    executor,
                    stream,
                )

            if not stream:
                self.process_results(futures, checked_futures)

        logging.info("workflow finished.")
        return True

    def execute_vertex(
        self,
        vertex,
        source_inputs,
        futures,
        checked_futures,
        filtered_vertices,
        executor,
        stream,
    ):
        logging.info(
            f"Executing {vertex.id}, task_type : {vertex.task_type} deps : {vertex._dependencies}."
        )

        if vertex.id in filtered_vertices:
            logging.info(f"skip {vertex.id}.")
            return

        self.wait_for_dependencies(vertex, futures, checked_futures)

        dependency_outputs = {
            dep._id: dep.output
            for dep in self.vertices.values()
            if dep._id in vertex._dependencies
        }

        filter_result = self.mayebe_filter_subgraph(vertex=vertex)
        if filter_result[0]:
            logging.info(
                f"vertex : {vertex} has been filterd, its subgraph might be skipped {filter_result[1]}"
            )
            filtered_vertices.update(filter_result[1])
            return

        future = executor.submit(
            vertex.execute,
            (dependency_outputs if vertex not in self.get_sources() else source_inputs),
            self.context,
        )

        futures[future] = vertex
        vertex.is_executed = True

        if stream:
            self.process_stream_result(future, vertex)

    def wait_for_dependencies(self, vertex, futures, checked_futures):
        dependencies_finished = all(
            future.done() for future in futures.keys() if future
        )

        if not dependencies_finished:
            for dep_id in vertex._dependencies:
                dep_future = [item for item in futures.items() if item[1]._id == dep_id]
                for item in dep_future:
                    f, v = item[0], item[1]
                    try:
                        logging.info(f"waiting for {v.id}.")
                        f.result()
                        checked_futures.add(f)
                        self.context.store_output(v._id, v.output)
                        logging.info(f"deps finished, info {v.id}")
                    except Exception as e:
                        raise e

    def process_stream_result(self, future, vertex):
        try:
            future.result()
            logging.debug(f"vertex finished, detail {vertex}")
            self.context.store_output(vertex._id, vertex.output)
        except Exception as e:
            logging.error(f"Failed to execute vertex {vertex}: {e}")
            raise e

    def process_results(self, futures, checked_futures):
        for future in as_completed(futures):
            if future in checked_futures:
                logging.debug(f"skip already checked future {future}.")
                continue
            with self.lock:
                vertex = futures[future]
                try:
                    future.result()
                    logging.debug(f"vertex finished, detail {vertex}")
                except Exception as e:
                    logging.error(f"Failed to execute vertex {vertex}: {e}")
                    raise e
                else:
                    self.context.store_output(vertex._id, vertex.output)

    def show_graph(
        self,
        include_params=False,
        include_dependencies=False,
        include_output=False,
        include_types=False,
    ):
        """
        输出当前的工作流图信息，格式为 JSON。

        :param include_params: 是否包含顶点的参数信息，默认为 False
        :param include_dependencies: 是否包含顶点的依赖信息，默认为 False
        :param include_output: 是否包含顶点的输出信息，默认为 False
        :param include_types: 是否包含顶点的输入输出类型信息，默认为 False
        """
        graph_info = {
            "vertices": [
                {
                    "id": vertex.id,
                    "task_type": vertex.task_type,
                    "params": vertex.params if include_params else None,
                    "dependencies": (
                        list(vertex.dependencies) if include_dependencies else None
                    ),
                    "output": vertex.output if include_output else None,
                    "input_type": vertex.input_type if include_types else None,
                    "output_type": vertex.output_type if include_types else None,
                    "variables": (vertex.variables if vertex.variables else None),
                }
                for vertex in self.vertices.values()
            ],
            "edges": [
                {
                    "source": edge.get_source_vertex().id,
                    "target": edge.get_target_vertex().id,
                    "type": str(edge.edge_type),
                }
                for edge in self.edges
            ],
        }

        # 使用 json.dumps 将字典序列化为 JSON 字符串
        json_string = json.dumps(graph_info, indent=4)
        print(json_string)
        return json_string

    def result(self) -> Dict[str, T]:
        """获取所有 SINK 类型顶点的输出结果"""
        sink_results = {}
        for vertex_id, vertex in self.vertices.items():
            if isinstance(vertex, SinkVertex) and vertex.is_executed:
                sink_results[vertex_id] = vertex.output
        return sink_results

    def status(self) -> Dict[str, T]:
        status_map = {}
        for vertex_id, vertex in self.vertices.items():
            if vertex.is_executed:
                status_map[vertex_id] = {
                    "name": vertex.name,
                    "status": vertex.success,
                    "cost_time": vertex.cost_time,
                    "error_message": vertex.error_message,
                    "traceback": vertex.traceback,
                }
        return status_map

    def get_vertice_by_id(self, id: str) -> Vertex[T]:
        """获取具有特定id的顶点列表"""
        return self.vertices[id]

    def get_vertices_by_type(self, task_type: str) -> List[Vertex[T]]:
        """获取具有特定类型的顶点列表"""
        return [
            vertex
            for vertex in self.vertices.values()
            if vertex._task_type == task_type
        ]

    def get_sources(self) -> List[Vertex[T]]:
        """获取所有 SOURCE 类型的顶点"""
        return self.get_vertices_by_type("SOURCE")

    def get_sinks(self) -> List[Vertex[T]]:
        """获取所有 SINK 类型的顶点"""
        return self.get_vertices_by_type("SINK")

    def get_llms(self) -> List[Vertex[T]]:
        """获取所有 LLM 类型的顶点"""
        return self.get_vertices_by_type("LLM")

    def get_iflese(self) -> List[Vertex[T]]:
        """获取所有 ifelse 类型的顶点"""
        return self.get_vertices_by_type(IfElseVertex.__call__.__name__)


def main():
    # 示例任务函数
    def source_task(inputs: Dict[str, str], context: WorkflowContext[str]) -> str:
        env_param = context.get_env_parameter("example_key", "default_value")
        logging.info("executing in source task")
        return f"Source input with env parameter: {env_param}"

    def sink_task(inputs: Dict[str, str], context: WorkflowContext[str]):
        env_param = context.get_env_parameter("example_key", "default_value")
        # SINK 类型的任务，这里假设只是打印输出
        result = f"Sink output with input: {inputs} and env parameter: {env_param}"
        logging.info(f"Sink result : {result}")

    # 创建顶点
    vertex_source = SourceVertex("SOURCE", task=source_task, params={})
    vertex_llm = LLMVertex(
        id="my_llm",
        task=lambda inputs: f"Processed: {inputs}",
    )
    vertex_function_a = FunctionVertex(
        "FUNCTION_A", task=lambda inputs: f"Function A output: {inputs}"
    )
    vertex_function_b = FunctionVertex(
        "FUNCTION_B", task=lambda inputs: f"Function B output: {inputs}"
    )
    vertex_sink = SinkVertex("SINK", task=sink_task)

    # 创建工作流
    workflow = Workflow()
    logging.info("Create workflow")

    # 构建工作流图
    (
        workflow.ensure_vertex_added(vertex_source)
        | workflow.ensure_vertex_added(vertex_llm)
        | workflow.ensure_vertex_added(vertex_function_a)
        | workflow.ensure_vertex_added(vertex_function_b)
        | workflow.ensure_vertex_added(vertex_sink)
    )
    # 连接顶点
    # vertex_source | vertex_llm
    # vertex_llm | vertex_function_a
    # vertex_function_a | vertex_function_b
    # vertex_function_b | vertex_sink

    # 创建 WorkflowContext
    workflow_context = WorkflowContext(env_parameters={"example_key": "example_value"})
    logging.info("Create workflow context.")

    # 设置工作流的上下文
    workflow.context = workflow_context

    logging.info("Connect vertex_flow.workflow.")

    # 输出工作流图信息
    workflow.show_graph(
        include_params=True, include_dependencies=True, include_output=True
    )

    # 执行工作流
    workflow.execute_workflow()
    logging.info(f"Workflow result : {workflow.result()}")
    logging.info(f"Workflow result : {workflow.context.get_outputs()}")


if __name__ == "__main__":
    main()
