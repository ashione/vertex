from typing import Generic, TypeVar

# Avoid cricle import.
# from vertex_flow.workflow.vertex import Vertex

T = TypeVar("T")  # 泛型类型变量


class EdgeType:
    """定义边的类型的基础类"""

    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name

    def __hash__(self) -> int:
        return hash(self.name)


class Always(EdgeType):
    """定义始终连接的边类型"""

    def __init__(self):
        super().__init__(name="always")

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, Always):
            return True
        else:
            return False

    def __hash__(self) -> int:
        return super().__hash__()


class Condition(EdgeType):
    """定义条件连接的边类型"""

    def __init__(self, id: str = "true"):
        super().__init__(name="condition")
        self.id = id

    def __str__(self):
        return f"{self.name}={self.id}"

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, Condition):
            return False
        return self.id == __value.id

    def __hash__(self) -> int:
        return hash((self.__class__.__name__, self.id))


class Edge(Generic[T]):
    """表示顶点之间的边"""

    ALWAYS = Always()
    CONDITION_TRUE = Condition()
    CONDITION_FALSE = Condition(id="false")

    def __init__(
        self,
        source_vertex: "Vertex[T]",
        target_vertex: "Vertex[T]",
        edge_type: EdgeType = ALWAYS,
    ):
        self.source_vertex = source_vertex
        self.target_vertex = target_vertex
        self._edge_type = edge_type

    def get_source_vertex(self) -> "Vertex[T]":
        return self.source_vertex

    def get_target_vertex(self) -> "Vertex[T]":
        return self.target_vertex

    def __eq__(self, other):
        """Check if two edges are equal."""
        if not isinstance(other, Edge):
            return False
        return (
            self.source_vertex == other.source_vertex
            and self.target_vertex == other.target_vertex
            and self.edge_type == other.edge_type
        )

    def __hash__(self):
        return hash((self.source_vertex, self.target_vertex, self.edge_type))

    @property
    def edge_type(self):
        return self._edge_type

    def __str__(self) -> str:
        return f"->({self.edge_type})->".join(
            [self.source_vertex.id, self.target_vertex.id]
        )
