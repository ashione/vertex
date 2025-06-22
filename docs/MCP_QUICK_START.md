# MCP (Model Context Protocol) 快速启动指南

## 概述

Vertex Flow 现在完全支持 MCP (Model Context Protocol)，可以连接到外部数据源和工具，大大扩展系统的集成能力。

## 功能特性

✅ **MCP客户端**: 连接外部MCP服务器（文件系统、GitHub、数据库等）  
✅ **MCP服务器**: 将Vertex Flow功能暴露给其他应用  
✅ **统一管理**: 通过MCPManager管理多个MCP连接  
✅ **增强LLM**: MCPLLMVertex自动集成外部资源和工具  
✅ **配置驱动**: 灵活的配置文件控制  
✅ **统一日志**: 使用项目标准日志系统  

## 快速启用

### 1. 在配置文件中启用MCP

在你的 `config/llm.yml` 文件中添加MCP配置：

```yaml
# MCP (Model Context Protocol) 配置
mcp:
  enabled: true  # 启用MCP功能
  
  # MCP客户端配置
  clients:
    # 文件系统访问
    filesystem:
      enabled: true
      transport: stdio
      command: "npx"
      args: ["@modelcontextprotocol/server-filesystem", "/path/to/allowed/directory"]
      description: "File system access"
      
    # GitHub集成  
    github:
      enabled: false  # 默认禁用，需要配置token
      transport: stdio
      command: "npx"
      args: ["@modelcontextprotocol/server-github"]
      env:
        GITHUB_PERSONAL_ACCESS_TOKEN: "your-github-token"
      description: "GitHub repository access"
      
    # SQLite数据库
    sqlite:
      enabled: false
      transport: stdio
      command: "npx" 
      args: ["@modelcontextprotocol/server-sqlite", "/path/to/database.db"]
      description: "SQLite database access"

  # 安全设置
  security:
    # 资源访问控制
    resource_access:
      mode: "allow"  # allow 或 block
      patterns: []   # 允许或阻止的资源模式
      
    # 工具执行限制
    tool_execution:
      timeout: 30          # 工具执行超时（秒）
      max_memory: 100      # 最大内存使用（MB）
      require_approval: false  # 是否需要用户批准
```

### 2. 安装MCP服务器依赖

```bash
# 安装常用的MCP服务器
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-github  
npm install -g @modelcontextprotocol/server-sqlite
```

### 3. 在工作流中使用MCP

```python
from vertex_flow.workflow.vertex.mcp_llm_vertex import MCPLLMVertex
from vertex_flow.workflow.mcp_manager import get_mcp_manager

# 创建MCP增强的LLM顶点
mcp_llm = MCPLLMVertex(
    vertex_id="mcp_analyzer",
    mcp_enabled=True,
    mcp_context_enabled=True,  # 自动包含MCP上下文
    mcp_tools_enabled=True,    # 启用MCP工具调用
    mcp_prompts_enabled=True   # 启用MCP提示
)

# 获取MCP管理器
mcp_manager = get_mcp_manager()

# 获取所有可用资源
resources = await mcp_manager.get_all_resources()
print(f"可用资源: {[r.name for r in resources]}")

# 获取所有可用工具
tools = await mcp_manager.get_all_tools()
print(f"可用工具: {[t.name for t in tools]}")
```

## 可用的MCP服务器

### 官方服务器
- **@modelcontextprotocol/server-filesystem**: 文件系统访问
- **@modelcontextprotocol/server-github**: GitHub仓库集成
- **@modelcontextprotocol/server-sqlite**: SQLite数据库访问
- **@modelcontextprotocol/server-postgres**: PostgreSQL数据库访问
- **@modelcontextprotocol/server-memory**: 内存存储和检索
- **@modelcontextprotocol/server-brave-search**: Brave搜索引擎
- **@modelcontextprotocol/server-puppeteer**: 网页自动化

### 第三方服务器
- **mcp-server-git**: Git仓库操作
- **mcp-server-docker**: Docker容器管理
- **mcp-server-aws**: AWS服务集成
- **mcp-server-notion**: Notion数据库访问

## 状态检查

```python
# 检查MCP状态
from vertex_flow.workflow.service import VertexFlowService

service = VertexFlowService()
print(f"MCP启用状态: {service.is_mcp_enabled()}")

mcp_manager = service.get_mcp_manager()
connected_clients = mcp_manager.get_connected_clients()
print(f"已连接的客户端: {connected_clients}")
```

## 故障排除

### 常见问题

1. **"MCP functionality not available"**
   - 确保配置文件中 `mcp.enabled: true`
   - 检查MCP服务器是否正确安装

2. **连接失败**
   - 检查MCP服务器命令路径是否正确
   - 验证环境变量设置
   - 查看日志输出获取详细错误信息

3. **权限问题**
   - 确保文件系统路径有正确的读写权限
   - 检查API token是否有效且权限足够

### 调试模式

启用详细日志来调试MCP连接问题：

```python
from vertex_flow.utils.logger import LoggerUtil
import logging

# 设置调试级别
LoggerUtil.get_logger("vertex_flow.mcp").setLevel(logging.DEBUG)
LoggerUtil.get_logger("vertex_flow.workflow.mcp_manager").setLevel(logging.DEBUG)
```

## 示例用例

### 1. 文件分析工作流
```python
# 连接文件系统，分析项目代码
mcp_config = {
    "enabled": True,
    "clients": {
        "filesystem": {
            "enabled": True,
            "transport": "stdio",
            "command": "npx",
            "args": ["@modelcontextprotocol/server-filesystem", "/path/to/project"]
        }
    }
}
```

### 2. GitHub代码审查
```python
# 连接GitHub，自动化代码审查
mcp_config = {
    "enabled": True,
    "clients": {
        "github": {
            "enabled": True,
            "transport": "stdio", 
            "command": "npx",
            "args": ["@modelcontextprotocol/server-github"],
            "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "your-token"}
        }
    }
}
```

### 3. 数据库查询和分析
```python
# 连接数据库，执行查询和分析
mcp_config = {
    "enabled": True,
    "clients": {
        "database": {
            "enabled": True,
            "transport": "stdio",
            "command": "npx", 
            "args": ["@modelcontextprotocol/server-sqlite", "/path/to/data.db"]
        }
    }
}
```

## 下一步

1. 根据需求配置具体的MCP服务器
2. 在工作流中集成MCP功能
3. 测试和验证MCP连接
4. 监控和优化MCP性能

更多详细信息请参考 [MCP集成文档](MCP_INTEGRATION.md)。 