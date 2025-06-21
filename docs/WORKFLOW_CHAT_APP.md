# Vertex Workflow Chat 应用

## 概述

Vertex Workflow Chat 是基于 Workflow LLM Vertex 的新一代聊天应用，它使用统一配置系统和强大的 LLM Vertex 功能，提供了更好的模型管理和聊天体验。

## 主要特性

### 🚀 **核心优势**

1. **统一配置系统**
   - 使用 `vertex_flow/config/llm.yml` 统一配置
   - 支持多种 LLM 提供商：DeepSeek、OpenRouter、Moonshot、Tongyi 等
   - 环境变量支持，便于部署管理

2. **基于 Workflow LLM Vertex**
   - 复用 workflow 系统的强大功能
   - 支持工具调用（Tool Calls）
   - 更好的错误处理和日志记录

3. **动态模型切换**
   - 运行时切换不同的 LLM 提供商
   - 实时显示可用模型列表
   - 无需重启应用

4. **现代化界面**
   - 基于 Gradio 的美观界面
   - 支持自定义系统提示
   - 响应式设计

5. **🎨 多模态支持**
   - 支持图片上传和图片URL输入
   - 基于 OpenRouter 的 Gemini 2.5 Pro 模型
   - 智能图片分析和描述
   - 文本+图片的混合对话

## 使用方法

### 启动应用

```bash
# 使用默认端口 7860
uv run vertex run

# 指定端口和主机
uv run vertex run --port 8080 --host 0.0.0.0

# 直接运行 workflow 应用
uv run python vertex_flow/src/workflow_app.py --port 7860
```

### 配置 LLM 模型

编辑 `vertex_flow/config/llm.yml` 文件：

```yaml
llm:
  deepseek:
    sk: ${llm.deepseek.sk:your-deepseek-api-key}
    enabled: true  # 启用此模型
    model-name: deepseek-chat
  
  openrouter:
    sk: ${llm.openrouter.sk:your-openrouter-api-key}
    enabled: false
    model-name: deepseek/deepseek-chat-v3-0324:free
  
  moonshoot:
    sk: ${llm.moonshoot.sk:your-moonshot-api-key}
    enabled: false
    model-name: moonshot-v1-128k
```

### 环境变量配置

```bash
# 设置 API 密钥
export llm_deepseek_sk="sk-your-deepseek-key"
export llm_openrouter_sk="sk-or-your-openrouter-key"
export llm_moonshoot_sk="sk-your-moonshot-key"

# 启动应用
uv run vertex run
```

## 界面功能

### 主要区域

1. **聊天区域**
   - 对话历史显示
   - 消息输入框
   - 发送和清除按钮

2. **多模态输入区域**
   - 图片上传组件：支持本地图片文件上传
   - 图片URL输入框：支持网络图片链接
   - 自动Base64编码：本地图片自动转换为兼容格式
   - 智能URL验证：检测不支持的图片源（如Discord）

3. **配置面板**
   - 系统提示自定义
   - 当前模型信息
   - 可用模型列表
   - 模型切换功能

### 系统提示

可以自定义系统提示来改变 AI 的行为：

```
你是一个专业的技术顾问，擅长回答编程和技术相关问题。
请提供详细、准确的技术建议。
```

### 模型切换

在界面右侧的"切换模型"输入框中输入提供商名称：

- `deepseek` - 切换到 DeepSeek 模型
- `openrouter` - 切换到 OpenRouter 模型
- `moonshoot` - 切换到 Moonshot 模型
- `tongyi` - 切换到通义千问模型

### 多模态输入

- 支持图片上传和图片URL输入
- 基于 OpenRouter 的 Gemini 2.5 Pro 模型
- 智能图片分析和描述
- 文本+图片的混合对话

## 与传统应用的对比

| 特性 | Workflow Chat App | 传统 App |
|------|------------------|----------|
| 配置系统 | 统一配置文件 | 命令行参数 |
| 模型管理 | 动态切换 | 固定模型 |
| 功能扩展 | 支持 Workflow 功能 | 基础聊天 |
| 错误处理 | 完善的异常处理 | 基础错误处理 |
| 界面设计 | 现代化 UI | 简单界面 |

## 技术架构

### 核心组件

1. **WorkflowChatApp**
   - 主应用类
   - 管理 LLM 模型和配置
   - 处理聊天逻辑

2. **VertexFlowService**
   - 统一配置服务
   - LLM 模型工厂
   - 配置管理

3. **LLMVertex**
   - Workflow 系统的 LLM 顶点
   - 支持工具调用
   - 完善的上下文管理

