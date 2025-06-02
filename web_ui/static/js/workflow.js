// 全局变量
let currentWorkflow = null;
let workflowId = null;
let network = null;
let nodes = new vis.DataSet([]);
let edges = new vis.DataSet([]);
let selectedNode = null;
let isConnecting = false;
let connectionStartNode = null;
let connectionPreview = null;
let connectionMode = false; // 全局连接模式

// 撤销功能相关变量
let operationHistory = [];
let historyIndex = -1;
const MAX_HISTORY = 50;

// 页面加载完成后初始化
$(document).ready(function() {
    // 从URL获取工作流ID
    const urlParams = new URLSearchParams(window.location.search);
    workflowId = urlParams.get('id');
    
    // 确保vis库已加载
    if (typeof vis === 'undefined') {
        console.error('vis.js library not loaded');
        return;
    }
    
    initializeWorkflowEditor();
    
    if (workflowId) {
        loadWorkflow(workflowId);
    } else {
        // 创建新工作流
        createNewWorkflow();
    }
});

// 初始化工作流编辑器
function initializeWorkflowEditor() {
    // 初始化图形编辑器
    initializeGraph();
    
    // 绑定节点面板拖拽事件
    bindNodePaletteDragEvents();
    
    // 绑定保存和执行按钮
    bindToolbarEvents();
    
    // 初始化输出面板
    initOutputPanelResize();
}

// 初始化图形编辑器
function initializeGraph() {
    const container = document.getElementById('workflow-canvas');
    
    const data = {
        nodes: nodes,
        edges: edges
    };
    
    const options = {
        nodes: {
            shape: 'box',
            margin: 15,
            widthConstraint: { minimum: 120, maximum: 200 },
            heightConstraint: { minimum: 60, maximum: 100 },
            font: {
                size: 14,
                color: '#ffffff',
                face: 'Arial, sans-serif',
                align: 'center'
            },
            borderWidth: 2,
            borderWidthSelected: 4,
            color: {
                border: '#495057',
                background: '#6c757d',
                highlight: {
                    border: '#007bff',
                    background: '#0056b3'
                },
                hover: {
                    border: '#17a2b8',
                    background: '#138496'
                }
            },
            shadow: {
                enabled: true,
                color: 'rgba(0,0,0,0.2)',
                size: 8,
                x: 2,
                y: 2
            },
            chosen: {
                node: function(values, id, selected, hovering) {
                    if (selected) {
                        values.borderWidth = 4;
                        values.borderColor = '#007bff';
                        values.shadow = true;
                        values.shadowColor = 'rgba(0,123,255,0.4)';
                        values.shadowSize = 12;
                    } else {
                        values.borderWidth = 2;
                        values.borderColor = '#495057';
                    }
                }
            }
        },
        edges: {
            arrows: {
                to: { 
                    enabled: true, 
                    scaleFactor: 1.2, 
                    type: 'arrow',
                    src: undefined,
                    imageHeight: undefined,
                    imageWidth: undefined
                }
            },
            color: {
                color: '#6c757d',
                highlight: '#007bff',
                hover: '#17a2b8',
                inherit: false
            },
            width: 3,
            smooth: {
                type: 'cubicBezier',
                forceDirection: 'horizontal',
                roundness: 0.4
            },
            shadow: {
                enabled: true,
                color: 'rgba(0,0,0,0.1)',
                size: 4,
                x: 1,
                y: 1
            },
            chosen: {
                edge: function(values, id, selected, hovering) {
                    values.color = '#007bff';
                    values.width = 4;
                }
            }
        },
        physics: {
            enabled: false
        },
        interaction: {
            dragNodes: true,
            dragView: true,
            zoomView: true
        },
        manipulation: {
            enabled: true,
            addNode: false,
            addEdge: {
                editWithoutDrag: function(data, callback) {
                    // 创建连接
                    createConnection(data.from, data.to);
                    callback(null);
                }
            },
            editEdge: false,
            deleteNode: false,
            deleteEdge: {
                editWithoutDrag: function(data, callback) {
                    // 保存操作到历史记录
                    saveOperationToHistory('deleteEdge', {
                        edges: data.edges.map(id => {
                            const edge = edges.get(id);
                            return { id: id, from: edge.from, to: edge.to, ...edge };
                        })
                    });
                    
                    // 删除连接（不弹出确认框）
                    edges.remove(data.edges);
                    showAlert('连接线已删除', 'success');
                    callback(null);
                }
            }
        }
    };
    
    network = new vis.Network(container, data, options);
    
    // 确保网络图正确渲染
    setTimeout(() => {
        if (network) {
            network.fit();
            network.redraw();
        }
    }, 100);
    
    // 绑定网络事件
    bindNetworkEvents();
    
    // 监听窗口大小变化
    window.addEventListener('resize', function() {
        if (network) {
            network.redraw();
        }
    });
    
    // 监听输出面板大小变化
    const outputPanel = document.getElementById('output-panel');
    if (outputPanel) {
        const resizeObserver = new ResizeObserver(function() {
            if (network) {
                setTimeout(() => {
                    network.redraw();
                }, 50);
            }
        });
        resizeObserver.observe(outputPanel);
    }
}

