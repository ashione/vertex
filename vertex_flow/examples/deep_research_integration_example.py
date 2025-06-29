#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度研究工作流集成示例

本示例展示如何使用集成了 WhileVertexGroup 的新型深度研究工作流
进行智能迭代分析，参考了 Dify 和 OpenAI 的深度研究最佳实践。
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.app.deep_research_workflow import DeepResearchWorkflow
from vertex_flow.utils.logger import setup_logger

logger = setup_logger(__name__)


async def test_deep_research_integration():
    """测试深度研究工作流集成"""
    
    try:
        # 初始化服务
        logger.info("初始化 VertexFlow 服务...")
        service = VertexFlowService()
        
        # 获取模型
        model = service.get_chatmodel()
        logger.info(f"使用模型: {model}")
        
        # 创建深度研究工作流构建器
        workflow_builder = DeepResearchWorkflow(service, model, language="zh")
        
        # 准备测试数据
        test_topics = [
            "人工智能在医疗诊断中的应用现状与发展趋势",
            "区块链技术在供应链管理中的创新应用",
            "可持续能源技术的发展前景与挑战"
        ]
        
        # 选择一个测试主题
        research_topic = test_topics[0]
        
        # 配置输入数据
        input_data = {
            "content": research_topic,
            "stream": False,  # 使用批处理模式进行测试
            "save_intermediate": True,
            "save_final_report": True,
            "language": "zh",
            "env_vars": {},
            "user_vars": {},
        }
        
        logger.info(f"开始深度研究测试，主题: {research_topic}")
        
        # 创建工作流
        workflow = workflow_builder.create_workflow(input_data)
        
        # 验证工作流结构
        logger.info("验证工作流结构...")
        vertices = list(workflow.vertices.values())
        edges = workflow.edges
        
        logger.info(f"工作流包含 {len(vertices)} 个顶点:")
        for vertex in vertices:
            logger.info(f"  - {vertex.id}: {type(vertex).__name__}")
        
        logger.info(f"工作流包含 {len(edges)} 条边")
        
        # 查找 WhileVertexGroup
        while_vertex_group = None
        for vertex in vertices:
            if vertex.id == "while_analysis_steps_group":
                while_vertex_group = vertex
                break
        
        if while_vertex_group:
            logger.info("✅ 找到 WhileVertexGroup 迭代分析组")
            logger.info(f"  - 子图顶点数: {len(while_vertex_group.subgraph_vertices)}")
            logger.info(f"  - 子图边数: {len(while_vertex_group.subgraph_edges)}")
            
            # 显示子图结构
            for sub_vertex in while_vertex_group.subgraph_vertices:
                logger.info(f"    * 子顶点: {sub_vertex.id} ({type(sub_vertex).__name__})")
        else:
            logger.warning("❌ 未找到 WhileVertexGroup")
        
        # 执行工作流（简化测试）
        logger.info("开始执行工作流...")
        
        # 准备输入
        workflow_input = {"content": research_topic}
        
        # 执行工作流
        workflow.execute_workflow(workflow_input)
        result = workflow.result()
        
        logger.info("✅ 工作流执行完成")
        
        # 分析结果
        if result:
            logger.info("分析执行结果:")
            
            # 检查各阶段的输出
            stages_to_check = [
                "topic_analysis",
                "analysis_plan", 
                "extract_steps",
                "while_analysis_steps_group",
                "information_collection",
                "deep_analysis",
                "cross_validation",
                "summary_report"
            ]
            
            for stage in stages_to_check:
                if stage in result:
                    stage_result = result[stage]
                    if isinstance(stage_result, str):
                        content_preview = stage_result[:100] + "..." if len(stage_result) > 100 else stage_result
                    else:
                        content_preview = str(stage_result)[:100] + "..."
                    
                    logger.info(f"  {stage}: {content_preview}")
                else:
                    logger.info(f"  {stage}: 未执行或无输出")
            
            # 特别关注迭代分析结果
            if "while_analysis_steps_group" in result:
                while_result = result["while_analysis_steps_group"]
                logger.info("🔄 迭代分析详细结果:")
                
                if isinstance(while_result, dict):
                    iteration_count = while_result.get('iteration_count', 0)
                    results = while_result.get('results', [])
                    logger.info(f"  - 总迭代次数: {iteration_count}")
                    logger.info(f"  - 分析步骤数: {len(results)}")
                    
                    # 显示前几个步骤的摘要
                    for i, step_result in enumerate(results[:3], 1):
                        if isinstance(step_result, dict):
                            step_info = step_result.get('step_info', {})
                            step_name = step_info.get('step_name', f'步骤{i}')
                            logger.info(f"    步骤 {i}: {step_name}")
                else:
                    logger.info(f"  - 结果类型: {type(while_result)}")
                    logger.info(f"  - 结果预览: {str(while_result)[:200]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"深度研究工作流集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_structure():
    """测试工作流结构（不执行）"""
    
    try:
        logger.info("测试工作流结构...")
        
        # 初始化服务
        service = VertexFlowService()
        model = service.get_chatmodel()
        
        # 创建工作流构建器
        workflow_builder = DeepResearchWorkflow(service, model, language="en")
        
        # 创建测试输入
        input_data = {
            "content": "Test topic",
            "stream": False,
            "save_intermediate": False,
            "save_final_report": False,
            "language": "en",
            "env_vars": {},
            "user_vars": {},
        }
        
        # 创建工作流
        workflow = workflow_builder.create_workflow(input_data)
        
        # 分析工作流结构
        vertices = list(workflow.vertices.values())
        edges = workflow.edges
        
        logger.info("📊 工作流结构分析:")
        logger.info(f"  - 总顶点数: {len(vertices)}")
        logger.info(f"  - 总边数: {len(edges)}")
        
        # 按类型统计顶点
        vertex_types = {}
        for vertex in vertices:
            vertex_type = type(vertex).__name__
            vertex_types[vertex_type] = vertex_types.get(vertex_type, 0) + 1
        
        logger.info("  - 顶点类型统计:")
        for vertex_type, count in vertex_types.items():
            logger.info(f"    * {vertex_type}: {count}")
        
        # 检查关键顶点
        key_vertices = ["topic_analysis", "analysis_plan", "extract_steps", "while_analysis_steps_group"]
        logger.info("  - 关键顶点检查:")
        
        for key_vertex in key_vertices:
            found = any(v.id == key_vertex for v in vertices)
            status = "✅" if found else "❌"
            logger.info(f"    {status} {key_vertex}")
        
        # 检查 WhileVertexGroup 的子图结构
        while_vertex = next((v for v in vertices if v.id == "while_analysis_steps_group"), None)
        if while_vertex and hasattr(while_vertex, 'subgraph_vertices'):
            logger.info("  - WhileVertexGroup 子图结构:")
            logger.info(f"    * 子顶点数: {len(while_vertex.subgraph_vertices)}")
            logger.info(f"    * 子边数: {len(while_vertex.subgraph_edges)}")
            
            for sub_vertex in while_vertex.subgraph_vertices:
                logger.info(f"      - {sub_vertex.id}: {type(sub_vertex).__name__}")
        
        logger.info("✅ 工作流结构测试完成")
        return True
        
    except Exception as e:
        logger.error(f"工作流结构测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    
    print("🚀 深度研究工作流集成测试")
    print("=" * 50)
    
    # 测试工作流结构
    print("\n1. 测试工作流结构...")
    structure_ok = test_workflow_structure()
    
    if structure_ok:
        print("✅ 工作流结构测试通过")
    else:
        print("❌ 工作流结构测试失败")
        return
    
    # 询问是否执行完整测试
    print("\n2. 是否执行完整的深度研究测试？")
    print("   注意：完整测试可能需要较长时间和API调用")
    
    user_input = input("   输入 'y' 或 'yes' 继续，其他键跳过: ").lower().strip()
    
    if user_input in ['y', 'yes']:
        print("\n开始完整的深度研究测试...")
        
        # 运行异步测试
        import asyncio
        success = asyncio.run(test_deep_research_integration())
        
        if success:
            print("✅ 深度研究工作流集成测试完成")
        else:
            print("❌ 深度研究工作流集成测试失败")
    else:
        print("跳过完整测试")
    
    print("\n" + "=" * 50)
    print("测试完成！")


if __name__ == "__main__":
    main() 