import json
from datetime import datetime

import yaml

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.edge import Always, Condition, Edge, EdgeType
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.utils import create_instance, load_task_from_data
from vertex_flow.workflow.vertex import (
    EmbeddingVertex,
    FunctionVertex,
    IfCase,
    IfElseVertex,
    LLMVertex,
    SinkVertex,
    SourceVertex,
    Vertex,
)
from vertex_flow.workflow.workflow import Workflow, WorkflowContext
from vertex_flow.workflow.workflow_instance import WorkflowInstance

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
            return WorkflowSerializer._deserialize_generic_vertex(vertex_class, vertex_data)

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
                params["model"] = create_instance(class_name=model_class_name, sk=sk, name=name)
            except ValueError as e:
                logger.error(f"Failed to create ChatModel instance: {e}")
                raise e

        vertex = LLMVertex(
            id=vertex_data["id"],
            name=vertex_data["name"],
            task=None,  # 暂时不设置 task，稍后处理
            params=params,
            variables=vertex_data.get("variables", []),  # 添加variables参数
        )

        # 设置 dependencies
        vertex.dependencies = set(vertex_data.get("dependencies", []))

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
            logger.error(f"Missing required key in vertex data: {e}, vertex data: {vertex_data}")
            raise ValueError(f"Invalid vertex data: missing key {e}")

        except Exception as e:
            logger.error(f"Failed to deserialize vertex: {e}", exc_info=True)
            raise ValueError(f"Failed to deserialize vertex: {e}, vertex data: {vertex_data}")

    @staticmethod
    def _deserialize_generic_vertex(vertex_class, vertex_data):
        try:
            # 加载任务函数
            task = load_task_from_data(vertex_data.get("task", None))

            # 过滤掉不需要的键
            required_keys = {"id", "name", "params", "variables", "dependencies"}
            filtered_vertex_data = {k: v for k, v in vertex_data.items() if k in required_keys}

            # 动态构造参数字典
            init_params = {
                "id": filtered_vertex_data["id"],
                "name": filtered_vertex_data.get("name", filtered_vertex_data["id"]),  # 使用 ID 作为默认名称
                "params": filtered_vertex_data.get("params", {}),
                "variables": filtered_vertex_data.get("variables", []),
            }
            task_load = (task if callable(task) else filtered_vertex_data.get("task", None),)
            if task_load and isinstance(task_load, tuple) and task_load[0]:
                init_params["task"] = task_load[0]

            # 实例化顶点对象
            vertex = vertex_class(**init_params)

            # 设置依赖关系
            vertex.dependencies = set(filtered_vertex_data.get("dependencies", []))

            return vertex

        except KeyError as e:
            logger.error(f"Missing required key in vertex data: {e}, vertex data: {vertex_data}")
            raise ValueError(f"Invalid vertex data: missing key {e}")

        except Exception as e:
            logger.error(f"Failed to deserialize vertex: {e}", exc_info=True)
            raise ValueError(f"Failed to deserialize vertex: {e}, vertex data: {vertex_data}")


