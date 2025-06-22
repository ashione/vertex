# CLI统一化文档

## 概述

本次更新将原来的 `cli.py` 和 `cli_mcp.py` 合并成一个统一的命令行工具，提供更好的用户体验和命令行一致性。

## 变更内容

### 1. 文件合并
- **删除**: `vertex_flow/cli_mcp.py`
- **更新**: `vertex_flow/cli.py` - 添加了MCP相关功能

### 2. 新增MCP子命令

现在可以通过统一的CLI访问所有MCP功能：

```bash
# 显示MCP帮助信息
vertex mcp --help

# 显示MCP功能说明和示例
vertex mcp info

# 启动MCP服务器
vertex mcp server

# 测试MCP客户端
vertex mcp client 'vertex mcp server'
```

### 3. 统一的命令结构

所有Vertex功能现在都通过一个统一的入口点访问：

```bash
vertex                    # 启动标准模式（默认）
vertex run                # 启动标准模式
vertex workflow           # 启动工作流模式
vertex deepresearch       # 启动深度研究分析工具
vertex config             # 配置管理
vertex rag                # RAG检索增强生成
vertex mcp                # MCP模型上下文协议
```

## MCP功能详解

### MCP服务器
- 提供资源访问功能
- 支持工具调用
- 提供提示模板管理
- 通过stdio协议通信

### MCP客户端
- 可以连接到任何MCP服务器
- 支持资源读取测试
- 支持工具调用测试
- 支持提示模板测试

### 示例资源和工具

MCP服务器默认配置包括：

**资源**:
- `config://test.yml` - 测试配置文件
- `workflow://sample.py` - 示例工作流

**工具**:
- `echo_text` - 文本回显工具，支持重复参数

**提示模板**:
- `analyze_code` - 代码分析提示模板
- `workflow_help` - 工作流创建辅助模板

## 使用示例

### 启动MCP服务器
```bash
vertex mcp server
```

### 在另一个终端测试客户端
```bash
vertex mcp client 'vertex mcp server'
```

### 查看详细信息
```bash
vertex mcp info
```

## 技术实现

### 异步支持
- 使用 `asyncio` 支持异步MCP操作
- 所有MCP相关函数都是异步的

### 错误处理
- 优雅处理MCP依赖缺失的情况
- 提供清晰的错误信息和安装指导

### 代码组织
- MCP相关函数统一放在CLI文件中
- 保持与其他子命令一致的结构和风格

## 向后兼容性

- 所有原有的CLI命令保持不变
- 原有的功能和参数都得到保留
- 只是增加了新的MCP子命令

## 好处

1. **统一性**: 所有功能通过一个入口点访问
2. **一致性**: 命令结构和参数风格统一
3. **易用性**: 更容易发现和使用MCP功能
4. **维护性**: 减少了重复代码和文件数量
5. **文档性**: 集中的帮助信息和示例

## 注意事项

- MCP功能需要相关依赖包的支持
- 如果MCP依赖缺失，会显示友好的错误信息
- 所有MCP操作都是异步的，使用 `asyncio.run()` 执行

# CLI统一配置说明

## 配置模板合并

### 概述
为了简化配置管理，我们已经将MCP配置模板合并到主配置文件 `vertex_flow/config/llm.yml.template` 中。现在只需要维护一个统一的配置文件。

### 合并后的配置结构

合并后的 `llm.yml.template` 包含以下主要配置块：

