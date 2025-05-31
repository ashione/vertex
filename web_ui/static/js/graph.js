// 图形编辑器辅助函数

// 连接两个节点
function connectNodes(fromNodeId, toNodeId) {
    const edgeId = `edge_${fromNodeId}_${toNodeId}`;
    
    // 检查是否已存在连接
    const existingEdge = edges.get({
        filter: function(edge) {
            return edge.from === fromNodeId && edge.to === toNodeId;
        }
    });
    
    if (existingEdge.length > 0) {
        showAlert('节点之间已存在连接', 'warning');
        return;
    }
    
    const newEdge = {
        id: edgeId,
        from: fromNodeId,
        to: toNodeId,
        label: ''
    };
    
    edges.add(newEdge);
}

// 自动布局
function autoLayout() {
    const nodeArray = nodes.get();
    if (nodeArray.length === 0) return;
    
    // 简单的层次布局
    const levels = {};
    const visited = new Set();
    
    // 找到开始节点
    const startNodes = nodeArray.filter(node => 
        node.data && node.data.type === 'start'
    );
    
    if (startNodes.length === 0) {
        // 如果没有开始节点，使用第一个节点
        if (nodeArray.length > 0) {
            assignLevel(nodeArray[0].id, 0, levels, visited);
        }
    } else {
        startNodes.forEach(node => {
            assignLevel(node.id, 0, levels, visited);
        });
    }
    
    // 应用布局
    const levelHeight = 150;
    const nodeWidth = 200;
    
    Object.keys(levels).forEach(level => {
        const nodesInLevel = levels[level];
        const y = parseInt(level) * levelHeight;
        
        nodesInLevel.forEach((nodeId, index) => {
            const x = (index - (nodesInLevel.length - 1) / 2) * nodeWidth;
            
            const node = nodes.get(nodeId);
            node.x = x;
            node.y = y;
            nodes.update(node);
        });
    });
    
    // 适应视图
    setTimeout(() => {
        network.fit();
    }, 100);
}

// 分配层级
function assignLevel(nodeId, level, levels, visited) {
    if (visited.has(nodeId)) return;
    
    visited.add(nodeId);
    
    if (!levels[level]) {
        levels[level] = [];
    }
    levels[level].push(nodeId);
    
    // 找到所有连接的下级节点
    const connectedEdges = edges.get({
        filter: function(edge) {
            return edge.from === nodeId;
        }
    });
    
    connectedEdges.forEach(edge => {
        assignLevel(edge.to, level + 1, levels, visited);
    });
}

// 验证工作流
function validateWorkflow() {
    const nodeArray = nodes.get();
    const edgeArray = edges.get();
    
    const errors = [];
    
    // 检查是否有开始节点
    const startNodes = nodeArray.filter(node => 
        node.data && node.data.type === 'start'
    );
    
    if (startNodes.length === 0) {
        errors.push('工作流必须包含至少一个开始节点');
    }
    
    // 检查是否有结束节点
    const endNodes = nodeArray.filter(node => 
        node.data && node.data.type === 'end'
    );
    
    if (endNodes.length === 0) {
        errors.push('工作流必须包含至少一个结束节点');
    }
    
    // 检查孤立节点
    nodeArray.forEach(node => {
        const hasIncoming = edgeArray.some(edge => edge.to === node.id);
        const hasOutgoing = edgeArray.some(edge => edge.from === node.id);
        
        if (!hasIncoming && !hasOutgoing && node.data.type !== 'start') {
            errors.push(`节点 "${node.label}" 没有连接`);
        }
    });
    
    // 检查必填配置
    nodeArray.forEach(node => {
        const config = node.data?.config || {};
        
        switch (node.data?.type) {
            case 'llm':
                if (!config.prompt) {
                    errors.push(`LLM节点 "${node.label}" 缺少提示词`);
                }
                break;
            case 'retrieval':
                if (!config.index_name) {
                    errors.push(`检索节点 "${node.label}" 缺少索引名称`);
                }
                break;
            case 'condition':
                if (!config.condition) {
                    errors.push(`条件节点 "${node.label}" 缺少条件表达式`);
                }
                break;
            case 'function':
                if (!config.function_name) {
                    errors.push(`函数节点 "${node.label}" 缺少函数名称`);
                }
                break;
        }
    });
    
    return errors;
}

