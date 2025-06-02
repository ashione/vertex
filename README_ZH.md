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

## Web UI 使用指南

### 界面概览

Vertex 提供了直观易用的 Web 界面，包含以下主要功能模块：

1. **聊天界面** - 支持多轮对话和流式输出
2. **工作流编辑器** - 可视化工作流设计与执行
3. **配置管理** - 模型参数和系统设置

### 聊天功能使用

#### 基本聊天
- 在主页面的聊天输入框中输入问题
- 支持多轮对话，系统会自动维护上下文
- 支持实时流式输出，可以看到模型逐字生成回复

#### 模型切换
- 在聊天界面可以选择不同的模型：
  - `local-qwen`：本地 Ollama 部署的 Qwen-7B 模型
  - `deepseek-chat`：DeepSeek API 模型
  - `openrouter/*`：OpenRouter 平台的各种模型

#### 自定义 System Prompt
- 在聊天界面的设置中可以自定义 System Prompt
- 用于指导模型的行为和回复风格
- 支持实时修改和应用

### 工作流编辑器使用

#### 访问工作流编辑器
- 点击导航栏中的「工作流」按钮
- 或直接访问 [http://localhost:7860/workflow](http://localhost:7860/workflow)

#### 节点类型说明
- **开始节点**：工作流的入口点
- **LLM节点**：调用大语言模型进行文本生成
- **检索节点**：从知识库中检索相关信息
- **条件节点**：根据条件进行分支判断
- **函数节点**：执行自定义函数逻辑
- **结束节点**：工作流的出口点

#### 创建工作流
1. **添加节点**：从左侧节点面板拖拽节点到画布
2. **连接节点**：点击连接模式，然后点击两个节点建立连接
3. **配置节点**：选择节点后在右侧属性面板配置参数
4. **执行工作流**：点击执行按钮运行工作流
5. **查看输出**：在底部输出面板查看节点执行结果

#### 节点配置详解

**LLM节点配置**：
- 模型选择：支持本地和云端模型
- 系统提示词：定义模型行为
- 用户消息：支持变量占位符
- 温度：控制输出随机性（0-1）
- 最大令牌数：限制输出长度

**检索节点配置**：
- 索引名称：指定要检索的知识库
- 查询内容：支持变量占位符
- 检索数量：返回的相关文档数量

**条件节点配置**：
- 条件表达式：使用 Python 表达式
- 支持多分支条件判断

#### 变量系统
- **环境变量**：`{{#env.变量名#}}`
- **用户变量**：`{{user.var.变量名}}`
- **节点输出**：`{{节点ID.输出字段}}`

#### 工作流操作
- **保存工作流**：自动保存到本地
- **加载工作流**：从配置文件加载
- **导出工作流**：导出为 YAML 格式
- **自动布局**：自动整理节点位置

### 输出面板功能

#### 查看节点输出
- 选择已执行的节点，在底部输出面板查看结果
- 支持 Markdown 格式渲染
- 支持原始内容查看
- 支持一键复制输出内容

#### 面板控制
- **展开**：将输出面板展开到全屏
- **最小化**：收起输出面板
- **拖拽调整**：拖拽分隔条调整面板高度

### 配置管理

#### API 配置
- 在配置页面设置外部 API 的密钥和基础 URL
- 支持 DeepSeek、OpenRouter 等多种 API 服务
- 配置后即可在聊天和工作流中使用对应模型

#### 配置文件安全（自动脱敏）
- **自动脱敏**：系统在提交前自动对配置文件中的敏感信息（API密钥、密钥等）进行脱敏处理
- **支持格式**：自动检测并脱敏 `sk`、`api-key` 等敏感字段
- **手动脱敏**：运行 `python scripts/sanitize_config.py` 手动对配置文件进行脱敏
- **环境变量**：使用环境变量在运行时注入真实API密钥（如：`export llm_deepseek_sk="your-real-key"`）
- **详细文档**：查看 `docs/SANITIZATION_README.md` 了解详细的脱敏规则和使用方法

#### 模型参数
- 温度：控制输出的随机性和创造性
- 最大令牌数：限制单次输出的最大长度
- 系统提示词：全局的模型行为指导

### 快捷键

- `Ctrl/Cmd + Enter`：发送聊天消息
- `Escape`：取消工作流节点连接模式
- `Ctrl/Cmd + S`：保存工作流（开发中）

## 开发指南

### 代码提交前检查（Pre-commit）

项目集成了自动化的代码质量检查和敏感信息脱敏功能，确保代码提交的安全性和质量。

#### 自动执行（推荐）

在每次 `git commit` 前，系统会自动执行预提交检查：

```bash
# 正常的git提交流程
git add .
git commit -m "your commit message"
```

系统会自动执行以下检查：
1. **配置文件脱敏**：自动检测并脱敏 `llm.yml` 等配置文件中的敏感信息
2. **代码质量检查**：运行 flake8、black、isort 等工具检查代码规范
3. **敏感信息扫描**：检查是否有遗漏的API密钥、密码等敏感信息

#### 手动执行

如需手动运行预提交检查：

```bash
# 执行完整的预提交检查
./scripts/precommit.sh

# 仅执行配置文件脱敏
python scripts/sanitize_config.py
```

#### 预提交检查详情

**配置文件脱敏**：
- 自动检测 `config/llm.yml` 中的敏感字段
- 支持 `sk`、`api-key` 等多种密钥格式
- 脱敏后格式：`sk-***SANITIZED***`、`sk-or-***SANITIZED***`

**代码质量检查**：
- **flake8**：Python代码风格和语法检查
- **black**：代码格式化检查
- **isort**：import语句排序检查

**敏感信息扫描**：
- 检查暂存区文件中的API密钥、密码等敏感信息
- 支持多种敏感信息模式匹配
- 发现敏感信息时会提示用户确认

#### 环境变量配置

为了在运行时使用真实的API密钥，建议配置环境变量：

```bash
# 在 ~/.bashrc 或 ~/.zshrc 中添加
export llm_deepseek_sk="your-real-deepseek-key"
export llm_openrouter_sk="your-real-openrouter-key"

# 或者在运行时临时设置
llm_deepseek_sk="your-key" python vertex_flow/src/app.py
```

#### 故障排除

**预提交检查失败**：
1. 检查Python环境是否正确安装所需依赖
2. 确保代码符合flake8、black、isort的规范要求
3. 检查是否有未脱敏的敏感信息

**脱敏功能异常**：
1. 确保 `scripts/sanitize_config.py` 有执行权限
2. 检查配置文件格式是否正确
3. 查看详细文档：`docs/SANITIZATION_README.md`

**更多信息**：
- 预提交详细说明：`docs/PRECOMMIT_README.md`
- 脱敏功能说明：`docs/SANITIZATION_README.md`

### 故障排除

#### 常见问题
1. **工作流图形不显示**：
   - 检查浏览器控制台是否有 JavaScript 错误
   - 刷新页面重新加载
   - 确保网络连接正常

2. **节点输出不显示**：
   - 确保节点已成功执行
   - 检查底部输出面板是否被最小化
   - 尝试重新选择节点

3. **模型调用失败**：
   - 检查 API 密钥配置是否正确
   - 确认网络连接和 API 服务状态
   - 查看控制台错误信息

#### 性能优化建议
- 大型工作流建议分步执行
- 定期清理浏览器缓存
- 使用现代浏览器以获得最佳体验

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
localqwen/
├── vertex_flow/            # 核心工作流引擎，支持多模型协同和高级工作流
├── web_ui/                 # Web 用户界面，提供可视化操作界面
├── scripts/                # 开发和部署脚本，包含预提交检查和配置脱敏功能
├── docs/                   # 项目文档，包含开发指南和使用说明
├── config/                 # 配置文件目录，存放 LLM 和其他配置
├── .github/                # GitHub Actions 工作流配置
└── 其他配置文件             # Python 项目配置、依赖管理等
```

### 主要模块说明

- **vertex_flow/**: 核心工作流引擎，包含多模型客户端、工作流管理、向量处理等功能
- **web_ui/**: Web 用户界面，提供聊天、配置管理、工作流可视化等功能
- **scripts/**: 开发工具脚本，包含环境配置、预提交检查、配置脱敏等功能
- **docs/**: 项目文档，包含详细的使用指南和开发说明
- **config/**: 配置文件存放目录，支持多种 LLM 服务配置

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