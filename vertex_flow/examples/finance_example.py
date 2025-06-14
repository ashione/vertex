#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金融工具使用示例

本文件展示了如何使用金融工具进行股票价格查询、汇率转换、财经新闻获取等操作。
"""

import asyncio
import json
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vertex_flow.workflow.event_channel import EventChannel
from vertex_flow.workflow.tools.finance import create_finance_tool, finance_function, finance_tool
from vertex_flow.workflow.workflow import Workflow


def example_stock_price_query():
    """股票价格查询示例"""
    print("=== 股票价格查询示例 ===")

    # 直接使用函数
    inputs = {"action": "stock_price", "symbol": "AAPL"}
    result = finance_function(inputs)

    if result.get("success"):
        data = result["data"]
        print(f"股票代码: {data['symbol']}")
        print(f"当前价格: ${data['price']}")
        print(f"涨跌额: ${data['change']}")
        print(f"涨跌幅: {data['change_percent']}")
        print(f"成交量: {data['volume']:,}")
        print(f"交易日期: {data['latest_trading_day']}")
        if "note" in data:
            print(f"注意: {data['note']}")
    else:
        print(f"查询失败: {result.get('error')}")

    print()


def example_exchange_rate_query():
    """汇率查询示例"""
    print("=== 汇率查询示例 ===")

    # 查询美元对人民币汇率
    inputs = {"action": "exchange_rate", "from_currency": "USD", "to_currency": "CNY"}
    result = finance_function(inputs)

    if result.get("success"):
        data = result["data"]
        print(f"汇率: 1 {data['from_currency']} = {data['rate']} {data['to_currency']}")
        print(f"日期: {data['date']}")
        if "note" in data:
            print(f"注意: {data['note']}")
    else:
        print(f"查询失败: {result.get('error')}")

    print()


def example_financial_news_query():
    """财经新闻查询示例"""
    print("=== 财经新闻查询示例 ===")

    # 查询科技类财经新闻
    inputs = {"action": "financial_news", "category": "technology", "count": 3}
    result = finance_function(inputs)

    if result.get("success"):
        data = result["data"]
        print(f"新闻类别: {data['category']}")
        print(f"新闻数量: {data['count']}")
        print("\n新闻列表:")

        for i, news in enumerate(data["news"], 1):
            print(f"{i}. {news['headline']}")
            print(f"   来源: {news['source']}")
            print(f"   时间: {news['datetime']}")
            print(f"   摘要: {news['summary']}")
            print()

        if "note" in data:
            print(f"注意: {data['note']}")
    else:
        print(f"查询失败: {result.get('error')}")

    print()


def example_function_tool_usage():
    """作为FunctionTool使用的示例"""
    print("=== FunctionTool使用示例 ===")

    # 方式1: 直接创建金融工具实例（原有方式）
    print("=== 方式1: 直接创建工具实例 ===")
    finance_tool = create_finance_tool()

    print(f"工具名称: {finance_tool.name}")
    print(f"工具描述: {finance_tool.description}")
    print(f"工具ID: {finance_tool.id}")
    print("\n工具Schema:")
    print(json.dumps(finance_tool.schema, indent=2, ensure_ascii=False))

    # 方式2: 通过VertexFlow服务获取配置好的工具实例（推荐方式）
    print("\n=== 方式2: 通过VertexFlow服务获取工具实例（推荐） ===")
    try:
        from vertex_flow.workflow.service import VertexFlowService

        # 获取服务实例
        service = VertexFlowService.get_instance()

        # 获取配置信息
        finance_config = service.get_finance_config()
        print("金融工具配置:")
        print(
            json.dumps(
                {
                    "alpha_vantage_enabled": finance_config["alpha_vantage"]["enabled"],
                    "alpha_vantage_key_configured": bool(finance_config["alpha_vantage"]["api_key"]),
                    "finnhub_enabled": finance_config["finnhub"]["enabled"],
                    "finnhub_key_configured": bool(finance_config["finnhub"]["api_key"]),
                    "yahoo_finance_enabled": finance_config["yahoo_finance"]["enabled"],
                },
                indent=2,
                ensure_ascii=False,
            )
        )

        # 获取配置好的工具实例
        service_finance_tool = service.get_finance_tool()
        print(f"\n通过服务获取的工具: {service_finance_tool.name}")

        # 使用服务获取的工具进行测试
        finance_tool = service_finance_tool

    except Exception as e:
        print(f"通过服务获取工具失败，使用直接创建的工具: {e}")
        # 继续使用直接创建的工具

    # 使用工具查询特斯拉股价
    print("\n=== 查询特斯拉股价 ===")
    inputs = {"action": "stock_price", "symbol": "TSLA"}
    result = finance_tool.execute(inputs)

    if result.get("success"):
        data = result["data"]
        print(f"✅ 查询成功!")
        print(f"股票: {data['symbol']} - ${data['price']} ({data['change_percent']})")
    else:
        print(f"❌ 查询失败: {result.get('error')}")

    # 使用工具查询欧元对美元汇率
    print("\n=== 查询欧元对美元汇率 ===")
    inputs = {"action": "exchange_rate", "from_currency": "EUR", "to_currency": "USD"}
    result = finance_tool.execute(inputs)

    if result.get("success"):
        data = result["data"]
        print(f"✅ 查询成功!")
        print(f"汇率: 1 {data['from_currency']} = {data['rate']} {data['to_currency']}")
    else:
        print(f"❌ 查询失败: {result.get('error')}")

    print()


def example_multiple_stocks():
    """批量查询多只股票示例"""
    print("=== 批量股票查询示例 ===")

    stocks = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]

    for symbol in stocks:
        inputs = {"action": "stock_price", "symbol": symbol}
        result = finance_function(inputs)

        if result.get("success"):
            data = result["data"]
            change_indicator = "📈" if data["change"] > 0 else "📉" if data["change"] < 0 else "➡️"
            print(f"{change_indicator} {data['symbol']}: ${data['price']} ({data['change_percent']})")
        else:
            print(f"❌ {symbol}: 查询失败")

    print()


def example_currency_conversion():
    """货币转换计算示例"""
    print("=== 货币转换计算示例 ===")

    # 假设要转换1000美元到人民币
    amount = 1000
    inputs = {"action": "exchange_rate", "from_currency": "USD", "to_currency": "CNY"}
    result = finance_function(inputs)

    if result.get("success"):
        data = result["data"]
        converted_amount = amount * data["rate"]
        print(f"💱 货币转换:")
        print(f"   {amount} {data['from_currency']} = {converted_amount:.2f} {data['to_currency']}")
        print(f"   汇率: 1 {data['from_currency']} = {data['rate']} {data['to_currency']}")
        print(f"   日期: {data['date']}")
    else:
        print(f"❌ 转换失败: {result.get('error')}")

    print()


if __name__ == "__main__":
    print("🏦 金融工具使用示例\n")

    # 运行各种示例
    example_stock_price_query()
    example_exchange_rate_query()
    example_financial_news_query()
    example_function_tool_usage()
    example_multiple_stocks()
    example_currency_conversion()

    print("✅ 所有示例运行完成!")