// 绑定网络事件
function bindNetworkEvents() {
    // 节点选择事件
    network.on('selectNode', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            
            if (connectionMode) {
                // 连接模式下的节点点击处理
                if (!isConnecting) {
                    // 开始连接
                    startConnection(nodeId);
                } else if (connectionStartNode && nodeId !== connectionStartNode) {
                    // 完成连接
                    if (createConnection(connectionStartNode, nodeId)) {
                        showAlert('节点连接成功', 'success');
                    }
                    endConnection();
                } else if (nodeId === connectionStartNode) {
                    // 点击同一个节点，取消连接
                    endConnection();
                    showAlert('连接已取消', 'warning');
                }
            } else if (isConnecting && connectionStartNode) {
                // 兼容旧的连接方式
                if (nodeId !== connectionStartNode) {
                    if (createConnection(connectionStartNode, nodeId)) {
                        showAlert('节点连接成功', 'success');
                    }
                }
                endConnection();
            } else {
                // 普通模式：选择节点并显示属性
                selectedNode = nodeId;
                showNodeProperties(selectedNode);
            }
        }
    });
    
    // 取消选择事件
    network.on('deselectNode', function() {
        if (!isConnecting) {
            selectedNode = null;
            hideNodeProperties();
        }
    });
    
    // 监听键盘事件
    document.addEventListener('keydown', function(event) {
        // 检查是否在输入框或文本区域中
        const activeElement = document.activeElement;
        const isInputActive = activeElement && (
            activeElement.tagName === 'INPUT' || 
            activeElement.tagName === 'TEXTAREA' || 
            activeElement.contentEditable === 'true' ||
            activeElement.classList.contains('ql-editor') // Quill编辑器
        );
        
        if (event.key === 'Escape') {
            if (isConnecting) {
                endConnection();
                showAlert('连接已取消', 'warning');
            } else if (connectionMode) {
                // 退出连接模式
                toggleConnectionMode();
            }
        } else if ((event.key === 'Delete' || event.key === 'Backspace') && !isInputActive) {
            // 只有在不是输入状态时才删除选中的连接线
            const selectedEdges = network.getSelectedEdges();
            if (selectedEdges.length > 0) {
                // 保存操作到历史记录
                saveOperationToHistory('deleteEdge', {
                    edges: selectedEdges.map(id => {
                        const edge = edges.get(id);
                        return { id: id, from: edge.from, to: edge.to, ...edge };
                    })
                });
                
                // 删除连接线（不弹出确认框）
                edges.remove(selectedEdges);
                showAlert(`已删除 ${selectedEdges.length} 条连接线`, 'success');
            }
        } else if ((event.ctrlKey || event.metaKey) && event.key === 'z' && !isInputActive) {
            // 撤销操作 (Ctrl+Z 或 Cmd+Z)，但不在输入状态时
            event.preventDefault();
            undoLastOperation();
        }
    });
    
    // 双击创建连接
    network.on('doubleClick', function(params) {
        if (params.nodes.length === 0) {
            // 在空白处双击，显示添加节点菜单
            showAddNodeMenu(params.pointer.canvas);
        }
    });
    
    // 拖拽放置事件
    network.on('dragEnd', function(params) {
        if (params.nodes.length > 0) {
            updateNodePosition(params.nodes[0]);
        }
    });
}

// 绑定节点面板拖拽事件
function bindNodePaletteDragEvents() {
    $('.node-item').each(function() {
        const nodeType = $(this).data('type');
        
        $(this).on('dragstart', function(e) {
            e.originalEvent.dataTransfer.setData('text/plain', nodeType);
        });
        
        $(this).attr('draggable', true);
    });
    
    // 画布拖拽事件
    $('#workflow-canvas').on('dragover', function(e) {
        e.preventDefault();
    });
    
    $('#workflow-canvas').on('drop', function(e) {
        e.preventDefault();
        const nodeType = e.originalEvent.dataTransfer.getData('text/plain');
        
        if (nodeType) {
            const canvasPosition = network.DOMtoCanvas({
                x: e.originalEvent.offsetX,
                y: e.originalEvent.offsetY
            });
            
            addNode(nodeType, canvasPosition);
        }
    });
}

// 添加节点
function addNode(nodeType, position) {
    const nodeId = 'node_' + Date.now();
    const nodeConfig = getNodeConfig(nodeType);
    
    const newNode = {
        id: nodeId,
        label: nodeConfig.label,
        x: position.x,
        y: position.y,
        color: {
            background: nodeConfig.color.background,
            border: nodeConfig.color.border,
            highlight: {
                background: nodeConfig.color.highlight,
                border: '#007bff'
            },
            hover: {
                background: nodeConfig.color.hover,
                border: '#17a2b8'
            }
        },
        font: { 
            color: '#ffffff',
            size: 14,
            face: 'Arial, sans-serif'
        },
        borderWidth: 2,
        borderWidthSelected: 4,
        data: {
            type: nodeType,
            config: nodeConfig.defaultConfig
        }
    };
    
    nodes.add(newNode);
    
    // 自动选择新添加的节点
    network.selectNodes([nodeId]);
    selectedNode = nodeId;
    showNodeProperties(nodeId);
}

// 获取节点配置
function getNodeConfig(nodeType) {
    const configs = {
        start: {
            label: '开始',
            color: {
                background: '#28a745',
                border: '#1e7e34',
                highlight: '#34ce57',
                hover: '#218838'
            },
            defaultConfig: {
                name: '开始节点',
                description: '工作流开始节点'
            }
        },
        llm: {
            label: 'LLM',
            color: {
                background: '#007bff',
                border: '#0056b3',
                highlight: '#0d8bff',
                hover: '#0056b3'
            },
            defaultConfig: {
                name: 'LLM节点',
                model: 'deepseek',
                model_name: 'deepseek-chat',
                system_prompt: '你是一个非常博学并幽默的聊天机器人',
                user_message: '请帮我制作一个关于杭州的旅游攻略.',
                temperature: 0.7,
                max_tokens: 1000
            },
            availableModels: {
                'deepseek': 'deepseek-chat',
                'tongyi': 'qwen-max',
                'openrouter': 'deepseek/deepseek-chat-v3-0324:free'
            }
        },
        retrieval: {
            label: '检索',
            color: {
                background: '#17a2b8',
                border: '#117a8b',
                highlight: '#1fb3d3',
                hover: '#138496'
            },
            defaultConfig: {
                name: '检索节点',
                index_name: '',
                query: '',
                top_k: 5
            }
        },
        condition: {
            label: '条件',
            color: {
                background: '#ffc107',
                border: '#d39e00',
                highlight: '#ffcd39',
                hover: '#e0a800'
            },
            defaultConfig: {
                name: '条件节点',
                condition: '',
                true_branch: '',
                false_branch: ''
            }
        },
        function: {
            label: '函数',
            color: {
                background: '#6f42c1',
                border: '#59359a',
                highlight: '#8a63d2',
                hover: '#59359a'
            },
            defaultConfig: {
                name: '函数节点',
                function_name: '',
                parameters: {}
            }
        },
        end: {
            label: '结束',
            color: {
                background: '#dc3545',
                border: '#c82333',
                highlight: '#e4606d',
                hover: '#bd2130'
            },
            defaultConfig: {
                name: '结束节点',
                description: '工作流结束节点'
            }
        }
    };
    
    return configs[nodeType] || configs.start;
}

