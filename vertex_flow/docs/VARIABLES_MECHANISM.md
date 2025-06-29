# Variables 变量透出机制和选择机制

## 概述

Variables 机制是 VertexFlow 框架中的核心功能，用于实现顶点之间的数据传递、依赖关系管理和变量暴露。它提供了灵活的数据流控制，支持复杂的工作流构建。

## 核心概念

### 1. 变量定义结构

每个变量定义包含以下字段：

```python
{
    "source_scope": "source_vertex_id",  # 源顶点ID或作用域
    "source_var": "output_variable",     # 源变量名
    "local_var": "local_variable"        # 本地变量名（可选）
}
```

### 2. 变量类型

#### 内部变量（Internal Variables）
- 在同一工作流或子图内部的顶点间传递
- 通过 `source_scope` 指定源顶点ID

#### 外部变量（External Variables）
- 从外部输入或父工作流传递到当前顶点
- `source_scope` 为空或 `None`

#### 暴露变量（Exposed Variables）
- 从子图内部暴露给外部使用
- 通过 VertexGroup 的 `exposed_outputs` 配置

## 变量透出机制

### 1. 基础透出

#### 顶点间数据传递
```python
# 从顶点A传递数据到顶点B
vertex_b = FunctionVertex(
    id="vertex_b",
    task=process_data,
    variables=[
        {
            "source_scope": "vertex_a",
            "source_var": "result",
            "local_var": "input_data"
        }
    ]
)
```

#### 自动依赖解析
```python
# 系统自动解析依赖关系
def resolve_dependencies(self, variable_selector=None, inputs=None):
    resolved_values = {}
    
    for var_def in self.variables:
        source_value = self._get_variable_value(var_def)
        local_name = var_def.get("local_var") or var_def["source_var"]
        resolved_values[local_name] = source_value
    
    return resolved_values
```

### 2. 子图变量透出

#### VertexGroup 变量暴露
```python
# 配置子图暴露的变量
group = VertexGroup(
    id="processing_group",
    subgraph_vertices=[vertex1, vertex2, vertex3],
    exposed_outputs=[
        {
            "vertex_id": "vertex1",
            "variable": "result",
            "exposed_as": "step1_output"
        },
        {
            "vertex_id": "vertex2", 
            "variable": "processed_data",
            "exposed_as": "final_result"
        }
    ]
)
```

#### 子图上下文管理
```python
class SubgraphContext:
    def __init__(self, parent_context=None):
        self.parent_context = parent_context
        self.exposed_variables = {}
    
    def expose_variable(self, internal_vertex_id, variable_name, exposed_name=None):
        """暴露内部变量给外部"""
        exposed_name = exposed_name or variable_name
        internal_output = self.get_internal_output(internal_vertex_id)
        
        if isinstance(internal_output, dict) and variable_name in internal_output:
            self.exposed_variables[exposed_name] = internal_output[variable_name]
        else:
            self.exposed_variables[exposed_name] = internal_output
```

### 3. 工作流级变量透出

#### 全局变量管理
```python
class WorkflowContext:
    def __init__(self, workflow):
        self.workflow = workflow
        self.vertex_outputs = {}
        self.exposed_variables = {}
    
    def store_output(self, vertex_id, output_data):
        """存储顶点输出"""
        self.vertex_outputs[vertex_id] = output_data
    
    def get_output(self, vertex_id, variable_name=None):
        """获取顶点输出"""
        output = self.vertex_outputs.get(vertex_id)
        if variable_name and isinstance(output, dict):
            return output.get(variable_name)
        return output
```

## 变量选择机制

### 1. 变量选择器

#### 基础选择器
```python
# 选择特定顶点的特定变量
variable_selector = {
    "source_scope": "data_processor",
    "source_var": "processed_data",
    "local_var": "input"
}
```

#### 动态选择器
```python
# 根据条件动态选择变量
def dynamic_variable_selector(inputs, context):
    if inputs.get("use_processed"):
        return {
            "source_scope": "processor",
            "source_var": "processed_data"
        }
    else:
        return {
            "source_scope": "raw_data",
            "source_var": "data"
        }
```

### 2. 变量优先级

#### 优先级顺序
1. **直接输入变量** - 通过 `inputs` 参数直接传递
2. **依赖变量** - 通过 `variables` 配置的依赖关系
3. **上下文变量** - 从工作流上下文获取
4. **默认值** - 顶点内部定义的默认值

