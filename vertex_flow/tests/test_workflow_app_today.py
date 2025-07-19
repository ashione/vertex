#!/usr/bin/env python3
"""
测试workflow app中的today工具功能
"""

import json
import time
from typing import Any, Dict

import requests


def test_workflow_app_today():
    """测试workflow app中的today工具"""

    # 测试配置
    base_url = "http://localhost:8000"  # 默认workflow app端口

    # 测试用例
    test_cases = [
        {"name": "默认today调用", "content": "请告诉我现在的时间", "expected_keywords": ["时间", "现在", "当前"]},
        {
            "name": "指定格式的today调用",
            "content": "请使用timestamp格式获取当前时间",
            "expected_keywords": ["时间戳", "timestamp"],
        },
        {"name": "指定时区的today调用", "content": "请获取UTC时区的当前时间", "expected_keywords": ["UTC", "时区"]},
        {
            "name": "自定义格式的today调用",
            "content": "请使用自定义格式 %Y-%m-%d %H:%M:%S 获取当前时间",
            "expected_keywords": ["自定义", "格式"],
        },
    ]

    print("🧪 开始测试workflow app中的today工具...")
    print(f"📡 目标URL: {base_url}")
    print("=" * 60)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {test_case['name']}")
        print(f"💬 输入: {test_case['content']}")

        # 构建请求数据
        request_data = {
            "workflow_name": "default",  # 使用默认workflow
            "content": test_case["content"],
            "stream": False,  # 非流式输出便于测试
            "enable_mcp": True,  # 启用MCP功能
            "system_prompt": "你是一个有用的助手，可以调用today工具来获取时间信息。",
            "enable_reasoning": False,
            "show_reasoning": False,
        }

        try:
            # 发送请求
            print("🚀 发送请求...")
            response = requests.post(
                f"{base_url}/workflow", json=request_data, headers={"Content-Type": "application/json"}, timeout=30
            )

            if response.status_code == 200:
                result = response.json()

                if result.get("status"):
                    output = result.get("output", "")
                    print(f"✅ 请求成功")
                    print(f"📤 输出: {output[:200]}...")

                    # 检查是否包含预期关键词
                    output_lower = output.lower()
                    found_keywords = []
                    for keyword in test_case["expected_keywords"]:
                        if keyword.lower() in output_lower:
                            found_keywords.append(keyword)

                    if found_keywords:
                        print(f"🎯 找到预期关键词: {', '.join(found_keywords)}")
                    else:
                        print(f"⚠️ 未找到预期关键词: {test_case['expected_keywords']}")

                    # 检查token使用情况
                    token_usage = result.get("token_usage", {})
                    if token_usage:
                        print(f"📊 Token使用: {token_usage}")

                else:
                    print(f"❌ 请求失败: {result.get('message', '未知错误')}")

            else:
                print(f"❌ HTTP错误: {response.status_code}")
                print(f"错误详情: {response.text}")

        except requests.exceptions.ConnectionError:
            print("❌ 连接失败: 请确保workflow app正在运行")
            print("💡 启动命令: python -m vertex_flow.workflow.app.app")
            break
        except requests.exceptions.Timeout:
            print("❌ 请求超时")
        except Exception as e:
            print(f"❌ 请求异常: {e}")

        # 测试间隔
        time.sleep(1)

    print("\n" + "=" * 60)
    print("🎉 测试完成!")


def test_workflow_app_health():
    """测试workflow app健康状态"""
    base_url = "http://localhost:8000"

    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Workflow app健康检查通过")
            return True
        else:
            print(f"❌ Workflow app健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Workflow app连接失败: {e}")
        return False


if __name__ == "__main__":
    print("🔍 检查workflow app状态...")

    if test_workflow_app_health():
        test_workflow_app_today()
    else:
        print("\n💡 请先启动workflow app:")
        print("   python -m vertex_flow.workflow.app.app")
        print("\n或者使用自定义端口:")
        print("   python -m vertex_flow.workflow.app.app --port 8001")
