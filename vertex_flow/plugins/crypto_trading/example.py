#!/usr/bin/env python3
"""
Crypto Trading Plugin Example

This example demonstrates how to use the crypto trading plugin for quantitative trading.
"""

import os
import sys
import time
from typing import Any, Dict

# Add the plugin to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ Loaded .env file")
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: uv add python-dotenv")
    print("   Environment variables will be loaded from system environment only.")
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")

from client import CryptoTradingClient
from indicators import TechnicalIndicators
from position_metrics import PositionMetrics
from trading import TradingEngine

from config import CryptoTradingConfig


def setup_config_example():
    """Example of setting up configuration programmatically"""
    config = CryptoTradingConfig()

    # Set OKX configuration (replace with your actual credentials)
    config.set_okx_config(
        api_key="your_okx_api_key",
        secret_key="your_okx_secret_key",
        passphrase="your_okx_passphrase",
        sandbox=True,  # Use sandbox for testing
    )

    # Set Binance configuration (replace with your actual credentials)
    config.set_binance_config(
        api_key="your_binance_api_key", secret_key="your_binance_secret_key", sandbox=True  # Use sandbox for testing
    )

    # Adjust trading parameters
    # config.trading_config.default_symbol = "BTC-USDT"
    config.trading_config.default_symbol = "PUMP-USDT"
    config.trading_config.risk_percentage = 0.01  # 1% risk per trade
    config.trading_config.max_position_size = 100.0  # Max $100 per trade

    return config


def get_symbol_for_exchange(config: CryptoTradingConfig, exchange: str) -> str:
    """
    Get the symbol formatted for the specific exchange

    Args:
        config: Trading configuration
        exchange: Exchange name ('okx' or 'binance')

    Returns:
        Symbol formatted for the exchange
    """
    default_symbol = config.trading_config.default_symbol

    # If the symbol is already in the correct format for the exchange, return it
    if exchange == "okx":
        # OKX uses format like "BTC-USDT"
        if "-" in default_symbol:
            return default_symbol
        else:
            # Convert from Binance format (BTCUSDT) to OKX format (BTC-USDT)
            # This is a simple conversion, might need adjustment for other symbols
            if default_symbol.endswith("USDT"):
                base = default_symbol[:-4]
                return f"{base}-USDT"
            elif default_symbol.endswith("USDC"):
                base = default_symbol[:-4]
                return f"{base}-USDC"
            else:
                return default_symbol
    else:
        # Binance uses format like "BTCUSDT"
        if "-" not in default_symbol:
            return default_symbol
        else:
            # Convert from OKX format (BTC-USDT) to Binance format (BTCUSDT)
            return default_symbol.replace("-", "")


def basic_usage_example():
    """Basic usage example"""
    print("=== Crypto Trading Plugin Basic Usage Example ===\n")

    # Initialize configuration (will load from environment variables and .env file)
    config = CryptoTradingConfig()
    client = CryptoTradingClient(config)

    # Display configuration status
    print("📋 Configuration Status:")
    print(f"   OKX configured: {'✅' if config.okx_config else '❌'}")
    print(f"   Binance configured: {'✅' if config.binance_config else '❌'}")

    # Check available exchanges
    exchanges = client.get_available_exchanges()
    print(f"\n🏢 Available exchanges: {exchanges}")

    if not exchanges:
        print("\n❌ No exchanges configured. Please set up your API credentials.")
        print("\n📝 To configure exchanges:")
        print("   1. Copy .env.example to .env")
        print("   2. Fill in your API credentials")
        print("   3. Set sandbox=true for testing")
        return

    # Use the first available exchange for examples
    exchange = exchanges[0]
    symbol = get_symbol_for_exchange(config, exchange)

    print(f"\n🔄 Using exchange: {exchange}")
    print(f"📊 Trading symbol: {symbol}")

    # Get account information
    print("\n--- Account Information ---")
    account_info = client.get_account_info(exchange)
    if "error" not in account_info:
        print(f"💰 Account balances: {account_info.get('balances', {})}")
    else:
        print(f"❌ Error getting account info: {account_info['error']}")

    # Get trading fees
    print("\n--- Trading Fees ---")
    fees = client.get_trading_fees(exchange, symbol)
    print(f"📈 Maker fee: {fees.get('maker_fee', 'N/A')}")
    print(f"📉 Taker fee: {fees.get('taker_fee', 'N/A')}")

    # Get ticker information
    print("\n--- Market Data ---")
    ticker = client.get_ticker(exchange, symbol)
    if "error" not in ticker:
        print(f"💵 Current price: ${ticker.get('price', 'N/A')}")
        print(f"📊 24h volume: {ticker.get('volume', 'N/A')}")
        print(f"📈 24h change: {ticker.get('change', 'N/A')}%")
    else:
        # 从错误字典中获取用户友好的错误消息
        error_msg = ticker.get("user_message", ticker.get("message", "Unknown error"))
        print(f"❌ Error getting ticker: {error_msg}")


