# Vertex - LLM/GraphLLM 工具

Vertex 是一个支持本地和云端大语言模型（LLM）推理与工作流编排的工具，提供简洁易用的 Web 聊天界面和强大的 VertexFlow 工作流引擎。支持本地 Ollama 部署的 Qwen-7B 模型，也可通过 API 调用外部模型，支持多模型协同、知识库检索、嵌入与重排序等高级能力。

## 功能特性

- 支持本地 Ollama 部署的 Qwen-7B 模型（chatbox 聊天界面）
- 支持通过 API 方式调用 DeepSeek、OpenRouter 等外部模型
- Web UI 聊天体验，支持上下文多轮对话
- 可扩展的客户端架构，便于集成更多模型
- 支持流式输出，实时显示生成内容
- 支持 VertexFlow 工作流编排与多模型协同
- 支持自定义 System Prompt
- 支持 DashVector 等多种向量引擎与知识库检索
- 支持多种嵌入与 Rerank 配置
- 兼容 Dify 工作流定义，便于迁移与扩展
- **新增：Function Tools** - 允许用户定义和注册自定义函数工具，以便在工作流中动态调用，增强工作流编排和实时聊天交互的能力。

## 环境要求

- Python 3.8 及以上
- Ollama（本地模型推理，详见 https://ollama.com ）

## 安装步骤

