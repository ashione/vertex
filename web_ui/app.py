from flask import Flask, render_template, request, jsonify
import sys
import os
import time

# 添加vertex_flow到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from vertex_flow.workflow.workflow_manager import WorkflowManager
from vertex_flow.workflow.workflow import Workflow

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# 初始化工作流管理器
workflow_manager = WorkflowManager()

@app.route('/')
def index():
    """主页 - 工作流列表"""
    return render_template('index.html')

@app.route('/workflow')
def workflow_editor():
    """工作流编辑器"""
    return render_template('workflow.html')

@app.route('/config')
def config_page():
    """配置页面"""
    return render_template('config.html')

# API路由
@app.route('/api/workflows', methods=['GET'])
def get_workflows():
    """获取所有工作流"""
    try:
        workflows = workflow_manager.get_all_workflows()  # 修改这里
        
        # 移除不可序列化的workflow_obj
        clean_workflows = []
        for workflow in workflows:
            if workflow and 'workflow_obj' in workflow:
                workflow_copy = workflow.copy()
                del workflow_copy['workflow_obj']
                clean_workflows.append(workflow_copy)
            else:
                clean_workflows.append(workflow)
        
        return jsonify({
            'success': True,
            'data': clean_workflows
        })
    except Exception as e:
        import traceback
        print(f"Update workflow error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/workflows', methods=['POST'])
def create_workflow():
    """创建新工作流"""
    try:
        data = request.json
        workflow_data = workflow_manager.create_workflow(
            name=data.get('name'),
            description=data.get('description', '')
            # 移除不支持的参数：config, edges 等
        )
        return jsonify({
            'success': True,
            'data': workflow_data
        })
    except Exception as e:
        import traceback
        print(f"Update workflow error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/workflows/<workflow_id>', methods=['GET'])
def get_workflow(workflow_id):
    """获取特定工作流"""
    try:
        workflow = workflow_manager.get_workflow(workflow_id)
        
        # 移除不可序列化的workflow_obj
        if workflow and 'workflow_obj' in workflow:
            workflow_copy = workflow.copy()
            del workflow_copy['workflow_obj']
            workflow = workflow_copy
            
        return jsonify({
            'success': True,
            'data': workflow if workflow else None
        })
    except Exception as e:
        import traceback
        print(f"Update workflow error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/workflows/<workflow_id>', methods=['PUT'])
def update_workflow(workflow_id):
    """更新工作流"""
    try:
        data = request.json
        result = workflow_manager.update_workflow(
            workflow_id,
            name=data.get('name'),
            description=data.get('description'),
            nodes=data.get('nodes'),
            edges=data.get('edges')
        )
        
        # 移除不可序列化的workflow_obj
        if result and 'workflow_obj' in result:
            result_copy = result.copy()
            del result_copy['workflow_obj']
            result = result_copy
            
        return jsonify({
            'success': result is not None,
            'data': result
        })
    except Exception as e:
        import traceback
        print(f"Update workflow error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/workflows/<workflow_id>/execute', methods=['POST'])
def execute_workflow(workflow_id):
    """执行工作流"""
    try:
        data = request.json
        input_data = data.get('input', {})
        
        result = workflow_manager.execute_workflow(workflow_id, input_data)
        
        # 如果执行成功，获取各个节点的输出
        if result.get('status') == 'success':
            workflow = workflow_manager.get_workflow(workflow_id)
            if workflow and 'workflow_obj' in workflow:
                workflow_obj = workflow['workflow_obj']
                # 获取工作流上下文中的所有节点输出
                node_outputs = workflow_obj.context.get_outputs() if hasattr(workflow_obj, 'context') else {}
                # 获取工作流状态信息
                vertices_status = workflow_obj.status() if hasattr(workflow_obj, 'status') else {}
                
                return jsonify({
                    'success': True,
                    'data': {
                        'result': result.get('result'),
                        'status': result.get('status'),
                        'node_outputs': node_outputs,
                        'vertices_status': vertices_status
                    }
                })
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        import traceback
        print(f"Execute workflow error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/workflows/import', methods=['POST'])
def import_workflow():
    """从JSON数据导入工作流"""
    try:
        data = request.json
        
        # 验证数据格式
        if not data.get('nodes') or not data.get('edges'):
            return jsonify({
                'success': False,
                'error': '无效的工作流数据格式，缺少nodes或edges'
            }), 400
        
        # 创建工作流
        workflow_data = workflow_manager.create_workflow(
            name=data.get('name', f'导入的工作流_{int(time.time())}'),
            description=data.get('description', '从JSON文件导入的工作流')
        )
        
        # 更新节点和边数据
        workflow_manager.update_workflow(
            workflow_data['id'],
            name=workflow_data['name'],
            description=workflow_data['description'],
            nodes=data.get('nodes'),
            edges=data.get('edges')
        )
        
        return jsonify({
            'success': True,
            'data': workflow_data
        })
    except Exception as e:
        import traceback
        print(f"Update workflow error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8500)