# MCP配置迁移指南

## 概述

为了简化配置管理，我们已经将MCP配置完全统一到主配置文件 `llm.yml` 中。这个文档说明了所有相关的变更和迁移步骤。

## 🔄 配置文件变更

### 变更前 (旧版本)
```
vertex_flow/config/
├── llm.yml.template      # LLM和其他配置
├── mcp.yml.template      # 独立的MCP配置
└── ...

用户配置:
~/.vertex/config/
├── llm.yml              # LLM和其他配置  
├── mcp.yml              # 独立的MCP配置 (如果存在)
└── ...
```

### 变更后 (新版本)
```
vertex_flow/config/
├── llm.yml.template      # 统一配置 (包含LLM + MCP)
└── ...

用户配置:
~/.vertex/config/
├── llm.yml              # 统一配置 (包含LLM + MCP)
└── ...
```

## 📋 更新的文件清单

### 1. 配置模板文件
- ✅ **已合并**: `vertex_flow/config/mcp.yml.template` → `vertex_flow/config/llm.yml.template`
- ✅ **已删除**: `vertex_flow/config/mcp.yml.template`

### 2. 示例和指南文件
- ✅ **已更新**: `vertex_flow/examples/mcp_usage_guide.py`
  - 更新配置文件引用: `mcp.yml.template` → `llm.yml.template`
  - 更新用户配置路径: `~/.vertex/config/mcp.yml` → `~/.vertex/config/llm.yml`

- ✅ **已更新**: `vertex_flow/examples/mcp_workflow_example.py`
  - 更新配置复制命令: `mcp.yml.template` → `llm.yml.template`

### 3. 文档文件
- ✅ **已更新**: `docs/MCP_INTEGRATION.md`
  - 更新配置文件引用: `vertex_flow/config/mcp.yml` → `vertex_flow/config/llm.yml`

- ✅ **已更新**: `docs/FUNCTION_TOOLS_MCP_INTEGRATION.md`
  - 更新配置文件路径: `~/.vertex/config/mcp.yml` → `~/.vertex/config/llm.yml`

- ✅ **已确认**: `docs/MCP_QUICK_START.md`
  - 已经使用正确的 `config/llm.yml` 引用

### 4. 本地配置文件
- ✅ **已更新**: `/Users/wjf/.vertex/config/llm.yml`
  - 添加了完整的MCP配置部分
  - 包含5个预配置的MCP客户端
  - 包含完整的集成设置

## 🔧 迁移步骤

### 对于开发者
如果您之前有独立的MCP配置文件，请按照以下步骤迁移：

1. **备份现有配置**:
   ```bash
   cp ~/.vertex/config/llm.yml ~/.vertex/config/llm.yml.backup
   cp ~/.vertex/config/mcp.yml ~/.vertex/config/mcp.yml.backup 2>/dev/null || true
   ```

2. **使用新模板**:
   ```bash
   cp vertex_flow/config/llm.yml.template ~/.vertex/config/llm.yml
   ```

3. **迁移配置项**:
   - 从 `llm.yml.backup` 复制LLM相关配置
   - 从 `mcp.yml.backup` 复制MCP相关配置到新文件的 `mcp` 和 `integration` 部分

4. **验证配置**:
   ```bash
   python -c "import yaml; yaml.safe_load(open('~/.vertex/config/llm.yml'.expanduser())); print('✅ 配置验证通过')"
   ```

### 对于新用户
新用户只需要：
```bash
cp vertex_flow/config/llm.yml.template ~/.vertex/config/llm.yml
```

## 📊 配置结构对比

### MCP配置在统一文件中的位置

```yaml
# ~/.vertex/config/llm.yml

# ... 其他配置 (llm, web-search, finance, etc.) ...

# ============================================================================
# MCP (Model Context Protocol) 配置
# ============================================================================
mcp:
  enabled: true
  clients:
    filesystem:      # 文件系统访问
    github:          # GitHub集成
    database:        # 数据库访问
    mcp_web_search:  # MCP网络搜索
    http_server:     # HTTP MCP服务器
  server:
    enabled: true
    name: "VertexFlow"
    version: "1.0.0"
    # ... 服务器配置 ...

# ============================================================================
# MCP集成设置 (MCP Integration Settings)
# ============================================================================
integration:
  auto_connect: true
  timeout: 30
  retry: { ... }
  logging: { ... }
  security: { ... }
```

## ✅ 验证清单

运行以下检查确保迁移成功：

### 1. 配置文件检查
```bash
# 检查统一配置文件是否存在
ls -la ~/.vertex/config/llm.yml

# 检查配置文件语法
python -c "import yaml; yaml.safe_load(open('~/.vertex/config/llm.yml'.expanduser())); print('✅ 语法正确')"
```

### 2. MCP配置检查
```bash
# 检查MCP配置是否加载
python -c "
from vertex_flow.config.config_loader import load_config
config = load_config()
print('✅ MCP配置存在:', 'mcp' in config)
print('✅ 集成配置存在:', 'integration' in config)
print('✅ MCP启用状态:', config.get('mcp', {}).get('enabled', False))
"
```

### 3. 功能检查
```bash
# 检查MCP模块是否正常工作
python -c "
from vertex_flow.mcp.vertex_integration import MCPLLMVertex
from vertex_flow.workflow.mcp_manager import get_mcp_manager
print('✅ MCP模块导入成功')
"
```

## 🚨 注意事项

### 1. 向后兼容性
- 现有的代码不需要修改，配置加载器会自动从统一文件中读取MCP配置
- 所有MCP相关的API保持不变

### 2. 文档引用
- 所有文档现在都引用统一的 `llm.yml` 配置文件
- 旧的 `mcp.yml` 引用已经全部更新

### 3. 示例代码
- 所有示例代码已更新为使用统一配置
- 配置复制命令已更新

## 📚 相关文档

- [配置统一化文档](CONFIGURATION_UNIFICATION.md)
- [CLI统一化文档](CLI_UNIFICATION.md)
- [MCP集成文档](MCP_INTEGRATION.md)
- [Function Tools MCP集成](FUNCTION_TOOLS_MCP_INTEGRATION.md)

## 🎯 总结

通过这次配置统一化：

1. ✅ **简化管理**: 只需要维护一个配置文件
2. ✅ **减少错误**: 避免多文件配置不一致的问题
3. ✅ **提升体验**: 更直观的配置结构
4. ✅ **保持兼容**: 现有代码无需修改
5. ✅ **完整迁移**: 所有相关文件都已更新

现在您可以享受更简洁的配置管理体验！ 