import argparse
import json
import threading
import traceback
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.app.finance_message_workflow import create_finance_message_workflow
from vertex_flow.workflow.constants import (
    CONTENT_KEY,
    ENABLE_REASONING_KEY,
    ENABLE_STREAM,
    ERROR_KEY,
    MESSAGE_KEY,
    MESSAGE_TYPE_END,
    MESSAGE_TYPE_ERROR,
    MESSAGE_TYPE_REGULAR,
    OUTPUT_KEY,
    SHOW_REASONING_KEY,
    SYSTEM,
    TYPE_KEY,
    USER,
    VERTEX_ID_KEY,
)
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.dify_workflow import get_dify_workflow_instances
from vertex_flow.workflow.event_channel import EventType
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.tools.functions import FunctionTool
from vertex_flow.workflow.utils import default_config_path
from vertex_flow.workflow.workflow import Any, LLMVertex, SinkVertex, SourceVertex, Workflow
from vertex_flow.workflow.workflow_instance import WorkflowInstance

# MCP相关导入
try:
    from vertex_flow.workflow.mcp_manager import get_mcp_manager
    from vertex_flow.workflow.vertex.mcp_llm_vertex import MCPLLMVertex

    MCP_AVAILABLE = True
except ImportError as e:
    LoggerUtil.get_logger(__name__).warning(f"MCP functionality not available: {e}")
    MCPLLMVertex = None
    get_mcp_manager = None
    MCP_AVAILABLE = False

logger = LoggerUtil.get_logger(__name__)

vertex_flow = FastAPI(title="Vertex Flow API", version="1.0.0")

# 全局变量
dify_workflow_instances = {}
workflow_instances = {}  # 存储workflow实例


class WorkflowInput(BaseModel):
    workflow_name: str
    env_vars: Dict[str, Any] = {}  # 环境变量，用于模板替换
    user_vars: Dict[str, Any] = {}  # 用户变量，用于模板替换
    content: str = ""  # 用户输入内容
    image_url: Optional[str] = None  # 图片URL，支持多模态输入
    stream: bool = False  # 是否启用流式输出
    enable_mcp: bool = True  # 是否启用MCP功能

    # LLM配置参数（与user_vars分离）
    system_prompt: Optional[str] = None  # 系统提示词
    enable_reasoning: bool = False  # 是否启用推理过程
    show_reasoning: bool = True  # 是否显示推理过程
    temperature: Optional[float] = None  # 温度参数
    max_tokens: Optional[int] = None  # 最大token数
    enable_search: bool = True  # 新增：通义千问联网搜索增强，默认为True


class WorkflowOutput(BaseModel):
    output: Any
    status: bool = False
    message: str = ""
    vertices_status: Dict[str, Any] = {}
    token_usage: Dict[str, Any] = {}  # 添加token使用统计
    total_token_usage: Dict[str, Any] = {}  # 添加总token使用统计（多轮对话）


class WorkflowInstanceManager:
    """管理workflow实例，避免重复运行"""

    def __init__(self):
        self.instances = {}

    def create_instance(self, workflow: Workflow, input_data: Dict[str, Any] = None) -> WorkflowInstance:
        """创建新的workflow实例"""
        # 创建workflow模板数据
        workflow_template = {
            "id": f"workflow_{len(self.instances)}",
            "name": "Dynamic Workflow",
            "nodes": [],
            "edges": [],
        }

        # 创建WorkflowInstance
        instance = WorkflowInstance(workflow_template, input_data, None)
        instance.workflow_obj = workflow  # 直接设置workflow对象

        # 存储实例
        self.instances[instance.id] = instance

        return instance

    def execute_instance(self, workflow: Workflow, input_data: Dict[str, Any] = None, stream: bool = False):
        """执行workflow实例"""
        # 创建新实例
        instance = self.create_instance(workflow, input_data)

        try:
            # 直接执行workflow对象，而不是通过WorkflowInstance的execute方法
            if stream:
                # 流式执行
                return instance.workflow_obj.execute_workflow(input_data, stream=True)
            else:
                # 普通执行
                result = instance.workflow_obj.execute_workflow(input_data, stream=False)
                # 收集输出
                instance.output_data = instance.workflow_obj.context.get_outputs()
                instance.status = "completed"
                return instance.output_data
        except Exception as e:
            logger.error(f"Failed to execute workflow instance: {e}")
            instance.status = "failed"
            instance.error_message = str(e)
            raise