def technical_analysis_example():
    """Technical analysis example"""
    print("\n=== Technical Analysis Example ===\n")

    config = CryptoTradingConfig()
    client = CryptoTradingClient(config)

    exchanges = client.get_available_exchanges()
    if not exchanges:
        print("No exchanges configured.")
        return

    exchange = exchanges[0]
    symbol = get_symbol_for_exchange(config, exchange)

    # Get klines data
    print(f"Getting klines data for {symbol} on {exchange}...")
    klines = client.get_klines(exchange, symbol, "1h", 100)

    if not klines:
        print("Failed to get klines data")
        return

    print(f"Retrieved {len(klines)} klines")

    # Calculate technical indicators
    print("\n--- Technical Indicators ---")
    indicators = TechnicalIndicators.calculate_all_indicators(klines)

    if "error" not in indicators:
        print(f"Current price: ${indicators.get('current_price', 'N/A')}")
        print(f"RSI (14): {indicators.get('rsi', 'N/A')}")
        print(f"SMA (20): ${indicators.get('sma_20', 'N/A')}")
        print(f"EMA (12): ${indicators.get('ema_12', 'N/A')}")

        if "macd" in indicators:
            macd = indicators["macd"]
            print(f"MACD: {macd.get('macd', 'N/A')}")
            print(f"MACD Signal: {macd.get('signal', 'N/A')}")

        if "bollinger_bands" in indicators:
            bb = indicators["bollinger_bands"]
            print(f"Bollinger Upper: ${bb.get('upper', 'N/A')}")
            print(f"Bollinger Lower: ${bb.get('lower', 'N/A')}")
    else:
        print(f"Error calculating indicators: {indicators['error']}")

    # Generate trading signals
    print("\n--- Trading Signals ---")
    signals = TechnicalIndicators.get_trading_signals(indicators)

    for indicator, signal in signals.items():
        print(f"{indicator.upper()}: {signal}")


def trading_example():
    """Trading example (DEMO ONLY - DO NOT USE WITH REAL MONEY)"""
    print("\n=== Trading Example (DEMO ONLY) ===\n")
    print("WARNING: This is for demonstration only. Do not use with real money!")

    config = CryptoTradingConfig()
    client = CryptoTradingClient(config)
    trading_engine = TradingEngine(client)

    exchanges = client.get_available_exchanges()
    if not exchanges:
        print("No exchanges configured.")
        return

    exchange = exchanges[0]
    symbol = get_symbol_for_exchange(config, exchange)

    # Get trading summary
    print(f"Getting trading summary for {symbol} on {exchange}...")
    summary = trading_engine.get_trading_summary(exchange, symbol)

    if "error" not in summary:
        print(f"\nMarket Price: ${summary['market_data'].get('price', 'N/A')}")
        print(f"Overall Signal: {summary['technical_analysis']['overall_signal']}")
        print(f"Recommended Position Size: ${summary['risk_management']['recommended_position_size_usdt']}")

        # Show individual signals
        signals = summary["technical_analysis"]["signals"]
        print("\nIndividual Signals:")
        for indicator, signal in signals.items():
            if indicator != "overall":
                print(f"  {indicator}: {signal}")
    else:
        print(f"Error getting trading summary: {summary['error']}")

    # Example of manual trading (commented out for safety)
    """
    # UNCOMMENT ONLY FOR TESTING WITH SANDBOX/TESTNET
    
    # Manual buy order example
    print("\n--- Manual Buy Order Example ---")
    buy_result = trading_engine.buy_market(exchange, symbol, 10.0)  # $10 worth
    print(f"Buy order result: {buy_result}")
    
    # Manual sell order example
    print("\n--- Manual Sell Order Example ---")
    sell_result = trading_engine.sell_market(exchange, symbol, 0.001)  # 0.001 BTC
    print(f"Sell order result: {sell_result}")
    
    # Auto trading based on signals
    print("\n--- Auto Trading Example ---")
    auto_trade_result = trading_engine.auto_trade_by_signals(exchange, symbol, 10.0)
    print(f"Auto trade result: {auto_trade_result}")
    """