#### 变量覆盖机制
```python
def resolve_variables(self, inputs, context):
    """解析变量，支持优先级和覆盖"""
    resolved = {}
    
    # 1. 处理直接输入
    if inputs:
        resolved.update(inputs)
    
    # 2. 处理依赖变量
    dependencies = self.resolve_dependencies(inputs=inputs)
    resolved.update(dependencies)
    
    # 3. 处理上下文变量
    context_vars = context.get_variables() if context else {}
    resolved.update(context_vars)
    
    return resolved
```

### 3. 条件变量选择

#### While顶点条件选择
```python
# 基于变量值的条件判断
condition = WhileCondition(
    variable_selector={
        "source_scope": "counter",
        "source_var": "count",
        "local_var": "current_count"
    },
    operator="<",
    value=10
)

while_vertex = WhileVertex(
    id="loop_vertex",
    execute_task=process_data,
    conditions=[condition]
)
```

#### 多条件逻辑
```python
# 支持AND/OR逻辑的条件组合
conditions = [
    WhileCondition(
        variable_selector={"source_scope": "data", "source_var": "size"},
        operator=">",
        value=0
    ),
    WhileCondition(
        variable_selector={"source_scope": "data", "source_var": "valid"},
        operator="==",
        value=True
    )
]

while_vertex = WhileVertex(
    id="complex_loop",
    execute_task=process_data,
    conditions=conditions,
    logical_operator="and"  # 或 "or"
)
```

## 实际应用场景

### 1. LLM 工作流变量传递

```python
# 文本预处理 -> LLM分析 -> 结果处理
preprocess_vertex = FunctionVertex(
    id="preprocess",
    task=clean_text
)

analysis_llm = LLMVertex(
    id="analysis",
    params={
        "model": chat_provider,
        "system": "分析文本情感"
    },
    variables=[
        {
            "source_scope": "preprocess",
            "source_var": "cleaned_text",
            "local_var": "text"
        }
    ]
)

result_vertex = FunctionVertex(
    id="result_processor",
    task=format_result,
    variables=[
        {
            "source_scope": "analysis",
            "source_var": "response",
            "local_var": "analysis_result"
        }
    ]
)
```

### 2. RAG 工作流变量管理

```python
# 文档嵌入 -> 向量存储 -> 语义搜索
embedding_vertex = EmbeddingVertex(
    id="embedder",
    params={"embedding_provider": embedding_provider}
)

vector_store_vertex = VectorStoreVertex(
    id="vector_store",
    params={"vector_engine": vector_engine},
    variables=[
        {
            "source_scope": "embedder",
            "source_var": "embedding",
            "local_var": "vector"
        },
        {
            "source_scope": "preprocessor",
            "source_var": "metadata",
            "local_var": "metadata"
        }
    ]
)

vector_query_vertex = VectorQueryVertex(
    id="searcher",
    params={"vector_engine": vector_engine},
    variables=[
        {
            "source_scope": "query_embedder",
            "source_var": "embedding",
            "local_var": "query_vector"
        }
    ]
)
```

### 3. 复杂子图变量暴露

```python
# 多步骤处理子图
processing_group = VertexGroup(
    id="complex_processing",
    subgraph_vertices=[step1, step2, step3],
    exposed_outputs=[
        {
            "vertex_id": "step1",
            "variable": "initial_result",
            "exposed_as": "step1_output"
        },
        {
            "vertex_id": "step2",
            "variable": "intermediate_result",
            "exposed_as": "step2_output"
        },
        {
            "vertex_id": "step3",
            "variable": "final_result",
            "exposed_as": "final_output"
        }
    ]
)

# 外部使用子图结果
external_vertex = FunctionVertex(
    id="external_processor",
    task=external_process,
    variables=[
        {
            "source_scope": "complex_processing",
            "source_var": "final_output",
            "local_var": "data"
        }
    ]
)
```

## 高级特性

### 1. 变量验证

#### 变量存在性检查
```python
def validate_variables(self, template, variables):
    """验证模板中使用的变量是否都已提供"""
    import re
    
    # 提取模板中的变量占位符
    pattern = r'\{(\w+)\}'
    required_vars = set(re.findall(pattern, template))
    provided_vars = set(variables.keys())
    
    missing_vars = required_vars - provided_vars
    if missing_vars:
        raise ValueError(f"Missing required variables: {missing_vars}")
    
    return variables
```