# 创建全局的WorkflowInstanceManager
workflow_instance_manager = WorkflowInstanceManager()


# 添加全局异常处理器
@vertex_flow.exception_handler(Exception)
async def custom_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error.",
        },
    )


@vertex_flow.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


@vertex_flow.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=422, content={"message": f"Validation error: {exc}"})


vertex_service = None


def check_mcp_availability():
    """检查MCP功能是否可用"""
    if not MCP_AVAILABLE:
        return False, "MCP modules not available"

    try:
        global vertex_service
        if vertex_service and vertex_service.is_mcp_enabled():
            return True, "MCP is available and enabled"
        else:
            return False, "MCP is not enabled in configuration"
    except Exception as e:
        return False, f"Error checking MCP status: {e}"


def create_llm_vertex(input_data: WorkflowInput, chatmodel, function_tools: List[FunctionTool]):
    """创建LLM Vertex，根据MCP开关选择类型，支持多模态输入"""

    # 构建用户消息，支持多模态
    user_messages = []

    # 如果有图片URL，创建多模态消息
    if input_data.image_url:
        if input_data.content and input_data.content.strip():
            # 有文本内容，创建多模态消息
            multimodal_content = [
                {"type": "text", "text": input_data.content},
                {"type": "image_url", "image_url": {"url": input_data.image_url}},
            ]
            user_messages = [multimodal_content]
        else:
            # 只有图片，创建纯图片消息
            multimodal_content = [{"type": "image_url", "image_url": {"url": input_data.image_url}}]
            user_messages = [multimodal_content]
    else:
        # 只有文本内容
        if input_data.content and input_data.content.strip():
            user_messages = [input_data.content]
        else:
            # 如果既没有文本也没有图片，使用默认消息
            user_messages = ["请帮助我。"]

    # 构建LLM参数
    llm_params = {
        "model": chatmodel,
        SYSTEM: input_data.system_prompt or "你是一个热情的聊天机器人。",
        USER: user_messages,
        ENABLE_STREAM: input_data.stream,
        ENABLE_REASONING_KEY: input_data.enable_reasoning,
        SHOW_REASONING_KEY: input_data.show_reasoning,
    }

    # 添加可选的LLM参数
    if input_data.temperature is not None:
        llm_params["temperature"] = input_data.temperature
    if input_data.max_tokens is not None:
        llm_params["max_tokens"] = input_data.max_tokens
    llm_params["enable_search"] = input_data.enable_search

    # 检查是否启用MCP
    if input_data.enable_mcp:
        mcp_available, mcp_message = check_mcp_availability()
        logger.info(f"MCP status: {mcp_message}")

        if mcp_available and MCPLLMVertex:
            try:
                # 创建MCP增强的LLM Vertex
                logger.info("Creating MCP-enhanced LLM Vertex")
                mcp_params = llm_params.copy()
                mcp_params.update(
                    {
                        # MCP相关参数
                        "mcp_enabled": True,
                        "mcp_context_enabled": True,  # 自动包含MCP上下文
                        "mcp_tools_enabled": True,  # 启用MCP工具调用
                        "mcp_prompts_enabled": True,  # 启用MCP提示
                    }
                )

                llm_vertex = MCPLLMVertex(
                    id="llm",
                    params=mcp_params,
                    tools=function_tools,
                )

                # 添加MCP状态信息到日志
                try:
                    mcp_manager = get_mcp_manager()
                    if mcp_manager:
                        connected_clients = mcp_manager.get_connected_clients()
                        logger.info(f"MCP clients connected: {connected_clients}")
                except Exception as e:
                    logger.warning(f"Could not get MCP manager status: {e}")

                return llm_vertex, "MCP-enhanced LLM Vertex created successfully"

            except Exception as e:
                logger.error(f"Failed to create MCP LLM Vertex: {e}")
                logger.info("Falling back to standard LLM Vertex")
        else:
            logger.warning(f"MCP requested but not available: {mcp_message}")

    # 创建标准LLM Vertex（默认或fallback）
    logger.info("Creating standard LLM Vertex")
    llm_vertex = LLMVertex(
        id="llm",
        params=llm_params,
        tools=function_tools,
    )

    mcp_status = "MCP not requested" if not input_data.enable_mcp else "MCP fallback to standard vertex"
    return llm_vertex, mcp_status


