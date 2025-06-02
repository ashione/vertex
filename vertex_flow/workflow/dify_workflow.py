# -*- coding: utf-8 -*-
from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.edge import (
    Condition,
    Edge,
)
from vertex_flow.workflow.rag_config import read_yaml_config
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.vertex import (
    CodeVertex,
    IfCase,
    IfElseVertex,
    LLMVertex,
    SinkVertex,
    SourceVertex,
)
from vertex_flow.workflow.workflow import (
    Any,
    Dict,
)
from vertex_flow.workflow.workflow import Edge as WorkflowEdge
from vertex_flow.workflow.workflow import (
    List,
    Workflow,
    WorkflowContext,
)

logger = LoggerUtil.get_logger()


class Node:
    def __init__(self, node_id, data):
        self.id = node_id
        self.title = data.get("data", {}).get("title", "")
        self.type = data.get("data", {}).get("type", "")
        self.selected = data.get("selected", False)
        self.connections = []
        self.llm_model = data.get("data", {}).get("model", {})
        self.variables = None

        self.extract_variables(data.get("data", {}).get("variables", []))
        self.extract_output_variables(data.get("data", {}).get("outputs", []))

    def extract_variables(self, variables):
        """Extracts and sets the variables from start node."""
        self.variables = variables

    def extract_output_variables(self, variables):
        """Extracts and sets the variables from start node."""
        self.output_variables = variables

    def to_workflow_variable(self, var_item: Dict[str, Any]):
        return {
            "source_scope": var_item["value_selector"][0],
            "source_var": var_item["value_selector"][1],
            "local_var": var_item["variable"] or var_item["value_selector"][1],
        }

    def to_workflow_variables(self, variables=None):
        return [self.to_workflow_variable(var_item) for var_item in variables or self.variables]

    def add_connection(self, edge):
        self.connections.append(edge)

    def __repr__(self):
        return (
            f"Node({self.id}, title={self.title}, type={self.type}, "
            # f"system_prompt={self.system_prompt[:20]}..., "
            # f"user_prompt={self.user_prompt[:20]}..., "
            f"variables={self.variables})"
        )


class SourceNode(Node):
    def __init__(self, node_id, data):
        super().__init__(node_id, data)
        self.type = "source"

    def to_workflow_input_variables(self):
        if self.variables:
            return [
                {
                    "source_var": variable["label"],
                    "local_var": variable["label"],
                    "required": variable["required"],
                }
                for variable in self.variables
            ]

    def __repr__(self):
        return f"SourceNode({self.id}, title={self.title}, " f"variables={self.variables})"


class SinkNode(Node):
    def __init__(self, node_id, data):
        super().__init__(node_id, data)
        self.type = "sink"

    def __repr__(self):
        return f"SinkNode({self.id}, title={self.title}, variables : {self.output_variables})"


class LLMNode(Node):
    def __init__(self, node_id, data):
        super().__init__(node_id, data)
        self.type = "llm"
        self.system_prompt = None
        self.user_prompt = None
        # Extract prompts if they exist
        self.extract_prompts(data.get("data", {}).get("prompt_template", []))
        self.model_conf = data.get("data", {}).get("model", {})

    def extract_prompts(self, prompt_template):
        """Extracts and sets the system and user prompts."""
        for item in prompt_template:
            if item.get("role") == "system":
                self.system_prompt = item.get("text")
            elif item.get("role") == "user":
                self.user_prompt = item.get("text")

    def __repr__(self):
        return (
            f"LLMNode({self.id}, title={self.title}, "
            f"model_conf({self.model_conf}, "
            f"system_prompt={self.system_prompt[:20]}..., "
            f"user_prompt={self.user_prompt[:20]}...)"
            f"llm_model={self.llm_model}"
        )


class CodeNode(Node):
    def __init__(self, node_id, data):
        super().__init__(node_id, data)
        self.type = "code"
        self.code_content = data.get("data", {}).get("code", "")

    def __repr__(self):
        return f"Code({self.id}, title={self.title}, " f"code_content={self.code_content}"


