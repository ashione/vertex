from .vertex import (
    Vertex,
    WorkflowContext,
    T,
)
from vertex_flow.workflow.vector import VectorEngine
from typing import Callable, Dict, Any
from vertex_flow.utils.logger import LoggerUtil
from abc import abstractmethod

logging = LoggerUtil.get_logger()


class VectorVertex(Vertex[T]):
    def __init__(
        self,
        id: str,
        name: str = None,
        task: Callable[[Dict[str, Any], WorkflowContext[T]], T] = None,
        params: Dict[str, Any] = None,
        vector_engine: VectorEngine = None,
    ):
        super().__init__(id=id, name=name, task_type="VECTOR", task=task, params=params)
        self.vector_engine = vector_engine

    @abstractmethod
    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        pass


class VectorStoreVertex(VectorVertex):
    DEFAULT_INPUT_KEY = "docs"

    def __init__(
        self,
        id: str,
        name: str = None,
        params: Dict[str, Any] = None,
        vector_engine: VectorEngine = None,
    ):
        super().__init__(
            id=id,
            name=name,
            params=params,
            vector_engine=vector_engine,
        )
        self.input_key = (
            params.get("input_key", self.DEFAULT_INPUT_KEY)
            if params
            else self.DEFAULT_INPUT_KEY
        )

    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        if self.vector_engine is None:
            raise ValueError("VectorEngine must be provided for VectorStoreVertex.")

        logging.debug(f"Vector store inputs : {inputs}")
        if self.variables:
            local_inputs = self.resolve_dependencies(inputs=inputs)
        else:
            local_inputs = inputs
        if self.input_key not in local_inputs:
            raise ValueError(
                f"Input '{self.input_key}' is required for VectorStoreVertex."
            )

        docs = local_inputs[self.input_key]
        try:
            # TODO(zuolingxuan): 这里仅仅只是把向量写进去，如果涉及到fields和id
            # 需要根据新的API文档来进行修改。
            self.vector_engine.insert(docs)
            self.output = {
                "status": "success",
                "message": "Documents inserted successfully.",
            }
        except Exception as e:
            logging.error(f"Error storing vectors in VectorStoreVertex {self.id}: {e}")
            self.output = {"status": "error", "message": str(e)}
            raise e


class VectorQueryVertex(VectorVertex):
    DEFAULT_INPUT_KEY = "query"

    def __init__(
        self,
        id: str,
        name: str = None,
        params: Dict[str, Any] = None,
        vector_engine: VectorEngine = None,
    ):
        super().__init__(
            id=id,
            name=name,
            params=params,
            vector_engine=vector_engine,
        )
        self.input_key = (
            params.get("input_key", self.DEFAULT_INPUT_KEY)
            if params
            else self.DEFAULT_INPUT_KEY
        )

    def execute(self, inputs: Dict[str, T] = None, context: WorkflowContext[T] = None):
        if self.vector_engine is None:
            raise ValueError("VectorEngine must be provided for VectorQueryVertex.")

        if self.variables:
            inputs = self.resolve_dependencies(inputs=inputs)

        if self.input_key not in inputs:
            raise ValueError(
                f"Input '{self.input_key}' is required for VectorQueryVertex."
            )

        query = inputs[self.input_key]
        top_k = inputs.get("top_k", 3)
        filter = inputs.get("filter", None)

        try:
            results = self.vector_engine.search(query, top_k=top_k, filter=filter)
            self.output = {"results": results, "status": "success"}
        except Exception as e:
            logging.error(f"Error querying vectors in VectorQueryVertex {self.id}: {e}")
            self.output = {"status": "error", "message": str(e)}
            raise e