def get_default_workflow(input_data):
    global vertex_service
    vertex_service = vertex_service or VertexFlowService(chatmodel_config)
    data = input_data.dict()
    # 创建上下文
    context = WorkflowContext(input_data.env_vars)

    # 创建工作流
    workflow = Workflow(context)

    def add_func(inputs, context=None):
        a = inputs.get("a", 0)
        b = inputs.get("b", 0)
        logger.info(f"add function a={a}, b={b}")
        return {"result": a + b}

    def echo_func(inputs, context=None):
        logger.info(f"echo function msg={inputs}")
        msg = inputs.get("msg", "")
        return {"echo": msg}

    def base1234_convert_func(inputs, context=None):
        """
        将十进制整数转换为1234进制字符串，或将1234进制字符串转换为十进制整数。
        输入参数：
          - value: 要转换的值（int 或 str）
          - direction: 'to1234'（十进制转1234进制）或 'to10'（1234进制转十进制）
        """
        value = inputs.get("value")
        direction = inputs.get("direction", "to1234")
        digits = "1234"
        if direction == "to1234":
            try:
                n = int(value)
                if n == 0:
                    return {"result": "1"}
                res = ""
                while n > 0:
                    res = digits[n % 4] + res
                    n //= 4
                return {"result": res + "XXX"}
            except Exception as e:
                return {"error": str(e)}
        elif direction == "to10":
            try:
                s = str(value)
                n = 0
                for c in s:
                    n = n * 4 + (digits.index(c))
                return {"result": n}
            except Exception as e:
                return {"error": str(e)}
        else:
            return {"error": 'direction must be "to1234" or "to10"'}

    function_tools = [
        FunctionTool(
            name="add",
            description="两个数字相加，返回它们的和。",
            func=add_func,
            schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "第一个数字"},
                    "b": {"type": "number", "description": "第二个数字"},
                },
                "required": ["a", "b"],
            },
        ),
        FunctionTool(
            name="echo",
            description="回显输入的字符串。",
            func=echo_func,
            schema={
                "type": "object",
                "properties": {"msg": {"type": "string", "description": "要回显的内容"}},
                "required": ["msg"],
            },
        ),
        FunctionTool(
            name="base1234_convert",
            description="十进制与1234进制互转。direction为'to1234'时将十进制整数转为1234进制字符串，为'to10'时将1234进制字符串转为十进制整数。",
            func=base1234_convert_func,
            schema={
                "type": "object",
                "properties": {
                    "value": {
                        "type": "string",
                        "description": "要转换的值，整数或1234进制字符串",
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["to1234", "to10"],
                        "description": "转换方向",
                    },
                },
                "required": ["value", "direction"],
            },
        ),
    ]

    # 创建顶点 - 支持多模态输入
    def source_task(inputs, context=None):
        # 构建多模态输入数据
        input_data_dict = {
            "content": input_data.content,
            "image_url": input_data.image_url,
            **data.get("user_vars", {}),
        }
        # 过滤掉None值
        return {k: v for k, v in input_data_dict.items() if v is not None}

    source = SourceVertex(id="source", task=source_task)

    # 🆕 使用新的LLM Vertex创建函数，支持MCP开关
    llm_vertex, mcp_status = create_llm_vertex(input_data, vertex_service.get_chatmodel(), function_tools)
    logger.info(f"LLM Vertex status: {mcp_status}")

    sink = SinkVertex(id="sink", task=lambda inputs, context: f"Received: {inputs['llm']}")

    # 添加顶点到工作流
    workflow.add_vertex(source)
    workflow.add_vertex(llm_vertex)
    workflow.add_vertex(sink)

    # 连接顶点
    source | llm_vertex
    llm_vertex | sink
    return workflow


# 定义一个函数来执行您希望在新线程中运行的任务
def execute_in_thread(workflow, user_vars):
    try:
        workflow.execute_workflow(user_vars, stream=True)
        logger.info("Workflow executed successfully in a separate thread.")
    except Exception as e:
        logger.error(f"Error executing workflow in thread: {e}")


# 在您的代码中创建并启动一个新线程
def execute_workflow_in_thread(workflow, user_vars):
    thread = threading.Thread(target=execute_in_thread, args=(workflow, user_vars))
    thread.start()