class IfElseNode(Node):
    def __init__(self, node_id, data):
        super().__init__(node_id, data)
        self.type = "if-else"
        self._cases = data.get("data", {}).get("cases", {})
        self.extract_conditions()

    def extract_conditions(self):
        if not self._cases:
            raise ValueError("At lest one case given.")
        self.cases: List[IfCase] = []
        for case_instance in self._cases:
            logical_operator = case_instance["logical_operator"]
            conditions = [
                {
                    "variable_selector": {
                        "source_scope": condition["variable_selector"][0],
                        "source_var": condition["variable_selector"][1],
                        "local_var": condition["variable_selector"][1],
                    },
                    "value": condition["value"],
                    "operator": condition["comparison_operator"],
                }
                for condition in case_instance["conditions"]
            ]
            self.cases.append(
                IfCase(
                    conditions=conditions,
                    logical_operator=logical_operator,
                    id=case_instance["case_id"],
                )
            )

    def __repr__(self):
        return f"IfElse({self.id}, title={self.title} ," f"cases={self.cases}, "


class Edge:
    def __init__(self, edge_id, source, target, data=None):
        self.id = edge_id
        self.source = source
        self.target = target
        self.data = data or {}
        self.type = self.data.get("type", "")
        self.source_handle = self.data.get("sourceHandle", "source")

    def connect_nodes(self, source_node, target_node):
        source_node.add_connection(self)
        target_node.add_connection(self)

    def __repr__(self):
        return f"Edge({self.id}, Source: {self.source.id}, Target: {self.target.id}, Type: {self.type}, handle :{self.source_handle})"


class Graph:
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.source_nodes = {}
        self.sink_nodes = {}
        self.llm_nodes = {}
        self.env_variables = {}

    def build_graph(self, yaml_config):
        self.env_variables = {
            env_variable["name"]: env_variable["value"]
            for env_variable in yaml_config["workflow"]["environment_variables"]
        }
        # 解析节点
        for node_data in yaml_config["workflow"]["graph"]["nodes"]:
            node_id = node_data.get("id")
            if node_data["data"].get("type") == "start":
                self.nodes[node_id] = SourceNode(node_id, node_data)
            elif node_data["data"].get("type") == "end":
                self.nodes[node_id] = SinkNode(node_id, node_data)
            elif node_data["data"].get("type") == "llm":
                self.nodes[node_id] = LLMNode(node_id, node_data)
            elif node_data["data"].get("type") == "code":
                self.nodes[node_id] = CodeNode(node_id, node_data)
            elif node_data["data"].get("type") == "if-else":
                self.nodes[node_id] = IfElseNode(node_id, node_data)
            else:
                self.nodes[node_id] = Node(node_id, node_data)

        # 解析边
        for edge_data in yaml_config["workflow"]["graph"]["edges"]:
            edge_id = edge_data.get("id")
            source_node = self.nodes.get(edge_data["source"])
            target_node = self.nodes.get(edge_data["target"])
            if source_node is not None and target_node is not None:
                new_edge = Edge(edge_id, source_node, target_node, edge_data)
                new_edge.connect_nodes(source_node, target_node)
                self.edges.append(new_edge)
                if source_node.type == "source":
                    self.source_nodes[source_node.id] = source_node
                elif source_node.type == "sink":
                    self.sink_nodes[source_node.id] = source_node
                elif source_node.type == "llm":
                    self.llm_nodes[source_node.id] = source_node

    def get_nodes(self):
        return list(self.nodes.values())

    def get_edges(self):
        return self.edges

    def get_source_nodes(self):
        return list(self.source_nodes.values())

    def get_sink_nodes(self):
        return list(self.sink_nodes.values())

    def get_llm_nodes(self):
        return list(self.llm_nodes.values())

    def extract_variables(self, inputs: Dict[str, Any], context: WorkflowContext):
        logger.info(f"source inputs variables : {inputs}")
        return inputs

    def to_workflow(self, vertex_service: VertexFlowService = None) -> Workflow:
        """将Graph转换为Workflow"""
        context = WorkflowContext(self.env_variables)
        workflow = Workflow(context=context)

        vertex_service = vertex_service or VertexFlowService()

        # 将Graph中的节点转换为Workflow中的顶点
        for node in self.get_nodes():
            if node.type.upper() == "SOURCE":
                vertex = SourceVertex(
                    id=node.id,
                    name=node.title,
                    variables=node.to_workflow_input_variables(),
                )
            elif node.type.upper() == "LLM":

                vertex = LLMVertex(
                    id=node.id,
                    name=node.title,
                    params={
                        "model": vertex_service.get_chatmodel_by_provider(
                            provider=node.model_conf["provider"],
                            name=node.model_conf["name"],
                        ),
                        "system": node.system_prompt,
                        "user": [node.user_prompt],
                        "postprocess": source_post_process_func,
                    },
                )
            elif node.type.upper() == "SINK":
                vertex = SinkVertex(
                    id=node.id,
                    name=node.title,
                    variables=node.to_workflow_variables(node.output_variables),
                )
            elif node.type.upper() == "IF-ELSE":
                vertex = IfElseVertex(
                    id=node.id,
                    name=node.title,
                    cases=node.cases,
                )
            elif node.type.upper() == "CODE":
                vertex = CodeVertex(
                    id=node.id,
                    name=node.title,
                    params={
                        "code": node.code_content,
                    },
                )
                for variable in node.to_workflow_variables():
                    vertex.add_variable(**variable)
            else:
                raise ValueError(f"Unsupported node type: {node.type}")

            workflow.ensure_vertex_added(vertex)

        # 将Graph中的边转换为Workflow中的边
        for edge in self.get_edges():
            source_vertex = workflow.vertices[edge.source.id]
            target_vertex = workflow.vertices[edge.target.id]
            if isinstance(edge.source, IfElseNode):
                source_vertex.to(target_vertex, Condition(id=edge.source_handle.lower()))
            else:
                source_vertex | target_vertex

        return workflow

    def __repr__(self):
        return f"{self.edges}" f"{self.nodes}"


