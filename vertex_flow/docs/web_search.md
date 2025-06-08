# Web Search 工具文档

基于博查AI的Web搜索工具，支持作为function calling工具使用，提供高质量的搜索结果和AI总结。

## 功能特性

- 🔍 **高质量搜索**: 基于博查AI搜索引擎，从近百亿网页中搜索信息
- 🤖 **AI总结**: 自动生成搜索结果的智能总结
- ⚡ **Function Calling**: 完全兼容function calling规范，可直接集成到LLM应用中
- 🔧 **配置驱动**: 从配置文件自动加载API密钥和设置
- 📊 **多种内容源**: 支持新闻、百科、学术、图片、视频等多种内容类型
- 🕒 **时效性控制**: 支持按时间范围筛选搜索结果
- 🛡️ **错误处理**: 完善的错误处理和参数验证机制

## 安装和配置

### 1. 依赖安装

确保已安装必要的依赖包：

```bash
pip install requests pyyaml ruamel.yaml
```

### 2. 配置API密钥

在 `config/llm.yml` 文件中配置博查API密钥：

```yaml
web-search:
  bocha:
    sk: ${web-search.bocha.sk:your-api-key-here}  # 替换为你的博查API密钥
    enabled: true
  bing:
    sk: ${web-search.bing.sk:}
    enabled: false
```

### 3. 获取API密钥

1. 访问 [博查AI开放平台](https://open.bochaai.com/)
2. 注册账号并登录
3. 在控制台中创建应用并获取API密钥
4. 将API密钥配置到上述配置文件中

## 使用方法

### 作为Function Tool使用

```python
from vertex_flow.workflow.tools.web_search import create_web_search_tool

# 创建工具实例（自动使用单例获取配置）
web_search_tool = create_web_search_tool()

# 在LLM中使用
tools = [web_search_tool]

# 执行搜索
result = web_search_tool.execute({
    "query": "人工智能最新发展",
    "num_results": 5
})
```

### 直接函数调用

```python
from vertex_flow.workflow.tools.web_search import web_search_function

# 直接调用搜索函数（自动使用单例获取配置）
result = web_search_function({
    "query": "机器学习教程",
    "search_type": "general",
    "num_results": 10,
    "enable_summary": True
})

if result["success"]:
    print(f"搜索结果: {result['data']}")
else:
    print(f"搜索失败: {result['error']}")
```

### 在LLM Vertex中集成

```python
from vertex_flow.workflow.tools.web_search import create_web_search_tool
from vertex_flow.workflow.service import VertexFlowService

# 在工作流中添加搜索工具
def setup_workflow():
    # 方式1：直接创建搜索工具（推荐）
    web_search_tool = create_web_search_tool()
    
    # 方式2：通过service单例获取
    service = VertexFlowService.get_instance()
    web_search_tool = service.get_web_search_tool("bocha")
    
    # 添加到工具列表
    tools = [
        web_search_tool,
        # 其他工具...
    ]
    
    return tools
```

## API参数说明

### 输入参数

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `query` | string | 是 | - | 搜索查询字符串 |
| `count` | integer | 否 | 8 | 返回结果数量 (1-20) |
| `freshness` | string | 否 | "oneYear" | 时效性: "oneDay", "oneWeek", "oneMonth", "oneYear" |
| `summary` | boolean | 否 | true | 是否返回AI总结 |

### 返回结果

```json
{
  "success": true,
  "query": "搜索查询",
  "summary": "AI生成的搜索结果总结",
  "results": [
    {
      "title": "页面标题",
      "url": "页面URL",
      "snippet": "页面摘要",
      "site_name": "网站名称",
      "site_icon": "网站图标URL"
    }
  ],
  "total_count": 1000,
  "error": ""
}
```

## 使用场景

### 1. 实时信息查询

```python
# 查询最新新闻
result = web_search_function({
    "query": "今日科技新闻",
    "freshness": "oneDay",
    "count": 5
})
```

### 2. 学术研究

```python
# 搜索学术资料
result = web_search_function({
    "query": "machine learning transformer architecture papers",
    "count": 10,
    "summary": True
})
```

### 3. 事实核查

```python
# 验证信息准确性
result = web_search_function({
    "query": "2024年诺贝尔物理学奖获得者",
    "freshness": "oneMonth",
    "summary": True
})
```

### 4. 市场调研

```python
# 行业趋势分析
result = web_search_function({
    "query": "电动汽车市场份额 2024",
    "count": 8,
    "summary": True
})
```

## Function Calling Schema

工具的完整schema定义：

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "搜索查询字符串，描述要搜索的内容"
    },
    "count": {
      "type": "integer",
      "description": "返回结果数量，默认8个，范围1-20",
      "minimum": 1,
      "maximum": 20,
      "default": 8
    },
    "freshness": {
      "type": "string",
      "description": "搜索结果时效性",
      "enum": ["oneDay", "oneWeek", "oneMonth", "oneYear"],
      "default": "oneYear"
    },
    "summary": {
      "type": "boolean",
      "description": "是否返回AI生成的搜索结果总结",
      "default": true
    }
  },
  "required": ["query"]
}
```

## 错误处理

工具包含完善的错误处理机制：

### 常见错误类型

1. **配置错误**
   - API密钥未配置
   - 服务未启用

2. **参数错误**
   - 查询字符串为空
   - 参数类型不正确

3. **网络错误**
   - 请求超时
   - 网络连接失败

4. **API错误**
   - API密钥无效
   - 请求频率限制

### 错误处理示例

```python
result = web_search_function({"query": "测试查询"})

