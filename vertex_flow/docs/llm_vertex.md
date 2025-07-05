# LLMVertex 文档

> **注意**: 关于变量传递和依赖管理的详细说明，请参考 [Variables 变量透出机制和选择机制](VARIABLES_MECHANISM.md) 文档。

## 概述

`LLMVertex` 是 VertexFlow 框架中专门用于大语言模型（LLM）交互的顶点类型。它继承自 `Vertex` 基类，提供了完整的聊天对话功能，支持消息管理、工具调用、预处理和后处理等高级特性。

## 设计理念

### 1. 对话管理
- **消息历史**: 自动管理对话历史和上下文
- **角色支持**: 支持 system、user、assistant 等多种角色
- **格式标准化**: 遵循 OpenAI 消息格式标准

### 2. 模型抽象
- **提供者无关**: 支持多种 LLM 提供者（OpenAI、Claude、本地模型等）
- **统一接口**: 通过 `ChatProvider` 抽象统一不同模型的调用方式
- **参数配置**: 支持温度、最大令牌数等模型参数配置

### 3. 扩展能力
- **工具调用**: 支持 Function Calling 和工具链集成
- **预处理**: 支持输入消息的预处理和格式化
- **后处理**: 支持输出结果的后处理和解析

## 核心特性

### 1. 消息管理
- 自动构建和维护对话历史
- 支持多轮对话上下文
- 智能消息格式转换

### 2. 模型集成
- 支持多种 LLM 提供者
- 统一的聊天接口
- 灵活的参数配置

### 3. 工具支持
- Function Calling 集成
- 自定义工具链
- 工具结果处理

### 4. 处理流水线
- 输入预处理钩子
- 输出后处理钩子
- 错误处理机制

## 类设计

### LLMVertex

```python
class LLMVertex(Vertex[T]):
    """大语言模型顶点，支持聊天对话"""
    
    def __init__(
        self,
        id: str,
        name: str = None,
        params: Dict[str, Any] = None,
        variables: List[Dict[str, Any]] = None,
    )
```

### 参数配置

`params` 字典支持以下配置项：

- **model**: `ChatProvider` 实例，必需
- **system**: 系统提示词字符串
- **tools**: 工具列表，支持 Function Calling
- **preprocess**: 预处理函数
- **postprocess**: 后处理函数
- **temperature**: 模型温度参数
- **max_tokens**: 最大令牌数
- **其他模型参数**: 传递给底层模型的参数

## 使用示例

### 基本聊天

```python
from vertex_flow.workflow.vertex import LLMVertex
from vertex_flow.providers.chat import OpenAIChatProvider

# 创建聊天提供者
chat_provider = OpenAIChatProvider(
    api_key="your-api-key",
    model="gpt-3.5-turbo"
)

# 创建 LLM 顶点
llm_vertex = LLMVertex(
    id="chat_vertex",
    name="聊天助手",
    params={
        "model": chat_provider,
        "system": "你是一个有用的AI助手。",
        "temperature": 0.7,
        "max_tokens": 1000
    }
)

# 执行对话
result = llm_vertex.execute(
    inputs={"message": "你好，请介绍一下自己。"},
    context=workflow_context
)

print(llm_vertex.output["response"])  # AI 的回复
```

### 多轮对话

```python
# 第一轮对话
llm_vertex.execute(
    inputs={"message": "我想学习 Python 编程。"},
    context=context
)

# 第二轮对话（会保持上下文）
llm_vertex.execute(
    inputs={"message": "请推荐一些学习资源。"},
    context=context
)

# 查看完整对话历史
print(llm_vertex.messages)
```

### 自定义系统提示

```python
system_prompt = """
你是一个专业的代码审查助手。请按照以下要求审查代码：
1. 检查代码逻辑是否正确
2. 评估代码性能和效率
3. 提出改进建议
4. 指出潜在的安全问题

请用中文回复，格式要清晰易读。
"""

code_reviewer = LLMVertex(
    id="code_reviewer",
    name="代码审查助手",
    params={
        "model": chat_provider,
        "system": system_prompt,
        "temperature": 0.3  # 较低温度确保回复更准确
    }
)
```

