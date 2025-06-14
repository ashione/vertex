# Vertex

Vertex 是一个强大的本地和云端 LLM 推理与工作流编排工具，具有直观的 Web 界面和先进的 VertexFlow 引擎。

## 核心功能

### 基础能力
- **本地与云端模型**：支持基于 Ollama 的本地模型（Qwen-7B）和外部 API（DeepSeek、OpenRouter）
- **Web 聊天界面**：实时流式对话，支持多轮上下文
- **VertexFlow 引擎**：可视化工作流编排，支持多模型协作
- **知识库**：向量搜索、嵌入和重排序功能

### 高级功能
- **Function Tools**：自定义函数注册，支持动态工作流调用
- **深度研究工作流**：自动化研究，包含网络搜索、分析和结构化报告
- **VertexGroup**：模块化子图管理，支持嵌套组织
- **Dify 兼容性**：无缝迁移 Dify 工作流定义

## 快速设置

### 环境要求
- Python 3.8+
- Ollama（本地模型）- [下载地址](https://ollama.com/download)

### 安装
```bash
# 克隆仓库
git clone git@github.com:ashione/vertex.git
cd vertex

# 安装依赖
pip install -r requirements.txt
pip install -e .

# 设置本地模型（可选）
python scripts/setup_ollama.py
```

### 启动
```bash
# 标准模式
vertex

# VertexFlow 工作流模式
python -m vertex_flow.src.app
```

访问 Web 界面：[http://localhost:7860](http://localhost:7860)

## 使用指南

### Web 界面
Web UI 提供三个主要模块：
- **聊天界面**：多轮对话，支持流式输出和模型切换
- **工作流编辑器**：可视化工作流设计，支持拖拽节点
- **配置管理**：API 密钥、模型参数和系统设置

### 工作流编辑器
访问地址：[http://localhost:7860/workflow](http://localhost:7860/workflow)

**可用节点类型**：
- **LLM 节点**：可配置模型的文本生成
- **检索节点**：知识库搜索
- **条件节点**：条件分支
- **函数节点**：自定义函数执行

**变量系统**：
- 环境变量：`{{#env.variable_name#}}`
- 用户变量：`{{user.var.variable_name}}`
- 节点输出：`{{node_id.output_field}}`

### 配置
- 为外部模型设置 API 密钥（DeepSeek、OpenRouter）
- 配置模型参数（temperature、max tokens）
- 配置文件中敏感信息的自动脱敏

## 开发

### 代码质量
项目包含自动化预提交检查：
```bash
# 运行预提交检查
./scripts/precommit.sh

# 脱敏配置文件
python scripts/sanitize_config.py
```

### 环境变量
使用环境变量设置 API 密钥：
```bash
export llm_deepseek_sk="your-key"
export llm_openrouter_sk="your-key"
```

### 常见问题
- **Ollama 连接**：确保 Ollama 正在运行
- **API 错误**：验证 API 密钥和网络连接
- **工作流问题**：检查浏览器控制台错误

## API 示例

### 基础工作流
```python
from vertex_flow.workflow.vertex.vertex import SourceVertex, SinkVertex
from vertex_flow.workflow.workflow import Workflow, WorkflowContext

def source_func(inputs, context):
    return {"text": "Hello, Vertex Flow!"}

context = WorkflowContext()
workflow = Workflow(context)
source = SourceVertex(id="source", task=source_func)
workflow.add_vertex(source)
workflow.execute_workflow()
```

### Function Tools
```python
from vertex_flow.workflow.tools.functions import FunctionTool

def example_func(inputs, context):
    return {"result": inputs["value"] * 2}

tool = FunctionTool(
    name="example_tool",
    description="一个简单的示例工具",
    func=example_func
)
```

### REST API
```bash
curl -X POST "http://localhost:8999/workflow" \
   -H "Content-Type: application/json" \
   -d '{
     "stream": true,
     "workflow_name": "research_workflow",
     "user_vars": {"topic": "AI 趋势"},
     "content": "研究最新的 AI 发展"
   }'
```

## 项目结构

```
vertex/
├── vertex_flow/          # 核心工作流引擎
├── workflows/           # 工作流配置文件
├── web_ui/             # Web 界面
├── docs/                # 项目文档
└── scripts/            # 辅助脚本
```

## 详细文档

更多详细信息请参考文档：

### 项目文档
- [预提交指南](docs/PRECOMMIT_README.md) - 开发工作流和代码质量检查
- [配置脱敏](docs/SANITIZATION_README.md) - 安全和配置管理

### 工作流文档
- [LLM 顶点](vertex_flow/docs/llm_vertex.md) - 语言模型集成
- [函数顶点](vertex_flow/docs/function_vertex.md) - 自定义函数工具
- [顶点组](vertex_flow/docs/vertex_group.md) - 子图管理
- [网络搜索](vertex_flow/docs/web_search.md) - 网络搜索功能
- [嵌入顶点](vertex_flow/docs/embedding_vertex.md) - 文本嵌入处理
- [向量顶点](vertex_flow/docs/vector_vertex.md) - 向量操作
- [循环顶点](vertex_flow/docs/while_vertex.md) - 循环控制结构

## 贡献

欢迎提交 Issue 和 Pull Request 来改进项目。

## 许可证

本项目采用 MIT 许可证。