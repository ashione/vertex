#!/usr/bin/env python3
"""
工作流历史记录支持示例

本示例展示如何在WorkflowInput中传入历史记录，实现多轮对话功能。
"""

import json
from typing import Any, Dict, List


# 模拟WorkflowInput类（实际使用时从app.py导入）
class WorkflowInput:
    def __init__(
        self, workflow_name: str = "default", content: str = "", history: List[Dict[str, Any]] = None, **kwargs
    ):
        self.workflow_name = workflow_name
        self.content = content
        self.history = history or []
        # 其他参数
        for key, value in kwargs.items():
            setattr(self, key, value)

    def dict(self):
        return {"workflow_name": self.workflow_name, "content": self.content, "history": self.history}


def create_workflow_input_with_history():
    """
    创建包含历史记录的WorkflowInput示例
    """

    # 示例1: 空历史记录（首次对话）
    print("=== 示例1: 首次对话（无历史记录） ===")
    input1 = WorkflowInput(workflow_name="chat", content="你好，我想了解一下人工智能的发展历史。", history=[])
    print(f"用户输入: {input1.content}")
    print(f"历史记录: {input1.history}")
    print()

    # 示例2: 包含历史记录的多轮对话
    print("=== 示例2: 多轮对话（包含历史记录） ===")

    # 模拟历史对话记录
    conversation_history = [
        {"role": "user", "content": "你好，我想了解一下人工智能的发展历史。"},
        {
            "role": "assistant",
            "content": "你好！人工智能的发展历史可以追溯到1950年代。主要里程碑包括：\n1. 1950年：图灵提出图灵测试\n2. 1956年：达特茅斯会议，AI概念正式提出\n3. 1980年代：专家系统兴起\n4. 1990年代：机器学习发展\n5. 2010年代：深度学习突破\n\n你想了解哪个特定阶段的详细信息吗？",
        },
        {"role": "user", "content": "我对深度学习的突破比较感兴趣，能详细介绍一下吗？"},
        {
            "role": "assistant",
            "content": "深度学习的突破主要发生在2010年代，关键事件包括：\n\n1. **2012年 - ImageNet突破**：AlexNet在图像识别竞赛中取得突破性成果\n2. **2014年 - 生成对抗网络(GAN)**：Ian Goodfellow提出GAN概念\n3. **2016年 - AlphaGo**：DeepMind的AlphaGo击败围棋世界冠军\n4. **2017年 - Transformer架构**：Google提出Transformer，为后续大语言模型奠定基础\n\n这些突破为现在的ChatGPT、GPT-4等大语言模型铺平了道路。你想了解其中哪个方面的技术细节？",
        },
    ]

    input2 = WorkflowInput(
        workflow_name="chat", content="Transformer架构的核心创新是什么？", history=conversation_history
    )

    print(f"用户输入: {input2.content}")
    print(f"历史记录条数: {len(input2.history)}")
    print("历史记录内容:")
    for i, msg in enumerate(input2.history):
        role = msg["role"]
        content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
        print(f"  {i+1}. [{role}]: {content}")
    print()

    # 示例3: 多模态对话历史记录
    print("=== 示例3: 多模态对话历史记录 ===")

    multimodal_history = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "这张图片显示的是什么？"},
                {"type": "image_url", "image_url": {"url": "https://example.com/image1.jpg"}},
            ],
        },
        {
            "role": "assistant",
            "content": "这张图片显示的是一只可爱的小猫咪，它正坐在阳光明媚的窗台上。猫咪有着橙白相间的毛色，看起来很放松和满足。",
        },
    ]

    input3 = WorkflowInput(
        workflow_name="multimodal_chat",
        content="这只猫咪看起来几岁了？",
        history=multimodal_history,
        image_url=None,  # 当前轮次没有新图片
    )

    print(f"用户输入: {input3.content}")
    print(f"历史记录条数: {len(input3.history)}")
    print("多模态历史记录:")
    for i, msg in enumerate(input3.history):
        role = msg["role"]
        if isinstance(msg["content"], list):
            print(f"  {i+1}. [{role}]: [多模态内容]")
            for content_item in msg["content"]:
                if content_item["type"] == "text":
                    print(f"    - 文本: {content_item['text']}")
                elif content_item["type"] == "image_url":
                    print(f"    - 图片: {content_item['image_url']['url']}")
        else:
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            print(f"  {i+1}. [{role}]: {content}")
    print()

    return input1, input2, input3


def demonstrate_api_usage():
    """
    演示如何在API调用中使用历史记录
    """
    print("=== API调用示例 ===")

    # 模拟API请求数据
    api_request_data = {
        "workflow_name": "chat",
        "content": "继续我们之前关于AI的讨论",
        "history": [
            {"role": "user", "content": "什么是机器学习？"},
            {
                "role": "assistant",
                "content": "机器学习是人工智能的一个分支，它使计算机能够在没有明确编程的情况下学习和改进。",
            },
        ],
        "stream": False,
        "enable_mcp": True,
        "system_prompt": "你是一个专业的AI助手，擅长解释技术概念。",
        "temperature": 0.7,
        "max_tokens": 1000,
    }

    print("API请求数据:")
    print(json.dumps(api_request_data, ensure_ascii=False, indent=2))
    print()

    # 展示如何处理历史记录
    print("历史记录处理:")
    history = api_request_data.get("history", [])
    if history:
        print(f"- 发现 {len(history)} 条历史记录")
        print("- 历史记录将被传递给LLM以保持对话上下文")
        print("- LLM将基于历史记录和当前输入生成回复")
    else:
        print("- 无历史记录，这是一个新的对话会话")

    return api_request_data


def main():
    """
    主函数：运行所有示例
    """
    print("工作流历史记录支持示例")
    print("=" * 50)
    print()

    # 创建WorkflowInput示例
    input1, input2, input3 = create_workflow_input_with_history()

    # 演示API使用
    api_data = demonstrate_api_usage()

    print("=== 总结 ===")
    print("历史记录功能的主要特点:")
    print("1. 支持多轮对话上下文保持")
    print("2. 兼容文本和多模态内容")
    print("3. 灵活的历史记录格式")
    print("4. 与现有API完全兼容")
    print("5. 支持流式和非流式输出")
    print()
    print("使用建议:")
    print("- 合理控制历史记录长度，避免token超限")
    print("- 保持历史记录格式的一致性")
    print("- 在多模态对话中正确处理图片URL")
    print("- 根据需要清理或截断过长的历史记录")


if __name__ == "__main__":
    main()
