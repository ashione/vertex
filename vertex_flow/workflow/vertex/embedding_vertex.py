from typing import Any, Callable, Dict, List, Optional, TypeVar

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.vertex.embedding_providers import TextEmbeddingProvider

# import fake interface
from .vertex import Vertex, WorkflowContext

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

    def initialize_embedding_provider(self, service: Any = None):
        """根据服务配置初始化嵌入提供者"""
        if not self.embedding_provider:
            logging.debug("Initializing embedding provider...")
            if service:
                self.embedding_provider = service.get_embedding()
        else:
            logging.debug("Embedding provider already initialized.")

    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        """执行嵌入任务"""
        if self.embedding_provider is None:
            raise ValueError("Embedding provider must be initialized before execution.")

        local_inputs = self.resolve_dependencies(inputs=inputs)
        if not local_inputs:
            raise ValueError("Inputs are required for embedding.")

        # 获取输入文本或文档
        text = local_inputs.get("text")
        docs = local_inputs.get("docs")
        
        # 减少日志输出，只记录关键信息
        if docs and isinstance(docs, list):
            logging.info(f"开始处理 {len(docs)} 个文档的嵌入生成")
        elif text:
            logging.debug("开始处理单个文本的嵌入生成")
        
        # 处理文档对象列表
        if docs and isinstance(docs, list):
            embeddings_list = []
            processed_count = 0
            error_count = 0
            
            for doc in docs:
                if isinstance(doc, dict) and 'content' in doc:
                    # 文档对象格式
                    content = doc['content']
                elif isinstance(doc, str):
                    # 直接文本
                    content = doc
                else:
                    logging.warning(f"跳过无效文档: {doc}")
                    error_count += 1
                    continue
                
                try:
                    embedding = self.embedding_provider.embedding(content)
                    embeddings_list.append({
                        'id': doc.get('id', f"doc_{len(embeddings_list)}"),
                        'content': content,
                        'embedding': embedding,
                        'metadata': doc.get('metadata', {})
                    })
                    processed_count += 1
                except Exception as e:
                    logging.error(f"文档嵌入失败: {e}")
                    error_count += 1
                    continue
            
            self.output = {"embeddings": embeddings_list}
            logging.info(f"嵌入生成完成: 成功 {processed_count} 个，失败 {error_count} 个")
            
        elif text:
            # 处理单个文本
            try:
                embeddings = self.embedding_provider.embedding(text)
                self.output = {"embeddings": embeddings}
                logging.debug("单个文本嵌入生成完成")
            except Exception as ex:
                logging.error(f"嵌入生成异常: {ex}")
                raise ex
        else:
            raise ValueError("Input 'text' or 'docs' is required for embedding.")
