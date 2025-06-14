# 金融工具文档 (Finance Tool)

## 概述

金融工具是VertexFlow框架中的一个综合性Function Tool，提供股票价格查询、汇率转换、财经新闻获取等金融数据服务。该工具设计为可扩展的架构，支持多种金融API集成。

## 功能特性

### 🏢 股票价格查询
- 实时股票价格获取
- 涨跌幅和成交量信息
- 支持主要美股代码（AAPL、TSLA、GOOGL等）
- 自动降级到模拟数据（演示模式）

### 💱 汇率转换
- 实时汇率查询
- 支持主要货币对（USD/CNY、EUR/USD等）
- 货币转换计算
- 历史汇率数据

### 📰 财经新闻
- 分类财经新闻获取
- 支持多种新闻类别（科技、外汇、加密货币等）
- 新闻摘要和来源信息
- 时间戳和分类标签

## 安装和配置

### 基本安装

金融工具已集成在VertexFlow中，无需额外安装：

```python
from vertex_flow.workflow.tools.finance import create_finance_tool, finance_function
```

### API配置（可选）

为了获取真实的金融数据，您可以配置以下API密钥：

```python
# 在finance.py中配置API密钥
class FinanceAPI:
    def __init__(self):
        # 配置Alpha Vantage API密钥（股票数据）
        self.alpha_vantage_key = "YOUR_ALPHA_VANTAGE_KEY"
        # 配置Finnhub API密钥（财经新闻）
        self.finnhub_key = "YOUR_FINNHUB_KEY"
```

**注意**: 当前版本使用模拟数据进行演示，实际部署时建议配置真实API密钥。

## 使用方法

### 作为Function Tool使用

```python
from vertex_flow.workflow.tools.finance import create_finance_tool

# 创建工具实例
finance_tool = create_finance_tool()

# 在LLM中使用
tools = [finance_tool]

# 查询股票价格
result = finance_tool.execute({
    "action": "stock_price",
    "symbol": "AAPL"
})

print(f"苹果股价: ${result['data']['price']}")
```

### 直接函数调用

```python
from vertex_flow.workflow.tools.finance import finance_function

# 查询汇率
result = finance_function({
    "action": "exchange_rate",
    "from_currency": "USD",
    "to_currency": "CNY"
})

print(f"美元对人民币汇率: {result['data']['rate']}")
```

## API参考

### 输入参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `action` | string | ✅ | 操作类型：`stock_price`、`exchange_rate`、`financial_news` |
| `symbol` | string | 条件 | 股票代码（stock_price时必需） |
| `from_currency` | string | 条件 | 源货币代码（exchange_rate时必需） |
| `to_currency` | string | 条件 | 目标货币代码（exchange_rate时必需） |
| `category` | string | ❌ | 新闻类别（financial_news时可选） |
| `count` | integer | ❌ | 返回数量（financial_news时可选，默认5） |

### 操作类型详解

#### 1. 股票价格查询 (`stock_price`)

**输入示例**:
```json
{
    "action": "stock_price",
    "symbol": "AAPL"
}
```

**输出示例**:
```json
{
    "success": true,
    "action": "stock_price",
    "data": {
        "symbol": "AAPL",
        "price": 175.50,
        "change": 2.30,
        "change_percent": "+1.33%",
        "volume": 1500000,
        "latest_trading_day": "2025-06-14",
        "previous_close": 173.20
    }
}
```

#### 2. 汇率转换 (`exchange_rate`)

**输入示例**:
```json
{
    "action": "exchange_rate",
    "from_currency": "USD",
    "to_currency": "CNY"
}
```

**输出示例**:
```json
{
    "success": true,
    "action": "exchange_rate",
    "data": {
        "from_currency": "USD",
        "to_currency": "CNY",
        "rate": 7.25,
        "date": "2025-06-14",
        "base": "USD"
    }
}
```

#### 3. 财经新闻 (`financial_news`)

**输入示例**:
```json
{
    "action": "financial_news",
    "category": "technology",
    "count": 3
}
```

**输出示例**:
```json
{
    "success": true,
    "action": "financial_news",
    "data": {
        "category": "technology",
        "count": 3,
        "news": [
            {
                "headline": "科技股领涨，AI概念股表现强劲",
                "summary": "今日科技股表现强劲...",
                "source": "科技财经",
                "datetime": "2025-06-14 19:35:17",
                "category": "technology"
            }
        ]
    }
}
```

### 支持的货币代码

| 代码 | 货币 |
|------|------|
| USD | 美元 |
| CNY | 人民币 |
| EUR | 欧元 |
| GBP | 英镑 |
| JPY | 日元 |

### 支持的新闻类别

| 类别 | 描述 |
|------|------|
| general | 综合财经新闻 |
| technology | 科技类新闻 |
| forex | 外汇新闻 |
| crypto | 加密货币新闻 |
| automotive | 汽车行业新闻 |
| monetary_policy | 货币政策新闻 |

## 使用示例

### 完整示例代码