@vertex_flow.post("/workflow", response_model=WorkflowOutput)
async def execute_workflow_endpoint(request: Request, input_data: WorkflowInput):
    logger.info(f"request data {input_data}")

    # 🆕 记录MCP开关状态
    logger.info(f"MCP enabled: {input_data.enable_mcp}")

    # 记录多模态输入状态
    if input_data.image_url:
        logger.info(f"Multimodal input detected: text='{input_data.content}', image_url='{input_data.image_url}'")
    else:
        logger.info(f"Text-only input: '{input_data.content}'")

    workflow_name = input_data.workflow_name
    workflow: Workflow = None
    if workflow_name in dify_workflow_instances:
        logger.info("Build new workflow from graph")
        instance = dify_workflow_instances[input_data.workflow_name]
        # 根据工作流名称构建不同的workflow实例
        if input_data.workflow_name == "deep-research":
            workflow = instance["builder"]({**input_data.user_vars, **{"stream": input_data.stream}})
        elif input_data.workflow_name == "finance-message":
            workflow = instance["builder"](
                {
                    "content": input_data.content,
                    "image_url": input_data.image_url,  # 添加图片URL支持
                    "env_vars": input_data.env_vars,
                    "user_vars": input_data.user_vars,
                    "stream": input_data.stream,
                }
            )
        else:
            workflow = instance["builder"](instance["graph"])
    else:
        logger.info("Build new workflow from code")
        workflow = get_default_workflow(input_data=input_data)

    if input_data.stream:
        # 使用WorkflowInstanceManager创建新实例进行流式执行
        workflow_instance = workflow_instance_manager.create_instance(workflow, input_data.user_vars)

        execute_workflow_in_thread(workflow_instance.workflow_obj, input_data.user_vars)

        async def result_generator():
            try:
                async for result in workflow_instance.workflow_obj.astream([EventType.MESSAGES, EventType.UPDATES]):
                    logger.info(f"workflow result {result}")
                    if result.get(VERTEX_ID_KEY):
                        # 统一处理不同的消息键名
                        output_content = result.get(CONTENT_KEY) or result.get(MESSAGE_KEY) or ""
                        # 获取消息类型，用于前端区分显示
                        message_type = result.get(TYPE_KEY, MESSAGE_TYPE_REGULAR)

                        # 检查是否为流式结束消息，附加usage
                        if message_type == MESSAGE_TYPE_END:
                            token_usage = {}
                            total_token_usage = {}
                            try:
                                if hasattr(workflow, "vertices"):
                                    for vertex in workflow.vertices.values():
                                        if hasattr(vertex, "task_type") and vertex.task_type == "LLM":
                                            if hasattr(vertex, "token_usage") and vertex.token_usage:
                                                token_usage = vertex.token_usage
                                            if hasattr(vertex, "get_total_usage"):
                                                total_token_usage = vertex.get_total_usage()
                                            break
                            except Exception as e:
                                logger.warning(f"Could not collect token usage: {e}")
                            yield json.dumps(
                                {
                                    VERTEX_ID_KEY: result[VERTEX_ID_KEY],
                                    OUTPUT_KEY: output_content,
                                    TYPE_KEY: message_type,
                                    "status": True,
                                    "token_usage": token_usage,
                                    "total_token_usage": total_token_usage,
                                },
                                ensure_ascii=False,
                            ) + "\n"
                        else:
                            yield json.dumps(
                                {
                                    VERTEX_ID_KEY: result[VERTEX_ID_KEY],
                                    OUTPUT_KEY: output_content,
                                    TYPE_KEY: message_type,
                                    "status": True,
                                },
                                ensure_ascii=False,
                            ) + "\n"
            except BaseException as e:
                logger.info(f"workflow run exception {e}")
                traceback.print_exc()
                yield json.dumps(
                    {
                        OUTPUT_KEY: ERROR_KEY,
                        "status": False,
                        MESSAGE_KEY: str(e),
                        "vertices_status": workflow_instance.workflow_obj.status(),
                    }
                ) + "\n"

        return StreamingResponse(
            result_generator(),
            media_type="application/json",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )
    else:
        # 普通响应
        try:
            # 使用WorkflowInstanceManager执行，避免重复运行
            result = workflow_instance_manager.execute_instance(workflow, input_data.user_vars, stream=False)

            # 收集token统计信息
            token_usage = {}
            total_token_usage = {}
            try:
                # 直接从workflow对象中获取LLM vertex的token统计
                if hasattr(workflow, "vertices"):
                    for vertex in workflow.vertices.values():
                        if hasattr(vertex, "task_type") and vertex.task_type == "LLM":
                            if hasattr(vertex, "token_usage") and vertex.token_usage:
                                token_usage = vertex.token_usage
                            if hasattr(vertex, "get_total_usage"):
                                total_token_usage = vertex.get_total_usage()
                            # 新增日志
                            logger.info(f"LLM Vertex token usage: {token_usage}, total usage: {total_token_usage}")
                            break
            except Exception as e:
                logger.warning(f"Could not collect token usage: {e}")

            return WorkflowOutput(
                output=result,
                status=True,
                message="Workflow executed successfully",
                vertices_status={},
                token_usage=token_usage,
                total_token_usage=total_token_usage,
            )
        except BaseException as e:
            logger.info(f"workflow run exception {e}")
            traceback.print_exc()
            return {
                OUTPUT_KEY: ERROR_KEY,
                "status": False,
                MESSAGE_KEY: str(e),
                "vertices_status": workflow.status(),
            }


