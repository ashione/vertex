// 全局变量
let workflows = [];

// 页面加载完成后初始化
$(document).ready(function() {
    loadWorkflows();
});

// 加载工作流列表
function loadWorkflows() {
    $.get('/api/workflows')
        .done(function(response) {
            if (response.success) {
                workflows = response.data;
                renderWorkflows();
            } else {
                showAlert('加载工作流失败: ' + response.error, 'danger');
            }
        })
        .fail(function() {
            showAlert('网络错误，无法加载工作流', 'danger');
        });
}

// 渲染工作流列表
function renderWorkflows() {
    const container = $('#workflow-list');
    const emptyState = $('#empty-state');
    
    if (workflows.length === 0) {
        container.hide();
        emptyState.show();
        return;
    }
    
    container.show();
    emptyState.hide();
    container.empty();
    
    workflows.forEach(workflow => {
        const card = createWorkflowCard(workflow);
        container.append(card);
        
        // 异步绘制工作流预览图
        setTimeout(() => {
            drawWorkflowPreview(workflow);
        }, 100);
    });
}

// 创建工作流卡片
function createWorkflowCard(workflow) {
    const cardId = `workflow-card-${workflow.id}`;
    const canvasId = `workflow-canvas-${workflow.id}`;
    
    return `
        <div class="col-md-4 mb-3">
            <div class="card workflow-card" id="${cardId}">
                <div class="card-body">
                    <h5 class="card-title">${workflow.name}</h5>
                    <div class="workflow-preview">
                        <canvas id="${canvasId}" width="300" height="80" style="border: 1px solid #dee2e6; border-radius: 4px; width: 100%;"></canvas>
                    </div>
                    <p class="card-text">${workflow.description || '无描述'}</p>
                    <small class="text-muted">创建时间: ${formatDate(workflow.created_at)}</small>
                </div>
                <div class="card-footer">
                    <button class="btn btn-primary btn-sm" onclick="editWorkflow('${workflow.id}')">
                        <i class="bi bi-pencil"></i> 编辑
                    </button>
                    <button class="btn btn-success btn-sm" onclick="executeWorkflow('${workflow.id}')">
                        <i class="bi bi-play"></i> 执行
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="deleteWorkflow('${workflow.id}')">
                        <i class="bi bi-trash"></i> 删除
                    </button>
                </div>
            </div>
        </div>
    `;
}

// 创建工作流
function createWorkflow() {
    $('#createWorkflowModal').modal('show');
}

// 提交创建工作流
function submitCreateWorkflow() {
    const name = $('#workflowName').val();
    const description = $('#workflowDescription').val();
    
    if (!name.trim()) {
        showAlert('请输入工作流名称', 'warning');
        return;
    }
    
    $.ajax({
        url: '/api/workflows',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            name: name,
            description: description
        })
    })
    .done(function(response) {
        if (response.success) {
            $('#createWorkflowModal').modal('hide');
            $('#createWorkflowForm')[0].reset();
            showAlert('工作流创建成功', 'success');
            loadWorkflows();
        } else {
            showAlert('创建失败: ' + response.error, 'danger');
        }
    })
    .fail(function() {
        showAlert('网络错误，创建失败', 'danger');
    });
}

// 编辑工作流
function editWorkflow(workflowId) {
    window.location.href = `/workflow?id=${workflowId}`;
}

// 执行工作流
function executeWorkflow(workflowId) {
    // 这里可以添加输入参数的对话框
    const input = prompt('请输入执行参数 (JSON格式):', '{}');
    if (input === null) return;
    
    try {
        const inputData = JSON.parse(input);
        
        $.ajax({
            url: `/api/workflows/${workflowId}/execute`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                input: inputData
            })
        })
        .done(function(response) {
            if (response.success) {
                alert('执行成功!\n结果: ' + JSON.stringify(response.data, null, 2));
            } else {
                showAlert('执行失败: ' + response.error, 'danger');
            }
        })
        .fail(function() {
            showAlert('网络错误，执行失败', 'danger');
        });
    } catch (e) {
        showAlert('输入参数格式错误', 'warning');
    }
}

// 删除工作流
function deleteWorkflow(workflowId) {
    if (!confirm('确定要删除这个工作流吗？')) {
        return;
    }
    
    $.ajax({
        url: `/api/workflows/${workflowId}`,
        method: 'DELETE'
    })
    .done(function(response) {
        if (response.success) {
            showAlert('工作流删除成功', 'success');
            loadWorkflows();
        } else {
            showAlert('删除失败: ' + response.error, 'danger');
        }
    })
    .fail(function() {
        showAlert('网络错误，删除失败', 'danger');
    });
}

// 显示提示信息
function showAlert(message, type) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // 在页面顶部显示提示
    $('body').prepend(alertHtml);
    
    // 3秒后自动消失
    setTimeout(() => {
        $('.alert').alert('close');
    }, 3000);
}

