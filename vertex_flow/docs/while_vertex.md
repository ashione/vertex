# WhileVertex 文档

> **注意**: 关于变量选择和条件判断的详细说明，请参考 [Variables 变量透出机制和选择机制](VARIABLES_MECHANISM.md) 文档。

## 概述

`WhileVertex` 是基于 `IfVertex` 和 `Vertex` 抽象设计的循环控制顶点，支持在工作流中实现while循环逻辑。它允许用户传入执行逻辑和判断逻辑，并支持多种循环跳出条件。

## 设计特性

### 1. 继承结构
- 继承自 `FunctionVertex`
- 遵循现有的 Vertex 抽象设计模式
- 与现有工作流系统完全兼容

### 2. 循环控制方式

#### 条件判断方式
- **condition_task**: 自定义条件判断函数
- **conditions**: 条件列表，支持多种比较操作符

#### 循环跳出条件
- **条件判断**: 当条件不满足时跳出循环
- **固定次数**: 通过 `max_iterations` 参数限制最大迭代次数
- **异常处理**: 执行过程中出现异常时自动跳出

### 3. 支持的操作符

条件判断支持以下操作符：
- `==`, `is`: 相等比较
- `!=`: 不等比较
- `>`, `<`, `>=`, `<=`: 数值比较
- `contains`, `not_contains`: 包含关系
- `starts_with`, `ends_with`: 字符串前缀/后缀
- `is_empty`, `is_not_empty`: 空值检查

## 类设计

### WhileVertex

```python
class WhileVertex(FunctionVertex):
    def __init__(
        self,
        id: str,
        name: str = None,
        execute_task: Callable[[Dict[str, Any], WorkflowContext[T]], Any] = None,
        condition_task: Callable[[Dict[str, Any], WorkflowContext[T]], bool] = None,
        conditions: List[WhileCondition] = None,
        logical_operator: str = "and",
        max_iterations: int = None,
        params: Dict[str, Any] = None,
        variables: List[Dict[str, Any]] = None,
    )
```

#### 参数说明
- `execute_task`: 循环体执行逻辑的函数（必需）
- `condition_task`: 条件判断逻辑的函数（与conditions二选一）
- `conditions`: 条件列表（与condition_task二选一）
- `logical_operator`: 多个条件之间的逻辑操作符（"and" 或 "or"）
- `max_iterations`: 最大迭代次数（可选）

### WhileCondition

```python
class WhileCondition:
    def __init__(
        self,
        variable_selector: Dict[str, str],
        operator: str,
        value: Any,
        logical_operator: str = "and"
    )
```

#### 参数说明
- `variable_selector`: 变量选择器，包含SOURCE_SCOPE, SOURCE_VAR, LOCAL_VAR
- `operator`: 比较操作符
- `value`: 比较值
- `logical_operator`: 逻辑操作符

## 使用示例

### 示例1：使用condition_task的简单计数

```python
from vertex_flow.workflow.vertex import WhileVertex
from vertex_flow.workflow.workflow import Workflow
from vertex_flow.workflow.context import WorkflowContext

# 创建工作流
workflow = Workflow("counter_workflow")

# 创建计数器
counter = {"count": 0}

def execute_logic(inputs):
    """执行逻辑：计数器加1"""
    counter["count"] += 1
    return {"count": counter["count"]}

def condition_logic(inputs):
    """条件逻辑：计数器小于5时继续"""
    return counter["count"] < 5

# 创建WhileVertex
while_vertex = WhileVertex(
    id="counter_while",
    name="计数循环",
    execute_task=execute_logic,
    condition_task=condition_logic
)

workflow.add_vertex(while_vertex)
context = WorkflowContext(workflow)
while_vertex.execute(inputs={}, context=context)

# 结果：循环执行5次
result = while_vertex.output
print(f"执行了 {result['iteration_count']} 次循环")
```

### 示例2：使用conditions列表的条件判断

```python
from vertex_flow.workflow.vertex import WhileVertex, WhileCondition, SourceVertex
from vertex_flow.workflow.constants import SOURCE_SCOPE, SOURCE_VAR, LOCAL_VAR

# 创建源顶点
source_vertex = SourceVertex(id="data_source")
source_vertex.output = {"value": 1}
workflow.add_vertex(source_vertex)

def execute_logic(inputs):
    """执行逻辑：值乘以2"""
    current_value = inputs.get("value", 1)
    new_value = current_value * 2
    source_vertex.output = {"value": new_value}
    return {"value": new_value}

# 创建条件：value < 100
condition = WhileCondition(
    variable_selector={
        SOURCE_SCOPE: "data_source",
        SOURCE_VAR: "value",
        LOCAL_VAR: "value"
    },
    operator="<",
    value=100
)

while_vertex = WhileVertex(
    id="multiply_while",
    execute_task=execute_logic,
    conditions=[condition],
    variables=[
        {
            SOURCE_SCOPE: "data_source",
            SOURCE_VAR: "value",
            LOCAL_VAR: "value"
        }
    ]
)
```

### 示例3：最大迭代次数限制

```python
while_vertex = WhileVertex(
    id="limited_while",
    execute_task=execute_logic,
    condition_task=lambda inputs: True,  # 无限循环条件
    max_iterations=10  # 最多执行10次
)
```

## 输出格式

WhileVertex的输出包含以下信息：

```python
{
    "results": [result1, result2, ...],  # 每次迭代的结果列表
    "iteration_count": 5,                # 实际执行的迭代次数
    "final_inputs": {...}               # 最终的输入状态
}
```

## 错误处理

### 验证错误
- 缺少 `execute_task` 时抛出 ValueError
- 同时缺少 `condition_task` 和 `conditions` 时抛出 ValueError
- 同时提供 `condition_task` 和 `conditions` 时抛出 ValueError
- 无效的 `logical_operator` 时抛出 ValueError

### 运行时错误
- 变量不存在时抛出 ValueError
- 不支持的操作符时抛出 ValueError
- 执行过程中的异常会被捕获并记录，循环会自动跳出

## 最佳实践

1. **选择合适的条件方式**
   - 简单条件使用 `condition_task`
   - 复杂条件或需要变量依赖时使用 `conditions`

2. **设置最大迭代次数**
   - 总是设置 `max_iterations` 避免无限循环
   - 根据业务需求合理设置上限

3. **错误处理**
   - 在 `execute_task` 中添加适当的错误处理
   - 使用日志记录循环执行状态

4. **性能考虑**
   - 避免在循环中进行重量级操作
   - 合理设计循环退出条件

## 与现有系统的集成

WhileVertex已经集成到现有的vertex系统中：

1. **模块导入**: 已添加到 `vertex_flow.workflow.vertex.__init__.py`
2. **工作流兼容**: 完全兼容现有的Workflow和WorkflowContext
3. **边连接**: 支持使用 `.to()` 方法连接其他顶点
4. **变量依赖**: 支持现有的变量依赖解析机制

## 测试

项目包含完整的测试套件：
- `test_while_vertex.py`: 单元测试
- `while_vertex_example.py`: 使用示例

运行测试：
```bash
python -m pytest vertex_flow/tests/test_while_vertex.py -v
```

运行示例：
```bash
python vertex_flow/examples/while_vertex_example.py
```