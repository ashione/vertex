import argparse
import json
import threading
import traceback
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.app.finance_message_workflow import create_finance_message_workflow
from vertex_flow.workflow.constants import (
    CONTENT_KEY,
    ENABLE_STREAM,
    ERROR_KEY,
    MESSAGE_KEY,
    MESSAGE_TYPE_ERROR,
    MESSAGE_TYPE_REGULAR,
    OUTPUT_KEY,
    TYPE_KEY,
    VERTEX_ID_KEY,
)
from vertex_flow.workflow.dify_workflow import get_dify_workflow_instances
from vertex_flow.workflow.event_channel import EventType
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.tools.functions import FunctionTool
from vertex_flow.workflow.utils import default_config_path
from vertex_flow.workflow.workflow import Any, LLMVertex, SinkVertex, SourceVertex, Workflow, WorkflowContext
from vertex_flow.workflow.workflow_instance import WorkflowInstance

logger = LoggerUtil.get_logger(__name__)

vertex_flow = FastAPI(title="Vertex Flow API", version="1.0.0")

# 全局变量
dify_workflow_instances = {}
workflow_instances = {}  # 存储workflow实例


class WorkflowInput(BaseModel):
    workflow_name: str
    env_vars: Dict[str, Any] = {}
    user_vars: Dict[str, Any] = {}
    content: str = ""
    stream: bool = False  # 新增参数，用于指定是否为流式模式


class WorkflowOutput(BaseModel):
    output: Any
    status: bool = False
    message: str = ""
    vertices_status: Dict[str, Any] = {}


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

    # 创建顶点
    source = SourceVertex(id="source", task=lambda inputs, context: data.get("input", "Default Input"))
    llm = LLMVertex(
        id="llm",
        params={
            "model": vertex_service.get_chatmodel(),
            "system": "你是一个热情的聊天机器人。",
            "user": [input_data.content],
            ENABLE_STREAM: input_data.stream,
        },
        tools=function_tools,  # 关键：传递function tools
    )
    sink = SinkVertex(id="sink", task=lambda inputs, context: f"Received: {inputs['llm']}")

    # 添加顶点到工作流
    workflow.add_vertex(source)
    workflow.add_vertex(llm)
    workflow.add_vertex(sink)

    # 连接顶点
    source | llm
    llm | sink
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
        try:
            # 使用WorkflowInstanceManager执行，避免重复运行
            result = workflow_instance_manager.execute_instance(workflow, input_data.user_vars, stream=False)
            return {
                "output": result,
                "status": True,
                "vertices_status": workflow.status(),
            }
        except BaseException as e:
            logger.info(f"workflow run exception {e}")
            traceback.print_exc()
            return {
                OUTPUT_KEY: ERROR_KEY,
                "status": False,
                MESSAGE_KEY: str(e),
                "vertices_status": workflow.status(),
            }


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
