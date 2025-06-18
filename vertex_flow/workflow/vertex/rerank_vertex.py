from typing import Any, Callable, Dict, List, TypeVar

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.rerank import BCERerankProvider, RerankProvider

# import fake interface
from .vertex import Vertex, WorkflowContext

logging = LoggerUtil.get_logger()

T = TypeVar("T")  # 泛型类型变量


class RerankVertex(Vertex[T]):
    """重排序顶点，有一个输入和一个输出"""

    def __init__(
        self,
        id: str,
        name: str = None,
        task: Callable[[Dict[str, Any], WorkflowContext[T]], T] = None,
        params: Dict[str, Any] = None,
        rerank_provider: RerankProvider = None,
        variables: List[Dict[str, Any]] = None,
    ):
        super().__init__(id=id, name=name, task_type="RERANK", task=task, params=params, variables=variables or [])
        self.rerank_provider: RerankProvider = rerank_provider
        # 这里还需要设置一个怎么从上层vertex拿具体对象的key。

    def initialize_rerank_provider(self, service: any = None):
        """根据服务配置初始化重排序提供者"""
        if not self.rerank_provider:
            logging.info("Initializing rerank provider...")
            if service:
                rerank_config = service.get_rerank_config()
                # 这里应该需要使用工厂方法，避免直接创建对象。
                self.rerank_provider = BCERerankProvider(
                    api_key=rerank_config["api_key"],
                    model_name=rerank_config["model_name"],
                    endpoint=rerank_config["endpoint"],
                )
            else:
                logging.warning("Service is not provided, using default rerank provider.")
        else:
            logging.info("Rerank provider already initialized.")

    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        """执行重排序任务"""
        if self.rerank_provider is None:
            raise ValueError("Rerank provider must be initialized before execution.")

        local_inputs = self.resolve_dependencies(inputs=inputs)
        if not local_inputs:
            raise ValueError("Inputs are required for reranking.")

        # 获取输入查询和文档
        query = local_inputs.get("query")
        top_n = local_inputs.get("top_n", 3)
        documents = local_inputs.get("documents")
        logging.info(f"inputs : {local_inputs}")
        if not query or not documents:
            raise ValueError("Input 'query' and 'documents' are required for reranking.")

        # 执行重排序
        try:
            reranked_documents = self.rerank_provider.rerank(query, documents, top_n)
            self.output = reranked_documents
            logging.debug(f"Rerank vertex task output {self.output}.")
        except Exception as ex:
            logging.warning(f"Rerank running exception: {ex}")
            raise ex
