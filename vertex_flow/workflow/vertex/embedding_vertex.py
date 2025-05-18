from typing import Dict, Any, Callable, TypeVar, List
from vertex_flow.workflow.vertex import Vertex
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.embedding import TextEmbeddingProvider
from vertex_flow.utils.logger import LoggerUtil

# import fake interface
from .vertex import WorkflowContext

logging = LoggerUtil.get_logger()

T = TypeVar("T")  # 泛型类型变量


class EmbeddingVertex(Vertex[T]):
    """嵌入顶点，有一个输入和一个输出"""

    def __init__(
        self,
        id: str,
        name: str = None,
        task: Callable[[Dict[str, Any], WorkflowContext[T]], T] = None,
        params: Dict[str, Any] = None,
        variables: List[Dict[str, str]] = None,
        embedding_provider: TextEmbeddingProvider = None,
    ):
        super().__init__(
            id=id,
            name=name,
            task_type="EMBEDDING",
            task=task,
            params=params,
            variables=variables,
        )
        self.embedding_provider: TextEmbeddingProvider = embedding_provider

    def __get_state__(self):
        data = super().__get_state__()
        if self.embedding_provider:
            data["embedding_provider"] = self.embedding_provider.__get_state__()
        return data

    def initialize_embedding_provider(self, service: VertexFlowService = None):
        """根据服务配置初始化嵌入提供者"""
        if not self.embedding_provider:
            logging.info("Initializing embedding provider...")
            if service:
                self.embedding_provider = service.get_embedding()
        else:
            logging.info("Embedding provider already initialized.")

    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        """执行嵌入任务"""
        if self.embedding_provider is None:
            raise ValueError("Embedding provider must be initialized before execution.")

        local_inputs = self.resolve_dependencies(inputs=inputs)
        if not local_inputs:
            raise ValueError("Inputs are required for embedding.")

        # 获取输入文本
        text = local_inputs.get("text")
        logging.info(f"inputs : {local_inputs}")
        if not text:
            raise ValueError("Input 'text' is required for embedding.")

        # 执行嵌入
        try:
            embeddings = self.embedding_provider.embedding(text)
            self.output = embeddings
            logging.debug(f"Embedding vertex task output {self.output}.")
        except Exception as ex:
            logging.warning(f"Embedding running exception: {ex}")
            raise ex
