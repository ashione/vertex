# FunctionVertex 文档

> **注意**: 关于变量依赖配置的详细说明，请参考 [Variables 变量透出机制和选择机制](VARIABLES_MECHANISM.md) 文档。

## 概述

`FunctionVertex` 是 VertexFlow 框架中最基础和通用的顶点类型，它继承自 `Vertex` 基类，允许用户通过传入自定义函数来实现各种业务逻辑。`FunctionVertex` 是许多其他特殊顶点类型的基础，如 `WhileVertex`、`IfElseVertex` 和 `CodeVertex`。

## 设计理念

### 1. 通用性
- **函数封装**: 将任意 Python 函数封装为工作流顶点
- **灵活输入**: 支持多种输入参数和依赖关系
- **标准接口**: 遵循 Vertex 的标准接口规范

### 2. 简单性
- **易于使用**: 只需提供一个函数即可创建顶点
- **自动推断**: 自动检测函数签名，智能传递参数
- **错误处理**: 内置异常捕获和日志记录

### 3. 扩展性
- **子类基础**: 作为其他特殊顶点的基类
- **参数化**: 支持通过参数自定义行为
- **类型安全**: 支持泛型类型约束

## 核心特性

### 1. 函数执行
- 自动检测函数签名中是否包含 `context` 参数
- 智能传递输入参数和工作流上下文
- 支持同步函数执行

### 2. 依赖解析
- 自动获取依赖顶点的输出
- 合并输入参数和依赖输出
- 支持复杂的数据流传递

### 3. 子类型支持
- 通过 `SubType` 参数自定义顶点类型
- 支持在运行时动态确定顶点行为

## 类设计

### FunctionVertex

```python
class FunctionVertex(Vertex[T]):
    """通用函数顶点，有一个输入和一个输出"""
    
    def __init__(
        self,
        id: str,
        name: str = None,
        task: Callable[[Dict[str, Any], WorkflowContext[T]], T] = None,
        params: Dict[str, Any] = None,
        variables: List[Dict[str, Any]] = None,
    )
```

### 参数说明

- **id**: 顶点的唯一标识符
- **name**: 顶点的显示名称（可选）
- **task**: 要执行的函数，支持两种签名：
  - `func(inputs: Dict[str, Any]) -> T`
  - `func(inputs: Dict[str, Any], context: WorkflowContext[T]) -> T`
- **params**: 顶点参数字典，可包含 `SubType` 等配置
- **variables**: 变量依赖配置列表

## 使用示例

### 基本使用

```python
from vertex_flow.workflow.vertex import FunctionVertex

# 定义业务函数
def add_numbers(inputs):
    a = inputs.get("a", 0)
    b = inputs.get("b", 0)
    return {"sum": a + b}

# 创建函数顶点
add_vertex = FunctionVertex(
    id="add_vertex",
    name="加法运算",
    task=add_numbers
)

# 执行顶点
result = add_vertex.execute(
    inputs={"a": 5, "b": 3},
    context=workflow_context
)
print(add_vertex.output)  # {"sum": 8}
```

### 使用上下文参数

```python
def process_with_context(inputs, context):
    """使用工作流上下文的函数"""
    data = inputs.get("data", [])
    
    # 从上下文获取其他顶点的输出
    previous_result = context.get_output("previous_vertex")
    
    # 处理数据
    processed = [x * 2 for x in data]
    
    return {
        "processed_data": processed,
        "previous_result": previous_result
    }

process_vertex = FunctionVertex(
    id="process_vertex",
    name="数据处理",
    task=process_with_context
)
```

### 依赖关系配置

```python
# 创建依赖其他顶点输出的函数顶点
dependent_vertex = FunctionVertex(
    id="dependent_vertex",
    name="依赖处理",
    task=lambda inputs: {"result": inputs["value"] * 10},
    variables=[
        {
            "source_scope": "source_vertex",
            "source_var": "output_value",
            "local_var": "value"
        }
    ]
)
```

