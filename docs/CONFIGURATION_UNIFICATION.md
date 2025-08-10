# Vertex Flow 配置统一化文档

## 概述

最初为了简化配置管理，我们曾将分离的MCP配置模板合并到主配置文件 `vertex_flow/config/llm.yml.template` 中，但现在MCP相关配置已重新拆分到独立文件 `vertex_flow/config/mcp.yml.template`，以便更灵活地管理。

## 统一化成果

### 🎯 合并完成

- ✅ **MCP配置模板** (`mcp.yml.template`) 已合并到 `llm.yml.template`
- ✅ **配置结构优化** 使用分区标题清晰组织配置
- ✅ **语法验证通过** YAML格式正确无误
- ✅ **功能完整性** 包含所有12个主要配置块

### 📊 配置统计

| 项目 | 数值 |
|------|------|
| **总行数** | 399行 |
| **配置块数量** | 12个 |
| **MCP客户端** | 5个预配置客户端 |
| **分区标题** | 3个主要分区 |

### 🏗️ 配置架构

```
llm.yml.template
├── 大语言模型配置 (LLM Configuration)
│   ├── llm (LLM提供商配置)
│   ├── web-search (网络搜索服务)
│   ├── finance (金融工具)
│   ├── workflow (工作流配置)
│   ├── web (Web服务)
│   ├── vector (向量存储)
│   ├── embedding (嵌入模型)
│   ├── rerank (重排序)
│   ├── document (文档处理)
│   └── retrieval (检索配置)
├── MCP协议配置 (MCP Configuration)
│   └── mcp (MCP客户端和服务器)
└── MCP集成设置 (Integration Settings)
    └── integration (集成和安全设置)
```

## 主要配置块详解

### 1. 大语言模型配置
```yaml
llm:
  deepseek:     # DeepSeek API配置
  tongyi:       # 通义千问配置
  openrouter:   # OpenRouter配置
  ollama:       # 本地Ollama配置
```

### 2. MCP协议配置
```yaml
mcp:
  enabled: true
  clients:      # 外部MCP服务器连接
    filesystem: # 文件系统访问
    github:     # GitHub集成
    database:   # 数据库访问
    mcp_web_search: # MCP网络搜索
    http_server:    # HTTP MCP服务器
  server:       # Vertex Flow MCP服务器
    resources:  # 资源暴露
    tools:      # 工具暴露
    prompts:    # 提示模板
```

### 3. 集成设置
```yaml
integration:
  auto_connect: true  # 自动连接
  timeout: 30         # 操作超时
  retry:              # 重试策略
  logging:            # 日志配置
  security:           # 安全设置
```

## 使用指南

### 快速开始

1. **复制模板**:
   ```bash
   cp vertex_flow/config/llm.yml.template vertex_flow/config/llm.yml
   ```

2. **基础配置**:
   ```bash
   # 设置LLM API密钥
   export llm_deepseek_sk="your-deepseek-key"
   
   # 设置GitHub Token (可选)
   export GITHUB_PERSONAL_ACCESS_TOKEN="your-github-token"
   ```

3. **启用MCP功能**:
   ```yaml
   mcp:
     enabled: true
     clients:
       filesystem:
         enabled: true  # 启用文件系统访问
         args: ["@modelcontextprotocol/server-filesystem", "/your/path"]
   ```

### 高级配置

#### MCP客户端配置示例
```yaml
mcp:
  clients:
    # 启用GitHub集成
    github:
      enabled: true
      transport: "stdio"
      command: "npx"
      args: ["@modelcontextprotocol/server-github"]
      env:
        GITHUB_PERSONAL_ACCESS_TOKEN: "your-token"
    
    # 启用数据库访问
    database:
      enabled: true
      transport: "stdio"
      command: "python"
      args: ["-m", "mcp_server_database", "--connection-string", "sqlite:///data.db"]
```

