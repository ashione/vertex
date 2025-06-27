#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地索引去重功能演示
演示如何使用LocalVectorEngine的自动去重功能
"""

import os
import shutil
import sys
import tempfile

from vertex_flow.workflow.unified_rag_workflow import UnifiedRAGSystem

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


def create_test_documents():
    """创建测试文档"""
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


def create_duplicate_documents(original_files):
    """创建重复文档（内容相同但文件名不同）"""
    temp_dir = tempfile.mkdtemp()
    duplicate_files = []

    for i, original_file in enumerate(original_files):
        # 读取原始文件内容
        with open(original_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 创建重复文件
        duplicate_path = os.path.join(temp_dir, f"duplicate_{i + 1}.txt")
        with open(duplicate_path, "w", encoding="utf-8") as f:
            f.write(content)
        duplicate_files.append(duplicate_path)

    return duplicate_files, temp_dir


def main():
    """主函数"""
    print("=== 本地索引去重功能演示 ===\n")

    # 创建测试文档
    print("1. 创建测试文档...")
    original_files, original_dir = create_test_documents()
    print(f"   创建了 {len(original_files)} 个原始文档")

    # 创建重复文档
    print("\n2. 创建重复文档...")
    duplicate_files, duplicate_dir = create_duplicate_documents(original_files)
    print(f"   创建了 {len(duplicate_files)} 个重复文档")

    try:
        # 创建RAG系统
        print("\n3. 初始化RAG系统...")
        rag_system = UnifiedRAGSystem()
        rag_system.build_workflows()

        # 首次索引原始文档
        print("\n4. 首次索引原始文档...")
        rag_system.index_documents(original_files)

        # 显示首次索引后的统计信息
        stats1 = rag_system.get_vector_db_stats()
        print(f"   首次索引后统计: {stats1}")

        # 索引重复文档
        print("\n5. 索引重复文档（应该被去重）...")
        rag_system.index_documents(duplicate_files)

        # 显示索引重复文档后的统计信息
        stats2 = rag_system.get_vector_db_stats()
        print(f"   索引重复文档后统计: {stats2}")

        # 再次索引原始文档
        print("\n6. 再次索引原始文档（应该被去重）...")
        rag_system.index_documents(original_files)

        # 显示最终统计信息
        stats3 = rag_system.get_vector_db_stats()
        print(f"   最终统计: {stats3}")

        # 验证去重效果
        print("\n7. 验证去重效果...")
        if stats3["total_documents"] == stats1["total_documents"]:
            print("✅ 去重功能正常工作！")
            print(f"   - 文档总数保持不变: {stats3['total_documents']}")
            print(f"   - 重复文档被正确跳过")
        else:
            print("❌ 去重功能异常！")
            print(f"   - 首次索引文档数: {stats1['total_documents']}")
            print(f"   - 最终文档数: {stats3['total_documents']}")

        # 测试查询功能
        print("\n8. 测试查询功能...")
        questions = ["什么是人工智能？", "机器学习和深度学习有什么区别？", "神经网络在深度学习中起什么作用？"]

        for question in questions:
            print(f"\n问题: {question}")
            try:
                answer = rag_system.query(question)
                print(f"答案: {answer[:100]}...")
            except Exception as e:
                print(f"查询失败: {e}")

        print("\n9. 演示持久化功能...")
        print("   重新创建RAG系统实例，验证数据持久化...")

        # 创建新的RAG系统实例
        new_rag_system = UnifiedRAGSystem()
        new_rag_system.build_workflows()

        # 检查是否加载了之前的索引
        new_stats = new_rag_system.get_vector_db_stats()
        print(f"   重新加载后统计: {new_stats}")

        if new_stats["total_documents"] == stats3["total_documents"]:
            print("✅ 持久化功能正常！")
        else:
            print("❌ 持久化功能异常！")

    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # 清理临时文件
        print("\n10. 清理临时文件...")
        for file_list, dir_path in [(original_files, original_dir), (duplicate_files, duplicate_dir)]:
            for file_path in file_list:
                if os.path.exists(file_path):
                    os.remove(file_path)
            if os.path.exists(dir_path):
                os.rmdir(dir_path)
        print("   清理完成！")


if __name__ == "__main__":
    main()
