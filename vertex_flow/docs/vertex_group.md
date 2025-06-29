# VertexGroup 文档

> **注意**: 关于变量透出机制的详细说明，请参考 [Variables 变量透出机制和选择机制](VARIABLES_MECHANISM.md) 文档。

## 概述

`VertexGroup` 是 VertexFlow 框架中的一个重要组件，它允许将多个相关的 `Vertex` 组织成一个逻辑单元，形成一个子图（Subgraph）。`VertexGroup` 本身也继承自 `Vertex`，因此可以像普通顶点一样在工作流中使用，同时提供了强大的子图管理和变量暴露功能。

## 设计理念

### 1. 模块化设计
- **封装复杂逻辑**: 将复杂的多步骤处理逻辑封装在一个 `VertexGroup` 中
- **可重用性**: 创建的子图可以在不同的工作流中重复使用
- **层次化组织**: 支持嵌套的 `VertexGroup`，实现多层次的逻辑组织

### 2. 隔离性
- **内部隔离**: 子图内部的顶点和边对外部不可见
- **受控暴露**: 通过配置选择性地暴露内部变量和结果
- **上下文管理**: 独立的子图上下文管理内部状态

### 3. 灵活性
- **动态构建**: 支持运行时动态添加顶点和边
- **可配置暴露**: 灵活配置哪些变量暴露给外部
- **标准接口**: 与普通 `Vertex` 具有相同的接口

## 核心组件

### SubgraphContext

`SubgraphContext` 负责管理子图内部的执行上下文：

```python
class SubgraphContext:
    def __init__(self, parent_context: WorkflowContext = None)
    def store_internal_output(self, vertex_id: str, output_data: T)
    def get_internal_output(self, vertex_id: str) -> T
    def expose_variable(self, internal_vertex_id: str, variable_name: str, exposed_name: str = None)
    def get_exposed_variables(self) -> Dict[str, Any]
```

**功能特性**:
- 存储子图内部顶点的输出
- 管理暴露给外部的变量
- 与父工作流上下文的关联

### VertexGroup

`VertexGroup` 是主要的子图管理类：

```python
class VertexGroup(Vertex[T]):
    def __init__(
        self,
        id: str,
        name: str = None,
        subgraph_vertices: List[Vertex[T]] = None,
        subgraph_edges: List[Edge[T]] = None,
        exposed_outputs: List[Dict[str, str]] = None,
        params: Dict[str, Any] = None,
        variables: List[Dict[str, Any]] = None,
    )
```

## 主要功能

### 1. 子图管理

#### 添加顶点
```python
# 静态添加（初始化时）
group = VertexGroup(
    id="my_group",
    subgraph_vertices=[vertex1, vertex2, vertex3]
)

# 动态添加
group.add_subgraph_vertex(new_vertex)
```

#### 添加边
```python
# 静态添加（初始化时）
group = VertexGroup(
    id="my_group",
    subgraph_vertices=[vertex1, vertex2],
    subgraph_edges=[Edge(vertex1, vertex2, Always())]
)

# 动态添加
group.add_subgraph_edge(Edge(vertex1, vertex2, Always()))
```

### 2. 拓扑排序和执行

`VertexGroup` 自动对子图进行拓扑排序，确保顶点按正确的依赖顺序执行：

```python
# 获取拓扑排序结果
execution_order = group.topological_sort_subgraph()

# 执行子图
result = group.execute_subgraph(inputs, context)
```

### 3. 变量暴露机制

通过 `exposed_outputs` 配置控制哪些内部变量暴露给外部：

```python
exposed_outputs = [
    {
        "vertex_id": "internal_vertex_1",
        "variable": "result",
        "exposed_as": "step1_result"
    },
    {
        "vertex_id": "internal_vertex_2",
        "variable": "output",
        "exposed_as": "final_output"
    }
]

group = VertexGroup(
    id="my_group",
    subgraph_vertices=[vertex1, vertex2],
    exposed_outputs=exposed_outputs
)
```

### 4. 依赖关系解析

`VertexGroup` 支持两种依赖关系：
- **内部依赖**: 子图内顶点之间的依赖
- **外部依赖**: 子图顶点对外部顶点的依赖

```python
# 内部依赖示例
vertex2 = FunctionVertex(
    id="vertex2",
    task=some_task,
    variables=[
        {"source_scope": "vertex1", "source_var": "output", "local_var": "input"}
    ]
)

# 外部依赖示例
vertex_in_group = FunctionVertex(
    id="internal_vertex",
    task=some_task,
    variables=[
        {"source_scope": "external_vertex", "source_var": "result", "local_var": "data"}
    ]
)
```

