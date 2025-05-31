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
    });
}

// 创建工作流卡片
function createWorkflowCard(workflow) {
    return `
        <div class="col-md-4 mb-3">
            <div class="card h-100">
                <div class="card-body">
                    <h5 class="card-title">${workflow.name}</h5>
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
    return date.toLocaleDateString('zh-CN');
}