### 自定义子类型

```python
# 使用自定义子类型
custom_vertex = FunctionVertex(
    id="custom_vertex",
    name="自定义处理",
    task=custom_function,
    params={
        "SubType": "CUSTOM_PROCESSOR",
        "config_param": "value"
    }
)
```

## 扩展类型

`FunctionVertex` 作为基类，支持多种扩展类型：

### IfElseVertex

条件分支顶点，支持复杂的条件判断逻辑：

```python
from vertex_flow.workflow.vertex import IfElseVertex, IfCase

# 定义条件案例
cases = [
    IfCase(
        id="positive",
        conditions=[
            {"variable": "value", "operator": ">", "value": 0}
        ]
    ),
    IfCase(
        id="negative",
        conditions=[
            {"variable": "value", "operator": "<", "value": 0}
        ]
    )
]

if_else_vertex = IfElseVertex(
    id="condition_vertex",
    name="条件判断",
    cases=cases
)
```

### CodeVertex

代码执行顶点，支持动态执行 Python 代码：

```python
from vertex_flow.workflow.vertex import CodeVertex

code_vertex = CodeVertex(
    id="code_vertex",
    name="代码执行",
    params={
        "code": """
result = inputs.get('x', 0) ** 2
output = {'squared': result}
"""
    }
)
```

## 函数签名检测

`FunctionVertex` 会自动检测传入函数的签名，并智能决定是否传递 `context` 参数：

```python
# 不需要 context 的函数
def simple_function(inputs):
    return {"result": inputs["value"] * 2}

# 需要 context 的函数
def context_function(inputs, context):
    previous = context.get_output("prev_vertex")
    return {"result": inputs["value"] + previous["data"]}

# FunctionVertex 会自动适配
simple_vertex = FunctionVertex(id="simple", task=simple_function)
context_vertex = FunctionVertex(id="context", task=context_function)
```

## 错误处理

### 异常捕获

`FunctionVertex` 内置异常处理机制：

```python
def risky_function(inputs):
    value = inputs["value"]
    if value == 0:
        raise ValueError("Value cannot be zero")
    return {"result": 100 / value}

risky_vertex = FunctionVertex(
    id="risky_vertex",
    task=risky_function
)

try:
    risky_vertex.execute(inputs={"value": 0})
except ValueError as e:
    print(f"Caught error: {e}")
```

### 日志记录

执行过程中会自动记录详细日志：

```python
# 成功执行时的日志
# INFO: Function vertex_id, output {...} after executed.

# 异常时的日志
# WARNING: Error executing vertex vertex_id: error_message
```

## 最佳实践

### 1. 函数设计

```python
# 好的实践：清晰的输入输出
def good_function(inputs):
    """处理用户数据
    
    Args:
        inputs: 包含 'user_data' 键的字典
        
    Returns:
        包含 'processed_data' 键的字典
    """
    user_data = inputs.get("user_data", {})
    
    # 数据验证
    if not user_data:
        raise ValueError("user_data is required")
    
    # 业务逻辑
    processed = process_user_data(user_data)
    
    return {"processed_data": processed}

# 避免的做法：不清晰的接口
def bad_function(inputs):
    # 没有文档说明
    # 没有输入验证
    # 返回格式不一致
    return inputs["x"] * 2  # 直接返回值而不是字典
```

### 2. 错误处理

```python
def robust_function(inputs):
    """健壮的函数实现"""
    try:
        # 输入验证
        required_keys = ["data", "config"]
        for key in required_keys:
            if key not in inputs:
                raise ValueError(f"Missing required input: {key}")
        
        # 业务逻辑
        result = process_data(inputs["data"], inputs["config"])
        
        return {"result": result, "status": "success"}
        
    except Exception as e:
        # 记录错误但不重新抛出，返回错误状态
        logging.error(f"Processing failed: {e}")
        return {"result": None, "status": "error", "error": str(e)}
```