1. 安装 Ollama

   - 访问 [https://ollama.com/download](https://ollama.com/download)
   - 下载并安装适用于您系统的 Ollama

2. 克隆本仓库

   ```bash
   git clone git@github.com:ashione/vertex.git
   cd vertex
   ```

3. 安装依赖

   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

## 快速启动

### 方式一：命令行启动（推荐）

```bash
vertex
```

### 方式二：直接运行主程序

```bash
python src/app.py
```

### 方式三：开发模式运行

```bash
python -m src.app
```

### 方式四：VertexFlow 工作流模式

```bash
python -m vertex_flow.src.app
```

启动后，浏览器访问 [http://localhost:7860](http://localhost:7860) 进入 Web 聊天界面（支持工作流与多模型）。

## 可选参数

- `--host`：Ollama 服务地址（默认：http://localhost:11434）
- `--port`：Web UI 端口（默认：7860）
- `--model`：模型名称（local-qwen 表示本地模型，其他为 API 模型）
- `--api-key`：外部 API 密钥（如调用 DeepSeek 时必填）
- `--api-base`：外部 API 基础 URL
- `--config`：VertexFlow 工作流配置文件（如 llm.yml）
- `system_prompt`：支持在 Web UI 中自定义 System Prompt

## Ollama 本地模型准备

如需自动拉取和配置本地 Qwen-7B 模型，可运行：

```bash
python scripts/setup_ollama.py
```

该脚本会自动检测 Ollama 安装、服务状态，并拉取所需模型。

## 示例代码

### 构建与执行一个简单工作流

```python
from vertex_flow.workflow.vertex.vertex import SourceVertex, SinkVertex
from vertex_flow.workflow.workflow import Workflow, WorkflowContext

def source_func(inputs, context):
    return {"text": "Hello, Vertex Flow!"}

def sink_func(inputs, context):
    print("Workflow output:", inputs["source"])

context = WorkflowContext()
workflow = Workflow(context)
source = SourceVertex(id="source", task=source_func)
sink = SinkVertex(id="sink", task=sink_func)
workflow.add_vertex(source)
workflow.add_vertex(sink)
source | sink
workflow.execute_workflow()
```
          
## Function Tools 说明

Function Tools 是 VertexFlow 的一部分，旨在增强工作流编排和实时聊天交互的能力。它允许用户定义和注册自定义函数工具，以便在工作流中动态调用。

### 如何定义 Function Tool

要定义一个 Function Tool，您需要创建一个 `FunctionTool` 实例，并提供以下参数：
- `name`: 工具名称
- `description`: 工具描述
- `func`: 实际执行的函数
- `schema`: 参数的 JSON Schema（可选）

### 示例代码

以下是一个简单的 Function Tool 示例：

```python
from vertex_flow.workflow.tools.functions import FunctionTool

def example_func(inputs, context):
    return {"result": inputs["value"] * 2}

example_tool = FunctionTool(
    name="example_tool",
    description="一个简单的示例工具",
    func=example_func,
    schema={"type": "object", "properties": {"value": {"type": "integer"}}}
)
```

### 如何注册 Function Tool

注册 Function Tool 后，您可以在 `LLMVertex` 中动态调用它。确保工具描述符合 LLM 的协议要求。

### 使用方法

在工作流中，您可以通过 `LLMVertex` 调用注册的 Function Tool，并处理其返回结果。

希望这些信息能帮助您更好地理解和使用 Function Tools。


## 示例用例

以下是一个使用`curl`命令与API进行交互的示例：

### 流式工作流执行

您可以使用以下`curl`命令来执行一个流式工作流请求：

```bash
curl -X POST "http://localhost:8999/workflow" --no-buffer \
   -H "Content-Type: application/json" -H "Accept: text/event-stream" \
   -d '{
     "stream": true,
     "workflow_name": "if_else_test-2",
     "env_vars": {},
     "user_vars": {"text": "333"},
     "content": "今天是2025年5月18日，历史上有什么故事发生？先主要列出10个。"
   }'
```

#### 参数说明

- `stream`: 指定是否为流式模式，`true`表示启用流式模式。
- `workflow_name`: 工作流的名称。
- `env_vars`: 环境变量的字典。
- `user_vars`: 用户变量的字典。
- `content`: 需要处理的文本内容。

#### 返回结果

该请求将返回一个流式响应，其中包含工作流执行的结果。每个结果块将以JSON格式返回，包含以下字段：
- `output`: 处理后的输出内容。
- `status`: 执行状态，`true`表示成功。
- `message`: 错误信息（如果有）。

## API 文档说明

- `Workflow.add_vertex(vertex)`：添加顶点到工作流。
- `vertex1 | vertex2`：连接两个顶点，自动添加边。
- `Workflow.execute_workflow(source_inputs)`：执行工作流，可传入初始输入。
- `Workflow.result()`：获取 SINK 顶点的输出结果。
- `WorkflowContext`：用于管理环境参数、用户参数和顶点输出。

## Dify 工作流兼容说明

- 支持 Dify 风格的变量占位符（如 `{{#env.xxx#}}`、`{{user.var.xxx}}`）。
- `WorkflowContext` 支持环境参数和用户参数，便于与 Dify 工作流参数体系对接。
- 顶点类型（如 LLM、Embedding、Rerank、IfElse）可直接映射 Dify 工作流节点。
- `IfElseVertex` 支持多条件分支，兼容 Dify 的条件跳转逻辑。
- 支持 YAML 工作流结构的序列化与反序列化，便于与 Dify 工作流配置文件互通。

## 常见问题

- 启动报错"无法连接到 Ollama 服务"：请确保 Ollama 已安装并启动，可手动打开 Ollama 应用或运行 `python scripts/setup_ollama.py`。
- 需要调用外部模型时，请在 Web UI 配置 API Key 和 Base URL。
- 如遇到 API 连接问题，请检查网络连接和 API 密钥是否正确。
- VertexFlow 工作流模式下，建议参考 `config/llm.yml` 配置多模型与知识库参数。
- 如需自定义 system prompt，可在 Web UI 中直接填写。

## 目录结构说明

```
vertex/
├── src/
│   ├── app.py              # 主应用入口
│   ├── native_client.py    # 本地 Ollama 客户端
│   ├── model_client.py     # 通用 API 客户端
│   ├── langchain_client.py # LangChain 客户端
│   ├── chat_util.py        # 聊天历史格式化工具
│   └── utils/
│       └── logger.py       # 日志工具
├── vertex_flow/
│   ├── src/                # VertexFlow 工作流主程序
│   ├── workflow/           # 工作流与 LLM 顶点定义
│   ├── utils/              # 工具与日志
├── scripts/
│   └── setup_ollama.py     # Ollama 环境与模型自动配置脚本
├── requirements.txt
├── setup.py
└── README.md
```
（VertexFlow 相关目录已集成，支持高级工作流与多模型协同）

## 开发计划

- [ ] 支持更多本地模型（如 LLaMA、Mistral 等）
- [ ] 添加知识库检索功能
- [ ] 支持文档上传和分析
- [ ] 增加图表生成功能
- [ ] 提供 API 服务接口
- [ ] 工作流可视化与多模型协同
- [ ] 支持自定义工具调用与插件扩展

## 贡献指南

欢迎提交 Pull Request 或 Issue 来帮助改进项目。贡献前请先查看现有 Issue，确保不会重复工作。