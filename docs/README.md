# Vertex 文档中心

欢迎来到Vertex文档中心！这里包含了Vertex本地AI工作流系统的完整使用指南和技术文档。

## 📖 使用指南

### 新手入门
- **[完整CLI使用指南](CLI_USAGE.md)** - Vertex命令行完整使用说明，从入门到高级用法
  - 标准模式、工作流模式、配置管理
  - 所有命令的详细说明和示例
  - 故障排除和性能优化

### 聊天应用
- **[Workflow Chat 应用](WORKFLOW_CHAT_APP.md)** - 基于 Workflow LLM Vertex 的新一代聊天应用
  - 统一配置系统，支持多种 LLM 提供商
  - 动态模型切换，现代化界面
  - 工具调用支持，完善的错误处理
  - AI思考过程显示（Reasoning功能）
- **[Workflow Chat Memory](WORKFLOW_MEMORY.md)** - 会话记忆启用及存储配置指南
  - CLI 和 Web UI 开关说明
  - 内存/Redis/文件等存储选择
  - 系统提示增强与摘要扩展
- **[多模态功能](MULTIMODAL_FEATURES.md)** - 图片分析和多模态对话
  - 智能图片分析，支持多种输入方式
  - 文本+图片混合对话，丰富交互体验
  - 基于Gemini 2.5 Pro的多模态能力

### RAG问答系统
- **[RAG CLI详细说明](RAG_CLI_USAGE.md)** - RAG问答系统专项指南
  - 文档索引和查询功能
  - 交互式问答模式
  - 文档管理和统计

- **[RAG性能优化](RAG_PERFORMANCE_OPTIMIZATION.md)** - 性能分析与优化建议
  - 查询速度优化（5-8倍提升）
  - 分离式架构设计
  - 智能回退策略

## 🔧 技术文档

### 系统架构
- **[版本管理](VERSION_MANAGEMENT.md)** - 项目版本管理和发布流程
- **[发布指南](PUBLISHING.md)** - 包发布和分发流程
- **[安装说明](../INSTALL.md)** - 详细安装配置指南

### 开发工具
- **[预提交检查](PRECOMMIT_README.md)** - 代码质量检查和自动化工具
- **[配置脱敏](SANITIZATION_README.md)** - 配置文件安全处理

## 🏗️ 核心组件文档

### VertexFlow工作流引擎
位于 `../vertex_flow/docs/` 目录：

- **[RAG系统详解](../vertex_flow/docs/RAG_README.md)** - 检索增强生成系统架构
- **[文档更新机制](../vertex_flow/docs/DOCUMENT_UPDATE.md)** - 增量更新和智能去重
- **[去重功能说明](../vertex_flow/docs/DEDUPLICATION.md)** - 智能文档去重算法
- **[Embedding组件](../vertex_flow/docs/embedding_vertex.md)** - 文本向量化组件
- **[向量存储](../vertex_flow/docs/vector_vertex.md)** - 向量数据库组件
- **[LLM组件](../vertex_flow/docs/llm_vertex.md)** - 大语言模型集成
- **[函数组件](../vertex_flow/docs/function_vertex.md)** - 自定义函数节点
- **[工作流组](../vertex_flow/docs/vertex_group.md)** - 复合工作流组件
- **[循环组件](../vertex_flow/docs/while_vertex.md)** - 循环控制流
- **[Web搜索](../vertex_flow/docs/web_search.md)** - 网络搜索工具
- **[金融工具](../vertex_flow/docs/finance_tool.md)** - 金融数据API集成

## 🚀 快速导航

### 按使用场景

#### 🎯 我想开始使用Vertex
1. [完整CLI使用指南](CLI_USAGE.md) - 从零开始
2. [安装说明](../INSTALL.md) - 环境配置
3. [RAG CLI详细说明](RAG_CLI_USAGE.md) - 文档问答

#### 📚 我想构建知识库
1. [RAG CLI详细说明](RAG_CLI_USAGE.md) - 基础功能
2. [RAG性能优化](RAG_PERFORMANCE_OPTIMIZATION.md) - 性能调优
3. [文档更新机制](../vertex_flow/docs/DOCUMENT_UPDATE.md) - 高级特性

#### 🔧 我想开发和贡献
1. [预提交检查](PRECOMMIT_README.md) - 开发规范
2. [版本管理](VERSION_MANAGEMENT.md) - 版本控制
3. [发布指南](PUBLISHING.md) - 包发布流程

#### 🏗️ 我想了解架构
1. [RAG系统详解](../vertex_flow/docs/RAG_README.md) - 核心架构
2. [工作流组件](../vertex_flow/docs/) - 所有技术组件
3. [配置脱敏](SANITIZATION_README.md) - 安全机制

### 按功能模块

| 功能 | 用户指南 | 技术文档 |
|------|----------|----------|
| **CLI命令** | [CLI使用指南](CLI_USAGE.md) | - |
| **RAG问答** | [RAG CLI说明](RAG_CLI_USAGE.md) | [RAG技术详解](../vertex_flow/docs/RAG_README.md) |
| **性能优化** | [性能优化指南](RAG_PERFORMANCE_OPTIMIZATION.md) | [文档更新机制](../vertex_flow/docs/DOCUMENT_UPDATE.md) |
| **工作流设计** | [CLI使用指南](CLI_USAGE.md#2-工作流模式-workflow-mode) | [工作流组件](../vertex_flow/docs/) |
| **配置管理** | [CLI使用指南](CLI_USAGE.md#3-配置管理-config-management) | [配置脱敏](SANITIZATION_README.md) |

## 🔗 外部资源

- **GitHub仓库**: [https://github.com/your-repo/localqwen](https://github.com/your-repo/localqwen)
- **问题追踪**: [GitHub Issues](https://github.com/your-repo/localqwen/issues)
- **贡献指南**: [CONTRIBUTING.md](../CONTRIBUTING.md)

## 📞 获取帮助

### 命令行帮助
```bash
vertex --help          # 查看所有命令
vertex config --help   # 配置管理帮助
vertex rag --help      # RAG系统帮助
vertex workflow --help # 工作流帮助
```

### 常见问题
查看各个文档中的"故障排除"章节：
- [CLI故障排除](CLI_USAGE.md#🔧-故障排除)
- [RAG常见问题](RAG_CLI_USAGE.md#故障排除)
- [性能问题](RAG_PERFORMANCE_OPTIMIZATION.md#🔧-关键技术实现)

### 社区支持
- 创建[GitHub Issue](https://github.com/your-repo/localqwen/issues)描述问题
- 查看现有的[讨论区](https://github.com/your-repo/localqwen/discussions)
- 参考[示例代码](../vertex_flow/examples/)

---

**📝 文档更新**: 2025-06-20
**🔄 最后同步**: RAG性能优化完成，CLI功能文档化
**📋 覆盖范围**: 从入门使用到高级开发的完整文档体系

欢迎贡献文档改进建议！ 