```python
#!/usr/bin/env python3
from vertex_flow.workflow.tools.finance import create_finance_tool

def main():
    # 创建金融工具
    finance_tool = create_finance_tool()
    
    # 1. 查询苹果股价
    result = finance_tool.execute({
        "action": "stock_price",
        "symbol": "AAPL"
    })
    
    if result["success"]:
        data = result["data"]
        print(f"📈 {data['symbol']}: ${data['price']} ({data['change_percent']})")
    
    # 2. 查询美元对人民币汇率
    result = finance_tool.execute({
        "action": "exchange_rate",
        "from_currency": "USD",
        "to_currency": "CNY"
    })
    
    if result["success"]:
        data = result["data"]
        print(f"💱 1 {data['from_currency']} = {data['rate']} {data['to_currency']}")
    
    # 3. 获取科技新闻
    result = finance_tool.execute({
        "action": "financial_news",
        "category": "technology",
        "count": 2
    })
    
    if result["success"]:
        news_list = result["data"]["news"]
        for news in news_list:
            print(f"📰 {news['headline']}")

if __name__ == "__main__":
    main()
```

### 在LLM Workflow中使用

```python
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.tools.finance import create_finance_tool

# 创建LLM顶点并添加金融工具
llm_vertex = LLMVertex(
    id="financial_assistant",
    name="金融助手",
    model="gpt-4",
    tools=[create_finance_tool()]
)

# 用户可以通过自然语言查询金融信息
# 例如："帮我查询苹果公司的股价"
# 或者："美元对人民币的汇率是多少？"
```

## 错误处理

金融工具包含完善的错误处理机制：

### 常见错误类型

1. **参数错误**
   ```json
   {"error": "缺少必需参数: symbol"}
   ```

2. **API限制**
   - 自动降级到模拟数据
   - 记录警告日志

3. **网络错误**
   - 自动重试机制
   - 降级到缓存数据

### 错误处理示例

```python
result = finance_tool.execute({"action": "stock_price"})  # 缺少symbol参数

if not result.get("success"):
    print(f"错误: {result['error']}")
    # 处理错误逻辑
else:
    # 正常处理数据
    data = result["data"]
```

## 扩展开发

### 添加新的金融API

```python
class FinanceAPI:
    def __init__(self):
        # 添加新的API配置
        self.new_api_key = "YOUR_API_KEY"
        self.new_api_base = "https://api.example.com"
    
    def get_crypto_price(self, symbol: str) -> Dict[str, Any]:
        """新增加密货币价格查询"""
        # 实现新功能
        pass
```

### 添加新的操作类型

```python
def finance_function(inputs: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
    action = inputs.get("action")
    
    # 添加新的操作类型
    if action == "crypto_price":
        symbol = inputs.get("symbol")
        result = finance_api.get_crypto_price(symbol)
        return {"success": True, "action": "crypto_price", "data": result}
```

## 性能优化

### 缓存机制

```python
from functools import lru_cache
from datetime import datetime, timedelta

class FinanceAPI:
    @lru_cache(maxsize=100)
    def get_stock_price_cached(self, symbol: str, date: str):
        """带缓存的股票价格查询"""
        return self.get_stock_price(symbol)
```

### 批量查询

```python
def batch_stock_query(symbols: List[str]) -> Dict[str, Any]:
    """批量股票查询"""
    results = {}
    for symbol in symbols:
        results[symbol] = finance_api.get_stock_price(symbol)
    return results
```

## 安全考虑

1. **API密钥管理**
   - 使用环境变量存储API密钥
   - 避免在代码中硬编码敏感信息

2. **请求限制**
   - 实现请求频率限制
   - 添加超时机制

3. **数据验证**
   - 验证输入参数
   - 清理输出数据

## 故障排除

### 常见问题

**Q: 为什么返回的是模拟数据？**
A: 当前版本默认使用模拟数据进行演示。要获取真实数据，请配置相应的API密钥。

**Q: 如何添加新的股票代码？**
A: 在`_get_mock_stock_data`方法中添加新的股票数据，或配置真实的API密钥。

**Q: 汇率数据不准确怎么办？**
A: 检查网络连接和API配置，确保使用的是可靠的汇率API服务。

### 调试模式

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 启用详细日志
result = finance_tool.execute({"action": "stock_price", "symbol": "AAPL"})
```

## 更新日志

### v1.0.0 (2025-06-14)
- ✅ 初始版本发布
- ✅ 支持股票价格查询
- ✅ 支持汇率转换
- ✅ 支持财经新闻获取
- ✅ 完整的错误处理机制
- ✅ 模拟数据支持

## 贡献指南

欢迎贡献代码和建议！请遵循以下步骤：

1. Fork项目仓库
2. 创建功能分支
3. 提交代码更改
4. 创建Pull Request

## 许可证

本项目遵循MIT许可证。详情请参阅LICENSE文件。

---

希望这个金融工具能够帮助您更好地处理金融数据查询需求！如有问题或建议，请随时联系我们。