#### 安全配置示例
```yaml
integration:
  security:
    require_approval: true  # 需要工具调用审批
    allowed_resources:
      - "file:///safe/path/*"
      - "workflow://*"
    blocked_resources:
      - "file:///etc/*"
      - "file:///root/*"
    tool_limits:
      max_execution_time: 30
      max_memory_usage: 50
```

## 迁移指南

### 从分离配置迁移

如果您之前使用了分离的MCP配置文件：

1. **备份现有配置**:
   ```bash
   cp vertex_flow/config/llm.yml vertex_flow/config/llm.yml.backup
   cp vertex_flow/config/mcp.yml vertex_flow/config/mcp.yml.backup 2>/dev/null || true
   ```

2. **使用新模板**:
   ```bash
   cp vertex_flow/config/llm.yml.template vertex_flow/config/llm.yml
   ```

3. **合并配置**:
   - 从 `llm.yml.backup` 复制LLM相关配置
   - 从 `mcp.yml.backup` 复制MCP相关配置到新文件的 `mcp` 和 `integration` 部分

4. **验证配置**:
   ```bash
   python -c "import yaml; yaml.safe_load(open('vertex_flow/config/llm.yml')); print('✅ 配置验证通过')"
   ```

## 优势与特性

### ✅ 优势
- **统一管理**: 单一配置文件，减少维护复杂度
- **结构清晰**: 分区组织，易于理解和编辑
- **向后兼容**: 保持原有配置项不变
- **功能完整**: 涵盖所有Vertex Flow功能
- **易于部署**: 简化Docker和生产环境配置

### 🔧 特性
- **环境变量支持**: 所有敏感配置支持环境变量覆盖
- **YAML完整支持**: 支持引用、锚点等高级YAML特性
- **配置验证**: 内置YAML语法验证
- **模块化设计**: 各功能模块独立配置
- **安全控制**: 细粒度的资源访问和工具执行控制

## 配置验证

### 语法检查
```bash
# 检查YAML语法
python -c "import yaml; yaml.safe_load(open('vertex_flow/config/llm.yml.template')); print('✅ 语法正确')"
```

### 配置加载测试
```bash
# 测试配置加载
python -c "
from vertex_flow.config.config_loader import load_config
config = load_config()
print(f'✅ 配置块数量: {len(config)}')
print(f'✅ MCP启用状态: {config.get(\"mcp\", {}).get(\"enabled\", False)}')
"
```

## 故障排除

### 常见问题

1. **配置文件找不到**:
   ```bash
   # 确保模板文件存在
   ls -la vertex_flow/config/llm.yml.template
   ```

2. **YAML语法错误**:
   ```bash
   # 使用Python验证语法
   python -c "import yaml; yaml.safe_load(open('vertex_flow/config/llm.yml'))"
   ```

3. **环境变量未生效**:
   ```bash
   # 检查环境变量
   env | grep llm_
   env | grep GITHUB_
   ```

4. **MCP客户端连接失败**:
   - 检查MCP服务器是否安装 (`npx @modelcontextprotocol/server-*`)
   - 验证命令路径和参数
   - 查看日志输出

### 调试技巧

1. **启用详细日志**:
   ```yaml
   integration:
     logging:
       level: "DEBUG"
       log_mcp_messages: true
       log_tool_calls: true
   ```

2. **测试MCP连接**:
   ```bash
   # 测试MCP服务器
   npx @modelcontextprotocol/server-filesystem /tmp
   ```

3. **配置项检查**:
   ```python
   from vertex_flow.config.config_loader import load_config
   import json
   config = load_config()
   print(json.dumps(config, indent=2, ensure_ascii=False))
   ```

## 总结

通过配置统一化，Vertex Flow现在提供了更加简洁和强大的配置管理体验。单一的 `llm.yml.template` 文件包含了所有功能的配置，使得部署、维护和扩展都变得更加容易。

这个统一配置不仅保持了向后兼容性，还为未来的功能扩展提供了良好的基础架构。用户可以根据需要选择性启用各种功能，同时享受统一配置带来的便利性。 