### 工作流程

```
用户输入 → WorkflowChatApp → LLMVertex → ChatModel → API调用 → 响应
```

## 故障排除

### 常见问题

1. **启动失败：配置文件错误**
   ```
   ❌ 启动失败: 无法获取聊天模型，请检查配置文件
   ```
   **解决方案：** 检查 `vertex_flow/config/llm.yml` 文件格式和 API 密钥

2. **模型切换失败**
   ```
   ❌ 无法切换到模型: deepseek
   ```
   **解决方案：** 确保目标模型在配置文件中存在且 API 密钥正确

3. **聊天错误**
   ```
   聊天错误: API调用失败
   ```
   **解决方案：** 检查网络连接和 API 密钥有效性

4. **多模态功能问题**
   ```
   ⚠️ 检测到Discord图片链接，可能不被支持
   ```
   **解决方案：** Discord图片链接不被支持，建议：
   - 下载图片后重新上传
   - 使用其他图片托管服务
   - 直接粘贴其他图片URL

5. **图片处理失败**
   ```
   图片处理失败，可能是图片格式不支持或链接无效
   ```
   **解决方案：**
   - 确保图片格式为常见格式（JPG、PNG等）
   - 检查图片链接是否可公开访问
   - 尝试使用其他图片

### 日志查看

应用会输出详细的日志信息，包括：
- 模型初始化状态
- 配置加载情况
- API 调用结果
- 错误详情

## 配置示例

### 完整配置文件示例

```yaml
llm:
  deepseek:
    sk: ${llm.deepseek.sk:sk-your-key}
    enabled: true
    model-name: deepseek-chat
  
  openrouter:
    sk: ${llm.openrouter.sk:sk-or-your-key}
    enabled: true  # 启用多模态支持
    model-name: google/gemini-2.5-pro  # Gemini 2.5 Pro 模型
  
  moonshoot:
    sk: ${llm.moonshoot.sk:sk-your-key}
    enabled: false
    model-name: moonshot-v1-128k
  
  tongyi:
    sk: ${llm.tongyi.sk:sk-your-key}
    enabled: false
    model-name: qwen-max

web:
  port: 7860
  host: 127.0.0.1
  workers: 1
```

### Docker 部署示例

```dockerfile
FROM python:3.9

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

ENV llm_deepseek_sk="your-api-key"
ENV llm_openrouter_sk="your-api-key"

EXPOSE 7860

CMD ["python", "vertex_flow/src/workflow_app.py", "--host", "0.0.0.0", "--port", "7860"]
```

### 多模态配置说明

要启用多模态功能，需要：

1. **启用 OpenRouter 提供商**
   ```yaml
   openrouter:
     enabled: true
     model-name: google/gemini-2.5-pro
   ```

2. **设置 OpenRouter API 密钥**
   ```bash
   export llm_openrouter_sk="sk-or-your-openrouter-api-key"
   ```

3. **确保网络访问**
   - 应用需要能够访问 OpenRouter API
   - 图片URL需要可公开访问

## 开发指南

### 扩展新的 LLM 提供商

1. 在 `vertex_flow/workflow/chat.py` 中添加新的 ChatModel 类
2. 在配置文件中添加相应的配置项
3. 测试模型切换功能

### 自定义界面

修改 `create_gradio_interface` 函数来自定义界面：
- 添加新的组件
- 修改样式和布局
- 增加新的功能按钮

## 总结

Vertex Workflow Chat 应用提供了一个现代化、可扩展的聊天界面，充分利用了 Vertex Flow 系统的强大功能。它不仅支持多种 LLM 提供商，还提供了灵活的配置管理和优雅的用户体验。

通过使用统一配置系统和 Workflow LLM Vertex，用户可以轻松地在不同模型之间切换，同时享受到 Workflow 系统带来的高级功能，如工具调用、上下文管理等。

### 🎨 多模态功能亮点

- **智能图片分析**：基于 Gemini 2.5 Pro 的强大图像理解能力
- **多种输入方式**：支持本地图片上传和网络图片URL
- **自动格式转换**：本地图片自动转换为兼容的Base64格式
- **智能错误处理**：对不支持的图片源提供友好提示
- **混合对话**：文本和图片的完美结合，提供更丰富的交互体验

多模态功能的加入使得 Vertex Workflow Chat 应用不仅是一个强大的文本聊天工具，更是一个能够理解和分析视觉内容的智能助手，为用户提供了更加全面和直观的AI交互体验。 