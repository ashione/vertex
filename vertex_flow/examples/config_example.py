#!/usr/bin/env python3
"""
配置系统使用示例
展示如何在应用程序中使用新的配置系统
"""

import sys
from pathlib import Path

from vertex_flow.config import get_config_loader, load_config

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent.parent))


def main():
    """主函数"""
    print("=== Vertex 配置系统示例 ===")

    # 获取配置加载器
    config_loader = get_config_loader()

    # 检查用户配置状态
    if config_loader.has_user_config():
        print(f"✓ 找到用户配置: {config_loader.get_config_path()}")
    else:
        print("✗ 未找到用户配置文件")
        config_loader.suggest_setup()

    # 加载配置
    print("\n正在加载配置...")
    config = load_config()

    # 显示配置信息
    print("\n=== 配置信息 ===")

    # LLM 配置
    llm_config = config.get("llm", {})
    print(f"LLM 配置项数量: {len(llm_config)}")
    for service, service_config in llm_config.items():
        enabled = service_config.get("enabled", False)
        model_name = service_config.get("model-name", "N/A")
        status = "✓ 已启用" if enabled else "✗ 未启用"
        print(f"  {service}: {status} (模型: {model_name})")

    # Web 配置
    web_config = config.get("web", {})
    if web_config:
        print(f"\nWeb 服务配置:")
        print(f"  端口: {web_config.get('port', 'N/A')}")
        print(f"  主机: {web_config.get('host', 'N/A')}")
        print(f"  工作进程: {web_config.get('workers', 'N/A')}")

    # 向量存储配置
    vector_config = config.get("vector", {})
    if vector_config:
        print(f"\n向量存储配置:")
        local_enabled = vector_config.get("local", {}).get("enabled", False)
        print(f"  本地向量存储: {'✓ 已启用' if local_enabled else '✗ 未启用'}")

        dashvector_enabled = vector_config.get("dashvector", {}).get("enabled", False)
        print(f"  DashVector云存储: {'✓ 已启用' if dashvector_enabled else '✗ 未启用'}")

    # 嵌入模型配置
    embedding_config = config.get("embedding", {})
    if embedding_config:
        print(f"\n嵌入模型配置:")
        local_enabled = embedding_config.get("local", {}).get("enabled", False)
        model_name = embedding_config.get("local", {}).get("model_name", "N/A")
        print(
            f"  本地嵌入: {
                '✓ 已启用' if local_enabled else '✗ 未启用'} (模型: {model_name})"
        )

        dashscope_enabled = embedding_config.get("dashscope", {}).get("enabled", False)
        print(f"  DashScope: {'✓ 已启用' if dashscope_enabled else '✗ 未启用'}")

        bce_enabled = embedding_config.get("bce", {}).get("enabled", False)
        print(f"  BCE: {'✓ 已启用' if bce_enabled else '✗ 未启用'}")

    print("\n=== 示例完成 ===")


if __name__ == "__main__":
    main()
