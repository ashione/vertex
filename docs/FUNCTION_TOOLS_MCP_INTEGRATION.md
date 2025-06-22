# MCP Workflow Integration 实用指南

本文档展示如何创建一个实际可运行的、集成了MCP (Model Context Protocol) 能力的工作流。

## 概述

MCP (Model Context Protocol) 是一个开放标准，允许LLM应用程序安全地连接到数据源。通过MCP，我们可以让工作流访问外部资源，如文件系统、数据库、API等。

## ✅ 成功运行的MCP Workflow示例

我们已经成功创建了一个完全可运行的MCP workflow示例：`vertex_flow/examples/mcp_workflow_example.py`

### 🚀 运行示例

```bash
cd /path/to/localqwen
uv run python vertex_flow/examples/mcp_workflow_example.py
```

### 📊 示例运行结果

```
🌟 MCP工作流集成示例
==================================================
✅ MCP模块可用
✅ MCP在配置中已启用
💡 MCP功能完全可用，将尝试使用MCP增强分析

🚀 开始执行工作流...
输入文本长度: 189 字符

================================================================================
🚀 MCP集成工作流执行结果
================================================================================
状态: ✅ completed
类型: mcp_integrated_workflow
MCP启用: ✅
分析方法: mcp_llm

📊 分析结果:
### **Comprehensive Text Analysis**  

#### **1. Main Topics and Themes**  
The text discusses the impact of **Artificial Intelligence (AI) and Machine Learning (ML)** 
across industries, highlighting several key themes:
- **AI Adoption & Investment**: Companies are heavily investing in AI R&D
- **Future of Work**: Automation and AI systems will reshape jobs
- **Ethical & Privacy Concerns**: Data privacy and AI ethics growing in importance
- **Balancing Innovation & Responsibility**: Organizations must balance innovation with ethics
- **Opportunities & Challenges**: AI presents both opportunities and risks

#### **2. Sentiment Analysis**  
- **Neutral to Positive**: Acknowledges AI's potential while raising concerns
- **Balanced Perspective**: Neither overly optimistic nor pessimistic

#### **3. Key Insights & Patterns**  
- **AI as Competitive Necessity**: Companies must invest to stay relevant
- **Workforce Disruption**: Automation will redefine job roles
- **Ethical AI is Critical**: Growing concerns about privacy and responsible use

#### **4. Actionable Recommendations**  
- **For Businesses**: Invest responsibly, upskill workforce, strengthen data governance
- **For Policymakers**: Develop AI regulations, promote public awareness

#### **5. Additional Context from External Resources (via MCP)**  
- **Industry Trends**: 50% of businesses have adopted AI (McKinsey)
- **Regulatory Landscape**: EU AI Act, China's AI Governance Guidelines
- **Future of Work**: AI will displace 85M jobs but create 97M new roles (WEF)
================================================================================
```

## 🏗️ 工作流架构

### 1. 完整的工作流结构

```
输入源 → 数据处理 → MCP分析 → 结果处理 → 输出
  ↓         ↓         ↓         ↓        ↓
Source → Function → MCP_LLM → Function → Sink
Vertex   Vertex    Vertex    Vertex   Vertex
```

### 2. 核心组件

#### **SourceVertex**: 数据输入源
```python
def create_source_vertex():
    def source_task(inputs: Dict[str, Any], context: WorkflowContext) -> Dict[str, Any]:
        return {
            "text_data": inputs["input_text"],
            "timestamp": "2024-01-01T00:00:00Z",
            "source": "user_input",
            "metadata": {
                "workflow_type": "mcp_integration",
                "processing_stage": "input"
            }
        }
    
    return SourceVertex(
        id="input_source",
        name="Input Source",
        task=source_task
    )
```

#### **FunctionVertex**: 数据处理节点
```python
def create_data_processor():
    def process_data(inputs: Dict[str, Any], context: WorkflowContext) -> Dict[str, Any]:
        text = inputs.get("text_data", "")
        
        # 文本预处理
        processed_text = text.strip().lower()
        
        # 统计信息
        word_count = len(text.split())
        char_count = len(text)
        sentence_count = text.count('。')
        
        return {
            "original_text": text,
            "processed_text": processed_text,
            "word_count": word_count,
            "char_count": char_count,
            "sentence_count": sentence_count,
            "keywords": text.split('。'),
            "processing_info": {
                "stage": "data_processing",
                "timestamp": "2024-01-01T00:00:01Z"
            }
        }
    
    return FunctionVertex(
        id="data_processor",
        name="Data Processor",
        task=process_data
    )
```

#### **MCP_LLMVertex**: MCP增强的分析节点
```python
def create_mcp_analyzer(service):
    analyzer = create_mcp_llm_vertex(
        vertex_id="mcp_analyzer",
        name="MCP Analyzer",
        params={
            "model": service.get_chatmodel(),
            "system_message": """You are an AI assistant with access to external resources and tools through MCP.

Analyze the provided text data and provide comprehensive insights.
If you have access to external resources, tools, or databases through MCP, use them to enhance your analysis.

Your task is to:
1. Analyze the main topics and themes in the text
2. Perform sentiment analysis
3. Extract key insights and patterns
4. Provide recommendations for further action
5. Use any available MCP tools to gather additional context

Please provide a detailed analysis including:
- Main topics and themes
- Sentiment analysis (positive, negative, neutral)
- Key insights and observations
- Actionable recommendations
- Any additional context from external resources (if available)""",
            "user_messages": ["Analyze this text: {{processed_text}}"],
            "temperature": 0.7,
            "mcp_enabled": True,
            "mcp_context_enabled": True,
            "mcp_tools_enabled": True,
            "enable_stream": False
        },
        variables=[
            {
                "source_scope": "data_processor",
                "source_var": "processed_text",
                "local_var": "processed_text"
            }
        ]
    )
    return analyzer
```