def risk_management_example():
    """Risk management example"""
    print("\n=== Risk Management Example ===\n")

    config = CryptoTradingConfig()
    client = CryptoTradingClient(config)
    trading_engine = TradingEngine(client)

    exchanges = client.get_available_exchanges()
    if not exchanges:
        print("No exchanges configured.")
        return

    exchange = exchanges[0]
    symbol = get_symbol_for_exchange(config, exchange)

    # Calculate position size
    position_size = trading_engine.calculate_position_size(exchange, symbol)
    print(f"Recommended position size: ${position_size}")

    # Get current price for stop loss/take profit calculation
    ticker = client.get_ticker(exchange, symbol)
    if "error" not in ticker:
        current_price = ticker["price"]

        # Calculate stop loss and take profit for buy order
        sl_tp_buy = trading_engine.calculate_stop_loss_take_profit(current_price, "buy")
        print(f"\nFor BUY at ${current_price}:")
        print(f"Stop Loss: ${sl_tp_buy['stop_loss']}")
        print(f"Take Profit: ${sl_tp_buy['take_profit']}")

        # Calculate stop loss and take profit for sell order
        sl_tp_sell = trading_engine.calculate_stop_loss_take_profit(current_price, "sell")
        print(f"\nFor SELL at ${current_price}:")
        print(f"Stop Loss: ${sl_tp_sell['stop_loss']}")
        print(f"Take Profit: ${sl_tp_sell['take_profit']}")


def positions_example():
    """Positions query example"""
    print("\n=== Positions Query Example ===\n")

    config = CryptoTradingConfig()
    client = CryptoTradingClient(config)

    exchanges = client.get_available_exchanges()
    if not exchanges:
        print("No exchanges configured.")
        return

    # 查询所有交易所的持仓
    print("=== All Exchanges Positions ===")
    all_positions = client.get_all_positions()

    if "error" in all_positions:
        print(f"Error getting all positions: {all_positions['error']}")
        return

    for exchange_name, positions in all_positions.get("all_exchanges", {}).items():
        print(f"\n--- {exchange_name.upper()} Exchange ---")

        # 现货持仓
        spot_positions = positions.get("spot", {})
        if "error" in spot_positions:
            print(f"Spot positions error: {spot_positions['error']}")
        else:
            # 修复：使用正确的数据字段
            spot_data = spot_positions.get("data", [])
            if spot_data:
                print("Spot Positions:")
                for position in spot_data:
                    currency = position["currency"]
                    balance = position["balance"]
                    available = position["available"]
                    frozen = position["frozen"]
                    print(f"  {currency}: Available={available:.8f}, " f"Frozen={frozen:.8f}, Total={balance:.8f}")
            else:
                print("No spot positions found")

        # 合约持仓
        futures_positions = positions.get("futures", {})
        if "error" in futures_positions:
            print(f"Futures positions error: {futures_positions['error']}")
        else:
            # 修复：使用正确的数据字段
            futures_data = futures_positions.get("data", [])
            if futures_data:
                print("Futures Positions:")
                for position in futures_data:
                    symbol = position["symbol"]
                    side = position["side"]
                    size = position["size"]
                    entry_price = position.get("entry_price", 0)
                    pnl = position.get("unrealized_pnl", 0)
                    pnl_str = f"+{pnl:.2f}" if pnl >= 0 else f"{pnl:.2f}"
                    print(f"  {symbol}: Side={side}, Size={size:.8f}, " f"Entry=${entry_price:.4f}, PnL=${pnl_str}")
            else:
                print("No futures positions found")

    # 查询单个交易所的详细持仓
    print(f"\n=== Detailed Positions for {exchanges[0].upper()} ===")
    exchange = exchanges[0]

    # 现货持仓详情
    spot_positions = client.get_spot_positions(exchange)
    print("\nSpot Positions Detail:")
    if "error" in spot_positions:
        print(f"Error: {spot_positions['error']}")
    else:
        # 修复：使用正确的数据字段
        positions_data = spot_positions.get("data", [])
        if positions_data:
            for position in positions_data:
                currency = position["currency"]
                balance = position["balance"]
                available = position["available"]
                frozen = position["frozen"]
                print(f"Currency: {currency}")
                print(f"  Available: {available:.8f}")
                print(f"  Frozen: {frozen:.8f}")
                print(f"  Total: {balance:.8f}")
                print()
        else:
            print("No spot positions")

    # 合约持仓详情
    futures_positions = client.get_futures_positions(exchange)
    print("Futures Positions Detail:")
    if "error" in futures_positions:
        print(f"Error: {futures_positions['error']}")
    else:
        # 修复：使用正确的数据字段
        positions_data = futures_positions.get("data", [])
        if positions_data:
            for position in positions_data:
                symbol = position["symbol"]
                side = position["side"]
                size = position["size"]
                entry_price = position.get("entry_price", 0)
                mark_price = position.get("mark_price", 0)
                pnl = position.get("unrealized_pnl", 0)
                leverage = position.get("leverage", "N/A")

                print(f"Symbol: {symbol}")
                print(f"  Side: {side}")
                print(f"  Size: {size:.8f}")
                print(f"  Entry Price: ${entry_price:.4f}")
                print(f"  Mark Price: ${mark_price:.4f}")
                print(f"  Unrealized PnL: ${pnl:.2f}")
                if leverage != "N/A":
                    print(f"  Leverage: {leverage}x")
                print()
        else:
            print("No futures positions")


