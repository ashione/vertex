#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号插件使用示例
"""

import asyncio
import os
from typing import Dict

# 设置环境变量（示例）
os.environ['WECHAT_TOKEN'] = 'your_test_token'
os.environ['VERTEX_FLOW_API_URL'] = 'http://localhost:8000'
os.environ['LOG_LEVEL'] = 'DEBUG'

from wechat_plugin.config import config
from wechat_plugin.message_processor import MessageProcessor
from wechat_plugin.wechat_handler import WeChatHandler


async def test_message_processing():
    """测试消息处理功能"""
    print("=== 测试消息处理功能 ===")
    
    # 初始化消息处理器
    processor = MessageProcessor(
        api_base_url=config.vertex_flow_api_url,
        default_workflow=config.default_workflow
    )
    
    # 测试文本消息处理
    test_messages = [
        "你好，请介绍一下自己",
        "今天天气怎么样？",
        "帮我写一首关于春天的诗",
        "什么是人工智能？"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- 测试消息 {i} ---")
        print(f"用户输入: {message}")
        
        try:
            response = await processor.process_message(
                user_id="test_user_123",
                content=message
            )
            print(f"AI回复: {response}")
        except Exception as e:
            print(f"处理失败: {str(e)}")


def test_wechat_handler():
    """测试微信处理器功能"""
    print("\n=== 测试微信处理器功能 ===")
    
    # 初始化微信处理器
    handler = WeChatHandler(config.wechat_token)
    
    # 测试签名验证
    print("\n--- 测试签名验证 ---")
    test_signature = "test_signature"
    test_timestamp = "1234567890"
    test_nonce = "test_nonce"
    
    is_valid = handler.verify_signature(test_signature, test_timestamp, test_nonce)
    print(f"签名验证结果: {is_valid}")
    
    # 测试XML消息解析
    print("\n--- 测试XML消息解析 ---")
    test_xml = """
    <xml>
    <ToUserName><![CDATA[toUser]]></ToUserName>
    <FromUserName><![CDATA[fromUser]]></FromUserName>
    <CreateTime>1234567890</CreateTime>
    <MsgType><![CDATA[text]]></MsgType>
    <Content><![CDATA[Hello World]]></Content>
    <MsgId>1234567890123456</MsgId>
    </xml>
    """.strip()
    
    message = handler.parse_xml_message(test_xml)
    print(f"解析结果: {message}")
    
    # 测试回复消息创建
    print("\n--- 测试回复消息创建 ---")
    if message:
        to_user, from_user, msg_type, content = handler.extract_message_info(message)
        reply_xml = handler.create_text_reply(from_user, to_user, "这是一个测试回复")
        print(f"回复XML:\n{reply_xml}")


def test_config():
    """测试配置功能"""
    print("\n=== 测试配置功能 ===")
    
    # 显示配置信息
    print(f"配置信息:\n{config}")
    
    # 验证配置
    is_valid, error_msg = config.validate()
    print(f"\n配置验证: {'通过' if is_valid else '失败'}")
    if error_msg:
        print(f"错误信息: {error_msg}")
    
    # 显示Webhook URL
    print(f"Webhook URL: {config.get_webhook_url()}")


async def test_health_check():
    """测试健康检查（模拟）"""
    print("\n=== 测试健康检查 ===")
    
    try:
        # 这里模拟健康检查逻辑
        health_status = {
            "status": "ok",
            "message": "微信公众号插件运行正常",
            "config": {
                "wechat_token_set": bool(config.wechat_token),
                "vertex_flow_api_url": config.vertex_flow_api_url,
                "webhook_url": config.get_webhook_url(),
                "features": {
                    "mcp": config.enable_mcp,
                    "search": config.enable_search,
                    "multimodal": config.enable_multimodal,
                    "reasoning": config.enable_reasoning
                }
            }
        }
        
        print(f"健康检查结果: {health_status}")
        
    except Exception as e:
        print(f"健康检查失败: {str(e)}")


def simulate_wechat_workflow():
    """模拟完整的微信消息处理流程"""
    print("\n=== 模拟微信消息处理流程 ===")
    
    # 模拟微信发送的XML消息
    incoming_xml = """
    <xml>
    <ToUserName><![CDATA[gh_123456789]]></ToUserName>
    <FromUserName><![CDATA[user_openid_123]]></FromUserName>
    <CreateTime>1234567890</CreateTime>
    <MsgType><![CDATA[text]]></MsgType>
    <Content><![CDATA[你好，请介绍一下Vertex Flow]]></Content>
    <MsgId>1234567890123456</MsgId>
    </xml>
    """.strip()
    
    print(f"收到微信消息:\n{incoming_xml}")
    
    # 初始化处理器
    handler = WeChatHandler(config.wechat_token)
    
    # 解析消息
    message = handler.parse_xml_message(incoming_xml)
    print(f"\n解析后的消息: {message}")
    
    # 提取消息信息
    to_user, from_user, msg_type, content = handler.extract_message_info(message)
    print(f"\n消息信息:")
    print(f"  发送给: {to_user}")
    print(f"  来自: {from_user}")
    print(f"  类型: {msg_type}")
    print(f"  内容: {content}")
    
    # 模拟AI回复
    ai_response = "你好！Vertex Flow是一个强大的工作流引擎，支持多种AI功能包括聊天、搜索、推理等。通过微信公众号，你可以方便地与AI进行对话。"
    
    # 创建回复消息
    reply_xml = handler.create_text_reply(from_user, to_user, ai_response)
    print(f"\n回复消息:\n{reply_xml}")


async def main():
    """主函数"""
    print("微信公众号插件测试示例")
    print("=" * 50)
    
    # 测试配置
    test_config()
    
    # 测试微信处理器
    test_wechat_handler()
    
    # 模拟微信工作流程
    simulate_wechat_workflow()
    
    # 测试健康检查
    await test_health_check()
    
    # 测试消息处理（需要Vertex Flow API运行）
    print("\n注意：以下测试需要Vertex Flow API正在运行")
    try:
        await test_message_processing()
    except Exception as e:
        print(f"消息处理测试跳过（API不可用）: {str(e)}")
    
    print("\n=" * 50)
    print("测试完成！")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())