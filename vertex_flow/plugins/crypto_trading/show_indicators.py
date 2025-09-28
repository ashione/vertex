#!/usr/bin/env python3
"""
展示持仓技术指标数据
"""

import argparse
import traceback

from client import CryptoTradingClient
from indicators import TechnicalIndicators

from config import CryptoTradingConfig


def format_number(value):
    """格式化数字显示"""
    if value is None:
        return "N/A"
    if isinstance(value, (int, float)):
        magnitude = abs(value)
        if magnitude >= 1000:
            return f"{value:,.2f}"
        if magnitude >= 1:
            return f"{value:.4f}"
        if magnitude >= 0.01:
            return f"{value:.6f}"
        return f"{value:.8f}"
    return str(value)


def safe_float(value):
    """尝试将任意值转换为浮点数"""
    try:
        if value in (None, ""):
            return None
        number = float(value)
        return number
    except (TypeError, ValueError):
        return None


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


def format_price(value):
    """格式化价格，若无数据返回N/A"""
    if value is None:
        return "N/A"
    return f"${format_number(value)}"


def display_indicators(symbol, indicators, position_info="", position_metrics=None):
    """显示单个币种的技术指标"""
    print(f"\n📊 {symbol}")
    if position_info:
        print(f"   {position_info}")

    if position_metrics:
        entry_price = position_metrics.get("entry_price")
        leverage = position_metrics.get("leverage")
        support_level = position_metrics.get("support_level")
        resistance_level = position_metrics.get("resistance_level")
        pivot_level = position_metrics.get("pivot")
        volume_node = position_metrics.get("volume_node")

        leverage_display = "N/A"
        if leverage is not None:
            leverage_display = f"{format_number(leverage)}x"

        print(f"   💰 买入成本: {format_price(entry_price)}")
        print(f"   🎯 杠杆倍数: {leverage_display}")
        print(f"   🛡 支撑位: {format_price(support_level)}")
        print(f"   🧱 阻力位: {format_price(resistance_level)}")
        if pivot_level is not None:
            print(f"   📍 枢轴点: {format_price(pivot_level)}")
        if volume_node is not None:
            print(f"   📦 成交量峰值: {format_price(volume_node)}")

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


def parse_args():
    parser = argparse.ArgumentParser(description="展示现货或合约的技术指标")
    parser.add_argument(
        "-m",
        "--market",
        choices=["spot", "futures", "both"],
        default="both",
        help="选择展示现货、合约或全部 (默认: both)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    show_spot = args.market in {"spot", "both"}
    show_futures = args.market in {"futures", "both"}

    try:
        # 初始化客户端
        config = CryptoTradingConfig()
        client = CryptoTradingClient(config)

        if show_spot:
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

                                support_level = None
                                resistance_level = None
                                pivot_level = None
                                volume_node = None
                                support_data = indicators.get("support_resistance")
                                if support_data:
                                    support_levels = support_data.get("support") or []
                                    if support_levels:
                                        support_level = support_levels[-1]
                                    resistance_levels = support_data.get("resistance") or []
                                    if resistance_levels:
                                        resistance_level = resistance_levels[0]
                                    pivot_level = support_data.get("pivot")
                                    volume_nodes = support_data.get("volume_nodes") or []
                                    if volume_nodes:
                                        volume_node = volume_nodes[0]

                                entry_price = None
                                for key in ("avg_price", "avgPrice", "avg_px", "average_price"):
                                    candidate = safe_float(position.get(key))
                                    if candidate:
                                        entry_price = candidate
                                        break

                                metrics = {
                                    "entry_price": entry_price,
                                    "leverage": 1,
                                    "support_level": support_level,
                                    "resistance_level": resistance_level,
                                    "pivot": pivot_level,
                                    "volume_node": volume_node,
                                }

                                display_indicators(symbol, indicators, position_info, metrics)
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

        if show_futures:
            if show_spot:
                print()
            print("🔸 合约持仓技术指标")
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

                                support_level = None
                                resistance_level = None
                                pivot_level = None
                                volume_node = None
                                support_data = indicators.get("support_resistance")
                                if support_data:
                                    support_levels = support_data.get("support") or []
                                    if support_levels:
                                        support_level = support_levels[-1]
                                    resistance_levels = support_data.get("resistance") or []
                                    if resistance_levels:
                                        resistance_level = resistance_levels[0]
                                    pivot_level = support_data.get("pivot")
                                    volume_nodes = support_data.get("volume_nodes") or []
                                    if volume_nodes:
                                        volume_node = volume_nodes[0]

                                entry_price = safe_float(position.get("avg_price"))
                                if entry_price is None:
                                    entry_price = safe_float(position.get("avg_price_str"))

                                leverage = safe_float(position.get("leverage"))
                                if not leverage:
                                    notional = abs(position.get("notional", 0))
                                    margin = position.get("margin", 0)
                                    if margin:
                                        leverage = notional / margin

                                metrics = {
                                    "entry_price": entry_price,
                                    "leverage": leverage,
                                    "support_level": support_level,
                                    "resistance_level": resistance_level,
                                    "pivot": pivot_level,
                                    "volume_node": volume_node,
                                }

                                display_indicators(symbol, indicators, position_info, metrics)
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
