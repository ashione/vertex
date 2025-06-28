# Vertex

一个强大的本地AI工作流系统，支持多模型和可视化工作流编排。

## 功能特性

| 分类 | 功能 | 说明 |
|------|------|------|
| **AI模型** | 多模型支持 | Ollama本地模型和外部API（DeepSeek、OpenRouter、通义） |
| **高级AI** | 🎨 多模态支持 | 基于Gemini 2.5 Pro的图片分析和文本+图片对话 |
| | 🤔 思考过程显示 | 支持AI推理过程展示（支持DeepSeek R1等reasoning模型） |
| | 🔬 深度研究 | 六阶段研究工作流，智能分析系统 |
| **工具与搜索** | 🔍 智能Web搜索 | 多搜索引擎支持（SerpAPI、DuckDuckGo、Bocha AI等） |
| | Function Tools | 内置命令行执行、Web搜索、金融数据等工具 |
| **界面** | ⚡ 流式输出 | 实时显示AI回复，提供更好的交互体验 |
| | 统一CLI | 简洁的命令行界面，支持多种运行模式 |
| | 桌面端应用 | 基于PyWebView的原生桌面应用 |
| **工作流** | VertexFlow引擎 | 可视化工作流编排，支持拖拽节点 |
| | RAG系统 | 本地检索增强生成，支持文档处理 |
| **配置** | 智能配置 | 简化的配置系统，自动化设置 |
| | 文档处理 | 支持TXT、MD、PDF、DOCX格式 |

## 快速开始

### 环境要求
- Python 3.9+
- Ollama（本地模型）- [下载地址](https://ollama.com/download)

### 安装方式

#### 方式一：Docker部署（推荐）

```bash
# 克隆项目
git clone https://github.com/ashione/vertex.git
cd vertex

# 使用Docker Compose快速启动
docker-compose -f docker/docker-compose.yml up -d

# 或使用Makefile
cd docker
make compose-up

# 访问Web界面
# http://localhost:7860
```

#### 方式二：本地安装

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

# 高级工作流聊天模式（支持Function Tools + Web搜索 + Reasoning）
python -m vertex_flow.src.workflow_app --port 7864

# 深度研究分析工具
vertex deepresearch
# 或简写形式
vertex dr

# VertexFlow工作流模式
vertex workflow

# RAG文档问答模式
vertex rag --interactive

# 桌面端模式
vertex --desktop
```

访问Web界面：[http://localhost:7860](http://localhost:7860)（或[http://localhost:7864](http://localhost:7864)访问工作流应用）

## Docker部署

### 快速开始

```bash
# 1. 构建镜像
cd docker
make build

# 2. 运行容器
make run

# 3. 访问应用
# http://localhost:7860
```

### 开发环境

```bash
# 构建开发镜像（支持热重载）
make build-dev

# 运行开发容器
make run-dev

# 查看日志
make logs
```

### 推送到阿里云ACR

```bash
# 设置ACR注册表地址
export ACR_REGISTRY=registry.cn-hangzhou.aliyuncs.com/your-namespace

# 构建并推送
make push

# 或使用构建脚本
./build.sh -r $ACR_REGISTRY
```

### 使用Docker Compose

```bash
# 启动生产环境
docker-compose -f docker/docker-compose.yml up -d

# 启动开发环境
docker-compose -f docker/docker-compose.yml --profile dev up -d

# 查看日志
docker-compose -f docker/docker-compose.yml logs -f

# 停止服务
docker-compose -f docker/docker-compose.yml down
```

详细Docker使用说明请参考：[docker/README.md](docker/README.md)

## 使用指南

### CLI命令
```bash
# 标准模式
vertex                    # 启动聊天界面
vertex run --port 8080   # 自定义端口

# 高级工作流聊天模式
python -m vertex_flow.src.workflow_app --port 7864  # 支持Function Tools、Web搜索、Reasoning

# 深度研究模式
vertex deepresearch       # 启动深度研究分析工具
vertex dr --topic "AI发展趋势"  # 命令行直接研究
vertex dr --port 8080     # 自定义Web界面端口

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

### 深度研究系统
深度研究工具通过六阶段工作流提供全面分析：

1. **主题分析** 🔍 - 初步理解主题并定义研究范围
2. **研究规划** 📋 - 制定战略性研究方法和策略
3. **信息收集** 📚 - 全面数据收集和信息源汇编
4. **深度分析** 🔬 - 深入检查和批判性评估
5. **交叉验证** ✅ - 跨信息源验证和事实核查
6. **总结报告** 📄 - 生成专业研究报告

```python
# 通过API使用深度研究
from vertex_flow.src.deep_research_app import DeepResearchApp

app = DeepResearchApp()
# 配置研究参数并执行
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
web_tool = service.get_web_search_tool()        # 智能Web搜索（SerpAPI/DuckDuckGo/Bocha等）
finance_tool = service.get_finance_tool()       # 金融数据获取

# 工具与AI工作流无缝集成，支持流式输出和reasoning
```

### 基础工作流
```python
from vertex_flow.workflow.vertex.vertex import SourceVertex
from vertex_flow.workflow.workflow import Workflow
from vertex_flow.workflow.context import WorkflowContext

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
export web_search_serpapi_api_key="your-serpapi-key"
export web_search_bocha_sk="your-bocha-key"
```

### 配置优先级
1. 用户配置文件：`~/.vertex/config/llm.yml`
2. 环境变量
3. 包内默认配置

## 文档

### 📖 用户指南
- [完整CLI使用指南](docs/CLI_USAGE.md) - 完整CLI命令参考和MCP集成
- [桌面端应用指南](docs/DESKTOP_APP.md) - 桌面端应用使用
- [工作流聊天应用指南](docs/WORKFLOW_CHAT_APP.md) - 高级聊天（支持Function Tools和Reasoning）
- [🎨 多模态功能指南](docs/MULTIMODAL_FEATURES.md) - 图片分析和文本+图片对话
- [🔍 Web搜索配置](docs/WEB_SEARCH_CONFIGURATION.md) - 多搜索引擎配置
- [MCP集成指南](docs/MCP_INTEGRATION.md) - 模型上下文协议支持
- [故障排除指南](docs/TROUBLESHOOTING.md) - 常见问题和解决方案

### 🔧 技术文档
- [Function Tools指南](docs/FUNCTION_TOOLS.md) - 完整功能工具参考
- [工作流链式调用](docs/WORKFLOW_CHAIN_CALLING.md) - 链式工作流执行
- [RAG系统概览](vertex_flow/docs/RAG_README.md) - 检索增强生成
- [文档更新机制](vertex_flow/docs/DOCUMENT_UPDATE.md) - 增量更新和去重
- [去重功能](vertex_flow/docs/DEDUPLICATION.md) - 智能文档去重
- [配置统一化](docs/CONFIGURATION_UNIFICATION.md) - 统一配置系统

### 🎯 开发与维护
- [发布指南](docs/PUBLISHING.md) - 包发布和版本管理
- [预提交检查](docs/PRECOMMIT_README.md) - 代码质量和自动化检查

## 示例

```bash
# Function tools示例
cd vertex_flow/examples
python command_line_example.py   # 命令行工具
python web_search_example.py     # Web搜索工具  
python finance_example.py        # 金融工具
python rag_example.py            # RAG系统
python deduplication_demo.py     # 去重功能
```

## 开发

```bash
# 运行预提交检查
./scripts/precommit.sh

# 版本管理
python scripts/version_bump.py
```

## 许可证

详见LICENSE文件。