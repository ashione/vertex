# MCP工作流使用指南

## 概述

本文档介绍如何使用MCP（Model Context Protocol）增强的工作流功能。我们提供了一个完整的工作示例，展示如何通过MCP协议访问外部资源并进行AI分析。

## 功能特点

- ✅ **确保MCP调用成功**：使用多种方法和回退机制
- ✅ **完整的工作流演示**：从文件创建到AI分析的完整流程
- ✅ **智能错误处理**：详细的错误诊断和恢复机制
- ✅ **中文友好**：完整的中文输出和说明

## 快速开始

### 1. 运行MCP工作流示例

```bash
cd /path/to/localqwen
uv run python vertex_flow/examples/mcp_simple_working_example.py
```

### 2. 示例输出

程序会输出详细的执行结果，包括：

```
🚀 MCP简单工作示例执行结果
================================================================================
📝 文件创建结果:
  ✅ 成功创建测试文件
  📁 文件路径: /Users/wjf/workspaces/mcp_workflow_test.txt
  📊 文件大小: 1234 字符

📖 MCP读取结果:
  ✅ 成功读取文件内容
  🔧 使用方法: MCP Manager - file:///Users/wjf/workspaces/mcp_workflow_test.txt
  📊 内容长度: 1234 字符
  🔗 MCP客户端: ['filesystem']

🔍 尝试详情:
  1. 尝试URI格式: /Users/wjf/workspaces/mcp_workflow_test.txt
  2. ✅ 成功读取 1234 字符

🤖 AI分析结果:
------------------------------------------------------------
[详细的AI内容分析结果]
------------------------------------------------------------
```

## 工作流架构

### 核心组件

1. **文件创建器 (File Creator)**
   - 在MCP服务器根目录创建测试文件
   - 确保文件路径在MCP访问范围内

2. **MCP读取器 (MCP Reader)**
   - 使用多种URI格式尝试读取文件
   - 提供文件系统回退机制
   - 详细记录尝试过程

3. **MCP分析器 (MCP Analyzer)**
   - 使用MCP增强的LLM进行内容分析
   - 支持中英文混合内容分析
   - 提供结构化的分析报告

4. **清理输出器 (Cleanup Sink)**
   - 输出详细的执行结果
   - 自动清理临时文件
   - 提供完整的状态报告

### 数据流

```
[输入] → [文件创建] → [MCP读取] → [AI分析] → [结果输出]
```

## MCP配置

### 服务器配置

确保MCP服务器正确启动：

```bash
npx @modelcontextprotocol/server-filesystem /Users/wjf/workspaces
```

### 配置文件

在 `~/.vertex/config/llm.yml` 中启用MCP：

```yaml
mcp:
  enabled: true
  clients:
    filesystem:
      enabled: true
      transport: "stdio"
      command: "npx"
      args: 
        - "@modelcontextprotocol/server-filesystem"
        - "/Users/wjf/workspaces"
```

## 故障排除

### 常见问题

1. **MCP客户端未连接**
   - 检查MCP服务器是否正确启动
   - 验证配置文件中的MCP设置
   - 确保网络连接正常

2. **文件读取为空**
   - 检查文件路径是否在MCP服务器根目录下
   - 验证文件权限
   - 尝试不同的URI格式

3. **AI分析失败**
   - 检查LLM配置
   - 验证API密钥
   - 确保网络连接正常

### 调试方法

1. **查看详细日志**：程序会输出详细的尝试过程
2. **检查文件系统**：确认测试文件是否正确创建
3. **验证MCP状态**：查看连接的客户端信息

## 扩展使用

### 自定义文件内容

修改 `create_source_vertex()` 中的 `test_content` 变量来自定义测试内容。

### 自定义分析提示

修改 `create_mcp_analyzer()` 中的 `system_message` 来自定义AI分析的重点。

### 添加更多MCP功能

可以扩展示例来使用更多MCP功能：
- 调用外部工具
- 访问数据库
- 集成API服务

## 最佳实践

1. **文件路径管理**：始终确保文件在MCP服务器访问范围内
2. **错误处理**：使用多种方法和回退机制确保稳定性
3. **资源清理**：及时清理临时文件避免积累
4. **日志记录**：保留详细的执行日志便于调试

## 相关文档

- [MCP集成指南](MCP_INTEGRATION.md)
- [MCP快速开始](MCP_QUICK_START.md)
- [功能工具MCP集成](FUNCTION_TOOLS_MCP_INTEGRATION.md)

## 技术支持

如果遇到问题，请：
1. 查看程序输出的详细错误信息
2. 检查MCP服务器和配置
3. 参考相关文档
4. 提交issue并附上完整的错误日志 