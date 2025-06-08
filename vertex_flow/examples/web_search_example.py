#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Search工具使用示例

本文件展示了如何使用基于博查AI的Web搜索工具进行各种搜索任务。
"""

import json

from vertex_flow.workflow.tools.web_search import create_web_search_tool, web_search_function


def example_basic_search():
    """基础搜索示例"""
    print("=== 基础搜索示例 ===")

    # 直接使用函数
    inputs = {"query": "人工智能最新发展趋势 2024", "count": 5, "summary": True}

    result = web_search_function(inputs)

    if result["success"]:
        print(f"搜索查询: {result['query']}")
        print(f"总结果数: {result['total_count']}")
        print(f"\nAI总结:\n{result['summary']}")
        print("\n搜索结果:")
        for i, item in enumerate(result["results"], 1):
            print(f"{i}. {item['title']}")
            print(f"   URL: {item['url']}")
            print(f"   摘要: {item['snippet'][:100]}...")
            print()
    else:
        print(f"搜索失败: {result['error']}")


def example_news_search():
    """新闻搜索示例"""
    print("=== 新闻搜索示例 ===")

    inputs = {"query": "OpenAI GPT-4 最新消息", "count": 3, "freshness": "noLimit", "summary": True}  # 搜索一周内的新闻

    result = web_search_function(inputs)

    if result["success"]:
        print(f"搜索查询: {result['query']}")
        print(f"\n一周内相关新闻总结:\n{result['summary']}")
        print("\n最新新闻:")
        for item in result["results"]:
            print(f"• {item['title']} ({item['site_name']})")
            print(f"  {item['url']}")
    else:
        print(f"搜索失败: {result['error']}")


def example_academic_search():
    """学术搜索示例"""
    print("=== 学术搜索示例 ===")

    inputs = {
        "query": "transformer architecture deep learning research papers",
        "count": 8,
        "freshness": "noLimit",
        "summary": True,
    }

    result = web_search_function(inputs)

    if result["success"]:
        print(f"搜索查询: {result['query']}")
        print(f"\n学术资料总结:\n{result['summary']}")
        print("\n相关学术资源:")
        for item in result["results"]:
            if any(keyword in item["url"].lower() for keyword in ["arxiv", "scholar", "ieee", "acm"]):
                print(f"📚 {item['title']}")
                print(f"   {item['url']}")
                print(f"   {item['snippet'][:150]}...")
                print()
    else:
        print(f"搜索失败: {result['error']}")


def example_function_tool_usage():
    """作为FunctionTool使用的示例"""
    print("=== FunctionTool使用示例 ===")

    # 创建工具实例
    search_tool = create_web_search_tool()

    print(f"工具名称: {search_tool.name}")
    print(f"工具描述: {search_tool.description}")
    print(f"工具ID: {search_tool.id}")
    print(f"\n工具Schema:")
    print(json.dumps(search_tool.schema, indent=2, ensure_ascii=False))

    # 使用工具执行搜索
    inputs = {"query": "Python机器学习库推荐", "count": 4, "summary": True}

    result = search_tool.execute(inputs)

    if result["success"]:
        print(f"\n搜索成功!")
        print(f"查询: {result['query']}")
        print(f"AI总结: {result['summary'][:200]}...")
        print(f"找到 {len(result['results'])} 个结果")
    else:
        print(f"\n搜索失败: {result['error']}")


def example_error_handling():
    """错误处理示例"""
    print("=== 错误处理示例 ===")

    # 测试空查询
    result1 = web_search_function({"query": ""})
    print(f"空查询结果: {result1['error']}")

    # 测试无效参数
    result2 = web_search_function({"query": "测试查询", "count": -1, "freshness": "invalid"})  # 无效数量  # 无效时效性
    print(f"无效参数处理: 搜索仍然执行，参数被自动修正")

    # 测试缺少查询参数
    result3 = web_search_function({"count": 5})
    print(f"缺少查询参数: {result3['error']}")


def example_integration_with_llm():
    """与LLM集成使用示例"""
    print("=== LLM集成使用示例 ===")

    # 模拟LLM调用工具的场景
    search_tool = create_web_search_tool()

    # 假设LLM决定需要搜索信息
    user_question = "请告诉我关于量子计算的最新进展"

    # LLM生成的工具调用参数
    tool_call_params = {
        "query": "量子计算最新进展 2025 突破性研究",
        "count": 6,
        "freshness": "noLimit",
        "summary": True,
    }

    print(f"用户问题: {user_question}")
    print(f"LLM生成的搜索参数: {tool_call_params}")

    # 执行搜索
    search_result = search_tool.execute(tool_call_params)

    if search_result["success"]:
        print(f"\n搜索成功，获得信息:")
        print(f"AI总结: {search_result['summary'][:300]}...")
        print(f"\n基于搜索结果，LLM可以生成更准确和及时的回答。")

        # 模拟LLM使用搜索结果生成回答
        print(f"\n[模拟LLM回答]")
        print(f"根据最新的搜索结果，量子计算领域确实有以下重要进展...")
        print(f"(这里LLM会基于search_result['summary']和search_result['results']生成详细回答)")
    else:
        print(f"搜索失败: {search_result['error']}")
        print(f"LLM将基于已有知识回答，但可能不够及时。")


if __name__ == "__main__":
    print("Web Search工具使用示例\n")
    print("注意: 运行这些示例需要在配置文件中正确配置博查API密钥")
    print("配置路径: config/llm.yml 中的 web-search.bocha.sk\n")

    try:
        example_basic_search()
        print("\n" + "=" * 50 + "\n")

        example_news_search()
        print("\n" + "=" * 50 + "\n")

        example_academic_search()
        print("\n" + "=" * 50 + "\n")

        example_function_tool_usage()
        print("\n" + "=" * 50 + "\n")

        example_error_handling()
        print("\n" + "=" * 50 + "\n")

        example_integration_with_llm()

    except Exception as e:
        print(f"示例执行出错: {e}")
        print("请检查配置文件和网络连接")
