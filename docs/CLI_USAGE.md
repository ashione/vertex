# Vertex CLI 完整使用指南

Vertex是一个本地AI工作流系统，提供多种运行模式和丰富的命令行功能。

## 🚀 快速开始

```bash
# 安装vertex
pip install -e .

# 查看帮助
vertex --help

# 启动标准模式（默认）
vertex

# 查看版本
vertex --version
```

## 📋 命令概览

Vertex CLI提供以下主要命令：

| 命令 | 功能 | 说明 |
|------|------|------|
| `vertex` | 标准模式 | 启动Vertex聊天界面（默认） |
| `vertex run` | 标准模式 | 同上，显式指定 |
| `vertex workflow` | 工作流模式 | 启动VertexFlow可视化编辑器 |
| `vertex deepresearch` | 深度研究 | 启动深度研究分析工具 |
| `vertex config` | 配置管理 | 管理系统配置文件 |
| `vertex rag` | RAG问答 | 基于文档的智能问答系统 |
| `vertex mcp` | MCP协议 | Model Context Protocol 功能 |
| `vertex --desktop` | 桌面端模式 | 使用PyWebView启动桌面应用 |

## 🎯 详细使用说明

### 1. 标准模式 (Standard Mode)

启动Vertex标准聊天界面，提供基础的AI对话功能。

```bash
# 使用默认配置启动
vertex
# 或
vertex run

# 指定Web服务端口
vertex run --port 8080

# 指定主机地址
vertex run --host 0.0.0.0 --port 8080
```

**功能特性**：
- ✅ 多模型支持（OpenRouter、DeepSeek等）
- ✅ Web界面聊天
- ✅ 对话历史管理
- ✅ 响应式设计

### 2. 工作流模式 (Workflow Mode)

启动VertexFlow可视化工作流编辑器，支持拖拽式工作流设计。

```bash
# 启动工作流编辑器
vertex workflow

# 指定端口
vertex workflow --port 8999
```

**功能特性**：
- ✅ 可视化工作流设计
- ✅ 拖拽式节点编辑
- ✅ 实时工作流执行
- ✅ 工作流模板管理

### 3. 深度研究模式 (Deep Research Mode)

启动深度研究分析工具，提供高级分析功能。

```bash
# 启动深度研究工具
vertex deepresearch

# 指定端口
vertex deepresearch --port 7865
```

**功能特性**：
- ✅ 深度内容分析
- ✅ 多维度研究报告
- ✅ 数据可视化
- ✅ 导出研究结果

### 4. 配置管理 (Config Management)

管理Vertex系统的配置文件，支持多种配置操作。

#### 4.1 配置初始化

```bash
# 快速初始化配置（使用默认模板）
vertex config init

# 交互式配置向导
vertex config setup
```

#### 4.2 配置检查

```bash
# 检查配置状态
vertex config check
```

输出示例：
```
配置检查结果:
  模板存在: ✓
  配置存在: ✓
  配置有效: ✓
  模板路径: /path/to/vertex_flow/config/llm.yml.template
  配置路径: /path/to/vertex_flow/config/llm.yml

建议运行: vertex config init
```

#### 4.3 配置重置

```bash
# 重置配置为默认模板
vertex config reset
```

**配置文件结构**：
```yaml
llm:
  openrouter:
    sk: ${llm.openrouter.sk:sk-or-your-key}
    enabled: true
    models:
      - name: deepseek/deepseek-chat-v3-0324:free
        enabled: true

embedding:
  local:
    enabled: true
    model_name: "all-MiniLM-L6-v2"
    use_mirror: true

vector:
  local:
    enabled: true
    dimension: 384

# MCP (Model Context Protocol) 配置
mcp:
  enabled: true
  clients:
    filesystem:
      enabled: true
      command: "npx"
      args: ["@modelcontextprotocol/server-filesystem", "/path/to/allowed/directory"]
    github:
      enabled: false
      command: "npx"
      args: ["@modelcontextprotocol/server-github"]
```

### 5. RAG问答系统 (RAG Mode)