### 工具调用（Function Calling）

```python
# 定义工具函数
def get_weather(location: str) -> str:
    """获取指定地点的天气信息"""
    # 模拟天气 API 调用
    return f"{location}今天晴天，温度25°C"

def calculate(expression: str) -> float:
    """计算数学表达式"""
    try:
        return eval(expression)
    except:
        return "计算错误"

# 定义工具描述
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "地点名称"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算数学表达式",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]

# 创建支持工具调用的 LLM 顶点
tool_llm = LLMVertex(
    id="tool_assistant",
    name="工具助手",
    params={
        "model": chat_provider,
        "system": "你是一个智能助手，可以使用工具来帮助用户。",
        "tools": tools
    }
)

# 使用工具
result = tool_llm.execute(
    inputs={"message": "北京今天天气怎么样？"},
    context=context
)
```

### 预处理和后处理

```python
def preprocess_message(inputs, context):
    """预处理输入消息"""
    message = inputs.get("message", "")
    
    # 添加时间戳
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 格式化消息
    formatted_message = f"[{timestamp}] {message}"
    
    return {"message": formatted_message}

def postprocess_response(response, context):
    """后处理模型响应"""
    # 提取关键信息
    content = response.get("response", "")
    
    # 添加元数据
    processed = {
        "response": content,
        "word_count": len(content.split()),
        "processed_at": datetime.now().isoformat()
    }
    
    return processed

# 创建带处理流水线的 LLM 顶点
processed_llm = LLMVertex(
    id="processed_llm",
    name="处理流水线LLM",
    params={
        "model": chat_provider,
        "system": "你是一个专业助手。",
        "preprocess": preprocess_message,
        "postprocess": postprocess_response
    }
)
```

### 消息格式自定义

```python
# 使用复杂的输入格式
complex_input = {
    "messages": [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮助你的吗？"},
        {"role": "user", "content": "请解释一下机器学习"}
    ]
}

result = llm_vertex.execute(
    inputs=complex_input,
    context=context
)

# 或者使用单个消息
simple_input = {
    "message": "什么是深度学习？"
}

result = llm_vertex.execute(
    inputs=simple_input,
    context=context
)
```

## 高级特性

### 1. 流式响应

```python
# 支持流式响应的聊天提供者
streaming_provider = OpenAIChatProvider(
    api_key="your-api-key",
    model="gpt-3.5-turbo",
    stream=True
)

streaming_llm = LLMVertex(
    id="streaming_llm",
    params={"model": streaming_provider}
)

# 流式执行
for chunk in streaming_llm.execute_stream(inputs={"message": "讲个故事"}):
    print(chunk, end="", flush=True)
```

### 2. 批量处理

```python
# 批量处理多个消息
batch_inputs = {
    "messages": [
        "翻译：Hello world",
        "翻译：Good morning",
        "翻译：Thank you"
    ]
}

batch_llm = LLMVertex(
    id="batch_translator",
    params={
        "model": chat_provider,
        "system": "你是一个专业翻译助手，请将英文翻译成中文。"
    }
)

results = batch_llm.execute_batch(inputs=batch_inputs)
```

### 3. 上下文管理

```python
# 自定义上下文管理
class CustomContextManager:
    def __init__(self, max_history=10):
        self.max_history = max_history
    
    def manage_context(self, messages):
        """管理对话上下文，保持最近的对话"""
        if len(messages) > self.max_history:
            # 保留系统消息和最近的对话
            system_msgs = [msg for msg in messages if msg["role"] == "system"]
            recent_msgs = messages[-(self.max_history-len(system_msgs)):]
            return system_msgs + recent_msgs
        return messages

context_manager = CustomContextManager(max_history=20)

managed_llm = LLMVertex(
    id="managed_llm",
    params={
        "model": chat_provider,
        "context_manager": context_manager
    }
)
```