// 导出工作流数据
function exportWorkflow() {
    const workflowData = {
        name: currentWorkflow?.name || '未命名工作流',
        description: currentWorkflow?.description || '',
        nodes: nodes.get(),
        edges: edges.get(),
        created_at: new Date().toISOString()
    };
    
    const dataStr = JSON.stringify(workflowData, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `${workflowData.name}.json`;
    link.click();
}

// 导入工作流数据
function importWorkflow() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const workflowData = JSON.parse(e.target.result);
                
                // 验证数据格式
                if (!workflowData.nodes || !workflowData.edges) {
                    throw new Error('无效的工作流文件格式');
                }
                
                // 先在前端显示导入的数据
                nodes.clear();
                edges.clear();
                
                nodes.add(workflowData.nodes);
                edges.add(workflowData.edges);
                
                // 适应视图
                setTimeout(() => {
                    network.fit();
                }, 100);
                
                // 创建新的工作流并保存到后端
                const newWorkflowData = {
                    name: workflowData.name || `导入的工作流_${new Date().getTime()}`,
                    description: workflowData.description || '从JSON文件导入的工作流',
                    nodes: workflowData.nodes,
                    edges: workflowData.edges
                };
                
                // 调用后端导入API
                $.ajax({
                    url: '/api/workflows/import',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify(newWorkflowData),
                    success: function(response) {
                         if (response.success) {
                             currentWorkflow = response.data;
                             workflowId = response.data.id;
                             // 更新URL
                             window.history.replaceState({}, '', `/workflow?id=${workflowId}`);
                             showAlert('工作流导入并保存成功', 'success');
                         } else {
                             showAlert('工作流导入失败: ' + response.error, 'danger');
                         }
                     },
                    error: function() {
                        showAlert('工作流导入失败，网络错误', 'danger');
                    }
                });
                
            } catch (error) {
                showAlert('导入失败: ' + error.message, 'danger');
            }
        };
        
        reader.readAsText(file);
    };
    
    input.click();
}

// 清空画布
function clearCanvas() {
    if (confirm('确定要清空画布吗？这将删除所有节点和连接。')) {
        nodes.clear();
        edges.clear();
        selectedNode = null;
        hideNodeProperties();
        showAlert('画布已清空', 'info');
    }
}

// 缩放到适合
function fitToView() {
    network.fit({
        animation: {
            duration: 500,
            easingFunction: 'easeInOutQuad'
        }
    });
}

// 添加工具栏按钮功能
$(document).ready(function() {
    // 添加额外的工具栏按钮
    const additionalButtons = `
        <button class="btn btn-outline-light me-2" onclick="autoLayout()" title="自动布局">
            <i class="bi bi-diagram-3"></i>
        </button>
        <button class="btn btn-outline-light me-2" onclick="validateWorkflow()" title="验证工作流">
            <i class="bi bi-check-circle"></i>
        </button>
        <button class="btn btn-outline-light me-2" onclick="exportWorkflow()" title="导出">
            <i class="bi bi-download"></i>
        </button>
        <button class="btn btn-outline-light me-2" onclick="importWorkflow()" title="导入">
            <i class="bi bi-upload"></i>
        </button>
        <button class="btn btn-outline-light me-2" onclick="clearCanvas()" title="清空">
            <i class="bi bi-trash"></i>
        </button>
        <button class="btn btn-outline-light me-2" onclick="fitToView()" title="适应视图">
            <i class="bi bi-arrows-fullscreen"></i>
        </button>
    `;
    
    $('.navbar-nav.ms-auto').prepend(additionalButtons);
});