def source_post_process_func(content, inputs, context):
    return {"text": content}


def sink_func(inputs, context):
    logger.info(f"inputs.values : {inputs.values()}")
    return list(inputs.values())[0]["text"]


def print_graph(graph):
    nodes = graph.get_nodes()
    edges = graph.get_edges()
    source_nodes = graph.get_source_nodes()
    sink_nodes = graph.get_sink_nodes()
    llm_nodes = graph.get_llm_nodes()

    logger.info("Nodes:")
    for node in nodes:
        logger.info(f"Node ID: {node.id}, Title: {node.title}, Type: {node.type}")
        if isinstance(node, SourceNode):
            logger.info(f"Variables: {node.variables}")
        elif isinstance(node, SinkNode):
            logger.info("This is a SinkNode.")
        elif isinstance(node, LLMNode):
            logger.debug(f"System Prompt: {node.system_prompt}")
            logger.debug(f"User Prompt: {node.user_prompt}")
            logger.debug(f"LLM model: {node.llm_model}")
        elif isinstance(node, CodeNode):
            logger.info(f"CodeNode Variables: {node.variables}")
        elif isinstance(node, IfElseNode):
            logger.info(f"IfElseNode : {node}")
        else:
            logger.info(f"Undefined node type, {node}")
        logger.info("Connections:")
        for edge in node.connections:
            logger.info(f"- Edge ID: {edge.id}, Source: {edge.source.id}, Target: {edge.target.id}, Type: {edge.type}")

    logger.info("\nEdges:")
    for edge in edges:
        logger.info(edge)

    logger.info("\nSource Nodes:")
    for source_node in source_nodes:
        logger.info(f"SourceNode ID: {source_node.id}, Title: {source_node.title}, Variables: {source_node.variables}")

    logger.info("\nSink Nodes:")
    for sink_node in sink_nodes:
        logger.info(f"SinkNode ID: {sink_node.id}, Title: {sink_node.title}")

    logger.info("\nLLM Nodes:")
    for llm_node in llm_nodes:
        logger.info(
            f"LLMNode ID: {llm_node.id}, Title: {llm_node.title}, System Prompt: {llm_node.system_prompt[:20]}..., User Prompt: {llm_node.user_prompt[:20]}..."
        )


instances = None


def get_dify_workflow_instances(
    vertex_service: VertexFlowService,
) -> Dict[str, Dict[str, Any]]:
    global instances
    if instances is not None:
        return instances

    instances = {}
    dify_instances_config = vertex_service.get_dify_workflow_instances()
    logger.info(f"dify instance config : {dify_instances_config}")
    for instance_config in dify_instances_config:
        graph = Graph()
        yaml_config = read_yaml_config(instance_config["path"])
        graph.build_graph(yaml_config=yaml_config)

        def build_workflow(graph):
            # 打印图信息
            print_graph(graph)
            workflow = graph.to_workflow(vertex_service=vertex_service)
            workflow.show_graph(include_dependencies=True)
            return workflow

        instances[instance_config["name"]] = {"graph": graph, "builder": build_workflow}
    return instances