class WorkflowManager:
    """工作流管理器，用于管理工作流的创建、保存、加载和执行"""

    def __init__(self, vertex_service=None):
        self.workflows = {}  # 存储workflow模板
        self.workflow_instances = {}  # 存储workflow执行实例
        self.execution_history = {}  # 存储执行历史
        self.current_workflow = None
        self.vertex_service = vertex_service  # 外部传入的 VertexFlowService 实例

    def create_workflow(self, name: str, description: str = "") -> dict:
        """创建新的工作流"""
        workflow_id = f"workflow_{len(self.workflows) + 1}"
        workflow_data = {
            "id": workflow_id,
            "name": name,
            "description": description,
            "nodes": [],
            "edges": [],
            "created_at": json.dumps(datetime.now(), default=str),
            "updated_at": json.dumps(datetime.now(), default=str),
        }
        self.workflows[workflow_id] = workflow_data
        return workflow_data

    def get_workflow(self, workflow_id: str) -> dict:
        """获取指定的工作流"""
        return self.workflows.get(workflow_id)

    def get_all_workflows(self) -> list:
        """获取所有工作流"""
        workflows_list = list(self.workflows.values())

        # 如果工作流列表为空，创建一个默认工作流
        if not workflows_list:
            default_workflow = self._create_default_workflow()
            workflows_list = [default_workflow]

        return workflows_list

    def _create_default_workflow(self) -> dict:
        """创建默认工作流"""
        import time

        # 生成唯一的节点ID
        timestamp = int(time.time() * 1000)
        start_node_id = f"node_{timestamp}"
        llm_node_id = f"node_{timestamp + 1}"
        end_node_id = f"node_{timestamp + 2}"

        # 创建默认节点
        default_nodes = [
            {
                "id": start_node_id,
                "label": "开始",
                "x": -200,
                "y": 0,
                "color": "#28a745",
                "font": {"color": "#fff"},
                "data": {"type": "start", "config": {"name": "开始", "description": "工作流开始节点"}},
            },
            {
                "id": llm_node_id,
                "label": "LLM",
                "x": 0,
                "y": 0,
                "color": "#007bff",
                "font": {"color": "#fff"},
                "data": {
                    "type": "llm",
                    "config": {
                        "name": "LLM",
                        "model": "deepseek",
                        "model_name": "deepseek-chat",
                        "system_prompt": "你是一个有用的AI助手。",
                        "user_message": "请帮我制作一个关于杭州的旅游攻略。",
                        "temperature": 0.7,
                        "max_tokens": 1000,
                    },
                },
            },
            {
                "id": end_node_id,
                "label": "结束",
                "x": 200,
                "y": 0,
                "color": "#dc3545",
                "font": {"color": "#fff"},
                "data": {"type": "end", "config": {"name": "结束", "description": "工作流结束节点"}},
            },
        ]

        # 创建默认连接边
        default_edges = [
            {"id": f"edge_{start_node_id}_{llm_node_id}", "from": start_node_id, "to": llm_node_id, "label": ""},
            {"id": f"edge_{llm_node_id}_{end_node_id}", "from": llm_node_id, "to": end_node_id, "label": ""},
        ]

        # 创建默认工作流
        default_workflow = self.create_workflow(
            name="默认工作流", description="系统自动创建的默认工作流，包含开始、LLM和结束节点"
        )

        # 更新节点和边
        default_workflow["nodes"] = default_nodes
        default_workflow["edges"] = default_edges

        # 尝试创建工作流对象
        try:
            workflow_obj = self._create_workflow_from_nodes_edges(default_nodes, default_edges)
            default_workflow["workflow_obj"] = workflow_obj
            logger.info("Created default workflow with workflow object")
        except Exception as e:
            logger.warning(f"Failed to create workflow object for default workflow: {e}")
            # 即使创建失败，也返回基本的工作流数据

        return default_workflow

    def _create_workflow_from_nodes_edges(self, nodes: list, edges: list):
        """基于节点和边创建工作流对象"""
        try:
            # 创建工作流上下文
            context = WorkflowContext()

            # 创建工作流对象
            workflow = Workflow(context=context)

            # 创建节点映射
            vertex_map = {}

            # 创建顶点
            for node in nodes:
                node_type = node.get("data", {}).get("type", "unknown")
                node_config = node.get("data", {}).get("config", {})

                if node_type == "start":
                    # 为 start 节点创建一个默认的任务函数
                    def default_source_task(inputs=None, context=None):
                        # 返回节点配置中的数据或空字典
                        return node_config.get("data", {})

                    vertex = SourceVertex(
                        id=node["id"],
                        name=node_config.get("name", "Start"),
                        task=default_source_task,
                        params=node_config,
                    )
                elif node_type == "end":
                    # 创建结束顶点
                    # SinkVertex 需要 name、task 或 variables 参数
                    end_name = node_config.get("name", "End")
                    end_task = node_config.get("task", None)
                    end_variables = node_config.get("variables", None)

                    # 如果没有提供 task 和 variables，创建一个默认的 task
                    if not end_task and not end_variables:

                        def default_sink_task(inputs, context, **kwargs):
                            """默认的结束节点任务，简单记录输入数据"""
                            logger.info(f"End node {node['id']} received inputs: {inputs}")
                            return inputs

                        end_task = default_sink_task

                    vertex = SinkVertex(
                        id=node["id"], name=end_name, task=end_task, variables=end_variables, params=node_config
                    )
                elif node_type == "llm":
                    # 创建LLM顶点
                    # 处理model参数，如果是字符串则需要转换为ChatModel对象
                    llm_params = node_config.copy()
                    if "model" in llm_params and isinstance(llm_params["model"], str):
                        # 使用 WorkflowManager 的 vertex_service 实例，避免重复创建
                        if self.vertex_service is None:
                            self.vertex_service = VertexFlowService()
                        # 尝试通过provider获取ChatModel，如果失败则使用默认模型
                        try:
                            llm_params["model"] = self.vertex_service.get_chatmodel_by_provider(llm_params["model"])
                        except BaseException:
                            # 如果获取失败，使用默认的ChatModel
                            llm_params["model"] = self.vertex_service.get_chatmodel()

                    # 映射前端参数到 LLMVertex 期望的参数格式
                    # 前端传递: model, model_name, system_prompt, user_message, temperature, max_tokens
                    # LLMVertex 期望: MODEL, SYSTEM, USER, temperature, max_tokens 等
                    from vertex_flow.workflow.constants import MODEL, SYSTEM, USER

                    # 构建 LLMVertex 参数
                    vertex_params = {}

                    # 模型参数
                    if "model" in llm_params:
                        vertex_params[MODEL] = llm_params["model"]

                    # 系统提示词
                    if "system_prompt" in llm_params:
                        vertex_params[SYSTEM] = llm_params["system_prompt"]

                    # 用户消息
                    if "user_message" in llm_params:
                        vertex_params[USER] = [llm_params["user_message"]]

                    # 其他参数直接传递
                    for key in ["temperature", "max_tokens", "tools"]:
                        if key in llm_params:
                            vertex_params[key] = llm_params[key]

                    # 保留原始配置用于调试和其他用途
                    vertex_params.update(llm_params)

                    vertex = LLMVertex(
                        id=node["id"],
                        name=node_config.get("name", "LLM"),
                        params=vertex_params,
                        variables=node_config.get("variables", []),  # 添加variables参数
                    )
                elif node_type == "function":
                    # 创建函数顶点
                    vertex = FunctionVertex(id=node["id"], name=node_config.get("name", "Function"), params=node_config)
                elif node_type == "if-else":
                    # 创建条件顶点
                    vertex = IfElseVertex(id=node["id"], name=node_config.get("name", "IfElse"), params=node_config)
                else:
                    # 对于未知类型，创建函数顶点作为默认
                    vertex = FunctionVertex(
                        id=node["id"], name=node_config.get("name", f"Unknown-{node_type}"), params=node_config
                    )

                vertex_map[node["id"]] = vertex
                workflow.add_vertex(vertex)

            # 创建边
            for edge in edges:
                from_vertex = vertex_map.get(edge["from"])
                to_vertex = vertex_map.get(edge["to"])

                if from_vertex and to_vertex:
                    # 创建边对象
                    workflow_edge = Edge(
                        source_vertex=from_vertex,
                        target_vertex=to_vertex,
                    )
                    workflow.add_edge(workflow_edge)

            logger.info(f"Successfully created workflow from nodes and edges, {workflow.show_graph()}")
            return workflow

        except Exception as e:
            logger.error(f"Failed to create workflow from nodes and edges: {e}")
            raise

    def update_workflow(self, workflow_id: str, **kwargs) -> dict:
        """更新工作流模板"""
        if workflow_id in self.workflows:
            workflow = self.workflows[workflow_id]

            # 检查是否有结构性变化
            nodes_changed = "nodes" in kwargs and kwargs["nodes"] != workflow.get("nodes")
            edges_changed = "edges" in kwargs and kwargs["edges"] != workflow.get("edges")

            if nodes_changed or edges_changed:
                # 结构发生变化，创建新版本
                workflow["version"] = workflow.get("version", 1) + 1
                workflow["structure_hash"] = self._calculate_structure_hash(
                    kwargs.get("nodes", []), kwargs.get("edges", [])
                )

            # 更新基本信息
            for key, value in kwargs.items():
                if key in workflow:
                    workflow[key] = value

            workflow["updated_at"] = datetime.now().isoformat()

            # 移除旧的workflow_obj，每次执行时重新创建
            if "workflow_obj" in workflow:
                del workflow["workflow_obj"]

            return workflow
        return None

    def execute_workflow(self, workflow_id: str, input_data: dict = None) -> dict:
        """执行工作流 - 每次都创建新的实例"""
        try:
            workflow_template = self.get_workflow(workflow_id)
            if not workflow_template:
                return {"error": "Workflow template not found", "status": "failed"}

            # 创建新的工作流实例
            instance = WorkflowInstance(workflow_template, input_data, self)

            # 执行实例
            instance.execute()

            # 保存实例到历史记录
            self.workflow_instances[instance.id] = instance

            # 更新执行历史
            if workflow_id not in self.execution_history:
                self.execution_history[workflow_id] = []
            self.execution_history[workflow_id].append(
                {
                    "instance_id": instance.id,
                    "executed_at": instance.started_at.isoformat(),
                    "status": instance.status,
                    "input_data": instance.input_data,
                    "output_data": instance.output_data,
                }
            )

            return {
                "instance_id": instance.id,
                "result": instance.output_data,
                "status": instance.status,
                "node_outputs": instance.node_outputs,
                "executed_at": instance.started_at.isoformat(),
            }

        except Exception as e:
            import traceback

            error_traceback = traceback.format_exc()
            logger.error(f"Failed to execute workflow: {e}\nTraceback:\n{error_traceback}")
            return {"error": str(e), "status": "failed", "traceback": error_traceback}

    def get_execution_history(self, workflow_id: str) -> list:
        """获取工作流执行历史"""
        return self.execution_history.get(workflow_id, [])

    def get_workflow_instance(self, instance_id: str) -> WorkflowInstance:
        """获取特定的工作流实例"""
        return self.workflow_instances.get(instance_id)

    def get_all_workflow_instances(self) -> list:
        """获取所有工作流实例"""
        instances = []
        for instance_id, instance in self.workflow_instances.items():
            instances.append(
                {
                    "id": instance_id,
                    "workflow_template_id": getattr(instance, "workflow_template_id", None),
                    "status": getattr(instance, "status", "unknown"),
                    "created_at": (
                        getattr(instance, "created_at", None).isoformat()
                        if getattr(instance, "created_at", None)
                        else None
                    ),
                    "started_at": (
                        getattr(instance, "started_at", None).isoformat()
                        if getattr(instance, "started_at", None)
                        else None
                    ),
                    "completed_at": (
                        getattr(instance, "completed_at", None).isoformat()
                        if getattr(instance, "completed_at", None)
                        else None
                    ),
                    "error_message": getattr(instance, "error_message", None),
                }
            )
        return instances

    def _calculate_structure_hash(self, nodes: list, edges: list) -> str:
        """计算工作流结构的哈希值"""
        import hashlib

        # 创建结构的字符串表示
        structure_data = {
            "nodes": sorted(
                [
                    {
                        "id": node.get("id"),
                        "type": node.get("data", {}).get("type"),
                        "config": node.get("data", {}).get("config", {}),
                    }
                    for node in nodes
                ],
                key=lambda x: x["id"],
            ),
            "edges": sorted(
                [{"from": edge.get("from"), "to": edge.get("to")} for edge in edges], key=lambda x: (x["from"], x["to"])
            ),
        }

        # 转换为字符串并计算哈希
        structure_str = json.dumps(structure_data, sort_keys=True)
        return hashlib.md5(structure_str.encode()).hexdigest()