// 显示节点属性
function showNodeProperties(nodeId) {
    const node = nodes.get(nodeId);
    if (!node) return;
    
    const propertiesPanel = $('#node-properties');
    const nodeData = node.data || {};
    const config = nodeData.config || {};
    
    // 添加调试信息
    if (nodeData.type === 'llm') {
        console.log('显示LLM节点属性:');
        console.log('节点ID:', nodeId);
        console.log('节点数据:', nodeData);
        console.log('配置数据:', config);
        console.log('用户消息配置值:', config.user_message);
    }
    
    let html = `
        <div class="mb-3">
            <label class="form-label">节点名称</label>
            <input type="text" class="form-control" id="node-name" value="${config.name || ''}">
        </div>
    `;
    
    // 根据节点类型显示不同的配置项
    switch (nodeData.type) {
        case 'llm':
            const nodeConfig = getNodeConfig('llm');
            const availableModels = nodeConfig.availableModels;
            let modelOptions = '';
            for (const [key, value] of Object.entries(availableModels)) {
                modelOptions += `<option value="${key}" ${config.model === key ? 'selected' : ''}>${key} (${value})</option>`;
            }
            html += `
                <div class="mb-3">
                    <label class="form-label">模型提供商</label>
                    <select class="form-control" id="node-model">
                        ${modelOptions}
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">模型名称</label>
                    <input type="text" class="form-control" id="node-model-name" value="${config.model_name || ''}" readonly>
                </div>
                <div class="mb-3">
                    <label class="form-label">系统提示词</label>
                    <textarea class="form-control" id="node-system-prompt" rows="3">${config.system_prompt || ''}</textarea>
                </div>
                <div class="mb-3">
                    <label class="form-label">用户消息</label>
                    <div id="node-user-message-editor" style="height: 150px;"></div>
                    <input type="hidden" id="node-user-message" value="${config.user_message || ''}">
                </div>
                <div class="mb-3">
                    <label class="form-label">温度</label>
                    <input type="number" class="form-control" id="node-temperature" value="${config.temperature || 0.7}" min="0" max="2" step="0.1">
                </div>
                <div class="mb-3">
                    <label class="form-label">最大令牌数</label>
                    <input type="number" class="form-control" id="node-max-tokens" value="${config.max_tokens || 1000}">
                </div>
            `;
            break;
            
        case 'retrieval':
            html += `
                <div class="mb-3">
                    <label class="form-label">索引名称</label>
                    <input type="text" class="form-control" id="node-index-name" value="${config.index_name || ''}">
                </div>
                <div class="mb-3">
                    <label class="form-label">查询</label>
                    <input type="text" class="form-control" id="node-query" value="${config.query || ''}">
                </div>
                <div class="mb-3">
                    <label class="form-label">返回数量</label>
                    <input type="number" class="form-control" id="node-top-k" value="${config.top_k || 5}">
                </div>
            `;
            break;
            
        case 'condition':
            html += `
                <div class="mb-3">
                    <label class="form-label">条件表达式</label>
                    <input type="text" class="form-control" id="node-condition" value="${config.condition || ''}">
                </div>
                <div class="mb-3">
                    <label class="form-label">真分支</label>
                    <input type="text" class="form-control" id="node-true-branch" value="${config.true_branch || ''}">
                </div>
                <div class="mb-3">
                    <label class="form-label">假分支</label>
                    <input type="text" class="form-control" id="node-false-branch" value="${config.false_branch || ''}">
                </div>
            `;
            break;
            
        case 'function':
            html += `
                <div class="mb-3">
                    <label class="form-label">函数名称</label>
                    <input type="text" class="form-control" id="node-function-name" value="${config.function_name || ''}">
                </div>
                <div class="mb-3">
                    <label class="form-label">参数 (JSON)</label>
                    <textarea class="form-control" id="node-parameters" rows="4">${JSON.stringify(config.parameters || {}, null, 2)}</textarea>
                </div>
            `;
            break;
    }
    
    html += `
        <div class="mt-3">
            <button class="btn btn-primary btn-sm" onclick="updateNodeProperties()">更新</button>
            <button class="btn btn-info btn-sm" onclick="startConnection('${nodeId}')">连接</button>
            <button class="btn btn-danger btn-sm" onclick="deleteNode()">删除</button>
        </div>
    `;
    
    propertiesPanel.html(html);
    
    // 显示节点输出（如果有的话）
    if (node.data && node.data.output) {
        updateNodePropertiesWithOutput(selectedNode, node.data.output);
    } else {
        // 清空底部输出面板
        $('#output-node-info').text('未选择节点');
        $('#output-content').html('<p class="text-muted mb-0">选择一个已执行的节点查看输出结果</p>');
    }
    
    // 为LLM节点添加模型选择变化事件和富文本编辑器
    if (nodeData.type === 'llm') {
        $('#node-model').on('change', function() {
            const selectedModel = $(this).val();
            const nodeConfig = getNodeConfig('llm');
            const modelName = nodeConfig.availableModels[selectedModel];
            $('#node-model-name').val(modelName);
        });
        
        // 初始化富文本编辑器
        if (typeof Quill !== 'undefined') {
            const quill = new Quill('#node-user-message-editor', {
                theme: 'snow',
                placeholder: '请输入用户消息...',
                modules: {
                    toolbar: [
                        ['bold', 'italic', 'underline', 'strike'],
                        ['blockquote', 'code-block'],
                        [{ 'header': 1 }, { 'header': 2 }],
                        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                        [{ 'script': 'sub'}, { 'script': 'super' }],
                        [{ 'indent': '-1'}, { 'indent': '+1' }],
                        [{ 'direction': 'rtl' }],
                        [{ 'size': ['small', false, 'large', 'huge'] }],
                        [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
                        [{ 'color': [] }, { 'background': [] }],
                        [{ 'font': [] }],
                        [{ 'align': [] }],
                        ['clean'],
                        ['link']
                    ]
                }
            });
            
            // 设置初始内容
            const userMessage = config.user_message || '';
            if (userMessage) {
                quill.root.innerHTML = userMessage;
            }
            
            // 保存编辑器实例到全局变量
            window.userMessageQuill = quill;
            
            // 监听内容变化，同步到隐藏输入框
            quill.on('text-change', function() {
                $('#node-user-message').val(quill.root.innerHTML);
            });
        }
    }
}

// 隐藏节点属性
function hideNodeProperties() {
    // 清理富文本编辑器实例
    if (window.userMessageQuill) {
        window.userMessageQuill = null;
    }
    
    $('#node-properties').html('<p class="text-muted">选择一个节点来编辑属性</p>');
}

// 更新节点属性
function updateNodeProperties() {
    if (!selectedNode) return;
    
    const node = nodes.get(selectedNode);
    if (!node) return;
    
    const nodeData = node.data || {};
    const config = nodeData.config || {};
    
    // 更新基本属性
    config.name = $('#node-name').val();
    
    // 根据节点类型更新特定属性
    switch (nodeData.type) {
        case 'llm':
            config.model = $('#node-model').val();
            config.model_name = $('#node-model-name').val();
            config.system_prompt = $('#node-system-prompt').val();
            
            // 从富文本编辑器获取内容
            if (window.userMessageQuill) {
                config.user_message = window.userMessageQuill.root.innerHTML;
            } else {
                config.user_message = $('#node-user-message').val();
            }
            
            config.temperature = parseFloat($('#node-temperature').val());
            config.max_tokens = parseInt($('#node-max-tokens').val());
            
            // 添加调试信息
            console.log('更新LLM节点属性:');
            console.log('节点ID:', selectedNode);
            console.log('用户消息输入框值:', $('#node-user-message').val());
            console.log('用户消息配置值:', config.user_message);
            console.log('系统提示词值:', config.system_prompt);
            console.log('完整配置:', config);
            console.log('更新前节点数据:', JSON.stringify(node, null, 2));
            break;
            
        case 'retrieval':
            config.index_name = $('#node-index-name').val();
            config.query = $('#node-query').val();
            config.top_k = parseInt($('#node-top-k').val());
            break;
            
        case 'condition':
            config.condition = $('#node-condition').val();
            config.true_branch = $('#node-true-branch').val();
            config.false_branch = $('#node-false-branch').val();
            break;
            
        case 'function':
            config.function_name = $('#node-function-name').val();
            try {
                config.parameters = JSON.parse($('#node-parameters').val());
            } catch (e) {
                alert('参数格式错误，请输入有效的JSON');
                return;
            }
            break;
    }
    
    // 更新节点标签
    node.label = config.name;
    node.data.config = config;
    
    // 添加更多调试信息
    console.log('更新后节点数据:', JSON.stringify(node, null, 2));
    
    nodes.update(node);
    
    // 验证更新是否成功
    const updatedNode = nodes.get(selectedNode);
    console.log('从nodes集合获取的更新后节点:', JSON.stringify(updatedNode, null, 2));
    
    showAlert('节点属性已更新', 'success');
}

// 删除节点
function deleteNode() {
    if (!selectedNode) return;
    
    if (confirm('确定要删除这个节点吗？')) {
        // 删除相关的边
        const connectedEdges = edges.get({
            filter: function(edge) {
                return edge.from === selectedNode || edge.to === selectedNode;
            }
        });
        
        edges.remove(connectedEdges.map(edge => edge.id));
        
        // 删除节点
        nodes.remove(selectedNode);
        
        selectedNode = null;
        hideNodeProperties();
        
        showAlert('节点已删除', 'success');
    }
}

// 显示执行结果
function displayExecutionResults(data) {
    console.log('执行结果:', data);
    
    // 显示工作流实例信息
    if (data.instance_id) {
        displayInstanceInfo(data);
    }
    
    // 如果有节点输出数据，更新节点显示
    if (data.node_outputs) {
        updateNodesWithOutputs(data.node_outputs);
    }
    
    // 如果有顶点状态信息，也可以显示
    if (data.vertices_status) {
        console.log('顶点状态:', data.vertices_status);
    }
    
    // 显示最终结果
    if (data.result) {
        console.log('最终结果:', data.result);
    }
    
    // 刷新执行历史
    setTimeout(() => {
        loadExecutionHistory();
    }, 1000);
}

// 显示工作流实例信息
function displayInstanceInfo(data) {
    const instanceInfo = `
        <div class="alert alert-info mt-3">
            <h6><i class="fas fa-info-circle"></i> 执行实例信息</h6>
            <p><strong>实例ID:</strong> ${data.instance_id}</p>
            <p><strong>状态:</strong> <span class="badge badge-${getStatusBadgeClass(data.status)}">${data.status}</span></p>
            <p><strong>执行时间:</strong> ${data.executed_at}</p>
            ${data.error ? `<p><strong>错误信息:</strong> <span class="text-danger">${data.error}</span></p>` : ''}
        </div>
    `;
    
    // 在输出面板中显示实例信息
    const outputPanel = document.getElementById('output-content');
    if (outputPanel) {
        outputPanel.innerHTML = instanceInfo + outputPanel.innerHTML;
    }
}

// 获取状态对应的Bootstrap样式类
function getStatusBadgeClass(status) {
    switch(status) {
        case 'completed': return 'success';
        case 'failed': return 'danger';
        case 'running': return 'warning';
        case 'created': return 'secondary';
        default: return 'secondary';
    }
 }
 
 // 加载执行历史
 function loadExecutionHistory() {
     if (!workflowId) return;
     
     $.get(`/api/workflows/${workflowId}/history`)
         .done(function(response) {
             if (response.success) {
                 displayExecutionHistory(response.data);
             }
         })
         .fail(function() {
             console.error('加载执行历史失败');
         });
 }
 
 // 显示执行历史
 function displayExecutionHistory(history) {
     const historyPanel = document.getElementById('execution-history');
     if (!historyPanel) {
         // 如果历史面板不存在，创建一个
         createExecutionHistoryPanel();
         return;
     }
     
     if (history.length === 0) {
         historyPanel.innerHTML = '<p class="text-muted">暂无执行历史</p>';
         return;
     }
     
     let historyHtml = '<h6><i class="fas fa-history"></i> 执行历史</h6>';
     history.forEach(item => {
         historyHtml += `
             <div class="card mb-2">
                 <div class="card-body p-2">
                     <div class="d-flex justify-content-between align-items-center">
                         <small class="text-muted">${item.executed_at}</small>
                         <span class="badge badge-${getStatusBadgeClass(item.status)}">${item.status}</span>
                     </div>
                     <div class="mt-1">
                         <button class="btn btn-sm btn-outline-primary" onclick="viewInstanceDetails('${item.instance_id}')">
                             查看详情
                         </button>
                     </div>
                 </div>
             </div>
         `;
     });
     
     historyPanel.innerHTML = historyHtml;
 }
 
 // 创建执行历史面板
 function createExecutionHistoryPanel() {
     const rightPanel = document.querySelector('#main-workspace .col-md-3');
     if (rightPanel) {
         const historyHtml = `
             <div class="card mt-3">
                 <div class="card-header">
                     <h6 class="mb-0">执行历史</h6>
                 </div>
                 <div class="card-body" id="execution-history">
                     <p class="text-muted">暂无执行历史</p>
                 </div>
             </div>
         `;
         rightPanel.insertAdjacentHTML('beforeend', historyHtml);
         
         // 重新加载历史
         loadExecutionHistory();
     }
 }
 
 // 查看实例详情
 function viewInstanceDetails(instanceId) {
     $.get(`/api/workflow-instances/${instanceId}`)
         .done(function(response) {
             if (response.success) {
                 showInstanceDetailsModal(response.data);
             } else {
                 showAlert('获取实例详情失败: ' + response.error, 'danger');
             }
         })
         .fail(function() {
             showAlert('网络错误，获取实例详情失败', 'danger');
         });
 }
 
 // 显示实例详情模态框
 function showInstanceDetailsModal(instance) {
     const modalHtml = `
         <div class="modal fade" id="instanceDetailsModal" tabindex="-1">
             <div class="modal-dialog modal-lg">
                 <div class="modal-content">
                     <div class="modal-header">
                         <h5 class="modal-title">工作流实例详情</h5>
                         <button type="button" class="close" data-dismiss="modal">
                             <span>&times;</span>
                         </button>
                     </div>
                     <div class="modal-body">
                         <div class="row">
                             <div class="col-md-6">
                                 <h6>基本信息</h6>
                                 <p><strong>实例ID:</strong> ${instance.id}</p>
                                 <p><strong>状态:</strong> <span class="badge badge-${getStatusBadgeClass(instance.status)}">${instance.status}</span></p>
                                 <p><strong>创建时间:</strong> ${instance.created_at}</p>
                                 <p><strong>开始时间:</strong> ${instance.started_at || '未开始'}</p>
                                 <p><strong>完成时间:</strong> ${instance.completed_at || '未完成'}</p>
                                 ${instance.error_message ? `<p><strong>错误信息:</strong> <span class="text-danger">${instance.error_message}</span></p>` : ''}
                             </div>
                             <div class="col-md-6">
                                 <h6>输入数据</h6>
                                 <pre class="bg-light p-2 rounded"><code>${JSON.stringify(instance.input_data, null, 2)}</code></pre>
                             </div>
                         </div>
                         ${instance.output_data ? `
                             <div class="mt-3">
                                 <h6>输出结果</h6>
                                 <pre class="bg-light p-2 rounded"><code>${JSON.stringify(instance.output_data, null, 2)}</code></pre>
                             </div>
                         ` : ''}
                         ${instance.node_outputs ? `
                             <div class="mt-3">
                                 <h6>节点输出</h6>
                                 <pre class="bg-light p-2 rounded"><code>${JSON.stringify(instance.node_outputs, null, 2)}</code></pre>
                             </div>
                         ` : ''}
                     </div>
                     <div class="modal-footer">
                         <button type="button" class="btn btn-secondary" data-dismiss="modal">关闭</button>
                     </div>
                 </div>
             </div>
         </div>
     `;
     
     // 移除已存在的模态框
     $('#instanceDetailsModal').remove();
     
     // 添加新的模态框
     $('body').append(modalHtml);
     
     // 显示模态框
     $('#instanceDetailsModal').modal('show');
 }
 
 // 用输出结果更新节点
function updateNodesWithOutputs(nodeOutputs) {
    const currentNodes = nodes.get();
    const updatedNodes = currentNodes.map(node => {
        if (nodeOutputs[node.id]) {
            // 为节点添加输出数据
            node.data = node.data || {};
            node.data.output = nodeOutputs[node.id];
            
            // 更新节点颜色以表示已执行
            node.color = {
                background: '#d4edda',
                border: '#28a745'
            };
        }
        return node;
    });
    
    nodes.update(updatedNodes);
    
    // 如果当前选中的节点有输出，更新属性面板
    if (selectedNode && nodeOutputs[selectedNode]) {
        updateNodePropertiesWithOutput(selectedNode, nodeOutputs[selectedNode]);
    }
}

// 检测是否为markdown格式
function isMarkdownContent(text) {
    if (typeof text !== 'string') return false;
    
    // 检测常见的markdown语法
    const markdownPatterns = [
        /^#{1,6}\s+/m,           // 标题
        /\*\*.*?\*\*/,           // 粗体
        /\*.*?\*/,               // 斜体
        /^\s*[-*+]\s+/m,        // 无序列表
        /^\s*\d+\.\s+/m,        // 有序列表
        /```[\s\S]*?```/,       // 代码块
        /`.*?`/,                 // 行内代码
        /\[.*?\]\(.*?\)/,       // 链接
        /^>\s+/m                 // 引用
    ];
    
    return markdownPatterns.some(pattern => pattern.test(text));
}

// 在底部输出面板中显示输出
function updateNodePropertiesWithOutput(nodeId, output) {
    const outputText = typeof output === 'string' ? output : JSON.stringify(output, null, 2);
    
    // 更新输出面板的节点信息
    const nodeData = nodes.get(nodeId);
    const nodeLabel = nodeData ? nodeData.label : `节点 ${nodeId}`;
    $('#output-node-info').text(`${nodeLabel} (${nodeId})`);
    
    let outputHtml;
    
    // 检测是否为markdown格式
    if (typeof output === 'string' && isMarkdownContent(output)) {
        // 渲染markdown
        const renderedMarkdown = typeof marked !== 'undefined' ? marked.parse(output) : output;
        outputHtml = `
            <div class="d-flex justify-content-between align-items-center mb-3">
                <span class="badge bg-info">Markdown格式</span>
                <button class="btn btn-sm btn-outline-secondary" onclick="toggleRawOutput('${nodeId}')">
                    <i class="bi bi-code"></i> 查看原始内容
                </button>
            </div>
            <div class="markdown-output border rounded p-3" style="background-color: #fff; max-height: calc(100% - 80px); overflow-y: auto;">
                ${renderedMarkdown}
            </div>
            <div id="raw-output-${nodeId}" class="mt-3" style="display: none;">
                <textarea class="form-control" readonly style="height: calc(100% - 120px); font-size: 12px; font-family: monospace; background-color: #f8f9fa; resize: none;">${outputText}</textarea>
            </div>
        `;
    } else {
        // 普通文本或JSON格式
        outputHtml = `
            <div class="d-flex justify-content-between align-items-center mb-3">
                <span class="badge bg-secondary">文本格式</span>
                <button class="btn btn-sm btn-outline-primary" onclick="copyOutputToClipboard('${nodeId}')">
                    <i class="bi bi-clipboard"></i> 复制
                </button>
            </div>
            <textarea id="output-text-${nodeId}" class="form-control" readonly style="height: calc(100% - 60px); font-size: 12px; font-family: monospace; background-color: #f8f9fa; resize: none;">${outputText}</textarea>
        `;
    }
    
    // 更新底部输出面板内容
    $('#output-content').html(outputHtml);
    
    // 确保输出面板可见
    if ($('#output-panel').hasClass('minimized')) {
        minimizeOutputPanel(); // 切换到正常状态
    }
}

// 切换原始输出显示
function toggleRawOutput(nodeId) {
    const rawOutput = $(`#raw-output-${nodeId}`);
    const button = rawOutput.prev().find('button');
    
    if (rawOutput.is(':visible')) {
        rawOutput.hide();
        button.html('<i class="bi bi-code"></i> 查看原始内容');
    } else {
        rawOutput.show();
        button.html('<i class="bi bi-eye-slash"></i> 隐藏原始内容');
    }
}

// 复制输出内容到剪贴板
function copyOutputToClipboard(nodeId) {
    const textarea = $(`#output-text-${nodeId}`);
    if (textarea.length) {
        textarea.select();
        document.execCommand('copy');
        
        // 显示复制成功提示
        const button = textarea.siblings().find('button');
        const originalHtml = button.html();
        button.html('<i class="bi bi-check"></i> 已复制');
        button.removeClass('btn-outline-primary').addClass('btn-success');
        
        setTimeout(() => {
            button.html(originalHtml);
            button.removeClass('btn-success').addClass('btn-outline-primary');
        }, 2000);
    }
}

// 展开输出面板
function expandOutputPanel() {
    const panel = $('#output-panel');
    panel.removeClass('minimized').addClass('expanded');
    
    // 更新按钮图标
    $('#expand-output-btn').html('<i class="bi bi-arrows-collapse"></i>');
    $('#expand-output-btn').attr('onclick', 'normalizeOutputPanel()').attr('title', '恢复输出面板');
}

// 最小化输出面板
function minimizeOutputPanel() {
    const panel = $('#output-panel');
    
    if (panel.hasClass('minimized')) {
        // 当前是最小化状态，恢复到正常状态
        panel.removeClass('minimized');
        $('#minimize-output-btn').html('<i class="bi bi-dash"></i>').attr('title', '最小化输出面板');
    } else {
        // 当前是正常状态，最小化
        panel.removeClass('expanded').addClass('minimized');
        $('#minimize-output-btn').html('<i class="bi bi-plus"></i>').attr('title', '展开输出面板');
        
        // 重置展开按钮
        $('#expand-output-btn').html('<i class="bi bi-arrows-expand"></i>');
        $('#expand-output-btn').attr('onclick', 'expandOutputPanel()').attr('title', '展开输出面板');
    }
}

// 恢复输出面板到正常大小
function normalizeOutputPanel() {
    const panel = $('#output-panel');
    panel.removeClass('expanded minimized');
    
    // 重置按钮
    $('#expand-output-btn').html('<i class="bi bi-arrows-expand"></i>');
    $('#expand-output-btn').attr('onclick', 'expandOutputPanel()').attr('title', '展开输出面板');
    $('#minimize-output-btn').html('<i class="bi bi-dash"></i>').attr('title', '最小化输出面板');
}

// 初始化输出面板调整大小功能
function initOutputPanelResize() {
    let isResizing = false;
    let startY = 0;
    let startHeight = 0;
    
    $('#output-panel-resizer').on('mousedown', function(e) {
        isResizing = true;
        startY = e.clientY;
        startHeight = $('#output-panel').height();
        
        $('body').css('user-select', 'none');
        $('body').css('cursor', 'ns-resize');
        
        e.preventDefault();
    });
    
    $(document).on('mousemove', function(e) {
        if (!isResizing) return;
        
        const deltaY = startY - e.clientY;
        const newHeight = Math.max(100, Math.min(window.innerHeight * 0.6, startHeight + deltaY));
        
        $('#output-panel').css('height', newHeight + 'px');
        $('#output-panel').removeClass('minimized expanded');
    });
    
    $(document).on('mouseup', function() {
        if (isResizing) {
            isResizing = false;
            $('body').css('user-select', '');
            $('body').css('cursor', '');
        }
    });
}

// 绑定工具栏事件
function bindToolbarEvents() {
    // 这些函数将在全局作用域中定义，供HTML调用
}

// 保存工作流
function saveWorkflow() {
    if (!currentWorkflow) {
        alert('没有可保存的工作流');
        return;
    }
    
    const workflowData = {
        name: currentWorkflow.name,
        description: currentWorkflow.description,
        nodes: nodes.get(),
        edges: edges.get()
    };
    
    // 添加调试信息
    console.log('保存工作流数据:');
    console.log('节点数据:', workflowData.nodes);
    workflowData.nodes.forEach(node => {
        if (node.data && node.data.type === 'llm') {
            console.log('LLM节点配置:', node.data.config);
            console.log('LLM节点用户消息:', node.data.config.user_message);
        }
    });
    
    const url = workflowId ? `/api/workflows/${workflowId}` : '/api/workflows';
    const method = workflowId ? 'PUT' : 'POST';
    
    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify(workflowData)
    })
    .done(function(response) {
        if (response.success) {
            showAlert('工作流保存成功', 'success');
            if (!workflowId && response.data && response.data.id) {
                workflowId = response.data.id;
                // 更新URL
                window.history.replaceState({}, '', `/workflow?id=${workflowId}`);
            }
        } else {
            showAlert('保存失败: ' + response.error, 'danger');
        }
    })
    .fail(function() {
        showAlert('网络错误，保存失败', 'danger');
    });
}