if not result["success"]:
    error_msg = result["error"]
    if "API密钥" in error_msg:
        print("请检查API密钥配置")
    elif "网络" in error_msg:
        print("请检查网络连接")
    else:
        print(f"其他错误: {error_msg}")
```

## 性能优化

### 1. 合理设置参数

- 根据需求设置合适的 `count` 值，避免请求过多结果
- 选择合适的 `freshness` 参数，平衡时效性和结果质量
- 在不需要总结时设置 `summary=False` 以提高响应速度

### 2. 缓存机制

```python
# 可以实现简单的缓存机制
cache = {}

def cached_search(query, **kwargs):
    cache_key = f"{query}_{kwargs}"
    if cache_key in cache:
        return cache[cache_key]
    
    result = web_search_function({"query": query, **kwargs})
    cache[cache_key] = result
    return result
```

### 3. 异步处理

对于批量搜索，可以考虑使用异步处理：

```python
import asyncio
import aiohttp

# 异步版本的搜索函数（需要额外实现）
async def async_web_search(queries):
    tasks = []
    for query in queries:
        task = asyncio.create_task(search_async(query))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

## 最佳实践

### 1. 查询优化

- 使用具体、明确的查询词
- 包含时间、地点等限定词
- 避免过于宽泛的查询

```python
# 好的查询示例
good_queries = [
    "OpenAI GPT-4 2024年最新功能更新",
    "中国新能源汽车销量 2024年第三季度",
    "量子计算IBM最新突破 2024"
]

# 避免的查询示例
bad_queries = [
    "AI",  # 过于宽泛
    "新闻",  # 没有具体内容
    "最新"  # 缺乏上下文
]
```

### 2. 结果处理

```python
def process_search_results(result):
    """处理搜索结果的最佳实践"""
    if not result["success"]:
        return f"搜索失败: {result['error']}"
    
    # 优先使用AI总结
    if result["summary"]:
        response = f"根据搜索结果总结:\n{result['summary']}\n\n"
    else:
        response = ""
    
    # 添加关键结果链接
    response += "相关链接:\n"
    for i, item in enumerate(result["results"][:3], 1):
        response += f"{i}. {item['title']}\n   {item['url']}\n"
    
    return response
```

### 3. 集成到工作流

```python
# 在深度研究工作流中使用
from vertex_flow.workflow.app.deep_research_workflow import DeepResearchWorkflow
from vertex_flow.workflow.tools.web_search import create_web_search_tool

class EnhancedResearchWorkflow(DeepResearchWorkflow):
    def __init__(self, vertex_service):
        super().__init__(vertex_service)
        # 为所有LLM顶点添加搜索工具
        self.search_tool = create_web_search_tool()
    
    def create_information_collection_vertex(self):
        # 信息收集阶段使用搜索工具
        return LLMVertex(
            id="information_collection",
            params={
                "system_prompt": "你是信息收集专家，使用搜索工具获取最新资料。",
                "model_name": "deepseek-chat"
            },
            tools=[self.search_tool]
        )
```

## 故障排除

### 常见问题

1. **"博查API密钥未配置"错误**
   - 检查 `config/llm.yml` 中的配置
   - 确认API密钥格式正确
   - 验证环境变量设置

2. **"博查搜索服务未启用"错误**
   - 将 `web-search.bocha.enabled` 设置为 `true`

3. **搜索请求失败**
   - 检查网络连接
   - 验证API密钥有效性
   - 确认请求频率未超限

4. **返回结果为空**
   - 尝试更通用的查询词
   - 调整 `freshness` 参数
   - 增加 `count` 参数值

### 调试模式

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.INFO)

# 执行搜索查看详细信息
result = web_search_function({
    "query": "测试查询",
    "count": 3
})
```

## 更新日志

### v1.0.0 (2024-01-XX)
- 初始版本发布
- 支持基础Web搜索功能
- 集成博查AI搜索API
- 完整的function calling支持
- 配置文件驱动的API密钥管理

## 许可证

本工具遵循项目的整体许可证。使用博查AI服务需要遵守其服务条款。

## 贡献

欢迎提交Issue和Pull Request来改进这个工具。

## 相关链接

- [博查AI开放平台](https://open.bochaai.com/)
- [博查AI API文档](https://bocha-ai.feishu.cn/wiki/RXEOw02rFiwzGSkd9mUcqoeAnNK)
- [VertexFlow项目文档](../../../README.md)