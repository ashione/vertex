#!/usr/bin/env python3
"""
展示持仓技术指标数据
"""

import traceback

from client import CryptoTradingClient
from config import CryptoTradingConfig
from indicators import TechnicalIndicators


def format_number(value):
    """格式化数字显示"""
    if value is None:
        return "N/A"
    if isinstance(value, (int, float)):
        if abs(value) >= 1000:
            return f"{value:,.2f}"
        else:
            return f"{value:.4f}"
    return str(value)


def get_signal_emoji(rsi, macd_histogram):
    """根据RSI和MACD获取信号表情"""
    if rsi is None or macd_histogram is None:
        return "⚪"

    if rsi > 70 and macd_histogram < 0:
        return "🔴"  # 超买且MACD下降，卖出信号
    elif rsi < 30 and macd_histogram > 0:
        return "🟢"  # 超卖且MACD上升，买入信号
    elif rsi > 50 and macd_histogram > 0:
        return "🟡"  # 中性偏多
    else:
        return "⚪"  # 中性


def display_indicators(symbol, indicators, position_info=""):
    """显示单个币种的技术指标"""
    print(f"\n📊 {symbol}")
    if position_info:
        print(f"   {position_info}")

    if "error" in indicators:
        print(f"   ❌ 计算指标出错: {indicators['error']}")
        return

    current_price = indicators.get("current_price")
    if current_price:
        print(f"   当前价格: ${format_number(current_price)}")

    # RSI
    rsi = indicators.get("rsi")
    if rsi is not None:
        rsi_status = "超买" if rsi > 70 else "超卖" if rsi < 30 else "正常"
        print(f"   📈 RSI(14): {format_number(rsi)} ({rsi_status})")

    # MACD
    macd = indicators.get("macd")
    if macd and isinstance(macd, dict):
        macd_line = macd.get("macd")
        signal_line = macd.get("signal")
        histogram = macd.get("histogram")

        if all(v is not None for v in [macd_line, signal_line, histogram]):
            trend = "上升" if histogram > 0 else "下降"
            print(
                f"   📊 MACD: {format_number(macd_line)} | 信号: {format_number(signal_line)} | 柱状: {format_number(histogram)} ({trend})"
            )

    # 移动平均线
    sma_20 = indicators.get("sma_20")
    ema_12 = indicators.get("ema_12")
    if sma_20 is not None:
        print(f"   📉 SMA(20): {format_number(sma_20)}")
    if ema_12 is not None:
        print(f"   📈 EMA(12): {format_number(ema_12)}")

    # 布林带
    bb = indicators.get("bollinger_bands")
    if bb and isinstance(bb, dict):
        upper = bb.get("upper")
        middle = bb.get("middle")
        lower = bb.get("lower")
        if all(v is not None for v in [upper, middle, lower]):
            print(
                f"   🎯 布林带: 上轨 {format_number(upper)} | 中轨 {format_number(middle)} | 下轨 {format_number(lower)}"
            )

    # 交易信号
    signal_emoji = get_signal_emoji(rsi, macd.get("histogram") if macd else None)
    print(f"   {signal_emoji} 综合信号")


def main():
    try:
        # 初始化客户端
        config = CryptoTradingConfig()
        client = CryptoTradingClient(config)

        print("🔸 现货持仓技术指标")
        print("=" * 40)

        # 获取现货持仓
        spot_positions = client.get_spot_positions("okx")

        if spot_positions.get("success") and spot_positions.get("data"):
            for position in spot_positions["data"]:
                currency = position["currency"]
                balance = position["balance"]

                # 跳过USDT和余额为0的币种
                if currency != "USDT" and float(balance) > 0:
                    symbol = f"{currency}-USDT"
                    position_info = f"持仓量: {format_number(float(balance))} {currency}"

                    try:
                        # 获取K线数据
                        klines = client.get_klines("okx", symbol, "1h", 100)
                        if klines and len(klines) > 26:  # 确保有足够数据计算MACD
                            indicators = TechnicalIndicators.calculate_all_indicators(klines)
                            display_indicators(symbol, indicators, position_info)
                        else:
                            print(f"\n📊 {symbol}")
                            print(f"   {position_info}")
                            print(f"   ❌ K线数据不足 (需要至少26条)")
                    except Exception as e:
                        print(f"\n📊 {symbol}")
                        print(f"   {position_info}")
                        print(f"   ❌ 获取数据失败: {str(e)}")
        else:
            print("   ❌ 无法获取现货持仓数据")

        print("\n\n🔸 合约持仓技术指标")
        print("=" * 40)

        # 获取合约持仓
        futures_positions = client.get_futures_positions("okx")

        if futures_positions.get("success") and futures_positions.get("data"):
            for position in futures_positions["data"]:
                symbol = position["symbol"]
                size = position["size"]
                side = position["side"]
                unrealized_pnl = position.get("unrealized_pnl", 0)

                if float(size) != 0:
                    position_info = f"方向: {side}, 数量: {format_number(float(size))}"
                    if unrealized_pnl:
                        pnl_str = f"${format_number(float(unrealized_pnl))}"
                        position_info += f"\n   未实现盈亏: {pnl_str}"

                    try:
                        # 获取K线数据
                        klines = client.get_klines("okx", symbol, "1h", 100)
                        if klines and len(klines) > 26:
                            indicators = TechnicalIndicators.calculate_all_indicators(klines)
                            display_indicators(symbol, indicators, position_info)
                        else:
                            print(f"\n📊 {symbol}")
                            print(f"   {position_info}")
                            print(f"   ❌ K线数据不足 (需要至少26条)")
                    except Exception as e:
                        print(f"\n📊 {symbol}")
                        print(f"   {position_info}")
                        print(f"   ❌ 获取数据失败: {str(e)}")
        else:
            print("   ❌ 无法获取合约持仓数据")

        print("\n" + "=" * 60)
        print("报告生成完成 ✅")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 程序执行出错: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
