import os

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.app.ragflow import DownloadFileVertex
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.vertex import FunctionVertex, SinkVertex, SourceVertex
from vertex_flow.workflow.workflow import Workflow
from vertex_flow.workflow.workflow_manager import WorkflowSerializer

logging = LoggerUtil.get_logger()


def sink_function(inputs, context):
    logging.info(f"inputs {inputs}")
    os.remove(inputs["DOWNLOAD"]["tmpfile_path"])


def source_function(inputs, context):
    return inputs


def make_workflow() -> Workflow:
    # 创建顶点
    vertex_source = SourceVertex(
        id="SOURCE",
        task=source_function,
    )

    vertex_download = DownloadFileVertex(
        id="DOWNLOAD",
        variables=[
            {
                "source_scope": "SOURCE",
                "source_var": "url",
                "local_var": "url",
            }
        ],
    )

    vertex_sink = SinkVertex(
        id="SINK",
        task=sink_function,
    )

    # 创建 WorkflowContext
    workflow_context = WorkflowContext(env_parameters={"example_key": "example_value"})
    # 创建工作流
    workflow = Workflow(workflow_context)
    vertex_flow.workflow.add_vertex(vertex_source)
    vertex_flow.workflow.add_vertex(vertex_download)
    vertex_flow.workflow.add_vertex(vertex_sink)

    # 构建工作流图
    vertex_source | vertex_download | vertex_sink
    return workflow


if __name__ == "__main__":
    workflow = make_workflow()
    workflow.show_graph()
    WorkflowSerializer.serialize_to_yaml(workflow=workflow, file_path="workflow.yaml")

    # 执行工作流
    workflow.execute_workflow(source_inputs={"url": "https://www.baidu.com"})

    logging.info(f"rerun in workflow2")
    workflow2 = WorkflowSerializer.deserialize_from_yaml(file_path="workflow.yaml")
    workflow2.execute_workflow(source_inputs={"url": "https://www.baidu.com"})