// 执行工作流
function executeWorkflow() {
    if (!workflowId) {
        alert('请先保存工作流');
        return;
    }
    
    const inputElement = document.getElementById('workflow-input');
    const input = inputElement.value.trim();
    if (!input) {
        showAlert('请输入执行参数', 'warning');
        return;
    }
    
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
                displayExecutionResults(response.data);
                showAlert('工作流执行成功', 'success');
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

// 加载工作流
function loadWorkflow(id) {
    $.get(`/api/workflows/${id}`)
        .done(function(response) {
            if (response.success) {
                currentWorkflow = response.data;
                
                // 加载节点和边
                if (currentWorkflow.nodes) {
                    nodes.clear();
                    nodes.add(currentWorkflow.nodes);
                }
                
                if (currentWorkflow.edges) {
                    edges.clear();
                    edges.add(currentWorkflow.edges);
                }
                
                // 适应视图
                setTimeout(() => {
                    network.fit();
                }, 100);
                
                // 创建执行历史面板并加载历史
                createExecutionHistoryPanel();
                
                showAlert('工作流加载成功', 'success');
            } else {
                showAlert('加载失败: ' + response.error, 'danger');
            }
        })
        .fail(function() {
            showAlert('网络错误，加载失败', 'danger');
        });
}

// 创建新工作流
function createNewWorkflow() {
    // 如果没有工作流ID，自动创建默认工作流
    if (!workflowId) {
        currentWorkflow = {
            name: '默认workflow',
            description: '默认创建的工作流，包含开始、LLM和结束节点',
            nodes: [],
            edges: []
        };
        
        // 清空画布
        nodes.clear();
        edges.clear();
        
        // 创建默认的三个节点：开始、LLM、结束
        createDefaultWorkflow();
        
        showAlert('默认workflow已创建', 'info');
        return;
    }
    
    // 如果有工作流ID，则弹出提示框创建新工作流
    const name = prompt('请输入工作流名称:', '新工作流');
    if (!name) return;
    
    const description = prompt('请输入工作流描述:', '');
    
    currentWorkflow = {
        name: name,
        description: description || '',
        nodes: [],
        edges: []
    };
    
    // 清空画布
    nodes.clear();
    edges.clear();
    
    // 创建默认的三个节点：开始、LLM、结束
    createDefaultWorkflow();
    
    showAlert('新工作流已创建，包含默认节点', 'info');
}

// 创建默认工作流（开始 -> LLM -> 结束）
function createDefaultWorkflow() {
    // 创建开始节点
    const startNodeId = 'node_' + Date.now();
    const startConfig = getNodeConfig('start');
    const startNode = {
        id: startNodeId,
        label: startConfig.label,
        x: -200,
        y: 0,
        color: startConfig.color,
        font: { color: '#fff' },
        data: {
            type: 'start',
            config: startConfig.defaultConfig
        }
    };
    
    // 创建LLM节点
    const llmNodeId = 'node_' + (Date.now() + 1);
    const llmConfig = getNodeConfig('llm');
    const llmNode = {
        id: llmNodeId,
        label: llmConfig.label,
        x: 0,
        y: 0,
        color: llmConfig.color,
        font: { color: '#fff' },
        data: {
            type: 'llm',
            config: llmConfig.defaultConfig
        }
    };
    
    // 创建结束节点
    const endNodeId = 'node_' + (Date.now() + 2);
    const endConfig = getNodeConfig('end');
    const endNode = {
        id: endNodeId,
        label: endConfig.label,
        x: 200,
        y: 0,
        color: endConfig.color,
        font: { color: '#fff' },
        data: {
            type: 'end',
            config: endConfig.defaultConfig
        }
    };
    
    // 添加节点到画布
    nodes.add([startNode, llmNode, endNode]);
    
    // 创建连接边
    const edge1 = {
        id: 'edge_' + startNodeId + '_' + llmNodeId,
        from: startNodeId,
        to: llmNodeId,
        label: ''
    };
    
    const edge2 = {
        id: 'edge_' + llmNodeId + '_' + endNodeId,
        from: llmNodeId,
        to: endNodeId,
        label: ''
    };
    
    // 添加边到画布
    edges.add([edge1, edge2]);
}

// 新的连接功能
function startConnection(nodeId) {
    isConnecting = true;
    connectionStartNode = nodeId;
    
    // 高亮起始节点
    const node = nodes.get(nodeId);
    if (node) {
        nodes.update({
            id: nodeId,
            borderWidth: 4,
            borderWidthSelected: 4,
            color: {
                ...node.color,
                border: '#ff6b6b'
            }
        });
    }
    
    // 添加鼠标移动监听器来创建动态预览线
    network.on('hoverNode', updateConnectionPreview);
    network.on('dragStart', clearConnectionPreview);
    network.on('dragEnd', restoreConnectionPreview);
    
    showAlert('请选择目标节点完成连接，按ESC取消', 'info');
}

// 更新连接预览
function updateConnectionPreview(params) {
    if (!isConnecting || !connectionStartNode || params.node === connectionStartNode) {
        return;
    }
    
    // 清除之前的预览线
    if (connectionPreview) {
        edges.remove(connectionPreview);
    }
    
    // 创建新的预览线（虚线）
    connectionPreview = {
        id: 'preview_' + Date.now(),
        from: connectionStartNode,
        to: params.node,
        color: {
            color: '#ff6b6b',
            opacity: 0.7
        },
        dashes: [10, 5],
        width: 2,
        smooth: {
            type: 'cubicBezier',
            forceDirection: 'horizontal',
            roundness: 0.4
        },
        arrows: {
            to: {
                enabled: true,
                scaleFactor: 1.2
            }
        },
        physics: false,
        selectable: false
    };
    
    edges.add(connectionPreview);
}

// 清除连接预览（拖动时）
function clearConnectionPreview() {
    if (connectionPreview) {
        edges.remove(connectionPreview);
        connectionPreview = null;
    }
}

// 恢复连接预览（拖动结束后）
function restoreConnectionPreview() {
    if (isConnecting && connectionStartNode) {
        // 延迟一点时间再恢复，确保拖动完成
        setTimeout(() => {
            const hoveredNodes = network.getNodeAt(network.getPointer());
            if (hoveredNodes && hoveredNodes !== connectionStartNode) {
                updateConnectionPreview({ node: hoveredNodes });
            }
        }, 100);
    }
}

function endConnection() {
    if (isConnecting && connectionStartNode) {
        // 恢复起始节点样式
        const startNode = nodes.get(connectionStartNode);
        if (startNode) {
            const nodeConfig = getNodeConfig(startNode.data.type);
            nodes.update({
                id: connectionStartNode,
                borderWidth: 2,
                borderWidthSelected: 4,
                color: nodeConfig.color
            });
        }
    }
    
    // 移除事件监听器
    network.off('hoverNode', updateConnectionPreview);
    network.off('dragStart', clearConnectionPreview);
    network.off('dragEnd', restoreConnectionPreview);
    
    isConnecting = false;
    connectionStartNode = null;
    
    // 清除连接预览
    if (connectionPreview) {
        edges.remove(connectionPreview);
        connectionPreview = null;
    }
}

function createConnection(fromNodeId, toNodeId) {
    if (fromNodeId === toNodeId) {
        showAlert('不能连接到自己', 'warning');
        return false;
    }
    
    // 检查是否已存在连接
    const existingEdges = edges.get();
    const edgeExists = existingEdges.some(edge => 
        edge.from === fromNodeId && edge.to === toNodeId
    );
    
    if (edgeExists) {
        showAlert('连接已存在', 'warning');
        return false;
    }
    
    // 创建新连接（实线）
    const newEdge = {
        id: 'edge_' + Date.now(),
        from: fromNodeId,
        to: toNodeId,
        color: {
            color: '#495057',
            opacity: 1.0
        },
        width: 2,
        smooth: {
            type: 'cubicBezier',
            forceDirection: 'horizontal',
            roundness: 0.4
        },
        arrows: {
            to: {
                enabled: true,
                scaleFactor: 1.2,
                color: '#495057'
            }
        },
        shadow: {
            enabled: true,
            color: 'rgba(0,0,0,0.2)',
            size: 3,
            x: 2,
            y: 2
        },
        physics: true,
        selectable: true
    };
    
    // 保存操作到历史记录
    saveOperationToHistory('addEdge', {
        edge: { ...newEdge }
    });
    
    edges.add(newEdge);
    return true;
}

// 保存操作到历史记录
function saveOperationToHistory(operationType, data) {
    // 如果当前不在历史记录的末尾，删除后面的记录
    if (historyIndex < operationHistory.length - 1) {
        operationHistory = operationHistory.slice(0, historyIndex + 1);
    }
    
    // 添加新操作到历史记录
    operationHistory.push({
        type: operationType,
        data: data,
        timestamp: Date.now()
    });
    
    // 限制历史记录数量
    if (operationHistory.length > MAX_HISTORY) {
        operationHistory.shift();
    } else {
        historyIndex++;
    }
}

// 撤销上一个操作
function undoLastOperation() {
    if (historyIndex < 0 || operationHistory.length === 0) {
        showAlert('没有可撤销的操作', 'warning');
        return;
    }
    
    const operation = operationHistory[historyIndex];
    
    try {
        switch (operation.type) {
            case 'addEdge':
                // 撤销添加连接：删除连接
                const edgeToRemove = operation.data.edge;
                edges.remove(edgeToRemove.id);
                showAlert('已撤销添加连接', 'info');
                break;
                
            case 'deleteEdge':
                // 撤销删除连接：恢复连接
                const edgesToRestore = operation.data.edges;
                edges.add(edgesToRestore);
                showAlert(`已撤销删除 ${edgesToRestore.length} 条连接线`, 'info');
                break;
                
            default:
                showAlert('不支持撤销此操作', 'warning');
                return;
        }
        
        historyIndex--;
    } catch (error) {
        console.error('撤销操作失败:', error);
        showAlert('撤销操作失败', 'danger');
    }
}

// 显示提示信息
function showAlert(message, type) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show position-fixed" style="top: 70px; right: 20px; z-index: 9999;" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    $('body').append(alertHtml);
    
    // 3秒后自动消失
    setTimeout(() => {
        $('.alert').alert('close');
    }, 3000);
}

// 切换连接模式
function toggleConnectionMode() {
    connectionMode = !connectionMode;
    const btn = document.getElementById('connection-mode-btn');
    
    if (connectionMode) {
        btn.classList.remove('btn-outline-light');
        btn.classList.add('btn-light');
        btn.innerHTML = '<i class="bi bi-arrow-left-right"></i> 连接模式 (开启)';
        showAlert('连接模式已开启，点击两个节点进行连接', 'info');
        
        // 如果当前有连接正在进行，取消它
        if (isConnecting) {
            endConnection();
        }
        
        // 隐藏属性面板
        hideNodeProperties();
        selectedNode = null;
    } else {
        btn.classList.remove('btn-light');
        btn.classList.add('btn-outline-light');
        btn.innerHTML = '<i class="bi bi-arrow-left-right"></i> 连接模式';
        showAlert('连接模式已关闭', 'info');
        
        // 如果当前有连接正在进行，取消它
        if (isConnecting) {
            endConnection();
        }
    }
}