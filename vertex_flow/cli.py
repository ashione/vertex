#!/usr/bin/env python3
"""
Vertex 统一命令行入口
支持多种运行模式和配置管理
"""

import argparse
import sys
import tempfile
from pathlib import Path


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="vertex",
        description="Vertex - 本地AI工作流系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  vertex                    # 启动标准模式（默认）
  vertex run                # 启动标准模式
  vertex workflow           # 启动工作流模式
  vertex config             # 交互式配置向导
  vertex config init        # 快速初始化配置
  vertex config check       # 检查配置状态
  vertex config reset       # 重置配置
  vertex --help             # 显示帮助信息
        """,
    )

    # 添加版本信息
    parser.add_argument("--version", "-v", action="version", version="vertex 0.1.0")

    # 添加子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令", metavar="COMMAND")

    # run 子命令（标准模式）
    run_parser = subparsers.add_parser("run", help="启动标准模式（默认）", description="启动Vertex标准聊天界面")
    run_parser.add_argument("--port", "-p", type=int, default=None, help="指定Web服务端口")
    run_parser.add_argument("--host", default=None, help="指定Web服务主机地址")

    # workflow 子命令
    workflow_parser = subparsers.add_parser(
        "workflow", help="启动工作流模式", description="启动VertexFlow可视化工作流编辑器"
    )
    workflow_parser.add_argument("--port", "-p", type=int, default=None, help="指定Web服务端口")

    # config 子命令
    config_parser = subparsers.add_parser("config", help="配置管理", description="管理Vertex配置文件")
    config_subparsers = config_parser.add_subparsers(dest="config_action", help="配置操作")

    # config init
    config_subparsers.add_parser("init", help="快速初始化配置文件")

    # config setup (交互式)
    config_subparsers.add_parser("setup", help="交互式配置向导")

    # config check
    config_subparsers.add_parser("check", help="检查配置状态")

    # config reset
    config_subparsers.add_parser("reset", help="重置配置为模板")

    # rag 子命令
    rag_parser = subparsers.add_parser("rag", help="RAG检索增强生成", description="基于文档的智能问答系统")
    rag_parser.add_argument("--directory", "-d", help="指定要扫描的文档目录路径")
    rag_parser.add_argument("--interactive", "-i", action="store_true", help="启动交互式查询模式")
    rag_parser.add_argument("--query", "-q", help="直接执行查询")
    rag_parser.add_argument("--reindex", action="store_true", help="强制重新索引所有文档")
    rag_parser.add_argument("--show-stats", action="store_true", help="显示向量数据库统计信息")
    rag_parser.add_argument("--fast", action="store_true", help="使用快速模式（跳过LLM生成，仅显示检索结果）")

    return parser


def run_standard_mode(args=None):
    """运行标准模式"""
    try:
        from vertex_flow.src.app import main as app_main

        print("启动Vertex标准模式...")

        # 如果有端口或主机参数，可以在这里处理
        if args and (args.port or args.host):
            # 这里可以设置配置覆盖
            import os

            if args.port:
                os.environ["VERTEX_PORT"] = str(args.port)
            if args.host:
                os.environ["VERTEX_HOST"] = args.host

        app_main()
    except ImportError as e:
        print(f"启动失败: {e}")
        print("请确保正确安装了vertex包")
        sys.exit(1)


def run_workflow_mode(args=None):
    """运行工作流模式"""
    try:
        import os
        import sys

        # 保存原始的sys.argv
        original_argv = sys.argv.copy()

        try:
            # 修改sys.argv来匹配workflow app的期望
            sys.argv = [sys.argv[0]]  # 只保留程序名

            # 如果有配置文件参数，添加到workflow app的参数中
            config_file = os.environ.get("CONFIG_FILE")
            if config_file:
                sys.argv.extend(["--config", config_file])

            from vertex_flow.workflow.app.app import main as workflow_main

            print("启动Vertex工作流模式...")

            # 设置端口环境变量（如果指定了的话）
            if args and args.port:
                os.environ["VERTEX_WORKFLOW_PORT"] = str(args.port)

            workflow_main()

        finally:
            # 恢复原始的sys.argv
            sys.argv = original_argv

    except ImportError as e:
        print(f"启动失败: {e}")
        print("请确保正确安装了vertex包")
        sys.exit(1)


def run_config_command(args):
    """运行配置相关命令"""
    if not args.config_action:
        # 如果没有指定配置动作，默认运行交互式配置
        args.config_action = "setup"

    if args.config_action == "init":
        run_config_init()
    elif args.config_action == "setup":
        run_config_setup()
    elif args.config_action == "check":
        run_config_check()
    elif args.config_action == "reset":
        run_config_reset()
    else:
        print(f"未知的配置操作: {args.config_action}")
        sys.exit(1)


def run_config_init():
    """快速初始化配置"""
    try:
        from vertex_flow.config.init_config import main as init_main

        init_main()
    except ImportError as e:
        print(f"配置初始化失败: {e}")
        sys.exit(1)


def run_config_setup():
    """交互式配置向导"""
    try:
        from vertex_flow.config.setup_config import main as setup_main

        setup_main()
    except ImportError as e:
        print(f"配置设置失败: {e}")
        sys.exit(1)


def run_config_check():
    """检查配置状态"""
    try:
        from vertex_flow.config.setup_config import ConfigManager

        manager = ConfigManager()

        print("=== 配置状态检查 ===")
        print(f"模板文件存在: {manager.has_template()}")
        print(f"用户配置文件存在: {manager.has_config()}")

        if manager.has_template():
            print(f"模板路径: {manager.template_file}")
        if manager.has_config():
            print(f"配置路径: {manager.config_file}")

        if not manager.has_config():
            print("\n建议运行: vertex config init")

    except ImportError as e:
        print(f"配置检查失败: {e}")
        sys.exit(1)


def run_config_reset():
    """重置配置"""
    try:
        from vertex_flow.config.setup_config import ConfigManager

        manager = ConfigManager()
        manager.reset_config()
    except ImportError as e:
        print(f"配置重置失败: {e}")
        sys.exit(1)


def run_rag_mode(args):
    """运行RAG模式"""
    print("=== RAG检索增强生成系统 ===")

    try:
        import tempfile
        from pathlib import Path

        from vertex_flow.workflow.unified_rag_workflow import UnifiedRAGSystem

        # 创建RAG系统
        rag_system = UnifiedRAGSystem()
        cleanup_temp = False

        # 处理文档输入
        if args.directory:
            # 扫描指定目录
            import os

            doc_extensions = {".txt", ".md", ".pdf", ".docx", ".doc"}
            documents = []

            for root, dirs, files in os.walk(args.directory):
                for file in files:
                    if Path(file).suffix.lower() in doc_extensions:
                        documents.append(os.path.join(root, file))

            if documents:
                print(f"找到 {len(documents)} 个文档文件")
                rag_system.index_documents(documents, force_reindex=args.reindex)
            else:
                print(f"目录 {args.directory} 中没有找到支持的文档文件")
                return
        else:
            # 使用内置示例文档
            print("使用内置示例文档...")
            documents, temp_dir = _create_sample_documents()
            cleanup_temp = True
            rag_system.index_documents(documents, force_reindex=args.reindex)

        # 根据参数执行相应操作
        try:
            if args.show_stats:
                # 显示统计信息
                stats = rag_system.get_vector_db_stats()
                print(f"\n向量数据库统计信息:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")

            elif args.query:
                # 单次查询模式
                print(f"\n查询: {args.query}")

                if args.fast:
                    print("使用快速查询模式（仅检索）...")
                    answer = rag_system.query_fast(args.query)
                else:
                    answer = rag_system.query(args.query)

                print(f"答案: {answer}")

            elif args.interactive:
                # 交互式查询模式（使用优化版本）
                rag_system.start_interactive_mode(fast_mode=args.fast)
            else:
                # 默认显示统计和帮助
                print("\n使用选项:")
                print("  --interactive    启动交互式查询")
                print("  --interactive --fast  启动快速交互式查询（跳过LLM）")
                print("  --query TEXT     直接查询")
                print("  --query TEXT --fast   快速查询（跳过LLM）")
                print("  --show-stats     显示统计信息")

        finally:
            # 清理临时文件
            if cleanup_temp and "temp_dir" in locals():
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)
                print("\n已清理临时文件")

    except ImportError as e:
        print(f"启动失败: {e}")
        print("请确保正确安装了vertex包和相关依赖")
        print("运行: pip install sentence-transformers faiss-cpu")
        sys.exit(1)
    except Exception as e:
        print(f"RAG系统运行失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def _create_sample_documents():
    """创建示例文档"""
    docs = [
        {
            "title": "人工智能基础",
            "content": """
            人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。
            AI的主要目标包括学习、推理、感知、语言理解和问题解决。
            人工智能可以分为弱人工智能和强人工智能，前者专注于特定任务，后者则具有与人类相当的通用智能。
            """,
        },
        {
            "title": "机器学习概述",
            "content": """
            机器学习是人工智能的一个子集，它使计算机能够在没有明确编程的情况下学习和改进。
            机器学习算法通过分析数据来识别模式，并使用这些模式来做出预测或决策。
            主要的机器学习类型包括监督学习、无监督学习和强化学习。
            """,
        },
        {
            "title": "深度学习技术",
            "content": """
            深度学习是机器学习的一个分支，使用神经网络来模拟人脑的学习过程。
            深度学习模型通常包含多个隐藏层，能够自动学习数据的层次化表示。
            常见的深度学习架构包括卷积神经网络（CNN）、循环神经网络（RNN）和Transformer。
            """,
        },
        {
            "title": "自然语言处理",
            "content": """
            自然语言处理（NLP）是人工智能的一个领域，专注于计算机理解和生成人类语言的能力。
            NLP的应用包括机器翻译、情感分析、文本摘要、问答系统和聊天机器人。
            现代NLP技术主要基于深度学习和Transformer架构。
            """,
        },
        {
            "title": "计算机视觉",
            "content": """
            计算机视觉是人工智能的一个分支，使计算机能够从图像和视频中理解和提取信息。
            计算机视觉的应用包括图像识别、目标检测、人脸识别、自动驾驶和医疗影像分析。
            深度学习在计算机视觉领域取得了突破性进展。
            """,
        },
    ]

    # 创建临时文件
    temp_dir = tempfile.mkdtemp()
    doc_files = []

    for doc in docs:
        doc_path = Path(temp_dir) / f"{doc['title']}.txt"
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(doc["content"].strip())
        doc_files.append(str(doc_path))

    return doc_files, temp_dir


def main():
    """主入口函数"""
    parser = create_parser()

    # 如果没有参数，默认运行标准模式
    if len(sys.argv) == 1:
        run_standard_mode()
        return

    args = parser.parse_args()

    # 根据命令执行相应操作
    if args.command is None or args.command == "run":
        run_standard_mode(args)
    elif args.command == "workflow":
        run_workflow_mode(args)
    elif args.command == "config":
        run_config_command(args)
    elif args.command == "rag":
        run_rag_mode(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
