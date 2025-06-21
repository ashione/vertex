# Web搜索配置指南

## 概述

Vertex Flow支持多种Web搜索引擎，采用同级别架构设计。系统会按优先级顺序自动选择第一个启用且配置正确的搜索服务。

## 支持的搜索引擎

### 1. Bocha AI（推荐）
- **特点**：高质量AI总结，支持日期过滤
- **费用**：付费服务，需要API密钥
- **优势**：搜索结果质量最高，提供智能总结
- **适用场景**：专业研究、深度分析

### 2. DuckDuckGo
- **特点**：免费即时答案，隐私保护
- **费用**：完全免费，无需API密钥
- **优势**：快速、免费、隐私友好
- **适用场景**：一般查询、备选方案

### 3. SerpAPI
- **特点**：Google搜索结果，高精度
- **费用**：免费层每月100次，需要API密钥
- **优势**：Google搜索质量，结构化数据
- **适用场景**：需要Google搜索结果的场景

### 4. SearchAPI.io
- **特点**：多搜索引擎支持
- **费用**：免费层每月100次，需要API密钥
- **优势**：支持多种搜索引擎
- **适用场景**：多样化搜索需求

## 优先级顺序

系统按以下顺序尝试搜索服务：
1. **SerpAPI** → 2. **DuckDuckGo** → 3. **Bocha AI** → 4. **SearchAPI.io** → 5. **Bing**

只有启用且配置正确的服务才会被使用。当前配置中SerpAPI被设为最高优先级，因为它提供高质量的Google搜索结果。

## 配置示例

### 基础配置（推荐）
```yaml
web-search:
  # 主要搜索服务（高质量Google结果）
  serpapi:
    api_key: "your-serpapi-key"
    enabled: true
  
  # 免费备选服务
  duckduckgo:
    enabled: true
  
  # 其他服务（可选）
  bocha:
    sk: "your-bocha-api-key"
    enabled: false
  
  searchapi:
    api_key: "your-searchapi-key"
    enabled: false
  
  bing:
    api_key: "your-bing-key"
    enabled: false
```

### 免费配置
```yaml
web-search:
  bocha:
    enabled: false
  
  duckduckgo:
    enabled: true  # 主要使用免费服务
  
  serpapi:
    enabled: false
  
  searchapi:
    enabled: false
```

### 高级配置
```yaml
web-search:
  bocha:
    sk: "your-bocha-api-key"
    enabled: true
  
  duckduckgo:
    enabled: true  # 作为备选
  
  serpapi:
    api_key: "your-serpapi-key"
    enabled: true  # 启用多个付费服务
  
  searchapi:
    api_key: "your-searchapi-key"
    enabled: false
```

## 环境变量支持

可以通过环境变量配置API密钥：

```bash
# Bocha AI
export WEB_SEARCH_BOCHA_SK="your-bocha-api-key"

# SerpAPI
export WEB_SEARCH_SERPAPI_KEY="your-serpapi-key"

# SearchAPI.io
export WEB_SEARCH_SEARCHAPI_KEY="your-searchapi-key"
```

## Function Tool使用

### 基本搜索
```python
{
    "query": "人工智能最新发展",
    "count": 5,
    "summary": true
}
```

### 高级搜索（仅Bocha AI支持）
```python
{
    "query": "ChatGPT发展历程",
    "count": 10,
    "freshness": "oneMonth",  # 一个月内的结果
    "summary": true
}
```

### 日期范围搜索（仅Bocha AI支持）
```python
{
    "query": "AI技术突破",
    "count": 8,
    "freshness": "2024-01-01..2024-06-01",  # 指定日期范围
    "summary": true
}
```

## 返回格式

统一的返回格式：
```json
{
    "success": true,
    "query": "搜索查询",
    "summary": "AI生成的总结（如果支持）",
    "results": [
        {
            "title": "结果标题",
            "url": "结果链接",
            "snippet": "结果摘要",
            "site_name": "网站名称",
            "source": "搜索引擎名称"
        }
    ],
    "total_count": 5,
    "search_engine": "实际使用的搜索引擎",
    "error": ""
}
```

## 故障排除

### 1. 所有搜索服务都不可用
- 检查是否至少启用了一个搜索服务
- 确认API密钥配置正确
- 验证网络连接

### 2. Bocha AI搜索失败
- 检查API密钥是否正确
- 确认API配额是否充足
- 验证网络连接

### 3. 免费服务配额用完
- SerpAPI和SearchAPI有月度免费配额限制
- 可以切换到DuckDuckGo（无限制）
- 或者升级到付费计划

## 最佳实践

### 1. 推荐配置策略
- **生产环境**：Bocha AI（主要）+ DuckDuckGo（备选）
- **开发环境**：DuckDuckGo（主要）+ 免费API（测试）
- **个人使用**：DuckDuckGo（免费）

### 2. API密钥管理
- 使用环境变量存储敏感信息
- 定期轮换API密钥
- 监控API使用量

### 3. 性能优化
- 根据使用场景选择合适的搜索引擎
- 合理设置搜索结果数量
- 利用缓存减少重复请求

## 迁移指南

### 从旧版本升级
如果您使用的是旧版本的配置，请按以下步骤迁移：

1. **备份现有配置**
2. **更新配置结构**：按照新的格式重新组织配置
3. **测试搜索功能**：确认所有搜索服务工作正常
4. **清理废弃配置**：移除不再使用的配置项

### 配置验证
运行以下命令验证配置：
```bash
uv run python -c "
from vertex_flow.workflow.service import VertexFlowService
service = VertexFlowService.get_instance()
for engine in ['bocha', 'duckduckgo', 'serpapi', 'searchapi']:
    config = service.get_web_search_config(engine)
    print(f'{engine}: enabled={config.get(\"enabled\", False)}')
"
```

## 技术支持

如果遇到配置问题，请：
1. 检查日志文件中的错误信息
2. 验证配置文件语法正确
3. 确认API密钥有效性
4. 查看相关文档和示例 