基于文档的检索增强生成系统，提供智能文档问答功能。

#### 5.1 基础用法

```bash
# 使用内置示例文档
vertex rag

# 索引指定目录的文档
vertex rag -d ./documents

# 显示向量数据库统计
vertex rag --show-stats
```

#### 5.2 查询模式

```bash
# 直接查询（完整模式）
vertex rag --query "什么是人工智能？"

# 快速查询（跳过LLM生成）
vertex rag --query "什么是人工智能？" --fast

# 交互式问答
vertex rag --interactive

# 快速交互式查询
vertex rag --interactive --fast
```

#### 5.3 文档管理

```bash
# 强制重新索引文档
vertex rag -d ./documents --reindex

# 组合使用：重新索引后查询
vertex rag -d ./documents --reindex --query "文档摘要"
```

#### 5.4 性能模式对比

| 模式 | 命令 | 耗时 | 功能 |
|------|------|------|------|
| 完整查询 | `--query "问题"` | 3-8秒 | 文档检索 + LLM生成 |
| 快速查询 | `--query "问题" --fast` | 0.5-1秒 | 仅文档检索 |
| 仅索引 | `-d path --reindex` | 按文档量 | 仅构建索引 |
| 统计信息 | `--show-stats` | <1秒 | 显示数据库状态 |

### 6. MCP协议功能 (Model Context Protocol)

MCP (Model Context Protocol) 是一个开放标准，允许LLM应用程序安全地连接到数据源。

#### 6.1 MCP命令概览

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

#### 6.2 MCP服务器功能

MCP服务器提供以下功能：
- **资源访问**: 提供文件和配置资源访问
- **工具调用**: 支持文本处理等工具
- **提示模板**: 提供代码分析和工作流辅助模板
- **stdio协议**: 通过标准输入输出通信

**默认资源**:
- `config://test.yml` - 测试配置文件
- `workflow://sample.py` - 示例工作流

**可用工具**:
- `echo_text` - 文本回显工具，支持重复参数

**提示模板**:
- `analyze_code` - 代码分析提示模板
- `workflow_help` - 工作流创建辅助模板

#### 6.3 MCP客户端测试

```bash
# 启动MCP服务器（终端1）
vertex mcp server

# 在另一个终端测试客户端（终端2）
vertex mcp client 'vertex mcp server'

# 查看详细信息和示例
vertex mcp info
```

#### 6.4 MCP配置集成

MCP配置已集成到主配置文件 `vertex_flow/config/llm.yml.template` 中：

```yaml
# MCP (Model Context Protocol) 配置
mcp:
  enabled: true        # 启用MCP集成
  clients:             # MCP客户端配置
    filesystem:        # 文件系统MCP客户端
      enabled: true
      command: "npx"
      args: ["@modelcontextprotocol/server-filesystem", "/path/to/directory"]
      transport: "stdio"
      env:
        NODE_ENV: "production"
    
    github:            # GitHub MCP客户端
      enabled: false
      command: "npx"
      args: ["@modelcontextprotocol/server-github"]
      transport: "stdio"
      env:
        GITHUB_PERSONAL_ACCESS_TOKEN: "${mcp.github.token:your-github-token}"
    
    database:          # 数据库MCP客户端
      enabled: false
      command: "npx"
      args: ["@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]
      transport: "stdio"
  
  server:              # MCP服务器配置
    enabled: true      # 启用MCP服务器
    name: "VertexFlow" # 服务器名称
    version: "1.0.0"   # 服务器版本
```

### 7. 桌面端模式 (Desktop Mode)

使用PyWebView封装Gradio应用，提供原生桌面应用体验。

#### 7.1 基础用法

```bash
# 启动桌面端应用（标准模式）
vertex --desktop

# 启动桌面端工作流模式
vertex workflow --desktop

# 启动桌面端深度研究模式
vertex deepresearch --desktop
```

#### 7.2 桌面端特性

**优势**：
- ✅ 原生桌面应用体验
- ✅ 无浏览器依赖
- ✅ 更好的系统集成
- ✅ 独立窗口管理

