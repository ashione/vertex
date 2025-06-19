import logging
from abc import abstractmethod
from typing import Any, Callable, Dict, List, Optional, TypeVar

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import DOCS, QUERY, STATUS, SUCCESS
from vertex_flow.workflow.vertex.vector_engines import VectorEngine
from vertex_flow.workflow.vertex.vertex import Vertex

from .vertex import T, Vertex, WorkflowContext

logging = LoggerUtil.get_logger()

T = TypeVar("T")


class VectorVertex(Vertex[T]):
    def __init__(
        self,
        id: str,
        name: str = None,
        task: Callable[[Dict[str, Any], WorkflowContext[T]], T] = None,
        params: Dict[str, Any] = None,
        vector_engine: VectorEngine = None,
        variables: List[Dict[str, Any]] = None,
    ):
        super().__init__(id=id, name=name, task_type="VECTOR", task=task, params=params, variables=variables or [])
        self.vector_engine = vector_engine

    @abstractmethod
    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        pass


class VectorStoreVertex(VectorVertex):
    DEFAULT_INPUT_KEY = DOCS

    def __init__(
        self,
        id: str,
        name: str = None,
        params: Dict[str, Any] = None,
        vector_engine: VectorEngine = None,
        variables: List[Dict[str, Any]] = None,
    ):
        super().__init__(
            id=id,
            name=name,
            params=params,
            vector_engine=vector_engine,
            variables=variables,
        )
        self.input_key = params.get("input_key", self.DEFAULT_INPUT_KEY) if params else self.DEFAULT_INPUT_KEY

    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        if self.vector_engine is None:
            raise ValueError("VectorEngine must be provided for VectorStoreVertex.")

        logging.debug(f"Vector store inputs : {inputs}")
        if self.variables:
            local_inputs = self.resolve_dependencies(inputs=inputs)
        else:
            local_inputs = inputs
        if self.input_key not in local_inputs:
            raise ValueError(f"Input '{self.input_key}' is required for VectorStoreVertex.")

        docs = local_inputs[self.input_key]

        # 处理EmbeddingVertex的输出格式
        if isinstance(docs, dict) and "embeddings" in docs:
            # EmbeddingVertex的输出格式
            embeddings_data = docs["embeddings"]
            if isinstance(embeddings_data, list):
                # 提取嵌入向量和元数据
                vectors = []
                for item in embeddings_data:
                    if isinstance(item, dict) and "embedding" in item:
                        vectors.append(
                            {
                                "id": item.get("id", ""),
                                "vector": item["embedding"],
                                "metadata": item.get("metadata", {}),
                                "content": item.get("content", ""),
                            }
                        )
                docs = vectors
            else:
                # 单个嵌入向量
                docs = [{"vector": embeddings_data}]

        try:
            self.vector_engine.insert(docs)
            self.output = {
                STATUS: SUCCESS,
                "message": "Documents inserted successfully.",
            }
        except Exception as e:
            logging.error(f"Error storing vectors in VectorStoreVertex {self.id}: {e}")
            self.output = {STATUS: "error", "message": str(e)}
            raise e


class VectorQueryVertex(VectorVertex):
    DEFAULT_INPUT_KEY = QUERY

    def __init__(
        self,
        id: str,
        name: str = None,
        params: Dict[str, Any] = None,
        vector_engine: VectorEngine = None,
        variables: List[Dict[str, Any]] = None,
    ):
        super().__init__(
            id=id,
            name=name,
            params=params,
            vector_engine=vector_engine,
            variables=variables,
        )
        self.input_key = params.get("input_key", self.DEFAULT_INPUT_KEY) if params else self.DEFAULT_INPUT_KEY

    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        if self.vector_engine is None:
            raise ValueError("VectorEngine must be provided for VectorQueryVertex.")

        if self.variables:
            inputs = self.resolve_dependencies(inputs=inputs)

        if self.input_key not in inputs:
            raise ValueError(f"Input '{self.input_key}' is required for VectorQueryVertex.")

        query = inputs[self.input_key]
        top_k = inputs.get("top_k", 3)
        filter = inputs.get("filter", None)
        similarity_threshold = inputs.get("similarity_threshold", 0.3)  # 默认最小阈值0.3

        # 处理EmbeddingVertex的输出格式
        if isinstance(query, dict) and "embeddings" in query:
            # EmbeddingVertex的输出格式
            embeddings_data = query["embeddings"]
            if isinstance(embeddings_data, list) and len(embeddings_data) > 0:
                # 使用第一个嵌入向量作为查询
                query = embeddings_data[0]["embedding"]
            else:
                # 单个嵌入向量
                query = embeddings_data

        try:
            results = self.vector_engine.search(query, top_k=top_k, filter=filter)

            # 根据相似度阈值过滤结果
            filtered_results = []
            for result in results:
                score = result.get("score", 0)
                if score >= similarity_threshold:
                    filtered_results.append(result)

            logging.info(
                f"向量查询返回 {len(results)} 个结果，经过阈值 {similarity_threshold} 过滤后剩余 {len(filtered_results)} 个"
            )

            self.output = {"results": filtered_results, STATUS: SUCCESS}
        except Exception as e:
            logging.error(f"Error querying vectors in VectorQueryVertex {self.id}: {e}")
            self.output = {STATUS: "error", "message": str(e)}
            raise e
