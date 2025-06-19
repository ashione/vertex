# Command Line Tool - 命令行工具

## 概述

Command Line Tool 是 Vertex Flow 中的一个 Function Tool，允许 AI 助手执行本地命令行操作。该工具提供了安全的命令执行环境，支持多种参数配置，并具备基本的安全防护机制。

## 特性

### 🛡️ 安全特性
- **危险命令拦截**: 自动识别并阻止潜在危险的命令
- **超时保护**: 防止命令无限执行
- **工作目录隔离**: 可指定命令执行的工作目录
- **错误处理**: 完善的异常捕获和错误报告

### ⚙️ 功能特性
- **流式输出**: 支持实时输出捕获
- **退出码检测**: 准确报告命令执行状态
- **编码处理**: 自动处理不同编码的输出
- **Shell 支持**: 支持复杂的 shell 命令和管道操作

## 使用方法

### 1. 在 Workflow App 中使用

启动 `workflow_app.py` 后，在界面中：

1. **启用工具**: 勾选 "启用Function Tools" 复选框
2. **测试命令**: 在 "命令行工具测试" 区域输入命令并执行
3. **AI 对话**: 在对话中请求 AI 执行命令行操作

```bash
uv run python vertex_flow/src/workflow_app.py --port 7864
```

### 2. 编程接口使用

```python
from vertex_flow.workflow.tools.command_line import create_command_line_tool

# 创建工具
cmd_tool = create_command_line_tool()

# 执行命令
result = cmd_tool.execute({
    "command": "ls -la",
    "timeout": 30,
    "working_dir": "/tmp"
})

print(f"成功: {result['success']}")
print(f"输出: {result['stdout']}")
```

### 3. 与 LLM 集成

```python
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.service import VertexFlowService

service = VertexFlowService()
cmd_tool = service.get_command_line_tool()

llm_vertex = LLMVertex(
    id="assistant",
    name="AI助手",
    model=service.get_chatmodel(),
    params={
        "system": "你是系统管理助手，可以执行命令行操作。",
        "user": [],
        "enable_stream": True
    },
    tools=[cmd_tool]  # 传入工具
)
```

## 参数说明

### 输入参数

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `command` | string | 是 | - | 要执行的命令 |
| `timeout` | integer | 否 | 30 | 超时时间（秒） |
| `working_dir` | string | 否 | 当前目录 | 工作目录 |
| `capture_output` | boolean | 否 | true | 是否捕获输出 |
| `shell` | boolean | 否 | true | 是否使用 shell |

### 返回结果

```json
{
    "success": true,
    "exit_code": 0,
    "stdout": "命令输出",
    "stderr": "错误输出",
    "command": "执行的命令",
    "working_dir": "工作目录"
}
```

## 安全机制

### 被阻止的危险命令

工具会自动阻止以下类型的危险命令：
- `rm -rf /` - 删除根目录
- `sudo rm` - 需要管理员权限的删除操作
- `del /s /q` - Windows 批量删除
- `format` - 磁盘格式化
- `fdisk` - 磁盘分区操作

### 建议的安全实践

1. **最小权限原则**: 只给予执行必要命令的权限
2. **工作目录限制**: 在受限的目录中执行命令
3. **超时设置**: 为长时间运行的命令设置合理超时
4. **输入验证**: 在 AI 系统提示中说明命令使用规则

## 示例用法

### 基本命令执行

```python
# 查看当前目录
result = cmd_tool.execute({"command": "pwd"})

# 列出文件
result = cmd_tool.execute({"command": "ls -la"})

# 检查软件版本
result = cmd_tool.execute({"command": "python --version"})
```

### 高级用法

```python
# 在指定目录执行
result = cmd_tool.execute({
    "command": "git status",
    "working_dir": "/path/to/repo"
})

# 设置超时
result = cmd_tool.execute({
    "command": "long_running_command",
    "timeout": 60
})

# 复合命令
result = cmd_tool.execute({
    "command": "echo 'Hello' && echo 'World'"
})
```

### AI 对话示例

当 AI 助手启用了命令行工具后，用户可以这样对话：

**用户**: "请帮我查看当前目录下的文件"
**AI**: "我来帮您查看当前目录的文件。" [调用 execute_command 工具]
**结果**: AI 会执行 `ls -la` 命令并返回文件列表

**用户**: "请检查 Python 版本"
**AI**: "我来检查 Python 版本。" [调用 execute_command 工具]
**结果**: AI 会执行 `python --version` 并返回版本信息

## 配置集成

### Service 层集成

工具已集成到 `VertexFlowService` 中：

```python
service = VertexFlowService()
cmd_tool = service.get_command_line_tool()
```

### Workflow App 集成

在 `workflow_app.py` 中已经集成了命令行工具：

1. **工具初始化**: 应用启动时自动初始化
2. **UI 控制**: 提供启用/禁用工具的界面
3. **测试功能**: 内置命令测试区域
4. **AI 集成**: 自动传递给 LLM Vertex

## 故障排除

### 常见问题

1. **命令被阻止**
   - 检查是否为危险命令
   - 尝试使用更安全的替代命令

2. **超时错误**
   - 增加 timeout 参数值
   - 检查命令是否需要交互式输入

3. **权限错误**
   - 确保有执行命令的权限
   - 避免需要 sudo 的命令

4. **编码问题**
   - 工具自动处理 UTF-8 编码
   - 对于特殊编码，输出可能显示异常

### 调试建议

1. **启用详细日志**:
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   ```

2. **测试简单命令**: 先用 `pwd`, `echo` 等简单命令测试

3. **检查工作目录**: 确保指定的工作目录存在

## API Reference

### create_command_line_tool()

创建命令行工具实例。

**返回**: FunctionTool 实例

### execute_command(inputs, context)

执行命令的核心函数。

**参数**:
- `inputs`: Dict[str, Any] - 输入参数
- `context`: Optional[Dict] - 执行上下文

**返回**: Dict[str, Any] - 执行结果

## 扩展开发

如需扩展命令行工具功能，可以：

1. **添加更多安全检查**: 在 `execute_command` 函数中添加命令验证
2. **支持更多参数**: 扩展 schema 定义
3. **添加命令模板**: 预定义常用命令组合
4. **增强错误处理**: 提供更详细的错误信息

## 注意事项

⚠️ **重要警告**:
- 命令行工具具有系统级权限，使用时需谨慎
- 不建议在生产环境中无限制地开放此工具
- 建议配合适当的系统提示和安全策略使用
- 定期检查和更新危险命令黑名单

🔒 **安全建议**:
- 在受限环境中运行
- 设置合理的超时限制
- 监控和记录命令执行日志
- 定期审查工具使用情况 