## 错误处理

### 异常类型

```python
try:
    result = llm_vertex.execute(
        inputs={"message": "测试消息"},
        context=context
    )
except Exception as e:
    if "rate_limit" in str(e).lower():
        print("API 调用频率限制")
        # 实现重试逻辑
    elif "timeout" in str(e).lower():
        print("请求超时")
        # 处理超时
    else:
        print(f"其他错误: {e}")
```

### 重试机制

```python
import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    print(f"重试 {attempt + 1}/{max_retries}: {e}")
                    time.sleep(delay * (2 ** attempt))  # 指数退避
            return None
        return wrapper
    return decorator

# 在 LLM 顶点中使用重试
class RobustLLMVertex(LLMVertex):
    @retry_on_failure(max_retries=3)
    def execute(self, inputs, context):
        return super().execute(inputs, context)
```

## 性能优化

### 1. 缓存机制

```python
from functools import lru_cache
import hashlib

class CachedLLMVertex(LLMVertex):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}
    
    def _get_cache_key(self, inputs):
        """生成缓存键"""
        message = str(inputs)
        return hashlib.md5(message.encode()).hexdigest()
    
    def execute(self, inputs, context):
        cache_key = self._get_cache_key(inputs)
        
        if cache_key in self.cache:
            print("使用缓存结果")
            self.output = self.cache[cache_key]
            return self.output
        
        result = super().execute(inputs, context)
        self.cache[cache_key] = result
        return result
```

### 2. 异步处理

```python
import asyncio
from typing import AsyncGenerator

class AsyncLLMVertex(LLMVertex):
    async def execute_async(self, inputs, context):
        """异步执行"""
        # 异步调用模型
        response = await self.params["model"].chat_async(
            messages=self._build_messages(inputs, context)
        )
        
        self.output = {"response": response}
        return self.output
    
    async def execute_stream_async(self, inputs, context) -> AsyncGenerator[str, None]:
        """异步流式执行"""
        async for chunk in self.params["model"].chat_stream_async(
            messages=self._build_messages(inputs, context)
        ):
            yield chunk
```

## 与工作流集成

### 在工作流中使用

```python
from vertex_flow.workflow.workflow import Workflow
from vertex_flow.workflow.edge import Edge, Always
from vertex_flow.workflow.vertex import FunctionVertex

# 创建数据预处理顶点
def preprocess_data(inputs):
    text = inputs["raw_text"]
    cleaned = text.strip().lower()
    return {"cleaned_text": cleaned}

preprocess_vertex = FunctionVertex(
    id="preprocess",
    task=preprocess_data
)

# 创建 LLM 分析顶点
analysis_llm = LLMVertex(
    id="analysis",
    params={
        "model": chat_provider,
        "system": "分析以下文本的情感倾向，返回正面、负面或中性。"
    },
    variables=[
        {
            "source_scope": "preprocess",
            "source_var": "cleaned_text",
            "local_var": "text"
        }
    ]
)

# 创建结果处理顶点
def process_result(inputs):
    sentiment = inputs["analysis_result"]
    confidence = calculate_confidence(sentiment)
    return {
        "sentiment": sentiment,
        "confidence": confidence
    }

result_vertex = FunctionVertex(
    id="result_processor",
    task=process_result,
    variables=[
        {
            "source_scope": "analysis",
            "source_var": "response",
            "local_var": "analysis_result"
        }
    ]
)

# 构建工作流
workflow = Workflow()
workflow.add_vertex(preprocess_vertex)
workflow.add_vertex(analysis_llm)
workflow.add_vertex(result_vertex)

workflow.add_edge(Edge(preprocess_vertex, analysis_llm, Always()))
workflow.add_edge(Edge(analysis_llm, result_vertex, Always()))

# 执行工作流
workflow.execute(inputs={"raw_text": "这个产品真的很棒！"})
```