### 3. 性能优化

```python
# 对于计算密集型任务，考虑缓存
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_calculation(value):
    # 昂贵的计算
    return complex_algorithm(value)

def optimized_function(inputs):
    value = inputs["value"]
    result = expensive_calculation(value)
    return {"result": result}
```

### 4. 类型提示

```python
from typing import Dict, Any

def typed_function(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """带类型提示的函数"""
    value: int = inputs["value"]
    result: int = value * 2
    return {"doubled": result}
```

## 与其他顶点的集成

### 在工作流中使用

```python
from vertex_flow.workflow.workflow import Workflow
from vertex_flow.workflow.edge import Edge, Always

# 创建工作流
workflow = Workflow()

# 添加函数顶点
workflow.add_vertex(function_vertex1)
workflow.add_vertex(function_vertex2)

# 创建边连接
workflow.add_edge(Edge(function_vertex1, function_vertex2, Always()))

# 执行工作流
workflow.execute()
```

### 与其他顶点类型混合使用

```python
# 函数顶点 -> LLM顶点 -> 函数顶点
preprocess_vertex = FunctionVertex(
    id="preprocess",
    task=preprocess_data
)

llm_vertex = LLMVertex(
    id="llm_process",
    params={"model": chat_model, "system": "You are a helpful assistant"}
)

postprocess_vertex = FunctionVertex(
    id="postprocess",
    task=postprocess_result
)

# 连接顶点
workflow.add_edge(Edge(preprocess_vertex, llm_vertex, Always()))
workflow.add_edge(Edge(llm_vertex, postprocess_vertex, Always()))
```

## 调试和测试

### 单元测试

```python
import pytest
from vertex_flow.workflow.vertex import FunctionVertex
from vertex_flow.workflow.context import WorkflowContext

def test_function_vertex():
    """测试函数顶点"""
    def test_task(inputs):
        return {"result": inputs["value"] * 2}
    
    vertex = FunctionVertex(
        id="test_vertex",
        task=test_task
    )
    
    context = WorkflowContext()
    vertex.execute(inputs={"value": 5}, context=context)
    
    assert vertex.output == {"result": 10}
```

### 调试技巧

```python
def debug_function(inputs, context=None):
    """带调试信息的函数"""
    print(f"Debug: inputs = {inputs}")
    
    if context:
        print(f"Debug: context outputs = {context.outputs}")
    
    # 业务逻辑
    result = process_inputs(inputs)
    
    print(f"Debug: result = {result}")
    return result

debug_vertex = FunctionVertex(
    id="debug_vertex",
    task=debug_function
)
```

## 常见问题

### Q: 如何在函数中访问其他顶点的输出？

A: 有两种方式：
1. 通过 `context` 参数：`context.get_output("vertex_id")`
2. 通过 `variables` 配置依赖关系，自动注入到 `inputs` 中

### Q: 函数返回值有什么要求？

A: 建议返回字典格式，便于后续顶点使用。如果返回其他类型，后续顶点需要相应处理。

### Q: 如何处理函数执行失败？

A: `FunctionVertex` 会自动捕获异常并重新抛出。可以在函数内部处理异常，或在工作流级别处理。

### Q: 可以使用 lambda 函数吗？

A: 可以，但建议用于简单逻辑。复杂逻辑建议定义具名函数，便于调试和维护。

## 总结

`FunctionVertex` 是 VertexFlow 框架的核心组件，提供了：

1. **通用性**: 支持任意 Python 函数的封装
2. **灵活性**: 智能的参数传递和依赖解析
3. **扩展性**: 作为其他特殊顶点的基础
4. **易用性**: 简单的 API 和自动化的错误处理
5. **可靠性**: 内置的异常处理和日志记录

通过合理使用 `FunctionVertex`，可以快速构建功能丰富、可维护的工作流应用。