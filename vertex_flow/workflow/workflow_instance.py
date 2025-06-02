from datetime import datetime
import uuid

class WorkflowInstance:
    def __init__(self, workflow_template, input_data=None, workflow_manager=None):
        self.id = str(uuid.uuid4())
        self.workflow_template_id = workflow_template['id']
        self.workflow_template = workflow_template
        self.workflow_manager = workflow_manager
        self.workflow_obj = None  # 实际的Workflow对象
        self.input_data = input_data or {}
        self.output_data = None
        self.status = 'created'  # created, running, completed, failed
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.node_outputs = {}  # 存储各节点的输出
        
    def execute(self):
        """执行工作流实例"""
        try:
            self.status = 'running'
            self.started_at = datetime.now()
            
            # 基于模板创建新的workflow对象
            self.workflow_obj = self._create_workflow_from_template()
            
            # 执行工作流
            self.output_data = self.workflow_obj.execute_workflow(self.input_data)
            
            # 收集各节点输出
            self.node_outputs = self.workflow_obj.context.get_outputs()
            
            self.status = 'completed'
            self.completed_at = datetime.now()
            
        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
            self.completed_at = datetime.now()
            raise
    
    def _create_workflow_from_template(self):
        """基于模板创建工作流对象"""
        if not self.workflow_manager:
            raise ValueError("WorkflowManager is required to create workflow from template")
        
        nodes = self.workflow_template.get('nodes', [])
        edges = self.workflow_template.get('edges', [])
        
        return self.workflow_manager._create_workflow_from_nodes_edges(nodes, edges)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'workflow_template_id': self.workflow_template_id,
            'input_data': self.input_data,
            'output_data': self.output_data,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'node_outputs': self.node_outputs
        }