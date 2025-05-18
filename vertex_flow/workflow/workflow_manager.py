import yaml
from vertex_flow.workflow.workflow import (
    Workflow,
    WorkflowContext,
)
from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.utils import load_task_from_data, create_instance

from vertex_flow.workflow.edge import (
    Edge,
    EdgeType,
    Condition,
    Always,
)

from vertex_flow.workflow.vertex import (
    Vertex,
    SourceVertex,
    LLMVertex,
    FunctionVertex,
    IfElseVertex,
    EmbeddingVertex,
    IfCase,
)
import json

logger = LoggerUtil.get_logger()


class WorkflowSerializer:
    pass


class WorkflowJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Vertex):
            return obj.__get_state__()
        elif isinstance(obj, Workflow):
            return WorkflowSerializer._serialize_workflow(obj)
        elif isinstance(obj, Edge):
            return WorkflowSerializer._serialize_edge(obj)
        elif isinstance(obj, EdgeType):
            return WorkflowSerializer._serialize_edge_type(obj)
        elif isinstance(obj, WorkflowContext):
            return WorkflowSerializer._serialize_workflow_context(obj)
        elif isinstance(obj, set):
            return list(obj)
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        logger.warning(f"Unsupported type: {type(obj)}, value {obj}")
        return super().default(obj)


