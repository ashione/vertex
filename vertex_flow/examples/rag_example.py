#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG系统使用示例
演示如何使用统一配置的RAG工作流
"""

import argparse
import os
import sys
import tempfile
from typing import Dict, Optional

from vertex_flow.workflow.unified_rag_workflow import UnifiedRAGSystem

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


def create_sample_documents(directory_path: str = None):
    """
    创建示例文档或扫描指定目录

    Args:
        directory_path: 要扫描的目录路径，如果为None或目录为空则使用示例文档

    Returns:
        tuple: (文档文件路径列表, 临时目录路径)
    """
    # 支持的文件扩展名
    supported_extensions = {".txt", ".md", ".pdf", ".docx", ".doc"}

    # 如果指定了目录路径，尝试扫描该目录
    if directory_path and os.path.exists(directory_path) and os.path.isdir(directory_path):
        print(f"扫描目录: {directory_path}")

        # 收集目录中的支持文件
        doc_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()

                if file_ext in supported_extensions:
                    doc_files.append(file_path)

        if doc_files:
            print(f"在目录中找到 {len(doc_files)} 个支持的文件")
            return doc_files, directory_path
        else:
            print(f"目录 {directory_path} 中没有找到支持的文件，使用示例文档")

    # 如果没有指定目录或目录为空，使用示例文档
    print("使用示例文档")

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

    for i, doc in enumerate(docs):
        doc_path = os.path.join(temp_dir, f"{doc['title']}.txt")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(doc["content"].strip())
        doc_files.append(doc_path)

    return doc_files, temp_dir


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="RAG系统使用示例")
    parser.add_argument("--directory", "-d", type=str, help="要扫描的文档目录路径")
    args = parser.parse_args()

    print("=== RAG系统使用示例 ===\n")

    # 创建示例文档或扫描指定目录
    print("1. 准备文档...")
    doc_files, doc_dir = create_sample_documents(args.directory)
    print(f"   准备了 {len(doc_files)} 个文档文件")

    try:
        # 创建RAG系统
        print("\n2. 初始化RAG系统...")
        rag_system = UnifiedRAGSystem()

        # 构建工作流
        print("3. 构建工作流...")
        rag_system.build_workflows()

        # 显示工作流图
        print("4. 工作流结构:")
        rag_system.show_workflows()

        # 索引文档
        print("\n5. 索引文档...")
        rag_system.index_documents(doc_files)
        print("   文档索引完成！")

        # 显示向量数据库统计信息
        stats = rag_system.get_vector_db_stats()
        print(f"   向量数据库统计: {stats}")

        # 交互式查询
        print("\n8. 开始交互式查询（输入 'quit' 退出）:")
        print("=" * 50)

        while True:
            question = input("\n请输入您的问题: ").strip()

            if question.lower() in ["quit", "exit", "退出"]:
                break

            if not question:
                continue

            print("\n正在生成答案...")
            try:
                answer = rag_system.query(question)
                print(f"\n答案: {answer}")
            except Exception as e:
                print(f"\n生成答案时出错: {e}")

            print("-" * 50)

    except Exception as e:
        print(f"系统初始化失败: {e}")
        print("请确保已安装必要的依赖包:")
        print("  pip install sentence-transformers faiss-cpu")

    finally:
        # 清理临时文件（只有在使用示例文档时才清理）
        if doc_dir != args.directory:  # 如果是临时目录才清理
            print("\n9. 清理临时文件...")
            for doc_file in doc_files:
                if os.path.exists(doc_file):
                    os.remove(doc_file)
            if os.path.exists(doc_dir):
                os.rmdir(doc_dir)
            print("   清理完成！")
        else:
            print(f"\n9. 文档目录 {doc_dir} 保持不变")


if __name__ == "__main__":
    main()