// 格式化日期
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});
}

// 绘制工作流预览图
function drawWorkflowPreview(workflow) {
    const canvasId = `workflow-canvas-${workflow.id}`;
    const canvas = document.getElementById(canvasId);
    
    if (!canvas) {
        console.warn(`Canvas ${canvasId} not found`);
        return;
    }
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    // 清空画布
    ctx.clearRect(0, 0, width, height);
    
    // 设置背景色
    ctx.fillStyle = '#f8f9fa';
    ctx.fillRect(0, 0, width, height);
    
    // 如果没有节点数据，显示空状态
    if (!workflow.nodes || workflow.nodes.length === 0) {
        drawEmptyWorkflow(ctx, width, height);
        return;
    }
    
    // 计算节点布局
    const nodes = workflow.nodes || [];
    const edges = workflow.edges || [];
    
    // 简化布局：将节点排列在画布中
    const nodePositions = calculateNodePositions(nodes, width, height);
    
    // 绘制连接线
    drawEdges(ctx, edges, nodePositions);
    
    // 绘制节点
    drawNodes(ctx, nodes, nodePositions);
}

// 绘制空工作流状态
function drawEmptyWorkflow(ctx, width, height) {
    ctx.fillStyle = '#6c757d';
    ctx.font = '14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('空工作流', width / 2, height / 2);
}

// 计算节点位置
function calculateNodePositions(nodes, width, height) {
    const positions = {};
    const padding = 30;
    const nodeWidth = 60;
    const nodeHeight = 30;
    
    if (nodes.length === 0) return positions;
    
    // 简单的网格布局
    const cols = Math.ceil(Math.sqrt(nodes.length));
    const rows = Math.ceil(nodes.length / cols);
    
    const cellWidth = (width - 2 * padding) / cols;
    const cellHeight = (height - 2 * padding) / rows;
    
    nodes.forEach((node, index) => {
        const row = Math.floor(index / cols);
        const col = index % cols;
        
        positions[node.id] = {
            x: padding + col * cellWidth + cellWidth / 2,
            y: padding + row * cellHeight + cellHeight / 2,
            width: nodeWidth,
            height: nodeHeight
        };
    });
    
    return positions;
}

// 绘制连接线
function drawEdges(ctx, edges, nodePositions) {
    ctx.strokeStyle = '#6c757d';
    ctx.lineWidth = 1;
    
    edges.forEach(edge => {
        const fromPos = nodePositions[edge.from];
        const toPos = nodePositions[edge.to];
        
        if (fromPos && toPos) {
            ctx.beginPath();
            ctx.moveTo(fromPos.x, fromPos.y);
            ctx.lineTo(toPos.x, toPos.y);
            ctx.stroke();
            
            // 绘制箭头
            drawArrow(ctx, fromPos.x, fromPos.y, toPos.x, toPos.y);
        }
    });
}

// 绘制箭头
function drawArrow(ctx, fromX, fromY, toX, toY) {
    const headlen = 8;
    const angle = Math.atan2(toY - fromY, toX - fromX);
    
    ctx.beginPath();
    ctx.moveTo(toX, toY);
    ctx.lineTo(toX - headlen * Math.cos(angle - Math.PI / 6), toY - headlen * Math.sin(angle - Math.PI / 6));
    ctx.moveTo(toX, toY);
    ctx.lineTo(toX - headlen * Math.cos(angle + Math.PI / 6), toY - headlen * Math.sin(angle + Math.PI / 6));
    ctx.stroke();
}

// 绘制节点
function drawNodes(ctx, nodes, nodePositions) {
    nodes.forEach(node => {
        const pos = nodePositions[node.id];
        if (!pos) return;
        
        // 根据节点类型设置颜色
        const nodeColor = getNodeColor(node.data?.type || 'default');
        
        // 绘制节点背景
        ctx.fillStyle = nodeColor;
        ctx.fillRect(
            pos.x - pos.width / 2,
            pos.y - pos.height / 2,
            pos.width,
            pos.height
        );
        
        // 绘制节点边框
        ctx.strokeStyle = '#333';
        ctx.lineWidth = 1;
        ctx.strokeRect(
            pos.x - pos.width / 2,
            pos.y - pos.height / 2,
            pos.width,
            pos.height
        );
        
        // 绘制节点标签
        ctx.fillStyle = '#333';
        ctx.font = '10px Arial';
        ctx.textAlign = 'center';
        const label = node.label || node.data?.type || 'Node';
        const truncatedLabel = label.length > 8 ? label.substring(0, 6) + '..' : label;
        ctx.fillText(truncatedLabel, pos.x, pos.y + 3);
    });
}

// 获取节点颜色
function getNodeColor(nodeType) {
    const colors = {
        'start': '#28a745',
        'llm': '#007bff',
        'retrieval': '#ffc107',
        'end': '#dc3545',
        'default': '#6c757d'
    };
    return colors[nodeType] || colors.default;
}