#### 类型检查
```python
def validate_variable_types(self, variables, expected_types):
    """验证变量类型"""
    for var_name, expected_type in expected_types.items():
        if var_name in variables:
            value = variables[var_name]
            if not isinstance(value, expected_type):
                raise TypeError(
                    f"Variable {var_name} expected {expected_type}, got {type(value)}"
                )
```

### 2. 变量转换

#### 自动类型转换
```python
def convert_variables(self, variables, conversions):
    """根据配置自动转换变量类型"""
    converted = {}
    
    for var_name, value in variables.items():
        if var_name in conversions:
            conversion_func = conversions[var_name]
            converted[var_name] = conversion_func(value)
        else:
            converted[var_name] = value
    
    return converted
```

#### 数据格式转换
```python
# 示例：文本到列表的转换
conversions = {
    "text_list": lambda x: x.split('\n') if isinstance(x, str) else x,
    "json_data": lambda x: json.loads(x) if isinstance(x, str) else x
}
```

### 3. 变量缓存

#### 缓存机制
```python
class VariableCache:
    def __init__(self):
        self.cache = {}
        self.ttl = 300  # 5分钟TTL
    
    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key, value):
        self.cache[key] = (value, time.time())
```

## 错误处理

### 1. 常见错误类型

#### 变量不存在
```python
try:
    source_value = self._get_variable_value(var_def)
except ValueError as e:
    logging.error(f"Variable not found: {e}")
    # 使用默认值或抛出异常
    raise
```

#### 类型不匹配
```python
def validate_variable_type(self, variable_name, value, expected_type):
    if not isinstance(value, expected_type):
        raise TypeError(
            f"Variable {variable_name} must be {expected_type}, got {type(value)}"
        )
```

#### 循环依赖
```python
def detect_circular_dependency(self, vertex_id, visited=None):
    """检测循环依赖"""
    if visited is None:
        visited = set()
    
    if vertex_id in visited:
        raise ValueError(f"Circular dependency detected: {vertex_id}")
    
    visited.add(vertex_id)
    
    for var_def in self.variables:
        if var_def.get("source_scope"):
            source_vertex = self.workflow.get_vertice_by_id(var_def["source_scope"])
            if source_vertex:
                source_vertex.detect_circular_dependency(vertex_id, visited)
    
    visited.remove(vertex_id)
```

### 2. 错误恢复策略

#### 优雅降级
```python
def resolve_variables_with_fallback(self, inputs, context):
    """带降级策略的变量解析"""
    try:
        return self.resolve_dependencies(inputs=inputs)
    except ValueError as e:
        logging.warning(f"Variable resolution failed: {e}, using fallback")
        return self.get_fallback_values()
```

#### 重试机制
```python
def resolve_variables_with_retry(self, inputs, context, max_retries=3):
    """带重试的变量解析"""
    for attempt in range(max_retries):
        try:
            return self.resolve_dependencies(inputs=inputs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logging.warning(f"Attempt {attempt + 1} failed: {e}, retrying...")
            time.sleep(1)
```

## 性能优化

### 1. 变量解析优化

#### 延迟解析
```python
class LazyVariableResolver:
    def __init__(self):
        self.resolved_cache = {}
    
    def get_variable(self, var_def, inputs, context):
        cache_key = f"{var_def['source_scope']}:{var_def['source_var']}"
        
        if cache_key not in self.resolved_cache:
            self.resolved_cache[cache_key] = self._resolve_variable(var_def, inputs, context)
        
        return self.resolved_cache[cache_key]
```

#### 批量解析
```python
def resolve_variables_batch(self, variable_defs, inputs, context):
    """批量解析多个变量"""
    resolved = {}
    
    # 按源顶点分组
    vertex_groups = {}
    for var_def in variable_defs:
        source_scope = var_def.get("source_scope")
        if source_scope not in vertex_groups:
            vertex_groups[source_scope] = []
        vertex_groups[source_scope].append(var_def)
    
    # 批量获取每个顶点的输出
    for source_scope, vars in vertex_groups.items():
        if source_scope:
            source_vertex = self.workflow.get_vertice_by_id(source_scope)
            if source_vertex and source_vertex.output:
                for var_def in vars:
                    source_var = var_def["source_var"]
                    local_var = var_def.get("local_var", source_var)
                    resolved[local_var] = source_vertex.output.get(source_var)
    
    return resolved
```