## 使用示例

### 基本使用

```python
from vertex_flow.workflow.vertex import VertexGroup, FunctionVertex
from vertex_flow.workflow.edge import Edge, Always

# 定义任务函数
def add_task(inputs):
    return {"sum": inputs["a"] + inputs["b"]}

def multiply_task(inputs):
    return {"product": inputs["value"] * inputs["factor"]}

# 创建顶点
add_vertex = FunctionVertex(id="add", task=add_task)
multiply_vertex = FunctionVertex(
    id="multiply", 
    task=multiply_task,
    variables=[{"source_scope": "add", "source_var": "sum", "local_var": "value"}]
)

# 创建子图
calc_group = VertexGroup(
    id="calculation_group",
    subgraph_vertices=[add_vertex, multiply_vertex],
    subgraph_edges=[Edge(add_vertex, multiply_vertex, Always())],
    exposed_outputs=[
        {"vertex_id": "add", "variable": "sum", "exposed_as": "addition_result"},
        {"vertex_id": "multiply", "variable": "product", "exposed_as": "final_result"}
    ]
)

# 执行子图
inputs = {"a": 5, "b": 3, "factor": 2}
result = calc_group.execute_subgraph(inputs)
print(result["subgraph_outputs"])  # {"addition_result": 8, "final_result": 16}
```

### 动态构建

```python
# 创建空的 VertexGroup
group = VertexGroup(id="dynamic_group")

# 动态添加顶点
vertex1 = FunctionVertex(id="v1", task=task1)
vertex2 = FunctionVertex(id="v2", task=task2)

group.add_subgraph_vertex(vertex1)
group.add_subgraph_vertex(vertex2)

# 动态添加边
group.add_subgraph_edge(Edge(vertex1, vertex2, Always()))

# 动态添加暴露输出
group.add_exposed_output("v1", "result", "step1_result")
group.add_exposed_output("v2", "output", "final_output")
```

### 嵌套使用

```python
# 创建内层子图
inner_group = VertexGroup(
    id="inner_group",
    subgraph_vertices=[vertex1, vertex2],
    subgraph_edges=[Edge(vertex1, vertex2, Always())],
    exposed_outputs=[{"vertex_id": "vertex2", "variable": "result"}]
)

# 创建外层子图，包含内层子图
outer_group = VertexGroup(
    id="outer_group",
    subgraph_vertices=[inner_group, vertex3],
    subgraph_edges=[Edge(inner_group, vertex3, Always())]
)
```

## 输出格式

`VertexGroup` 的执行结果包含两个主要部分：

```python
{
    "subgraph_outputs": {
        "exposed_var1": value1,
        "exposed_var2": value2,
        # ... 其他暴露的变量
    },
    "execution_summary": {
        "executed_vertices": ["vertex1", "vertex2", ...],
        "total_vertices": 3,
        "success": True,
        "error": None  # 仅在失败时存在
    }
}
```

### 字段说明

- **subgraph_outputs**: 根据 `exposed_outputs` 配置暴露的变量
- **execution_summary**: 执行摘要信息
  - `executed_vertices`: 已执行的顶点ID列表
  - `total_vertices`: 子图中的总顶点数
  - `success`: 执行是否成功
  - `error`: 错误信息（仅在失败时）

## 错误处理

### 验证错误

`VertexGroup` 在初始化时会进行以下验证：

1. **边的有效性**: 确保边的源顶点和目标顶点都在子图中
2. **暴露输出的有效性**: 确保暴露输出配置中的顶点ID存在于子图中

```python
# 这会抛出 ValueError
group = VertexGroup(
    id="invalid_group",
    subgraph_vertices=[vertex1],
    subgraph_edges=[Edge(vertex1, external_vertex, Always())]  # external_vertex 不在子图中
)
```

### 执行错误

执行过程中的错误会被捕获并记录在结果中：

```python
result = group.execute_subgraph(inputs)
if not result["execution_summary"]["success"]:
    print(f"执行失败: {result['execution_summary']['error']}")
```

### 循环检测

`VertexGroup` 会检测子图中的循环依赖：

```python
# 这会抛出 ValueError: "Subgraph contains a cycle"
group = VertexGroup(
    id="cyclic_group",
    subgraph_vertices=[vertex1, vertex2],
    subgraph_edges=[
        Edge(vertex1, vertex2, Always()),
        Edge(vertex2, vertex1, Always())  # 创建循环
    ]
)
group.topological_sort_subgraph()  # 抛出异常
```

