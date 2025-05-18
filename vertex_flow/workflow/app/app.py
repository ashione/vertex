import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from vertex_flow.workflow.constants import ENABLE_STREAM
from vertex_flow.workflow.utils import default_config_path
from pydantic import BaseModel
import threading
import argparse
import traceback
from vertex_flow.workflow.workflow import (
    Workflow,
    SourceVertex,
    SinkVertex,
    LLMVertex,
    WorkflowContext,
    Any,
)
from vertex_flow.workflow.service import VertexFlowService
from typing import Dict, List
from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.dify_workflow import get_dify_workflow_instances

from fastapi.responses import StreamingResponse

logger = LoggerUtil.get_logger()

vertex_flow = FastAPI()


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
    return JSONResponse(
        status_code=422, content={"message": f"Validation error: {exc}"}
    )


dify_workflow_instances = {}


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


vertex_service = None


def get_default_workflow(input_data):
    global vertex_service
    vertex_service = vertex_service or VertexFlowService(chatmodel_config)
    data = input_data.dict()
    # 创建上下文
    context = WorkflowContext(input_data.env_vars)

    # 创建工作流
    workflow = Workflow(context)

    # 创建顶点
    source = SourceVertex(
        id="source", task=lambda inputs, context: data.get("input", "Default Input")
    )
    llm = LLMVertex(
        id="llm",
        params={
            "model": vertex_service.get_chatmodel(),
            "system": "你是一个热情的聊天机器人。",
            "user": [input_data.content],
            ENABLE_STREAM : input_data.stream,
        },
    )
    sink = SinkVertex(
        id="sink", task=lambda inputs, context: f"Received: {inputs['llm']}"
    )

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
        workflow = instance["builder"](instance["graph"])
    else:
        logger.info("Build new workflow from code")
        workflow = get_default_workflow(input_data=input_data)

    if input_data.stream:

        execute_workflow_in_thread(workflow, input_data.user_vars)
        async def result_generator():
            try:
                async for result in workflow.astream("messages"):
                    logger.info(f"workflow result {result}")
                    yield json.dumps({
                        "output": result,
                        "status": True,
                        "vertices_status": workflow.status(),
                    })
            except BaseException as e:
                logger.info(f"workflow run exception {e}")
                traceback.print_exc()
                yield json.dumps({
                    "output": "error",
                    "status": False,
                    "message": str(e),
                    "vertices_status": workflow.status(),
                })

        return StreamingResponse(result_generator(), media_type="application/json")
    else:
        try:
            workflow.execute_workflow(input_data.user_vars, stream=False)
            return {
                "output": list(workflow.result().values())[0],
                "status": True,
            }
        except BaseException as e:
            logger.info(f"workflow run exception {e}")
            traceback.print_exc()
            return {
                "output": "error",
                "status": False,
                "message": str(e),
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
    vertex_service = VertexFlowService(chatmodel_config)
    global dify_workflow_instances
    dify_workflow_instances = get_dify_workflow_instances(vertex_service=vertex_service)
    logger.info(f"Application startup, finished, loaded {len(dify_workflow_instances)}...")


def main():
    parser = argparse.ArgumentParser(description="vertex-flow app")

    # 添加命令行参数
    parser.add_argument(
        "--config",
        default=default_config_path("llm.yml"),
        help="指定模型与请求配置",
    )

    # 解析命令行参数
    args = parser.parse_args()
    global chatmodel_config
    chatmodel_config= args.config
    global vertex_service

    vertex_service = VertexFlowService(chatmodel_config)

    import uvicorn

    uvicorn.run(
        vertex_flow,
        host=vertex_service.get_service_host(),
        port=vertex_service.get_service_port(),
    )

if __name__ == "__main__":
    main()