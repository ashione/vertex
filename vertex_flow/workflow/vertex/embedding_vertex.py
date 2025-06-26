from typing import Any, Callable, Dict, List, Optional, TypeVar
import asyncio
import math

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
        name: Optional[str] = None,
        task: Optional[Callable[[Dict[str, Any], WorkflowContext[T]], T]] = None,
        params: Optional[Dict[str, Any]] = None,
        variables: Optional[List[Dict[str, str]]] = None,
        embedding_provider: Optional[TextEmbeddingProvider] = None,
    ):
        super().__init__(
            id=id,
            name=name,
            task_type="EMBEDDING",
            task=task,
            params=params,
            variables=variables,
        )
        self.embedding_provider = embedding_provider

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

        # 记录嵌入提供者信息
        logging.info(f"使用嵌入提供者: {self.embedding_provider.__class__.__name__}")
        if hasattr(self.embedding_provider, 'dimension'):
            logging.info(f"嵌入维度: {self.embedding_provider.dimension}")

        # 如果没有 workflow 引用，直接使用输入参数
        if not hasattr(self, 'workflow') or self.workflow is None:
            local_inputs = inputs or {}
        else:
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

        # 处理文档对象列表（包括空列表）
        if isinstance(docs, list):
            if not docs:
                # 空文档列表，直接返回空的embeddings
                logging.info("接收到空文档列表，跳过embedding处理")
                self.output = {"embeddings": []}
                return

            # 使用异步并发处理文档列表
            embeddings_list = asyncio.run(self._process_docs_async(docs))
            
            # 检查生成的嵌入维度
            if embeddings_list and len(embeddings_list) > 0:
                first_embedding = embeddings_list[0].get("embedding", [])
                if first_embedding:
                    logging.info(f"生成的嵌入维度: {len(first_embedding)}")
                    if hasattr(self.embedding_provider, 'dimension'):
                        expected_dim = self.embedding_provider.dimension
                        actual_dim = len(first_embedding)
                        if expected_dim != actual_dim:
                            logging.warning(f"嵌入维度不匹配: 期望 {expected_dim}, 实际 {actual_dim}")
            
            self.output = {"embeddings": embeddings_list}

        elif text:
            # 处理单个文本
            try:
                safe_text = self._safe_encode_content(text)
                embeddings = self.embedding_provider.embedding(safe_text)
                
                # 检查单个文本的嵌入维度
                if embeddings:
                    logging.info(f"单个文本嵌入维度: {len(embeddings)}")
                    if hasattr(self.embedding_provider, 'dimension'):
                        expected_dim = self.embedding_provider.dimension
                        actual_dim = len(embeddings)
                        if expected_dim != actual_dim:
                            logging.warning(f"嵌入维度不匹配: 期望 {expected_dim}, 实际 {actual_dim}")
                
                self.output = {"embeddings": embeddings}
                logging.debug("单个文本嵌入生成完成")
            except Exception as ex:
                logging.error(f"嵌入生成异常: {ex}")
                raise ex
        else:
            raise ValueError("Input 'text' or 'docs' is required for embedding.")

    async def _process_docs_async(self, docs: List[Any]) -> List[Dict[str, Any]]:
        """
        异步处理文档列表，按批次顺序处理
        
        Args:
            docs: 文档列表
            
        Returns:
            处理后的嵌入列表
        """
        if not self.embedding_provider or not self.embedding_provider.supports_batch():
            # 不支持批量，回退到顺序处理
            return self._process_docs_sequential(docs)
        
        # 获取 provider 的 batch_size
        batch_size = self.embedding_provider.get_batch_size()
        total_docs = len(docs)
        
        # 计算批次数量
        num_batches = math.ceil(total_docs / batch_size)
        logging.info(f"将 {total_docs} 个文档按 batch_size={batch_size} 分为 {num_batches} 个批次，顺序处理")
        
        # 分割文档为批次
        batches = []
        for i in range(0, total_docs, batch_size):
            batch = docs[i:i + batch_size]
            batches.append((i // batch_size, batch))
        
        # 顺序处理每个批次
        embeddings_list = []
        processed_count = 0
        error_count = 0
        
        try:
            for batch_idx, batch_docs in batches:
                logging.info(f"开始处理批次 {batch_idx + 1}/{num_batches}，包含 {len(batch_docs)} 个文档")
                
                # 处理当前批次
                batch_results = await self._process_batch_async(batch_docs, batch_idx)
                
                # 添加批次结果
                embeddings_list.extend(batch_results)
                processed_count += len(batch_results)
                
                logging.info(f"批次 {batch_idx + 1} 处理完成，成功 {len(batch_results)} 个文档")
                
        except Exception as e:
            logging.error(f"批次处理失败: {e}")
            # 回退到顺序处理
            return self._process_docs_sequential(docs)
        
        logging.info(f"所有批次处理完成: 成功 {processed_count} 个，失败 {error_count} 个")
        return embeddings_list

    async def _process_batch_async(self, batch_docs: List[Any], batch_idx: int) -> List[Dict[str, Any]]:
        """
        异步处理单个批次的文档
        
        Args:
            batch_docs: 批次文档列表
            batch_idx: 批次索引
            
        Returns:
            批次的嵌入结果列表
        """
        batch_results = []
        
        for doc_idx, doc in enumerate(batch_docs):
            if isinstance(doc, dict) and "content" in doc:
                # 文档对象格式
                content = doc["content"]
                doc_id = doc.get("id", f"doc_{batch_idx}_{doc_idx}")
                metadata = doc.get("metadata", {})
            elif isinstance(doc, str):
                # 直接文本
                content = doc
                doc_id = f"doc_{batch_idx}_{doc_idx}"
                metadata = {}
            else:
                logging.warning(f"批次 {batch_idx} 跳过无效文档: {doc}")
                continue

            try:
                safe_content = self._safe_encode_content(content)
                embedding = await self._embed_async(safe_content)
                
                batch_results.append({
                    "id": doc_id,
                    "content": safe_content,
                    "embedding": embedding,
                    "metadata": metadata,
                })
            except Exception as e:
                logging.error(f"批次 {batch_idx} 文档 {doc_idx} 嵌入失败: {e}")
                continue
        
        return batch_results

    async def _embed_async(self, text: str) -> List[float]:
        """
        异步执行嵌入操作
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        # 在线程池中执行同步的嵌入操作
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embedding_provider.embedding, text)

    def _process_docs_sequential(self, docs: List[Any]) -> List[Dict[str, Any]]:
        """
        顺序处理文档列表（原有逻辑）
        
        Args:
            docs: 文档列表
            
        Returns:
            处理后的嵌入列表
        """
        embeddings_list = []
        processed_count = 0
        error_count = 0

        for doc in docs:
            if isinstance(doc, dict) and "content" in doc:
                # 文档对象格式
                content = doc["content"]
            elif isinstance(doc, str):
                # 直接文本
                content = doc
            else:
                logging.warning(f"跳过无效文档: {doc}")
                error_count += 1
                continue

            try:
                # 对内容进行编码异常处理
                safe_content = self._safe_encode_content(content)
                embedding = self.embedding_provider.embedding(safe_content)
                embeddings_list.append(
                    {
                        "id": doc.get("id", f"doc_{len(embeddings_list)}"),
                        "content": safe_content,
                        "embedding": embedding,
                        "metadata": doc.get("metadata", {}),
                    }
                )
                processed_count += 1
            except Exception as e:
                logging.error(f"文档嵌入失败: {e}")
                error_count += 1
                continue

        logging.info(f"顺序嵌入生成完成: 成功 {processed_count} 个，失败 {error_count} 个")
        return embeddings_list

    def _safe_encode_content(self, content: str) -> str:
        """
        安全处理文本内容，避免编码异常

        Args:
            content: 原始文本内容

        Returns:
            处理后的安全文本内容
        """
        if not isinstance(content, str):
            try:
                content = str(content)
            except Exception:
                return ""

        try:
            # 尝试编码和解码，以确保内容可以安全处理
            content.encode("utf-8")
            return content
        except UnicodeEncodeError:
            # 如果编码失败，使用忽略错误的方式处理
            try:
                safe_bytes = content.encode("utf-8", errors="ignore")
                safe_content = safe_bytes.decode("utf-8")
                logging.warning("文本内容包含无法编码的字符，已忽略相关字符")
                return safe_content
            except Exception:
                logging.error("文本内容编码处理失败，返回空内容")
                return ""
        except Exception as e:
            logging.error(f"文本内容处理异常: {e}")
            return ""