```yaml
# ============================================================================
# 大语言模型配置 (LLM Configuration)
# ============================================================================
llm:                    # 大语言模型配置
  deepseek:            # DeepSeek配置
  tongyi:              # 通义千问配置  
  openrouter:          # OpenRouter配置
  ollama:              # 本地Ollama配置

web-search:            # 网络搜索服务配置
  bocha:               # Bocha AI搜索
  duckduckgo:          # DuckDuckGo搜索
  serpapi:             # SerpAPI搜索
  searchapi:           # SearchAPI.io搜索

finance:               # 金融工具配置
  alpha-vantage:       # Alpha Vantage API
  finnhub:             # Finnhub API
  yahoo-finance:       # Yahoo Finance

workflow:              # 工作流配置
  dify:                # Dify工作流实例

web:                   # Web服务配置
  port: 8999           # 服务端口
  host: 0.0.0.0        # 服务地址

vector:                # 向量存储配置
  local:               # 本地向量存储
  dashvector:          # 云端向量存储

embedding:             # 嵌入模型配置
  local:               # 本地嵌入模型
  dashscope:           # DashScope云端嵌入
  bce:                 # BCE云端嵌入

rerank:                # 重排序配置
  local:               # 本地重排序
  bce:                 # BCE云端重排序

document:              # 文档处理配置
  chunk_size: 1000     # 文档分块大小
  chunk_overlap: 200   # 分块重叠大小

retrieval:             # 检索配置
  top_k: 3             # 检索数量
  similarity_threshold: 0.7  # 相似度阈值

# ============================================================================
# MCP (Model Context Protocol) 配置
# ============================================================================
mcp:                   # MCP协议配置
  enabled: true        # 启用MCP集成
  clients:             # MCP客户端配置
    filesystem:        # 文件系统MCP客户端
    github:            # GitHub MCP客户端
    database:          # 数据库MCP客户端
    mcp_web_search:    # MCP网络搜索客户端
    http_server:       # HTTP MCP客户端
  
  server:              # MCP服务器配置
    enabled: true      # 启用MCP服务器
    name: "VertexFlow" # 服务器名称
    version: "1.0.0"   # 服务器版本
    transport:         # 传输配置
      stdio:           # stdio传输
      http:            # HTTP传输
    resources:         # 资源暴露配置
      workflows:       # 工作流资源
      docs:            # 文档资源
      configs:         # 配置资源
    tools:             # 工具暴露配置
      function_tools:  # Function Tools
      workflow_execution:  # 工作流执行
      vertex_operations:   # Vertex操作
    prompts:           # 提示模板配置
      system_prompts:  # 系统提示
      task_prompts:    # 任务提示
      custom_prompts:  # 自定义提示

# ============================================================================
# MCP集成设置 (MCP Integration Settings)
# ============================================================================
integration:           # MCP集成设置
  auto_connect: true   # 自动连接
  timeout: 30          # 操作超时
  retry:               # 重试配置
    max_attempts: 3    # 最大重试次数
    delay: 1.0         # 重试延迟
    backoff_factor: 2.0  # 退避因子
  logging:             # 日志配置
    level: "INFO"      # 日志级别
    log_mcp_messages: false  # 记录MCP消息
    log_tool_calls: true     # 记录工具调用
  security:            # 安全配置
    require_approval: false  # 需要审批
    allowed_resources:       # 允许的资源
    blocked_resources:       # 阻止的资源
    tool_limits:             # 工具限制
```

### 配置文件统计

- **总行数**: 399行
- **主要配置块**: 12个
- **配置项**: 涵盖LLM、MCP、向量存储、网络搜索、金融工具等所有功能

### 使用方法

1. **复制模板文件**:
   ```bash
   cp vertex_flow/config/llm.yml.template vertex_flow/config/llm.yml
   ```

2. **编辑配置**:
   - 配置LLM API密钥
   - 启用需要的MCP客户端
   - 配置向量存储和嵌入模型
   - 设置网络搜索服务

3. **环境变量支持**:
   ```bash
   # 设置DeepSeek API密钥
   export llm_deepseek_sk="your-api-key"
   
   # 设置GitHub Token用于MCP
   export GITHUB_PERSONAL_ACCESS_TOKEN="your-github-token"
   ```

### 优势

1. **统一管理**: 所有配置集中在一个文件中
2. **结构清晰**: 使用分区标题组织配置
3. **易于维护**: 减少配置文件数量
4. **向后兼容**: 保持原有配置结构不变
5. **功能完整**: 包含所有Vertex Flow功能的配置

### 迁移指南

如果您之前使用了分离的配置文件：

1. **备份现有配置**:
   ```bash
   cp vertex_flow/config/llm.yml vertex_flow/config/llm.yml.backup
   ```

2. **使用新模板**:
   ```bash
   cp vertex_flow/config/llm.yml.template vertex_flow/config/llm.yml
   ```

3. **迁移配置项**: 将备份文件中的配置项复制到新文件的对应位置

4. **测试配置**: 运行应用确保配置正确加载

### 注意事项

- MCP配置默认启用但客户端默认禁用，需要手动启用需要的客户端
- 安全配置包含资源访问控制和工具执行限制
- 所有API密钥都支持环境变量覆盖
- 配置文件支持YAML的所有特性，包括引用和锚点

这样的统一配置简化了部署和维护，使得Vertex Flow的配置更加直观和易于管理。 