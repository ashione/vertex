# Crypto Trading Plugin

数字货币量化交易插件，支持OKX和Binance交易所的API集成，提供账户管理、技术分析和自动化交易功能。

## 功能特性

- **多交易所支持**: 支持OKX和Binance交易所
- **账户管理**: 获取账户信息、余额、交易费率
- **技术分析**: 计算多种技术指标（RSI、MACD、布林带等）
- **自动交易**: 基于技术分析信号的自动买卖
- **风险管理**: 内置止损止盈和仓位管理
- **实时数据**: 获取实时价格、K线数据

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置设置

### 1. 环境变量配置

复制 `.env.example` 到 `.env` 并填入你的API密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# OKX配置
OKX_API_KEY=your_okx_api_key
OKX_SECRET_KEY=your_okx_secret_key
OKX_PASSPHRASE=your_okx_passphrase
OKX_SANDBOX=true  # 测试环境

# Binance配置
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key
BINANCE_SANDBOX=true  # 测试环境
```

### 2. 程序化配置

```python
from crypto_trading.config import CryptoTradingConfig

config = CryptoTradingConfig()

# 设置OKX配置
config.set_okx_config(
    api_key="your_api_key",
    secret_key="your_secret_key",
    passphrase="your_passphrase",
    sandbox=True
)

# 设置Binance配置
config.set_binance_config(
    api_key="your_api_key",
    secret_key="your_secret_key",
    sandbox=True
)
```

## 基本使用

### 1. 初始化客户端

```python
from crypto_trading import CryptoTradingClient, TradingEngine

# 初始化客户端
client = CryptoTradingClient()

# 初始化交易引擎
trading_engine = TradingEngine(client)
```

### 2. 获取账户信息

```python
# 获取所有交易所账户信息
all_accounts = client.get_all_account_info()

# 获取特定交易所账户信息
okx_account = client.get_account_info("okx")
binance_account = client.get_account_info("binance")

# 获取余额
usdt_balance = client.get_balance("okx", "USDT")
all_balances = client.get_balance("okx")
```

### 3. 获取市场数据

```python
# 获取价格信息
ticker = client.get_ticker("okx", "BTC-USDT")
print(f"当前价格: ${ticker['price']}")

# 获取K线数据
klines = client.get_klines("okx", "BTC-USDT", "1h", 100)

# 获取交易费率
fees = client.get_trading_fees("okx", "BTC-USDT")
print(f"挂单费率: {fees['maker_fee']}")
print(f"吃单费率: {fees['taker_fee']}")
```

### 4. 技术分析

```python
from crypto_trading.indicators import TechnicalIndicators

# 获取K线数据
klines = client.get_klines("okx", "BTC-USDT", "1h", 100)

# 计算所有技术指标
indicators = TechnicalIndicators.calculate_all_indicators(klines)

print(f"RSI: {indicators['rsi']}")
print(f"MACD: {indicators['macd']}")
print(f"布林带: {indicators['bollinger_bands']}")

# 生成交易信号
signals = TechnicalIndicators.get_trading_signals(indicators)
print(f"整体信号: {signals['overall']}")
```

### 5. 手动交易

```python
# 市价买入
buy_result = trading_engine.buy_market("okx", "BTC-USDT", 100.0)  # 买入$100
print(f"买入结果: {buy_result}")

# 市价卖出
sell_result = trading_engine.sell_market("okx", "BTC-USDT", 0.001)  # 卖出0.001 BTC
print(f"卖出结果: {sell_result}")

# 限价买入
limit_buy = trading_engine.buy_limit("okx", "BTC-USDT", 0.001, 50000.0)

# 限价卖出
limit_sell = trading_engine.sell_limit("okx", "BTC-USDT", 0.001, 60000.0)
```

### 6. 自动交易

```python
# 基于技术分析信号自动交易
auto_result = trading_engine.auto_trade_by_signals("okx", "BTC-USDT", 100.0)
print(f"自动交易结果: {auto_result}")

# 获取交易摘要
summary = trading_engine.get_trading_summary("okx", "BTC-USDT")
print(f"推荐信号: {summary['technical_analysis']['overall_signal']}")
print(f"推荐仓位: ${summary['risk_management']['recommended_position_size_usdt']}")
```

## 技术指标说明

插件支持以下技术指标：

- **移动平均线**: SMA, EMA
- **动量指标**: RSI, Williams %R
- **趋势指标**: MACD, 布林带
- **波动率指标**: ATR, 布林带
- **成交量指标**: OBV
- **震荡指标**: 随机指标, CCI
- **支撑阻力**: 自动识别支撑阻力位

## 风险管理

插件内置多种风险管理功能：

- **仓位管理**: 基于账户余额和风险比例计算仓位
- **止损止盈**: 自动计算止损止盈价位
- **风险控制**: 限制单笔交易最大金额

```python
# 风险管理配置
config.trading_config.risk_percentage = 0.02  # 每笔交易风险2%
config.trading_config.max_position_size = 1000.0  # 最大仓位$1000
config.trading_config.stop_loss_percentage = 0.05  # 止损5%
config.trading_config.take_profit_percentage = 0.10  # 止盈10%
```

## 注意事项

⚠️ **重要提醒**:

1. **测试环境**: 首次使用请务必在沙盒/测试环境中测试
2. **API权限**: 确保API密钥有足够的交易权限
3. **资金安全**: 不要在生产环境中使用未经充分测试的策略
4. **风险控制**: 始终设置合理的止损和仓位管理
5. **监控**: 定期监控交易结果和账户状态

## 示例代码

运行示例代码：

```bash
python example.py
```

示例包含：
- 基本功能演示
- 技术分析示例
- 交易操作示例
- 风险管理示例

合约订单辅助脚本：

```bash
# 查看当前合约持仓并关联订单ID
python manage_futures_orders.py --show-positions --symbol BTC-USDT-SWAP

# 列出指定合约的未完成订单（可用 state=filled 等历史状态）
python manage_futures_orders.py --list --symbol BTC-USDT-SWAP --state open

# 查询单个订单（ordId或clOrdId）并按需平仓，终端会二次确认
python manage_futures_orders.py --symbol BTC-USDT-SWAP --order-id <ordId> --close --position-side long
```

## 故障排除

### 常见问题

1. **API连接失败**
   - 检查API密钥是否正确
   - 确认网络连接正常
   - 验证API权限设置

2. **交易失败**
   - 检查账户余额是否充足
   - 确认交易对格式正确
   - 验证最小交易数量要求

3. **技术指标计算错误**
   - 确保K线数据充足（至少50根）
   - 检查数据格式是否正确

### 调试模式

启用调试模式获取详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 许可证

本插件遵循MIT许可证。

## 免责声明

本插件仅供学习和研究使用。数字货币交易存在高风险，可能导致资金损失。使用本插件进行实际交易的风险由用户自行承担。