def run_dify_workflow(yaml_file, sources_input):
    # 解析YAML字符串
    yaml_config = read_yaml_config(yaml_file)
    # 创建 Graph 实例并构建图
    graph = Graph()
    graph.build_graph(yaml_config)

    # 打印图信息G
    print_graph(graph)
    workflow = graph.to_workflow()
    vertex_flow.workflow.show_graph(include_dependencies=True)
    if vertex_flow.workflow.execute_workflow(source_inputs=sources_input):
        logger.info(f"{vertex_flow.workflow.result()}")
    return vertex_flow.workflow.result(), vertex_flow.workflow.status()


if __name__ == "__main__":
    yaml_file = "config/content_v2.yml"
    sources_input = {
        "SubTitle": "第四章 技术方案  第一节 技术方案概述    二、技术方案内容 ",
        "TableOfContent": "第一章 项目概述 \n第一节 项目背景 \n一、项目介绍 \n二、项目投标方 \n三、可行性分析 \n四、项目目标 \n五、项目意义 \n六、项目范围 \n七、项目预算 \n八、项目时间表 \n第二章 项目需求分析 \n第一节 项目需求概述 \n一、项目需求来源 \n二、项目需求内容 \n三、项目需求目标 \n四、项目需求标准 \n五、项目需求变更管理 \n六、项目需求优先级 \n第三章 投标人介绍 \n第一节 企业概况 \n一、企业基本信息 \n二、企业资质 \n三、企业业绩 \n四、企业规模 \n五、企业团队 \n六、企业优势 \n第四章 技术方案 \n第一节 技术方案概述 \n一、技术方案目标 \n二、技术方案内容 \n三、技术方案实施计划 \n四、技术方案创新点 \n五、技术方案可行性分析 \n六、技术方案风险控制 \n第五章 施工组织设计 \n第一节 施工组织架构 \n一、施工组织架构图 \n二、施工队伍组成 \n三、施工人员配备 \n四、施工设备配置 \n五、施工进度计划 \n六、施工质量保证措施 \n第六章 成本预算规划 \n第一节 成本预算概述 \n一、成本预算编制依据 \n二、成本预算内容 \n三、成本预算控制措施 \n四、成本预算调整机制 \n五、成本预算分析 \n六、成本预算风险 \n第七章 进度安排 \n第一节 进度计划概述 \n一、进度计划编制依据 \n二、进度计划内容 \n三、进度计划调整机制 \n四、进度计划风险 \n五、进度计划监控措施 \n六、进度计划保障措施 \n第八章 质量保证措施 \n第一节 质量保证体系 \n一、质量保证体系概述 \n二、质量保证措施 \n三、质量检查与验收 \n四、质量改进措施 \n五、质量风险控制 \n六、质量保证承诺 \n第九章 安全保证措施 \n第一节 安全保证体系 \n一、安全保证体系概述 \n二、安全保证措施 \n三、安全检查与验收 \n四、安全事故处理 \n五、安全风险控制 \n六、安全保证承诺 \n第十章 环境保护措施 \n第一节 环境保护体系 \n一、环境保护体系概述 \n二、环境保护措施 \n三、环境检查与验收 \n四、环境风险控制 \n五、环境保护承诺 \n第十一章 人员培训计划 \n第一节 培训计划概述 \n一、培训计划目标 \n二、培训计划内容 \n三、培训计划实施 \n四、培训计划评估 \n五、培训计划风险 \n六、培训计划保障措施 \n第十二章 结束语 \n第一节 项目总结 \n一、项目实施总结 \n二、项目经验教训 \n三、项目展望 \n四、感谢致辞 \n五、联系方式 \n六、附件",
        "WordCountRequired": 5000,
        "Title": "墨玉县乡村振兴发展资金项目（二期）新建内容-工程采购",
        "BrotherSubTitle": "第四章 技术方案  第一节 技术方案概述 \n一、技术方案目标 \n三、技术方案实施计划 \n四、技术方案创新点 \n五、技术方案可行性分析 \n六、技术方案风险控制",
        "ItemCriteria": "",
    }
    run_dify_workflow(yaml_file=yaml_file, sources_input=sources_input)
