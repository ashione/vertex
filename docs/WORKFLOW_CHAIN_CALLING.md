# Workflow 链式调用功能

## 概述

VertexFlow 提供了三种灵活的构图方法来构建 workflow，满足不同场景的需求：

1. **🔗 `to()` 方法** - 创建 always edge 的链式调用
2. **🎯 `c_to()` 方法** - 创建 conditional edge 的链式调用  
3. **⚡ `|` 操作符** - 使用管道操作符构图（保持向后兼容）

## 功能特性

### ✨ 链式调用
所有三种方法都支持链式调用，返回目标 vertex 以便继续连接：

```python
# 链式调用示例
vertex_a.to(vertex_b).to(vertex_c).to(vertex_d)
vertex_a.c_to(vertex_b, "condition").to(vertex_c)
vertex_a | vertex_b | vertex_c | vertex_d
```

### 🔄 向后兼容
保留原有的 `__or__` 方法，确保现有代码无需修改即可运行。

## 使用方法

### 1. `to()` 方法 - Always Edge

用于创建无条件连接，适合线性工作流：

```python
from vertex_flow.workflow.vertex import SourceVertex, LLMVertex, SinkVertex
from vertex_flow.workflow.workflow import Workflow

# 创建 vertices
source = SourceVertex(id="source", name="数据源")
llm1 = LLMVertex(id="llm1", name="处理器1")
llm2 = LLMVertex(id="llm2", name="处理器2")
sink = SinkVertex(id="sink", name="输出")

# 链式调用构建流程
source.to(llm1).to(llm2).to(sink)
```

**语法：**
```python
def to(self, next_vertex: "Vertex[T]", edge_type: EdgeType = Edge.ALWAYS) -> "Vertex[T]"
```

### 2. `c_to()` 方法 - Conditional Edge

用于创建条件连接，适合分支工作流：

```python
# 创建条件分支
decision = LLMVertex(id="decision", name="决策节点")
success_path = LLMVertex(id="success", name="成功路径")
failure_path = LLMVertex(id="failure", name="失败路径")
final_process = LLMVertex(id="final", name="最终处理")

# 条件链式调用
decision.c_to(success_path, "true").to(final_process)
decision.c_to(failure_path, "false").to(final_process)
```

**语法：**
```python
def c_to(self, next_vertex: "Vertex[T]", condition_id: str = "true") -> "Vertex[T]"
```

**参数：**
- `next_vertex`: 目标节点
- `condition_id`: 条件标识符（默认："true"）

### 3. `|` 操作符 - 管道操作符

保持向后兼容的构图方法：

```python
# 使用管道操作符
source | preprocessor | analyzer | sink

# 支持分支
source | branch1 | aggregator
source | branch2 | aggregator
```

**语法：**
```python
def __or__(self, other: "Vertex[T]") -> "Vertex[T]"
```

## 应用场景

### 🔄 简单线性流程
```python
# 数据处理管道
data_source.to(validator).to(transformer).to(saver)
```

### 🌿 条件分支流程
```python
# 审批工作流
application.to(reviewer).c_to(approved_handler, "approved").to(notification_sender)
reviewer.c_to(rejected_handler, "rejected").to(notification_sender)
```

### 🎯 复杂混合流程
```python
# 混合使用三种方法
start | preprocessor                                    # 管道操作符
preprocessor.to(decision)                              # 链式调用
decision.c_to(route_a, "condition_a").to(postprocessor)  # 条件分支
decision.c_to(route_b, "condition_b")                  # 条件分支
route_b | postprocessor | end                          # 管道操作符
```

## 最佳实践

### 💡 选择合适的方法

| 场景 | 推荐方法 | 理由 |
|------|----------|------|
| 线性处理流程 | `to()` | 清晰直观，支持链式调用 |
| 条件分支流程 | `c_to()` | 明确表达条件逻辑 |
| 简单连接 | `\|` 操作符 | 简洁，向后兼容 |
| 复杂流程 | 混合使用 | 灵活应对不同需求 |

### ⚠️ 注意事项

1. **返回值**：所有方法都返回目标 vertex，支持链式调用
2. **边类型**：`to()` 创建 always edge，`c_to()` 创建 conditional edge
3. **兼容性**：三种方法可以在同一个 workflow 中混合使用
4. **错误处理**：传入非 Vertex 对象会抛出 `ValueError`

## 完整示例

```python
#!/usr/bin/env python3
from vertex_flow.workflow.vertex import SourceVertex, LLMVertex, SinkVertex
from vertex_flow.workflow.workflow import Workflow

def create_complex_workflow():
    # 创建 workflow
    workflow = Workflow()
    
    # 创建 vertices
    start = SourceVertex(id="start", name="开始")
    preprocessor = LLMVertex(id="preprocess", name="预处理")
    decision = LLMVertex(id="decision", name="决策节点")
    route_a = LLMVertex(id="route_a", name="路径A")
    route_b = LLMVertex(id="route_b", name="路径B")
    postprocessor = LLMVertex(id="postprocess", name="后处理")
    end = SinkVertex(id="end", name="结束")
    
    # 添加到 workflow
    for vertex in [start, preprocessor, decision, route_a, route_b, postprocessor, end]:
        workflow.add_vertex(vertex)
    
    # 混合使用三种构图方法
    start | preprocessor                                    # 管道操作符
    preprocessor.to(decision)                              # 链式调用
    decision.c_to(route_a, "route_a").to(postprocessor)   # 条件分支 + 链式
    decision.c_to(route_b, "route_b")                      # 条件分支
    route_b | postprocessor | end                          # 管道操作符
    
    return workflow

if __name__ == "__main__":
    workflow = create_complex_workflow()
    print(f"Created workflow with {len(workflow.edges)} edges")
```

## 总结

链式调用功能让 VertexFlow 的工作流构建更加灵活和直观：

- **🔗 `to()`** - 适合线性流程的链式调用
- **🎯 `c_to()`** - 适合条件分支的链式调用
- **⚡ `|`** - 保持向后兼容的管道操作符
- **🎨 混合使用** - 灵活应对复杂场景

选择最适合你场景的方法，享受更优雅的工作流构建体验！ 