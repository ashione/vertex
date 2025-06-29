# VertexFlow 文档索引

## 核心机制

### [Variables 变量透出机制和选择机制](VARIABLES_MECHANISM.md)
Variables 机制是 VertexFlow 框架中的核心功能，用于实现顶点之间的数据传递、依赖关系管理和变量暴露。它提供了灵活的数据流控制，支持复杂的工作流构建。

## 顶点类型文档

### [FunctionVertex 文档](function_vertex.md)
FunctionVertex 是 VertexFlow 框架中最基础和通用的顶点类型，允许用户通过传入自定义函数来实现各种业务逻辑。

### [LLMVertex 文档](llm_vertex.md)
LLMVertex 是专门用于大语言模型调用的顶点类型，支持多种 LLM 提供商和模型配置。

### [VectorVertex 文档](vector_vertex.md)
VectorVertex 提供向量存储和检索功能，支持多种向量数据库和相似度搜索算法。

### [EmbeddingVertex 文档](embedding_vertex.md)
EmbeddingVertex 负责文本嵌入，将文本转换为向量表示，支持多种嵌入模型。

### [VertexGroup 文档](vertex_group.md)
VertexGroup 允许将多个相关的 Vertex 组织成一个逻辑单元，形成子图，提供变量暴露功能。

### [WhileVertex 文档](while_vertex.md)
WhileVertex 提供循环执行功能，支持条件判断和迭代控制。

## 应用场景文档

### [RAG 应用文档](RAG_README.md)
基于检索增强生成（RAG）的应用场景和实现方案。

### [RAG 安装指南](RAG_INSTALL.md)
RAG 相关组件的安装和配置指南。

### [深度研究应用](DEEP_RESEARCH_APP.md)
深度研究应用的工作流设计和实现。

### [文档更新机制](DOCUMENT_UPDATE.md)
文档更新和版本管理的机制说明。

### [去重机制](DEDUPLICATION.md)
数据去重和重复检测的实现方案。

### [金融工具](finance_tool.md)
金融相关的工具和功能实现。

### [网络搜索](web_search.md)
网络搜索功能的实现和配置。

## 快速开始

1. 首先阅读 [Variables 变量透出机制和选择机制](VARIABLES_MECHANISM.md) 了解核心概念
2. 根据需求选择合适的顶点类型文档
3. 参考应用场景文档了解具体实现方案

## 文档贡献

如需更新或添加文档，请遵循以下原则：
- 保持文档结构清晰
- 提供完整的代码示例
- 包含错误处理和最佳实践
- 在相关文档中添加交叉引用 