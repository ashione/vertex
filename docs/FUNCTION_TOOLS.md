# Function Tools Guide - 功能工具完整指南

## 概述

Function Tools 是 Vertex Flow 的核心功能，允许 AI 助手执行各种实际操作，如系统命令、网络搜索、金融数据查询等。这些工具通过标准化接口与 LLM 集成，提供强大的系统交互能力。

## 🛠️ 可用工具

### 1. 命令行工具 (Command Line Tool)

执行本地系统命令，提供安全的命令行接口。

**功能特性**:
- 安全的命令执行环境
- 危险命令自动拦截
- 超时保护和错误处理
- 工作目录隔离

**使用方法**:
```python
from vertex_flow.workflow.service import VertexFlowService

service = VertexFlowService()
cmd_tool = service.get_command_line_tool()

# 执行命令
result = cmd_tool.execute({
    "command": "ls -la",
    "timeout": 30,
    "working_dir": "/tmp"
})
```

**支持的参数**:
- `command`: 要执行的命令 (必需)
- `timeout`: 超时时间(秒) (默认: 30)
- `working_dir`: 工作目录 (默认: 当前目录)
- `capture_output`: 是否捕获输出 (默认: true)
- `shell`: 是否使用 shell (默认: true)

**示例命令**:
- `pwd` - 查看当前目录
- `ls -la` - 列出文件详情
- `python --version` - 检查Python版本
- `git status` - 查看Git状态
- `ps aux | grep python` - 查找Python进程

**详细文档**: [Command Line Tool Guide](COMMAND_LINE_TOOL.md)

### 2. 网络搜索工具 (Web Search Tool)

通过多个搜索引擎API进行网络搜索。

**功能特性**:
- 支持多种搜索引擎 (Bocha, SerpAPI等)
- 实时网络信息获取
- 结构化搜索结果
- 可配置搜索参数

**使用方法**:
```python
service = VertexFlowService()
web_tool = service.get_web_search_tool(provider="bocha")

# 搜索信息
result = web_tool.execute({
    "query": "OpenAI GPT-4最新消息",
    "count": 5
})
```

**支持的参数**:
- `query`: 搜索关键词 (必需)
- `count`: 返回结果数量 (默认: 10)
- `language`: 搜索语言 (默认: auto)
- `region`: 搜索区域 (默认: auto)

**示例查询**:
- "2024年AI最新发展"
- "Python 3.12新特性"
- "深度学习最佳实践"
- "OpenAI API使用指南"

**配置要求**:
```yaml
# config/llm.yml
web-search:
  bocha:
    sk: "your-bocha-api-key"
    enabled: true
```

### 3. 金融数据工具 (Finance Tool)

获取股票、经济数据和金融信息。

**功能特性**:
- 实时股价查询
- 历史价格数据
- 经济指标获取
- 多数据源支持 (Alpha Vantage, Finnhub, Yahoo Finance)

**使用方法**:
```python
service = VertexFlowService()
finance_tool = service.get_finance_tool()

# 查询股票信息
result = finance_tool.execute({
    "action": "get_stock_price",
    "symbol": "AAPL",
    "period": "1d"
})
```

**支持的操作**:
- `get_stock_price`: 获取股票价格
- `get_historical_data`: 获取历史数据
- `get_market_news`: 获取市场新闻
- `get_company_info`: 获取公司信息

**示例查询**:
- 苹果公司当前股价
- 过去一年的股价走势
- 最新财经新闻
- 市场指数表现

**配置要求**:
```yaml
# config/llm.yml
finance:
  alpha-vantage:
    api-key: "your-alpha-vantage-key"
    enabled: true
  finnhub:
    api-key: "your-finnhub-key"
    enabled: true
  yahoo-finance:
    enabled: true
```

## 🚀 在 Workflow App 中使用

### 启动带工具的聊天应用

```bash
# 启动支持Function Tools的聊天应用
python vertex_flow/src/workflow_app.py --port 7864
```

### 界面操作

1. **启用工具**: 勾选 "启用Function Tools" 复选框
2. **查看可用工具**: 在 "可用工具" 下拉菜单中查看已加载的工具
3. **测试工具**: 在 "命令行工具测试" 区域直接测试命令
4. **AI对话**: 在对话中请求AI使用工具

### AI对话示例

**用户**: "请帮我查看当前目录的文件"
**AI**: 使用命令行工具执行 `ls -la` 命令

**用户**: "搜索一下最新的AI技术发展"
**AI**: 使用网络搜索工具查找相关信息

**用户**: "查询苹果公司的股价"
**AI**: 使用金融工具获取AAPL股票信息

## 🛡️ 安全机制

### 命令行工具安全
- 危险命令自动拦截 (`rm -rf /`, `sudo rm`, `format`等)
- 超时保护防止无限执行
- 工作目录隔离
- 详细的执行日志

### 网络搜索安全
- API密钥安全存储
- 请求频率限制
- 内容过滤机制

### 金融工具安全
- 只读数据访问
- API密钥加密存储
- 请求验证机制

## 📝 开发自定义工具

### 工具结构