### 2. 内存优化

#### 变量引用计数
```python
class VariableReferenceManager:
    def __init__(self):
        self.reference_counts = {}
    
    def add_reference(self, variable_key):
        self.reference_counts[variable_key] = self.reference_counts.get(variable_key, 0) + 1
    
    def remove_reference(self, variable_key):
        if variable_key in self.reference_counts:
            self.reference_counts[variable_key] -= 1
            if self.reference_counts[variable_key] <= 0:
                del self.reference_counts[variable_key]
                return True  # 可以清理
        return False
```

## 最佳实践

### 1. 变量命名规范

#### 命名约定
```python
# 使用描述性的变量名
variables=[
    {
        "source_scope": "text_preprocessor",
        "source_var": "cleaned_text",
        "local_var": "input_text"  # 清晰表达用途
    }
]

# 避免使用缩写
# 错误: {"source_var": "txt", "local_var": "inp"}
# 正确: {"source_var": "text", "local_var": "input"}
```

#### 命名空间管理
```python
# 使用前缀避免命名冲突
variables=[
    {
        "source_scope": "step1_processor",
        "source_var": "result",
        "local_var": "step1_result"
    },
    {
        "source_scope": "step2_processor", 
        "source_var": "result",
        "local_var": "step2_result"
    }
]
```

### 2. 变量组织策略

#### 按功能分组
```python
# 将相关变量组织在一起
input_variables = [
    {"source_scope": "data_source", "source_var": "raw_data"},
    {"source_scope": "config", "source_var": "settings"}
]

output_variables = [
    {"source_scope": "processor", "source_var": "result"},
    {"source_scope": "validator", "source_var": "validation_status"}
]
```

#### 层次化组织
```python
# 使用嵌套结构组织复杂变量
complex_variables = {
    "input": {
        "data": {"source_scope": "data_source", "source_var": "data"},
        "config": {"source_scope": "config", "source_var": "settings"}
    },
    "output": {
        "result": {"source_scope": "processor", "source_var": "result"},
        "metadata": {"source_scope": "processor", "source_var": "metadata"}
    }
}
```

### 3. 错误处理策略

#### 防御性编程
```python
def safe_variable_resolution(self, var_def, inputs, context):
    """安全的变量解析"""
    try:
        return self._get_variable_value(var_def)
    except (ValueError, KeyError) as e:
        logging.warning(f"Variable resolution failed: {e}")
        return self.get_default_value(var_def)
    except Exception as e:
        logging.error(f"Unexpected error in variable resolution: {e}")
        raise
```

#### 验证和测试
```python
def validate_workflow_variables(self, workflow):
    """验证工作流中的变量配置"""
    for vertex in workflow.vertices:
        if hasattr(vertex, 'variables') and vertex.variables:
            for var_def in vertex.variables:
                # 检查源顶点是否存在
                if var_def.get("source_scope"):
                    source_vertex = workflow.get_vertice_by_id(var_def["source_scope"])
                    if not source_vertex:
                        raise ValueError(f"Source vertex {var_def['source_scope']} not found")
                
                # 检查必需字段
                required_fields = ["source_var"]
                for field in required_fields:
                    if field not in var_def:
                        raise ValueError(f"Missing required field: {field}")
```

### 4. 性能优化建议

#### 减少变量传递
```python
# 避免不必要的变量传递
# 错误：传递整个对象
variables=[{"source_scope": "processor", "source_var": "full_result"}]

# 正确：只传递需要的字段
variables=[{"source_scope": "processor", "source_var": "processed_data"}]
```

#### 使用缓存
```python
# 对于计算密集型的变量，使用缓存
@lru_cache(maxsize=128)
def expensive_variable_computation(self, input_data):
    # 复杂的计算逻辑
    return processed_result
```

## 总结

Variables 机制是 VertexFlow 框架的核心功能，提供了灵活、强大的数据流控制能力。通过合理使用变量透出和选择机制，可以构建复杂而高效的工作流系统。

关键要点：
1. **变量定义**：使用标准的三字段结构定义变量关系
2. **透出机制**：支持顶点间、子图间和工作流间的变量传递
3. **选择机制**：提供灵活的条件选择和优先级控制
4. **错误处理**：完善的错误检测和恢复机制
5. **性能优化**：多种优化策略提升执行效率

通过遵循最佳实践，可以充分发挥 Variables 机制的潜力，构建高质量的工作流应用。 