def futures_metrics_example():
    """合约持仓指标计算示例"""
    print("\n=== 合约持仓指标计算示例 ===\n")

    config = CryptoTradingConfig()
    client = CryptoTradingClient(config)

    exchanges = client.get_available_exchanges()
    if not exchanges:
        print("No exchanges configured.")
        return

    # 收集所有交易所的合约持仓
    all_futures_positions = []
    total_balance = 0

    for exchange in exchanges:
        print(f"\n--- 分析 {exchange.upper()} 合约持仓指标 ---")

        # 获取合约持仓
        futures_positions = client.get_futures_positions(exchange)

        if "error" in futures_positions:
            print(f"❌ 获取 {exchange} 合约持仓失败: {futures_positions['error']}")
            continue

        positions_data = futures_positions.get("data", [])

        if not positions_data:
            print(f"📭 {exchange} 暂无合约持仓")
            continue

        print(f"📊 找到 {len(positions_data)} 个合约持仓")

        # 计算每个持仓的指标
        for position in positions_data:
            metrics = PositionMetrics.calculate_position_metrics(position, exchange)
            if "error" not in metrics:
                all_futures_positions.append(metrics)
                print(PositionMetrics.format_metrics_display(metrics))

        # 尝试获取账户余额（用于计算资产利用率）
        try:
            account_info = client.get_balance(exchange)
            if "error" not in account_info and "total_balance" in account_info:
                total_balance += account_info["total_balance"]
        except:
            pass

    # 计算投资组合综合指标
    if all_futures_positions:
        print("\n" + "=" * 60)
        print("🎯 计算投资组合综合指标...")
        print("=" * 60)

        portfolio_metrics = PositionMetrics.calculate_portfolio_metrics(all_futures_positions, total_balance)

        if "error" not in portfolio_metrics:
            print(PositionMetrics.format_metrics_display(portfolio_metrics))

            # 风险提醒
            print("\n⚠️ 风险提醒:")
            risk_dist = portfolio_metrics.get("风险等级分布", {})

            if risk_dist.get("extreme", 0) > 0:
                print(f"🔴 发现 {risk_dist['extreme']} 个极高风险持仓，建议立即关注！")

            if risk_dist.get("high", 0) > 0:
                print(f"🟠 发现 {risk_dist['high']} 个高风险持仓，请密切监控")

            # 杠杆提醒
            avg_leverage = float(portfolio_metrics.get("平均杠杆", "0x").replace("x", ""))
            if avg_leverage > 10:
                print(f"⚡ 平均杠杆较高 ({avg_leverage:.1f}x)，请注意风险控制")

            # 盈亏提醒
            total_pnl_pct = float(portfolio_metrics.get("总盈亏率", "0%").replace("%", ""))
            if total_pnl_pct < -20:
                print(f"📉 总盈亏率为 {total_pnl_pct:.1f}%，建议考虑止损策略")
            elif total_pnl_pct > 50:
                print(f"📈 总盈亏率为 {total_pnl_pct:.1f}%，建议考虑止盈策略")
        else:
            print(f"❌ 计算投资组合指标失败: {portfolio_metrics['error']}")
    else:
        print("\n📭 未找到任何合约持仓，无法计算指标")


def main():
    """Main function to run all examples"""
    print("🚀 Crypto Trading Plugin Examples")
    print("=" * 50)

    try:
        # Basic usage
        basic_usage_example()

        # Technical analysis
        technical_analysis_example()

        # Trading example
        trading_example()

        # Risk management
        risk_management_example()

        # Positions query
        positions_example()

        # Futures metrics calculation
        futures_metrics_example()

    except Exception as e:
        print(f"Error running examples: {e}")


if __name__ == "__main__":
    main()