### 多 LLM 协作

```python
# 创建多个专门的 LLM 顶点
summarizer = LLMVertex(
    id="summarizer",
    params={
        "model": chat_provider,
        "system": "你是一个专业的文本摘要助手，请提供简洁准确的摘要。"
    }
)

translator = LLMVertex(
    id="translator",
    params={
        "model": chat_provider,
        "system": "你是一个专业翻译助手，请将中文翻译成英文。"
    },
    variables=[
        {
            "source_scope": "summarizer",
            "source_var": "response",
            "local_var": "text_to_translate"
        }
    ]
)

reviewer = LLMVertex(
    id="reviewer",
    params={
        "model": chat_provider,
        "system": "你是一个质量审查员，请评估翻译质量并提出改进建议。"
    },
    variables=[
        {
            "source_scope": "translator",
            "source_var": "response",
            "local_var": "translation"
        }
    ]
)

# 连接 LLM 顶点
workflow.add_edge(Edge(summarizer, translator, Always()))
workflow.add_edge(Edge(translator, reviewer, Always()))
```

## 调试和监控

### 日志记录

```python
import logging

# 配置详细日志
logging.basicConfig(level=logging.DEBUG)

# LLM 顶点会自动记录详细信息
llm_vertex = LLMVertex(
    id="debug_llm",
    params={
        "model": chat_provider,
        "system": "测试系统",
        "debug": True  # 启用调试模式
    }
)

# 执行时会看到详细日志
# DEBUG: Building messages for LLM vertex: debug_llm
# DEBUG: Input messages: [...]
# DEBUG: Model response: {...}
# INFO: LLM vertex debug_llm executed successfully
```

### 性能监控

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(name):
    start = time.time()
    yield
    end = time.time()
    print(f"{name} 耗时: {end - start:.2f} 秒")

class MonitoredLLMVertex(LLMVertex):
    def execute(self, inputs, context):
        with timer(f"LLM顶点 {self.id}"):
            return super().execute(inputs, context)
```

### 成本跟踪

```python
class CostTrackingLLMVertex(LLMVertex):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_tokens = 0
        self.total_cost = 0.0
    
    def execute(self, inputs, context):
        result = super().execute(inputs, context)
        
        # 假设模型返回了 token 使用信息
        if "usage" in result:
            tokens = result["usage"]["total_tokens"]
            cost = self._calculate_cost(tokens)
            
            self.total_tokens += tokens
            self.total_cost += cost
            
            print(f"本次调用: {tokens} tokens, ${cost:.4f}")
            print(f"累计: {self.total_tokens} tokens, ${self.total_cost:.4f}")
        
        return result
    
    def _calculate_cost(self, tokens):
        # 根据模型定价计算成本
        price_per_1k_tokens = 0.002  # 示例价格
        return (tokens / 1000) * price_per_1k_tokens
```

## 最佳实践

### 1. 系统提示设计

```python
# 好的系统提示
good_system_prompt = """
你是一个专业的代码审查助手。请按照以下标准审查代码：

## 审查要点
1. **功能正确性**: 代码是否实现了预期功能
2. **性能效率**: 是否存在性能瓶颈
3. **安全性**: 是否存在安全漏洞
4. **可维护性**: 代码是否易于理解和维护
5. **最佳实践**: 是否遵循语言和框架的最佳实践

## 输出格式
请使用以下格式输出审查结果：

### 总体评分
[1-10分]

### 主要问题
- 问题1: 描述和建议
- 问题2: 描述和建议

### 改进建议
- 建议1
- 建议2

请用中文回复，保持专业和建设性的语调。
"""

