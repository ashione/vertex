# Vertex

一个强大的本地AI工作流系统，支持多模型和可视化工作流编排。

## 功能特性

- **多模型支持**：Ollama本地模型和外部API（DeepSeek、OpenRouter、通义）
- **Function Tools**：内置命令行执行和系统集成工具
- **统一CLI**：简洁的命令行界面，支持多种运行模式
- **VertexFlow引擎**：可视化工作流编排，支持拖拽节点
- **RAG系统**：本地检索增强生成，支持文档处理
- **智能配置**：基于模板的配置系统，自动化设置
- **文档处理**：支持TXT、MD、PDF、DOCX格式
- **桌面端应用**：基于PyWebView的原生桌面应用

## 快速开始

### 环境要求
- Python 3.9+
- Ollama（本地模型）- [下载地址](https://ollama.com/download)

### 安装
```bash
# 通过pip安装（推荐）
pip install vertex

# 或从源码安装
git clone https://github.com/ashione/vertex.git
cd vertex
pip install -e .
```

### 配置
```bash
# 快速设置 - 初始化配置
vertex config init

# 交互式配置向导
vertex config

# 检查配置状态
vertex config check
```

### 启动
```bash
# 标准聊天模式（默认）
vertex

# 或明确指定运行模式
vertex run

# VertexFlow工作流模式
vertex workflow

# RAG文档问答模式
vertex rag --interactive

# 桌面端模式
vertex --desktop
```

访问Web界面：[http://localhost:7860](http://localhost:7860)

## 使用指南

### CLI命令
```bash
# 标准模式
vertex                    # 启动聊天界面
vertex run --port 8080   # 自定义端口

# 工作流模式
vertex workflow           # 可视化工作流编辑器
vertex workflow --port 8080

# 配置管理
vertex config             # 交互式配置
vertex config init        # 快速初始化
vertex config check       # 检查配置状态
vertex config reset       # 重置配置

# RAG系统
vertex rag --interactive  # 交互式问答
vertex rag --query "问题"  # 直接查询
vertex rag --directory /path/to/docs  # 索引文档

# 桌面端模式
vertex --desktop          # 桌面端应用
vertex workflow --desktop # 桌面端工作流编辑器
```

### RAG系统
```python
from vertex_flow.workflow.unified_rag_workflow import UnifiedRAGSystem

# 创建RAG系统
rag_system = UnifiedRAGSystem()

# 索引文档
documents = ["document1.txt", "document2.pdf"]
rag_system.index_documents(documents)

# 查询知识库
answer = rag_system.query("主要主题是什么？")
print(answer)
```

### Function Tools
```python
# 通过服务访问各种功能工具
from vertex_flow.workflow.service import VertexFlowService

service = VertexFlowService()
cmd_tool = service.get_command_line_tool()      # 命令行执行
web_tool = service.get_web_search_tool()        # 网络搜索
finance_tool = service.get_finance_tool()       # 金融数据

# 工具与AI工作流无缝集成
```

### 基础工作流
```python
from vertex_flow.workflow.vertex.vertex import SourceVertex
from vertex_flow.workflow.workflow import Workflow, WorkflowContext

def source_func(inputs, context):
    return {"text": "Hello, Vertex Flow!"}

context = WorkflowContext()
workflow = Workflow(context)
source = SourceVertex(id="source", task=source_func)
workflow.add_vertex(source)
workflow.execute_workflow()
```

## 配置

### 快速配置
安装vertex包后，使用以下命令快速设置配置：

```bash
# 快速初始化配置文件
vertex config init

# 交互式配置向导
vertex config

# 检查配置状态
vertex config check

# 重置配置
vertex config reset
```

### 手动配置
配置文件位于 `~/.vertex/config/llm.yml`，您可以直接编辑此文件。

### 环境变量配置
为外部模型设置API密钥：
```bash
export llm_deepseek_sk="your-deepseek-key"
export llm_openrouter_sk="your-openrouter-key"
export llm_tongyi_sk="your-tongyi-key"
export web_search_bocha_sk="your-bocha-key"
```

### 配置优先级
1. 用户配置文件：`~/.vertex/config/llm.yml`
2. 环境变量
3. 包内默认配置

## 文档

### 📖 使用指南
- [完整CLI使用指南](docs/CLI_USAGE.md) - Vertex命令行完整使用说明
- [桌面端应用指南](docs/DESKTOP_APP.md) - 桌面端应用使用说明
- [RAG CLI详细说明](docs/RAG_CLI_USAGE.md) - RAG问答系统专项指南
- [RAG性能优化](docs/RAG_PERFORMANCE_OPTIMIZATION.md) - 性能分析与优化建议
- [故障排除指南](docs/TROUBLESHOOTING.md) - 常见问题和解决方案

### 🔧 技术文档
- [Function Tools指南](docs/FUNCTION_TOOLS.md) - 完整的功能工具参考
- [RAG系统详解](vertex_flow/docs/RAG_README.md) - 检索增强生成系统
- [文档更新机制](vertex_flow/docs/DOCUMENT_UPDATE.md) - 增量更新和去重
- [去重功能说明](vertex_flow/docs/DEDUPLICATION.md) - 智能文档去重
- [工作流组件](vertex_flow/docs/) - VertexFlow引擎组件

## 示例

```bash
# Function Tools示例
cd vertex_flow/examples
python command_line_example.py   # 命令行工具
python web_search_example.py     # 网络搜索工具  
python finance_example.py        # 金融数据工具

# 其他示例
python rag_example.py            # RAG系统
python deduplication_demo.py     # 去重功能
```

## 开发

```bash
# 运行预提交检查
./scripts/precommit.sh

# 脱敏配置文件
python scripts/sanitize_config.py
```

## 许可证

详见LICENSE文件。