```python
from vertex_flow.workflow.tools.functions import FunctionTool

def custom_function(inputs, context=None):
    """自定义工具函数"""
    # 处理输入参数
    param1 = inputs.get('param1')
    
    # 执行功能逻辑
    result = do_something(param1)
    
    # 返回结果
    return {
        "success": True,
        "data": result
    }

def create_custom_tool():
    """创建自定义工具"""
    schema = {
        "type": "function",
        "function": {
            "name": "custom_function",
            "description": "自定义功能描述",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "参数描述"
                    }
                },
                "required": ["param1"]
            }
        }
    }
    
    return FunctionTool(
        name="custom_function",
        description="自定义工具",
        func=custom_function,
        schema=schema
    )
```

### 集成到Service

```python
# 在 vertex_flow/workflow/service.py 中添加
def get_custom_tool(self):
    """获取自定义工具实例"""
    from vertex_flow.workflow.tools.custom import create_custom_tool
    return create_custom_tool()
```

### 在LLM Vertex中使用

```python
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex

# 创建包含工具的LLM Vertex
llm_vertex = LLMVertex(
    id="assistant",
    name="AI助手",
    model=model,
    params={
        "system": "你是一个智能助手，可以使用各种工具帮助用户。",
        "user": [],
        "enable_stream": True
    },
    tools=[cmd_tool, web_tool, finance_tool, custom_tool]
)
```

## 📊 工具性能监控

### 执行日志

所有工具执行都会产生详细日志：

```
2024-01-01 10:00:00 - INFO - Tool 'execute_command' called with inputs: {'command': 'ls -la'}
2024-01-01 10:00:00 - INFO - Command completed with exit code: 0
```

### 性能指标

- 执行时间统计
- 成功/失败率
- 错误类型分析
- 资源使用情况

### 调试建议

1. **启用详细日志**:
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   ```

2. **检查工具状态**:
   ```python
   service = VertexFlowService()
   print(f"可用工具: {len(service.available_tools)}")
   ```

3. **测试单个工具**:
   ```python
   tool = service.get_command_line_tool()
   result = tool.execute({"command": "echo test"})
   print(result)
   ```

## 🔧 配置管理

### 工具配置文件

所有工具的配置都在 `config/llm.yml` 中：

```yaml
# 网络搜索配置
web-search:
  bocha:
    sk: "api-key"
    enabled: true

# 金融数据配置  
finance:
  alpha-vantage:
    api-key: "api-key"
    enabled: true
  yahoo-finance:
    enabled: true

# 其他工具配置...
```

### 环境变量支持

```bash
export WEB_SEARCH_BOCHA_SK="your-bocha-key"
export FINANCE_ALPHA_VANTAGE_API_KEY="your-alpha-key"
export FINANCE_FINNHUB_API_KEY="your-finnhub-key"
```

### 配置优先级

1. 环境变量
2. 用户配置文件
3. 默认配置

## 📖 示例代码

### 完整示例

```bash
# 运行各种工具示例
cd vertex_flow/examples

# 命令行工具示例
python command_line_example.py

# 网络搜索工具示例  
python web_search_example.py

# 金融数据工具示例
python finance_example.py
```

### 集成示例

```python
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex

# 初始化服务和工具
service = VertexFlowService()
cmd_tool = service.get_command_line_tool()
web_tool = service.get_web_search_tool()
finance_tool = service.get_finance_tool()

# 创建支持所有工具的LLM
llm_model = service.get_chatmodel()
llm_vertex = LLMVertex(
    id="multi_tool_assistant",
    name="多功能AI助手", 
    model=llm_model,
    params={
        "system": "你是一个多功能AI助手，可以执行命令、搜索网络、查询金融数据。",
        "user": [],
        "enable_stream": True
    },
    tools=[cmd_tool, web_tool, finance_tool]
)

# 使用示例
user_messages = [
    "请查看当前目录的文件",
    "搜索Python最新版本信息", 
    "查询苹果公司股价"
]

for message in user_messages:
    inputs = {
        "conversation_history": [],
        "current_message": message
    }
    
    # AI会自动选择合适的工具
    response = llm_vertex.execute(inputs, {})
    print(f"用户: {message}")
    print(f"AI: {response}")
    print("-" * 50)
```

## 🚨 注意事项

### 安全警告

⚠️ **命令行工具**:
- 具有系统级权限，使用需谨慎
- 不建议在生产环境无限制开放
- 定期检查和更新危险命令黑名单

⚠️ **网络搜索工具**:
- 遵守API使用条款和频率限制
- 注意搜索内容的版权和隐私问题

⚠️ **金融工具**:
- 数据仅供参考，不构成投资建议
- 注意API配额和费用

### 最佳实践

1. **权限控制**: 为不同用户/环境配置不同的工具权限
2. **监控日志**: 定期检查工具使用日志
3. **配额管理**: 设置API调用频率限制
4. **错误处理**: 实现优雅的错误处理和回退机制
5. **安全审计**: 定期进行安全审计和漏洞检查

### 故障排除

1. **工具不可用**: 检查配置文件和API密钥
2. **权限错误**: 确认执行权限和工作目录
3. **网络错误**: 检查网络连接和防火墙设置
4. **超时问题**: 调整超时设置或优化命令
5. **配额超限**: 检查API使用情况和配额限制

## 📚 相关文档

- [Command Line Tool详细指南](COMMAND_LINE_TOOL.md)
- [Web Search示例](../vertex_flow/examples/web_search_example.py)
- [Finance Tool示例](../vertex_flow/examples/finance_example.py)
- [Workflow Chat App使用指南](WORKFLOW_CHAT_APP.md)
- [配置系统文档](../vertex_flow/config/README.md) 