# 避免的做法
bad_system_prompt = "你是助手，帮我审查代码。"  # 太简单，缺乏具体指导
```

### 2. 错误恢复

```python
class ResilientLLMVertex(LLMVertex):
    def execute(self, inputs, context):
        try:
            return super().execute(inputs, context)
        except Exception as e:
            # 记录错误
            logging.error(f"LLM执行失败: {e}")
            
            # 返回默认响应
            self.output = {
                "response": "抱歉，我现在无法处理您的请求，请稍后再试。",
                "error": True,
                "error_message": str(e)
            }
            return self.output
```

### 3. 输入验证

```python
def validate_llm_inputs(inputs):
    """验证 LLM 输入"""
    if not inputs:
        raise ValueError("输入不能为空")
    
    if "message" not in inputs and "messages" not in inputs:
        raise ValueError("必须提供 'message' 或 'messages' 字段")
    
    if "message" in inputs:
        message = inputs["message"]
        if not isinstance(message, str) or not message.strip():
            raise ValueError("消息必须是非空字符串")
        
        if len(message) > 10000:  # 限制消息长度
            raise ValueError("消息长度不能超过10000字符")
    
    return True

class ValidatedLLMVertex(LLMVertex):
    def execute(self, inputs, context):
        validate_llm_inputs(inputs)
        return super().execute(inputs, context)
```

## 常见问题

### Q: 如何处理 API 调用限制？

A: 实现重试机制和速率限制：

```python
import time
from threading import Lock

class RateLimitedLLMVertex(LLMVertex):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_call_time = 0
        self.min_interval = 1.0  # 最小调用间隔（秒）
        self.lock = Lock()
    
    def execute(self, inputs, context):
        with self.lock:
            current_time = time.time()
            time_since_last_call = current_time - self.last_call_time
            
            if time_since_last_call < self.min_interval:
                sleep_time = self.min_interval - time_since_last_call
                time.sleep(sleep_time)
            
            result = super().execute(inputs, context)
            self.last_call_time = time.time()
            return result
```

### Q: 如何管理长对话的上下文？

A: 实现智能上下文截断：

```python
def smart_context_management(messages, max_tokens=4000):
    """智能管理对话上下文"""
    # 估算 token 数量（简化版本）
    def estimate_tokens(text):
        return len(text.split()) * 1.3
    
    total_tokens = sum(estimate_tokens(msg["content"]) for msg in messages)
    
    if total_tokens <= max_tokens:
        return messages
    
    # 保留系统消息和最近的对话
    system_messages = [msg for msg in messages if msg["role"] == "system"]
    other_messages = [msg for msg in messages if msg["role"] != "system"]
    
    # 从最新消息开始保留
    kept_messages = []
    current_tokens = sum(estimate_tokens(msg["content"]) for msg in system_messages)
    
    for msg in reversed(other_messages):
        msg_tokens = estimate_tokens(msg["content"])
        if current_tokens + msg_tokens <= max_tokens:
            kept_messages.insert(0, msg)
            current_tokens += msg_tokens
        else:
            break
    
    return system_messages + kept_messages
```

### Q: 如何实现流式响应？

A: 使用生成器和异步处理：

```python
class StreamingLLMVertex(LLMVertex):
    def execute_stream(self, inputs, context):
        """流式执行"""
        messages = self._build_messages(inputs, context)
        
        response_chunks = []
        for chunk in self.params["model"].chat_stream(messages):
            response_chunks.append(chunk)
            yield chunk
        
        # 保存完整响应
        full_response = "".join(response_chunks)
        self.output = {"response": full_response}
```

## 总结

`LLMVertex` 是 VertexFlow 框架中功能最丰富的顶点类型之一，提供了：

1. **完整的对话管理**: 支持多轮对话和上下文维护
2. **灵活的模型集成**: 支持多种 LLM 提供者和配置
3. **强大的工具支持**: 集成 Function Calling 和自定义工具
4. **可扩展的处理流水线**: 支持预处理和后处理钩子
5. **企业级特性**: 包括错误处理、性能监控和成本跟踪

通过合理使用 `LLMVertex`，可以构建智能、可靠的 AI 应用和工作流。