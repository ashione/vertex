# Vertex

一个强大的本地和云端LLM推理与工作流编排工具，具有直观的Web界面和先进的VertexFlow引擎。

## 功能特性

- **多模型支持**：Ollama本地模型和外部API（DeepSeek、OpenRouter）
- **Web聊天界面**：实时流式对话，支持多轮上下文
- **VertexFlow引擎**：可视化工作流编排，支持拖拽节点
- **RAG系统**：本地检索增强生成，支持文档处理
- **函数工具**：自定义函数注册，支持动态工作流
- **文档处理**：支持TXT、MD、PDF、DOCX格式

## 快速开始

### 环境要求
- Python 3.8+
- Ollama（本地模型）- [下载地址](https://ollama.com/download)

### 安装
```bash
# 克隆仓库
git clone git@github.com:ashione/vertex.git
cd vertex

# 安装依赖
uv pip install -r requirements.txt
uv pip install -e .

# 设置本地模型（可选）
python scripts/setup_ollama.py

# 安装RAG依赖
./scripts/install_rag_deps.sh
```

### 启动
```bash
# 标准模式
vertex

# VertexFlow工作流模式
python -m vertex_flow.src.app
```

访问Web界面：[http://localhost:7860](http://localhost:7860)

## 使用指南

### Web界面
- **聊天**：多轮对话，支持流式输出
- **工作流编辑器**：可视化工作流设计，访问 [http://localhost:7860/workflow](http://localhost:7860/workflow)
- **配置管理**：API密钥和模型参数

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

为外部模型设置API密钥：
```bash
export llm_deepseek_sk="your-key"
export llm_openrouter_sk="your-key"
```

## 文档

- [RAG系统](vertex_flow/docs/RAG_README.md)
- [文档更新](vertex_flow/docs/DOCUMENT_UPDATE.md)
- [去重功能](vertex_flow/docs/DEDUPLICATION.md)
- [工作流组件](vertex_flow/docs/)

## 示例

```bash
# 运行RAG示例
cd vertex_flow/examples
python rag_example.py

# 运行去重演示
python deduplication_demo.py
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