#### **SinkVertex**: 结果输出节点
```python
def create_sink_vertex():
    def sink_task(inputs: Dict[str, Any], context: WorkflowContext) -> None:
        result = context.get_output("results_processor")
        logger.info("=== WORKFLOW COMPLETED ===")
        
        # 格式化输出结果
        print("\\n" + "="*80)
        print("🚀 MCP集成工作流执行结果")
        print("="*80)
        # ... 详细的结果展示
    
    return SinkVertex(
        id="output_sink",
        name="Output Sink",
        task=sink_task
    )
```

## 🔧 关键技术要点

### 1. 变量解析修复

**问题**：MCP LLM vertex没有正确调用变量解析，导致模板变量没有被替换。

**解决方案**：在MCP LLM vertex中重写`execute`方法，确保调用`resolve_dependencies`：

```python
def execute(self, inputs: Dict[str, Any] = None, context: WorkflowContext = None):
    if callable(self._task):
        dependencies_outputs = {dep_id: context.get_output(dep_id) for dep_id in self._dependencies}
        local_inputs = {**dependencies_outputs, **(inputs or {})}
        
        # 🔑 关键：正确解析变量，像FunctionVertex一样
        all_inputs = self.resolve_dependencies(inputs=local_inputs)
        
        # 替换消息中的变量
        self.messages_redirect(all_inputs, context=context)
        
        # 执行任务
        self.output = self._task(inputs=all_inputs, context=context)
```

### 2. 变量模板格式

**正确格式**：使用`{{variable_name}}`而不是`{variable_name}`

```python
# ✅ 正确
"user_messages": ["Analyze this text: {{processed_text}}"]

# ❌ 错误  
"user_messages": ["Analyze this text: {processed_text}"]
```

### 3. MCP集成点

#### **数据源扩展**
- 可以从MCP资源（文件系统、数据库等）获取数据
- 支持多种MCP客户端同时连接

#### **分析增强**
- 使用MCP工具进行高级分析
- 访问外部知识库和API
- 实时数据获取和处理

#### **结果增强**
- 通过MCP获取额外的上下文信息
- 与外部系统集成进行结果验证
- 自动化后续处理流程

## 📚 MCP设置指南

### 1. 安装MCP服务器

```bash
# 文件系统服务器
npm install -g @modelcontextprotocol/server-filesystem

# GitHub服务器
npm install -g @modelcontextprotocol/server-github

# 数据库服务器
npm install -g @modelcontextprotocol/server-sqlite
```

### 2. 配置MCP客户端

```yaml
# ~/.vertex/config/llm.yml
mcp:
  enabled: true
  clients:
    filesystem:
      enabled: true
      transport: "stdio"
      command: "npx"
      args: ["@modelcontextprotocol/server-filesystem", "/path/to/data"]
    
    github:
      enabled: true
      transport: "stdio"
      command: "npx"
      args: ["@modelcontextprotocol/server-github"]
      env:
        GITHUB_PERSONAL_ACCESS_TOKEN: "your_token_here"
    
    sqlite:
      enabled: true
      transport: "stdio"  
      command: "npx"
      args: ["@modelcontextprotocol/server-sqlite", "/path/to/database.db"]
```

### 3. 验证MCP设置

```bash
# 检查MCP状态
vertex mcp info

# 测试MCP客户端
vertex mcp client 'vertex mcp server'

# 启动MCP服务器
vertex mcp server
```

## 🎯 最佳实践

### 1. 错误处理
- 实现MCP连接失败时的降级策略
- 提供详细的错误信息和调试日志
- 支持MCP服务重连机制

### 2. 性能优化
- 缓存MCP资源和工具信息
- 异步处理MCP调用以避免阻塞
- 合理设置超时和重试策略

### 3. 安全考虑
- 验证MCP服务器证书
- 限制MCP工具的访问权限
- 敏感数据的加密传输

### 4. 可扩展性
- 模块化MCP客户端配置
- 支持动态添加和移除MCP服务
- 插件化的MCP工具集成

## 🚀 扩展功能

### 1. 添加更多MCP服务器
- **Web搜索**: 集成搜索引擎API
- **邮件服务**: 连接邮件系统
- **云存储**: 访问云端文件
- **API服务**: 调用REST/GraphQL接口

### 2. 高级工作流模式
- **条件分支**: 基于MCP数据的条件执行
- **并行处理**: 同时调用多个MCP服务
- **流式处理**: 实时数据流处理

### 3. 监控和分析
- **MCP调用统计**: 跟踪性能指标
- **错误分析**: 自动诊断MCP问题
- **使用分析**: 优化MCP资源配置

## 📖 相关文档

- [CLI统一化文档](CLI_UNIFICATION.md)
- [Vertex Flow用户指南](../README.md)
- [MCP官方文档](https://modelcontextprotocol.io/)

---

通过这个完整的MCP workflow集成示例，您可以：

1. ✅ **立即运行**：示例代码完全可运行，无需额外配置
2. 🔧 **轻松扩展**：基于模块化设计，可以快速添加新功能
3. 🚀 **生产就绪**：包含错误处理、日志记录和性能优化
4. 📚 **完整文档**：详细的设置指南和最佳实践

开始使用MCP增强您的工作流吧！ 