**要求**：
- Python 3.8+
- PyWebView 依赖包
- 系统WebView支持

#### 7.3 桌面端配置

```bash
# 检查桌面端依赖
python -c "import webview; print('PyWebView available')"

# 如果缺少依赖，安装：
pip install pywebview
```

## 🔧 高级用法

### 组合命令

```bash
# 初始化配置后启动工作流
vertex config init && vertex workflow

# 检查配置状态并启动RAG
vertex config check && vertex rag --interactive

# 启动MCP服务器并在桌面端运行
vertex mcp server & vertex --desktop
```

### 环境变量

```bash
# 指定配置文件
CONFIG_FILE=config/custom.yml vertex

# 启用调试模式
DEBUG=1 vertex workflow

# 设置日志级别
LOG_LEVEL=DEBUG vertex
```

### 批处理脚本

```bash
#!/bin/bash
# 自动化启动脚本

# 检查配置
vertex config check

# 如果配置不存在，初始化
if [ $? -ne 0 ]; then
    vertex config init
fi

# 启动工作流模式
vertex workflow --port 8999
```

## 🛠️ CLI统一化说明

### 架构改进

本次更新将原来的多个CLI文件合并成一个统一的命令行工具：

- **删除**: `vertex_flow/cli_mcp.py`
- **更新**: `vertex_flow/cli.py` - 添加了所有MCP相关功能

### 统一的命令结构

所有Vertex功能现在都通过一个统一的入口点访问，提供：

1. **统一性**: 所有功能通过一个入口点访问
2. **一致性**: 命令结构和参数风格统一
3. **易用性**: 更容易发现和使用各种功能
4. **维护性**: 减少了重复代码和文件数量
5. **文档性**: 集中的帮助信息和示例

### 向后兼容性

- ✅ 所有原有的CLI命令保持不变
- ✅ 原有的功能和参数都得到保留
- ✅ 只是增加了新的MCP子命令
- ✅ 配置文件格式保持兼容

## 📚 相关文档

- [配置管理详细指南](CONFIGURATION_UNIFICATION.md)
- [MCP集成指南](MCP_INTEGRATION.md)
- [Function Tools指南](FUNCTION_TOOLS.md)
- [故障排除指南](TROUBLESHOOTING.md)

## 🔍 故障排除

### 常见问题

1. **命令未找到**
   ```bash
   # 确保正确安装
   pip install -e .
   
   # 检查PATH环境变量
   which vertex
   ```

2. **配置文件问题**
   ```bash
   # 检查配置状态
   vertex config check
   
   # 重新初始化配置
   vertex config init
   ```

3. **端口占用**
   ```bash
   # 使用不同端口
   vertex workflow --port 9000
   
   # 检查端口占用
   lsof -i :8999
   ```

4. **MCP依赖问题**
   ```bash
   # 安装MCP相关依赖
   npm install -g @modelcontextprotocol/server-filesystem
   
   # 检查Node.js版本
   node --version
   ```

5. **桌面端启动失败**
   ```bash
   # 安装桌面端依赖
   pip install pywebview
   
   # 检查系统WebView支持
   python -c "import webview; webview.start()"
   ```

更多故障排除信息，请参考 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)。

## 🔗 相关文档

- [RAG CLI详细说明](./RAG_CLI_USAGE.md)
- [RAG性能优化](./RAG_PERFORMANCE_OPTIMIZATION.md)
- [配置文件说明](./CONFIG_REFERENCE.md)
- [工作流设计指南](./WORKFLOW_GUIDE.md)
- [桌面端应用指南](./DESKTOP_APP.md)

## 🆘 获取帮助

```bash
# 查看命令帮助
vertex --help
vertex config --help
vertex rag --help

# 查看版本信息
vertex --version

# 在线文档
# https://github.com/your-repo/localqwen/tree/main/docs
```

---

通过这个完整的CLI指南，你可以充分利用Vertex的所有功能，从基础聊天到高级工作流设计，再到智能文档问答系统和桌面端应用。选择适合你需求的模式，享受AI驱动的工作流体验！