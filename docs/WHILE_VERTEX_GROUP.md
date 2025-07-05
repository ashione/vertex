# WhileVertexGroup 功能说明

## 概述

WhileVertexGroup是VertexGroup的子类，专门用于在工作流中创建循环执行的复杂子图结构。它结合了WhileVertex的循环控制能力和VertexGroup的子图管理能力，为深度研究等需要迭代处理的场景提供了强大的工具。

## 核心特性

### 1. 继承自VertexGroup
- 完全兼容现有的VertexGroup功能
- 支持子图的顶点和边管理
- 提供完整的依赖解析机制

### 2. 内置WhileVertex循环控制
- 集成WhileVertex作为循环控制机制
- 支持条件函数和条件列表两种循环控制方式
- 可配置最大迭代次数限制

### 3. 复杂子图循环执行
- 可以包含多个不同类型的Vertex
- 支持子图内部的复杂边连接关系
- 在循环中重复执行整个子图

### 4. 灵活的数据传递
- 支持通过execute_task传递外部数据到子图
- 提供变量暴露机制，将内部结果暴露给外部
- 自动处理循环迭代中的数据流转

## 构造函数参数

```python
WhileVertexGroup(
    id: str,                                    # 唯一标识符
    name: str = None,                          # 显示名称
    subgraph_vertices: List[Vertex] = None,    # 子图顶点列表
    subgraph_edges: List[Edge] = None,         # 子图边列表
    # WhileVertex参数
    execute_task: Callable = None,             # 循环执行任务
    condition_task: Callable = None,           # 条件判断函数
    conditions: List[WhileCondition] = None,   # 条件列表
    logical_operator: str = "and",             # 逻辑操作符
    max_iterations: int = None,                # 最大迭代次数
    # 通用参数
    params: Dict[str, Any] = None,             # 参数字典
    variables: List[Dict[str, Any]] = None,    # 变量配置
)
```

## 使用示例

### 基本用法

```python
from vertex_flow.workflow.vertex import (
    FunctionVertex, 
    WhileVertexGroup
)
from vertex_flow.workflow.edge import Edge, Always

# 创建子图顶点
prepare_vertex = FunctionVertex(id="prepare", task=prepare_task)
process_vertex = FunctionVertex(id="process", task=process_task)
finalize_vertex = FunctionVertex(id="finalize", task=finalize_task)

# 创建子图边
edge1 = Edge(prepare_vertex, process_vertex, Always())
edge2 = Edge(process_vertex, finalize_vertex, Always())

# 创建循环条件
def condition_task(inputs, context=None):
    return inputs.get("counter", 0) < 5

# 创建WhileVertexGroup
while_group = WhileVertexGroup(
    id="processing_loop",
    name="数据处理循环",
    subgraph_vertices=[prepare_vertex, process_vertex, finalize_vertex],
    subgraph_edges=[edge1, edge2],
    condition_task=condition_task
)
```

### 在深度研究工作流中的应用

WhileVertexGroup特别适用于深度研究工作流中的步骤化分析：

```python
# 创建分析步骤子图
step_prepare = FunctionVertex(id="step_prepare", task=step_prepare_task)
step_analysis = LLMVertex(id="step_analysis", params=analysis_params)
step_postprocess = FunctionVertex(id="step_postprocess", task=step_postprocess_task)

# 连接子图
step_edge1 = Edge(step_prepare, step_analysis, Always())
step_edge2 = Edge(step_analysis, step_postprocess, Always())

# 创建循环条件：当还有未处理的分析步骤时继续
def step_condition_task(inputs, context=None):
    steps = inputs.get("steps", [])
    current_index = inputs.get("step_index", 0)
    return current_index < len(steps)

# 创建分析步骤循环组
analysis_loop = WhileVertexGroup(
    id="analysis_steps_loop",
    name="分析步骤循环执行",
    subgraph_vertices=[step_prepare, step_analysis, step_postprocess],
    subgraph_edges=[step_edge1, step_edge2],
    condition_task=step_condition_task
)
```

## 技术实现

### 1. 循环控制机制
- 内置WhileVertex实例作为循环控制器
- 重写WhileVertex的依赖解析方法，支持子图内依赖查找
- 自动设置workflow引用，确保子图正常运行

### 2. 子图执行流程
1. 检查循环条件
2. 如果条件满足，执行子图
3. 收集子图执行结果
4. 更新循环状态
5. 重复直到条件不满足或达到最大迭代次数

### 3. 依赖解析
- 继承VertexGroup的依赖解析机制
- 支持子图内vertex之间的依赖关系
- 提供自定义依赖解析方法给内置WhileVertex

## 优势与应用场景

### 优势
1. **结构化循环**：提供比简单WhileVertex更强大的循环结构
2. **可重用性**：子图可以包含复杂的处理逻辑，易于重用
3. **可维护性**：清晰的子图结构，便于理解和维护
4. **扩展性**：可以轻松添加新的处理步骤到子图中

### 适用场景
1. **深度研究工作流**：需要对多个分析步骤进行循环处理
2. **数据处理管道**：需要对数据进行多轮迭代处理
3. **批量任务处理**：需要对任务列表进行逐一处理
4. **条件循环处理**：需要根据复杂条件进行循环控制

## 注意事项

1. **变量作用域**：子图内的变量引用只能指向子图内的vertex
2. **循环条件**：确保循环条件能够正确终止，避免无限循环
3. **性能考虑**：大量迭代可能影响性能，建议设置合理的最大迭代次数
4. **错误处理**：子图内的错误会中断整个循环，需要适当的错误处理机制

## 与其他组件的集成

WhileVertexGroup可以无缝集成到现有的工作流系统中：

- 作为标准Vertex添加到Workflow
- 与其他Vertex类型（LLMVertex、FunctionVertex等）协同工作
- 支持流式输出和实时进度跟踪
- 兼容现有的边连接和数据传递机制

## 总结

WhileVertexGroup为复杂的循环处理场景提供了强大而灵活的解决方案。它特别适用于需要结构化、多步骤迭代处理的工作流，如深度研究分析、数据处理管道等。通过结合VertexGroup的子图管理能力和WhileVertex的循环控制能力，WhileVertexGroup成为了构建复杂工作流的重要工具。 