class WorkflowSerializer:
    @staticmethod
    def _serialize_workflow(workflow: Workflow) -> dict:
        return {
            "context": vertex_flow.workflow.context,
            "vertices": vertex_flow.workflow.vertices,
            "edges": vertex_flow.workflow.edges,
        }

    @staticmethod
    def _serialize_edge(edge: Edge) -> dict:
        return {
            "type": edge.edge_type,
            "source_vertex_id": edge.source_vertex.id,
            "target_vertex_id": edge.target_vertex.id,
        }

    @staticmethod
    def _serialize_edge_type(edge_type: EdgeType) -> dict:
        data = {
            "name": edge_type.name,
        }
        if isinstance(edge_type, Condition):
            data["id"] = edge_type.id
        return data

    @staticmethod
    def _serialize_workflow_context(workflow_context: WorkflowContext) -> dict:
        return {
            "env_parameters": workflow_context.env_parameters,
            "user_parameters": workflow_context.user_parameters,
        }

    @staticmethod
    def _deserialize_edge(edge_data: dict, vertices: dict) -> Edge:
        source_vertex_id = edge_data["source_vertex_id"]
        target_vertex_id = edge_data["target_vertex_id"]
        edge_type_data = edge_data["type"]

        # 获取源顶点和目标顶点
        source_vertex = vertices[source_vertex_id]
        target_vertex = vertices[target_vertex_id]

        # 反序列化边类型
        edge_type = WorkflowSerializer._deserialize_edge_type(edge_type_data)

        # 创建并返回新的 Edge 实例
        return Edge(source_vertex, target_vertex, edge_type)

    @staticmethod
    def _deserialize_edge_type(edge_type_data: dict) -> EdgeType:
        name = edge_type_data["name"]

        if "id" in edge_type_data:
            # 如果是条件类型的边
            condition_id = edge_type_data["id"]
            return Condition(name=name, id=condition_id)
        else:
            # 普通的 EdgeType
            return Always()

    @staticmethod
    def serialize_to_yaml(workflow: Workflow, file_path: str):
        with open(file_path, "w") as file:
            json_data = json.dumps(workflow, cls=WorkflowJSONEncoder, indent=4)
            logger.info(f"json = {json_data}")
            yaml.dump(
                json.loads(json_data),
                file,
                default_flow_style=False,
                allow_unicode=True,
            )

    @staticmethod
    def deserialize_from_yaml(file_path: str) -> Workflow:
        with open(file_path, "r") as file:
            data = yaml.safe_load(file)

        # 重新构建上下文
        context = WorkflowContext(
            env_parameters=data["context"]["env_parameters"],
            user_parameters=data["context"]["user_parameters"],
        )

        # 重新构建顶点
        vertices = {}
        for vertex_data in data["vertices"].values():
            vertex = WorkflowSerializer._deserialize_vertex(vertex_data)
            vertices[vertex.id] = vertex

        # 重新构建边
        edges = set()
        for edge_data in data["edges"]:
            edge = WorkflowSerializer._deserialize_edge(edge_data, vertices=vertices)
            edges.add(edge)

        # 重新构建工作流
        workflow = Workflow(context=context)
        for vertex in vertices.values():
            vertex_flow.workflow.add_vertex(vertex)
        for edge in edges:
            vertex_flow.workflow.add_edge(edge)

        return workflow

    @staticmethod
    def _deserialize_vertex(vertex_data):
        class_module = vertex_data.get("class_module")
        class_name = vertex_data.get("class_name")

        # 动态导入类
        module = __import__(class_module, fromlist=[class_name])
        vertex_class = getattr(module, class_name)

        if vertex_class == IfElseVertex:
            return WorkflowSerializer._deserialize_if_else_vertex(vertex_data)
        elif vertex_class == SourceVertex:
            return WorkflowSerializer._deserialize_source_vertex(vertex_data)
        elif vertex_class == LLMVertex:
            return WorkflowSerializer._deserialize_llm_vertex(vertex_data)
        elif vertex_class == FunctionVertex:
            return WorkflowSerializer._deserialize_function_vertex(vertex_data)
        elif vertex_class == EmbeddingVertex:
            return WorkflowSerializer._deserialize_embedding_vertex(vertex_data)
        else:
            return WorkflowSerializer._deserialize_generic_vertex(
                vertex_class, vertex_data
            )

    @staticmethod
    def _deserialize_if_else_vertex(vertex_data):
        cases = [
            IfCase(
                conditions=[
                    {
                        key: value if not key.endswith("__name__") else globals()[value]
                        for key, value in condition.items()
                    }
                    for condition in case_data["conditions"]
                ],
                logical_operator=case_data["logical_operator"],
                id=case_data["id"],
            )
            for case_data in vertex_data["cases"]
        ]
        return IfElseVertex(
            id=vertex_data["id"],
            name=vertex_data["name"],
            cases=cases,
            params=vertex_data["params"],
        )

    @staticmethod
    def _deserialize_source_vertex(vertex_data):
        task = load_task_from_data(vertex_data["task"])
        vertex = SourceVertex(
            id=vertex_data["id"],
            name=vertex_data["name"],
            task=task if task else vertex_data["task"],
            params=vertex_data["params"],
        )
        vertex.dependencies = set(vertex_data["dependencies"])
        vertex.variables = vertex_data["variables"]
        return vertex

    @staticmethod
    def _deserialize_llm_vertex(vertex_data):
        # 初始化 LLMVertex 的基本属性
        params = vertex_data.get("params", {}).copy()  # 深拷贝原始参数字典

        # 将 user_messages 和 system_message 放入 params 中
        if "user_messages" in vertex_data:
            params["user_messages"] = vertex_data["user_messages"]
        if "system_message" in vertex_data:
            params["system_message"] = vertex_data["system_message"]

        # 反序列化 ChatModel 实例（假设 ChatModelFactory 存在并可用）
        if "model" in vertex_data:
            model_state = vertex_data["model"]
            model_class_name = model_state.get("class_name")
            sk = model_state.get("sk")
            name = model_state.get("name")
            base_url = model_state.get("base_url")

            try:
                params["model"] = create_instance(
                    class_name=model_class_name, sk=sk, name=name
                )
            except ValueError as e:
                logger.error(f"Failed to create ChatModel instance: {e}")
                raise e

        vertex = LLMVertex(
            id=vertex_data["id"],
            name=vertex_data["name"],
            task=None,  # 暂时不设置 task，稍后处理
            params=params,
        )

        # 设置 dependencies 和 variables
        vertex.dependencies = set(vertex_data.get("dependencies", []))
        vertex.variables = vertex_data.get("variables", {})

        return vertex

    @staticmethod
    def _deserialize_function_vertex(vertex_data):
        vertex = FunctionVertex(
            id=vertex_data["id"],
            name=vertex_data["name"],
            task=vertex_data["task"],
            params=vertex_data["params"],
        )
        vertex.dependencies = set(vertex_data["dependencies"])
        vertex.variables = vertex_data["variables"]
        return vertex

    @staticmethod
    def _deserialize_embedding_vertex(vertex_data):
        try:
            # 加载任务函数
            task = load_task_from_data(vertex_data.get("task", None))

            # 提取必要的字段
            id = vertex_data.get("id")
            name = vertex_data.get("name", id)
            params = vertex_data.get("params", {})
            dependencies = vertex_data.get("dependencies", [])
            variables = vertex_data.get("variables", [])

            # 反序列化 embedding_provider
            embedding_provider_data = vertex_data.get("embedding_provider", {})
            embedding_provider_class_name = embedding_provider_data.get("class_name")

            if embedding_provider_class_name:
                try:
                    embedding_provider = create_instance(**embedding_provider_data)
                except ValueError as e:
                    logger.error(f"Failed to create EmbeddingProvider instance: {e}")
                    raise e
            else:
                embedding_provider = None

            # 创建 EmbeddingVertex 实例
            vertex = EmbeddingVertex(
                id=id,
                name=name,
                task=task,
                params=params,
                embedding_provider=embedding_provider,
            )

            # 设置依赖关系
            vertex.dependencies = set(dependencies)
            vertex.variables = variables

            return vertex

        except KeyError as e:
            logger.error(
                f"Missing required key in vertex data: {e}, vertex data: {vertex_data}"
            )
            raise ValueError(f"Invalid vertex data: missing key {e}")

        except Exception as e:
            logger.error(f"Failed to deserialize vertex: {e}", exc_info=True)
            raise ValueError(
                f"Failed to deserialize vertex: {e}, vertex data: {vertex_data}"
            )

    @staticmethod
    def _deserialize_generic_vertex(vertex_class, vertex_data):
        try:
            # 加载任务函数
            task = load_task_from_data(vertex_data.get("task", None))

            # 过滤掉不需要的键
            required_keys = {"id", "name", "params", "variables", "dependencies"}
            filtered_vertex_data = {
                k: v for k, v in vertex_data.items() if k in required_keys
            }

            # 动态构造参数字典
            init_params = {
                "id": filtered_vertex_data["id"],
                "name": filtered_vertex_data.get(
                    "name", filtered_vertex_data["id"]
                ),  # 使用 ID 作为默认名称
                "params": filtered_vertex_data.get("params", {}),
                "variables": filtered_vertex_data.get("variables", []),
            }
            task_load = (
                task if callable(task) else filtered_vertex_data.get("task", None),
            )
            if task_load and isinstance(task_load, tuple) and task_load[0]:
                init_params["task"] = task_load[0]

            # 实例化顶点对象
            vertex = vertex_class(**init_params)

            # 设置依赖关系
            vertex.dependencies = set(filtered_vertex_data.get("dependencies", []))

            return vertex

        except KeyError as e:
            logger.error(
                f"Missing required key in vertex data: {e}, vertex data: {vertex_data}"
            )
            raise ValueError(f"Invalid vertex data: missing key {e}")

        except Exception as e:
            logger.error(f"Failed to deserialize vertex: {e}", exc_info=True)
            raise ValueError(
                f"Failed to deserialize vertex: {e}, vertex data: {vertex_data}"
            )
