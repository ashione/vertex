# 工作流历史记录支持

本文档介绍如何在 Vertex Flow 工作流中使用历史记录功能，实现多轮对话和上下文保持。

## 概述

历史记录功能允许您在工作流中传入之前的对话历史，使 LLM 能够理解对话上下文，提供更连贯和相关的回复。

## 功能特性

- ✅ 支持多轮对话上下文保持
- ✅ 兼容文本和多模态内容
- ✅ 灵活的历史记录格式
- ✅ 与现有 API 完全兼容
- ✅ 支持流式和非流式输出
- ✅ 支持 MCP 增强功能

## 使用方法

### 1. 基本用法

在 `WorkflowInput` 中添加 `history` 字段：

```python
from vertex_flow.workflow.app.app import WorkflowInput

# 创建包含历史记录的输入
input_data = WorkflowInput(
    workflow_name="chat",
    content="继续我们之前的讨论",
    history=[
        {
            "role": "user",
            "content": "什么是人工智能？"
        },
        {
            "role": "assistant",
            "content": "人工智能是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统。"
        }
    ]
)
```

### 2. API 调用示例

通过 HTTP API 使用历史记录：

```bash
curl -X POST "http://localhost:8000/workflow" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "chat",
    "content": "能详细解释一下机器学习吗？",
    "history": [
      {
        "role": "user",
        "content": "什么是人工智能？"
      },
      {
        "role": "assistant",
        "content": "人工智能是计算机科学的一个分支..."
      }
    ],
    "stream": false,
    "enable_mcp": true
  }'
```

### 3. 多模态历史记录

支持包含图片的多模态对话历史：

```python
multimodal_history = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "这张图片显示的是什么？"},
            {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
        ]
    },
    {
        "role": "assistant",
        "content": "这张图片显示的是一只可爱的小猫咪。"
    }
]

input_data = WorkflowInput(
    workflow_name="multimodal_chat",
    content="这只猫咪看起来几岁了？",
    history=multimodal_history
)
```

## 历史记录格式

### 标准格式

每条历史记录应包含以下字段：

```python
{
    "role": "user" | "assistant",  # 角色：用户或助手
    "content": "消息内容"              # 消息内容
}
```

### 多模态格式

对于包含图片的消息：

```python
{
    "role": "user",
    "content": [
        {"type": "text", "text": "文本内容"},
        {"type": "image_url", "image_url": {"url": "图片URL"}}
    ]
}
```

## 完整参数示例

```python
input_data = WorkflowInput(
    workflow_name="advanced_chat",
    content="当前用户输入",
    history=[
        {"role": "user", "content": "历史问题"},
        {"role": "assistant", "content": "历史回答"}
    ],
    
    # 其他可选参数
    env_vars={"ENVIRONMENT": "production"},
    user_vars={"user_id": "12345"},
    image_url="https://example.com/current_image.jpg",
    stream=True,
    enable_mcp=True,
    
    # LLM 配置
    system_prompt="你是一个专业的AI助手",
    enable_reasoning=True,
    show_reasoning=True,
    temperature=0.7,
    max_tokens=2000,
    enable_search=True,
    enable_tools=True
)
```

## 最佳实践

### 1. 历史记录长度管理

```python
# 限制历史记录长度，避免 token 超限
def truncate_history(history, max_length=10):
    """保留最近的对话记录"""
    if len(history) > max_length:
        return history[-max_length:]
    return history

# 使用示例
truncated_history = truncate_history(long_history, max_length=8)
input_data = WorkflowInput(
    workflow_name="chat",
    content="新问题",
    history=truncated_history
)
```

### 2. 历史记录验证

```python
def validate_history(history):
    """验证历史记录格式"""
    for item in history:
        if "role" not in item or "content" not in item:
            raise ValueError("历史记录格式错误")
        if item["role"] not in ["user", "assistant"]:
            raise ValueError("角色必须是 'user' 或 'assistant'")
    return True

# 使用前验证
validate_history(history)
```

### 3. 内存优化

```python
# 对于长文本，考虑摘要化历史记录
def summarize_old_history(history, keep_recent=5):
    """摘要化旧的历史记录"""
    if len(history) <= keep_recent:
        return history
    
    # 保留最近的记录
    recent_history = history[-keep_recent:]
    
    # 摘要化旧记录
    old_history = history[:-keep_recent]
    summary = {
        "role": "assistant",
        "content": f"[历史对话摘要：共 {len(old_history)} 条记录，主要讨论了...]"
    }
    
    return [summary] + recent_history
```

## 错误处理

### 常见错误及解决方案

1. **历史记录格式错误**
   ```python
   # 错误：缺少必要字段
   bad_history = [{"content": "消息"}]  # 缺少 role
   
   # 正确：包含所有必要字段
   good_history = [{"role": "user", "content": "消息"}]
   ```

2. **Token 超限**
   ```python
   # 解决方案：截断或摘要化历史记录
   def handle_token_limit(history, max_tokens=4000):
       # 估算 token 数量并截断
       estimated_tokens = sum(len(item["content"]) // 4 for item in history)
       if estimated_tokens > max_tokens:
           return truncate_history(history, max_length=5)
       return history
   ```

3. **多模态内容处理**
   ```python
   # 确保图片 URL 有效
   def validate_image_urls(history):
       for item in history:
           if isinstance(item["content"], list):
               for content_item in item["content"]:
                   if content_item["type"] == "image_url":
                       url = content_item["image_url"]["url"]
                       # 验证 URL 格式
                       if not url.startswith(("http://", "https://")):
                           raise ValueError(f"无效的图片 URL: {url}")
   ```

## 性能考虑

1. **历史记录大小**：建议单次请求的历史记录不超过 20 条
2. **Token 限制**：注意模型的 token 限制，合理控制历史记录长度
3. **图片处理**：多模态内容会消耗更多 token，需要特别注意
4. **缓存策略**：对于频繁访问的历史记录，考虑使用缓存

## 示例代码

完整的使用示例请参考：
- `vertex_flow/examples/workflow_history_example.py` - 基本使用示例
- `vertex_flow/tests/test_workflow_history.py` - 测试用例

## 技术实现

历史记录功能的技术实现细节：

1. **数据流**：`WorkflowInput.history` → `create_llm_vertex()` → `LLMVertex/MCPLLMVertex`
2. **常量**：使用 `CONVERSATION_HISTORY` 常量传递历史记录
3. **兼容性**：与现有的流式输出、MCP 功能完全兼容
4. **验证**：通过 Pydantic 模型自动验证输入格式

## 更新日志

- **v1.0.0**: 初始版本，支持基本历史记录功能
- **v1.1.0**: 添加多模态历史记录支持
- **v1.2.0**: 优化性能，添加验证和错误处理

## 相关文档

- [工作流配置文档](./WORKFLOW_CHAT_APP.md)
- [MCP 集成文档](./MCP_INTEGRATION.md)
- [多模态功能文档](./MULTIMODAL_FEATURES.md)