## 最佳实践

### 1. 合理的粒度

- **功能相关性**: 将功能相关的顶点组织在同一个 `VertexGroup` 中
- **适中的大小**: 避免创建过大或过小的子图
- **清晰的边界**: 确保子图有明确的输入和输出边界

### 2. 变量暴露策略

- **最小暴露原则**: 只暴露必要的变量，保持接口简洁
- **语义化命名**: 使用有意义的暴露变量名
- **文档化**: 为暴露的变量提供清晰的文档说明

```python
# 好的实践
exposed_outputs = [
    {"vertex_id": "data_processor", "variable": "cleaned_data", "exposed_as": "processed_data"},
    {"vertex_id": "analyzer", "variable": "summary", "exposed_as": "analysis_result"}
]

# 避免的做法
exposed_outputs = [
    {"vertex_id": "v1", "variable": "x", "exposed_as": "y"},  # 名称不清晰
    {"vertex_id": "v2", "variable": "internal_state", "exposed_as": "state"}  # 暴露内部状态
]
```

### 3. 错误处理

- **验证输入**: 在子图执行前验证输入的有效性
- **优雅降级**: 为关键错误提供备选方案
- **详细日志**: 记录详细的执行日志便于调试

### 4. 性能考虑

- **避免深度嵌套**: 过深的嵌套会影响性能和可维护性
- **合理的并行度**: 设计子图时考虑并行执行的可能性
- **资源管理**: 注意子图中顶点的资源使用

## 与现有系统的集成

### 在 Workflow 中使用

`VertexGroup` 可以像普通 `Vertex` 一样在 `Workflow` 中使用：

```python
from vertex_flow.workflow.workflow import Workflow

# 创建工作流
workflow = Workflow()

# 添加 VertexGroup
workflow.add_vertex(my_vertex_group)

# 添加其他顶点
workflow.add_vertex(other_vertex)

# 创建边
workflow.add_edge(Edge(my_vertex_group, other_vertex, Always()))

# 执行工作流
workflow.execute()
```

### 与其他 Vertex 类型的兼容性

`VertexGroup` 与所有现有的 `Vertex` 类型兼容：

- `FunctionVertex`
- `LLMVertex`
- `EmbeddingVertex`
- `WhileVertex`
- 其他自定义 `Vertex`

## 测试

### 单元测试

```bash
# 运行 VertexGroup 相关测试
python -m pytest tests/test_vertex_group.py -v
```

### 集成测试

```bash
# 运行示例
python examples/vertex_group_example.py
```

### 测试覆盖的场景

- 基本子图创建和执行
- 动态添加顶点和边
- 变量暴露机制
- 错误处理和验证
- 嵌套 `VertexGroup`
- 与 `Workflow` 的集成

## 常见问题

### Q: VertexGroup 与普通 Vertex 有什么区别？

A: `VertexGroup` 继承自 `Vertex`，具有相同的接口，但内部包含一个子图。主要区别在于：
- `VertexGroup` 可以包含多个顶点和边
- 支持变量暴露机制
- 提供子图管理功能
- 执行时会按拓扑顺序执行内部顶点

### Q: 如何处理子图中的循环依赖？

A: `VertexGroup` 会在拓扑排序时检测循环依赖并抛出异常。避免循环依赖的方法：
- 仔细设计顶点间的依赖关系
- 使用条件边（`Condition`）而不是无条件边（`Always`）
- 将循环逻辑封装在单个顶点中（如 `WhileVertex`）

### Q: 可以在 VertexGroup 中嵌套另一个 VertexGroup 吗？

A: 可以。`VertexGroup` 本身就是一个 `Vertex`，因此可以作为子顶点添加到另一个 `VertexGroup` 中，实现多层次的组织结构。

### Q: 如何调试 VertexGroup 的执行？

A: 可以通过以下方式调试：
- 查看执行摘要中的 `executed_vertices` 列表
- 检查日志输出
- 使用 `get_subgraph_vertex()` 方法访问内部顶点的状态
- 在开发阶段暴露更多的内部变量

## 总结

`VertexGroup` 是 VertexFlow 框架中的一个强大组件，它提供了：

1. **模块化**: 将相关顶点组织成逻辑单元
2. **封装性**: 隐藏内部实现细节，提供清晰的接口
3. **灵活性**: 支持动态构建和配置
4. **可重用性**: 创建的子图可以在多个工作流中重用
5. **标准化**: 与现有 `Vertex` 接口完全兼容

通过合理使用 `VertexGroup`，可以构建更加模块化、可维护和可扩展的工作流应用。