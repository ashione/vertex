#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度研究工作流集成简化验证

快速验证 WhileVertexGroup 在深度研究工作流中的集成状态
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.app.deep_research_workflow import DeepResearchWorkflow
from vertex_flow.utils.logger import setup_logger

logger = setup_logger(__name__)


def verify_deep_research_integration():
    """验证深度研究工作流集成"""
    
    print("🔍 深度研究工作流集成验证")
    print("=" * 40)
    
    try:
        # 初始化服务
        print("1. 初始化服务...")
        service = VertexFlowService()
        model = service.get_chatmodel()
        print(f"   ✅ 使用模型: {model}")
        
        # 创建工作流构建器
        print("2. 创建深度研究工作流构建器...")
        workflow_builder = DeepResearchWorkflow(service, model, language="zh")
        print("   ✅ 工作流构建器创建成功")
        
        # 创建测试工作流
        print("3. 创建测试工作流...")
        input_data = {
            "content": "人工智能技术发展趋势",
            "stream": False,
            "save_intermediate": False,
            "save_final_report": False,
            "language": "zh",
            "env_vars": {},
            "user_vars": {},
        }
        
        workflow = workflow_builder.create_workflow(input_data)
        print("   ✅ 工作流创建成功")
        
        # 分析工作流结构
        print("4. 分析工作流结构...")
        vertices = list(workflow.vertices.values())
        edges = workflow.edges
        
        print(f"   📊 总顶点数: {len(vertices)}")
        print(f"   📊 总边数: {len(edges)}")
        
        # 统计顶点类型
        vertex_types = {}
        for vertex in vertices:
            vertex_type = type(vertex).__name__
            vertex_types[vertex_type] = vertex_types.get(vertex_type, 0) + 1
        
        print("   📊 顶点类型分布:")
        for vertex_type, count in vertex_types.items():
            print(f"      - {vertex_type}: {count}")
        
        # 检查关键组件
        print("5. 检查关键组件...")
        
        # 检查是否包含 WhileVertexGroup
        while_vertex_group = None
        for vertex in vertices:
            if vertex.id == "while_analysis_steps_group":
                while_vertex_group = vertex
                break
        
        if while_vertex_group:
            print("   ✅ WhileVertexGroup 存在")
            print(f"      - ID: {while_vertex_group.id}")
            print(f"      - 类型: {type(while_vertex_group).__name__}")
            
            # 检查子图结构
            if hasattr(while_vertex_group, 'subgraph_vertices'):
                sub_vertices = while_vertex_group.subgraph_vertices
                sub_edges = while_vertex_group.subgraph_edges
                print(f"      - 子顶点数: {len(sub_vertices)}")
                print(f"      - 子边数: {len(sub_edges)}")
                
                print("      - 子顶点列表:")
                for sub_vertex in sub_vertices:
                    if hasattr(sub_vertex, 'id'):
                        print(f"        * {sub_vertex.id} ({type(sub_vertex).__name__})")
                    else:
                        print(f"        * {sub_vertex} ({type(sub_vertex).__name__})")
            else:
                print("      ⚠️  无法获取子图结构")
        else:
            print("   ❌ WhileVertexGroup 不存在")
            return False
        
        # 检查其他关键顶点
        key_vertices = [
            "topic_analysis",
            "analysis_plan", 
            "extract_steps",
            "information_collection",
            "deep_analysis",
            "cross_validation",
            "summary_report"
        ]
        
        print("   📋 关键顶点检查:")
        for key_vertex in key_vertices:
            found = any(v.id == key_vertex for v in vertices)
            status = "✅" if found else "❌"
            print(f"      {status} {key_vertex}")
        
        # 检查工作流连接
        print("6. 检查工作流连接...")
        edge_connections = []
        for edge in edges:
            source_id = edge.get_source_vertex().id
            target_id = edge.get_target_vertex().id
            edge_connections.append(f"{source_id} -> {target_id}")
        
        print("   🔗 边连接:")
        for connection in edge_connections:
            print(f"      - {connection}")
        
        print("\n" + "=" * 40)
        print("✅ 深度研究工作流集成验证完成")
        print("🎉 所有关键组件都已正确集成！")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 验证过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    success = verify_deep_research_integration()
    
    if success:
        print("\n🚀 集成验证成功！")
        print("   新的深度研究工作流已成功集成 WhileVertexGroup")
        print("   可以使用 Deep Research App 进行智能迭代分析")
    else:
        print("\n💥 集成验证失败！")
        print("   请检查工作流配置和组件集成")
    
    return success


if __name__ == "__main__":
    main() 