# 🆕 新增MCP状态检查端点
@vertex_flow.get("/mcp/status")
async def get_mcp_status():
    """获取MCP状态信息"""
    mcp_available, mcp_message = check_mcp_availability()

    status_info = {"mcp_available": mcp_available, "message": mcp_message, "modules_loaded": MCP_AVAILABLE}

    if mcp_available:
        try:
            mcp_manager = get_mcp_manager()
            if mcp_manager:
                connected_clients = mcp_manager.get_connected_clients()
                status_info["connected_clients"] = connected_clients
                status_info["client_count"] = len(connected_clients)
        except Exception as e:
            status_info["manager_error"] = str(e)

    return status_info


@vertex_flow.get("/workflow", response_model=WorkflowOutput)
async def execute_workflow_endpoint(request: Request):
    workflow_name = request.query_params.get("name")
    if workflow_name and workflow_name in dify_workflow_instances:
        return {
            "output": f"{dify_workflow_instances[workflow_name].get('graph')}",
            "status": True,
        }
    else:
        return {"output": list(dify_workflow_instances.keys()), "status": True}


class VectorSinkData(BaseModel):
    user_id: str
    vertexflow_id: str
    content: str
    options: Dict[str, Any]


class VectorSinkResponse(BaseModel):
    output: Any
    status: bool = False
    message: str = ""


class VectorSearchData(BaseModel):
    user_id: str
    vertexflow_id: str
    content: str
    options: Dict[str, Any]


class VectorSearchResponse(BaseModel):
    content: List[str]
    status: bool = False
    message: str = ""


@vertex_flow.post("/vector/ingest", response_model=VectorSinkData)
async def execute_workflow_endpoint(request: Request):
    return VectorSinkResponse(output="hello world")


@vertex_flow.post("/vector/search", response_model=VectorSearchData)
async def execute_workflow_endpoint(request: Request):
    return VectorSearchData(output="hello world")


chatmodel_config = None


@vertex_flow.on_event("startup")
async def on_startup():
    logger.info(f"Application startup, config file : ${chatmodel_config}")
    vertex_service = VertexFlowService(chatmodel_config) if chatmodel_config is not None else VertexFlowService()
    global dify_workflow_instances
    dify_workflow_instances = get_dify_workflow_instances(vertex_service=vertex_service)
    # 注册finance-message workflow
    dify_workflow_instances["finance-message"] = {
        "builder": create_finance_message_workflow(vertex_service),
        "graph": None,
    }
    logger.info(f"Application startup, finished, loaded {len(dify_workflow_instances)}...")


def main():
    parser = argparse.ArgumentParser(description="vertex-flow app")

    # 添加命令行参数
    parser.add_argument(
        "--config",
        default=None,  # 改为None，让VertexFlowService自动选择配置文件
        help="指定模型与请求配置",
    )

    # 解析命令行参数
    args = parser.parse_args()
    global chatmodel_config
    chatmodel_config = args.config
    global vertex_service

    vertex_service = VertexFlowService(chatmodel_config)

    import uvicorn

    uvicorn.run(
        "vertex_flow.workflow.app.app:vertex_flow",
        host=vertex_service.get_service_host(),
        port=vertex_service.get_service_port(),
        reload=True,
    )


if __name__ == "__main__":
    main()
