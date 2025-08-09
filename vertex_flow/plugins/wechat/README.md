# 微信公众号插件 for Vertex Flow

这个插件允许用户通过微信公众号与部署在Google Cloud上的Vertex Flow聊天应用进行交互。

## 功能特性

- ✅ 微信公众号消息接收和验证
- ✅ 与Vertex Flow Chat API无缝集成
- ✅ 支持文本消息处理
- ✅ 支持图片消息处理（多模态）
- ✅ 用户会话管理
- ✅ MCP功能支持
- ✅ 搜索功能集成
- ✅ 推理功能支持
- ✅ 健康检查和监控
- ✅ 支持Serverless部署

## 快速开始

### 1. 环境配置

复制环境变量模板并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要的配置：

```bash
# 微信公众号Token（必填）
WECHAT_TOKEN=your_wechat_token_here

# Vertex Flow API地址（必填）
VERTEX_FLOW_API_URL=https://your-vertex-flow-api.com
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动服务

```bash
# 开发模式
python -m vertex_flow.plugins.wechat.main --reload

# 生产模式
python -m vertex_flow.plugins.wechat.main --host 0.0.0.0 --port 8001
```

### 4. 配置微信公众号

1. 登录微信公众平台
2. 进入「开发」->「基本配置」
3. 设置服务器地址为：`https://your-domain.com/wechat`
4. 设置Token为环境变量中的 `WECHAT_TOKEN`
5. 选择消息加解密方式为「明文模式」
6. 提交配置并启用

## API接口

### 微信Webhook

- **GET /wechat** - 微信服务器验证
- **POST /wechat** - 接收微信消息

### 健康检查

- **GET /health** - 服务健康状态检查
- **GET /** - 服务基本信息

## 配置说明

### 必填配置

| 环境变量 | 说明 | 示例 |
|---------|------|------|
| `WECHAT_TOKEN` | 微信公众号Token | `your_token_123` |
| `VERTEX_FLOW_API_URL` | Vertex Flow API地址 | `https://api.example.com` |

### 可选配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `DEFAULT_WORKFLOW` | `default_chat` | 默认工作流名称 |
| `SERVER_HOST` | `0.0.0.0` | 服务器监听地址 |
| `SERVER_PORT` | `8001` | 服务器监听端口 |
| `ENABLE_MCP` | `true` | 启用MCP功能 |
| `ENABLE_SEARCH` | `true` | 启用搜索功能 |
| `ENABLE_MULTIMODAL` | `true` | 启用多模态功能 |
| `ENABLE_REASONING` | `false` | 启用推理功能 |
| `MAX_MESSAGE_LENGTH` | `2000` | 最大消息长度 |
| `SESSION_TIMEOUT` | `3600` | 会话超时时间（秒） |
| `LOG_LEVEL` | `INFO` | 日志级别 |

## 部署方式

### 本地部署

```bash
# 直接运行
python -m wechat_plugin.main

# 使用uvicorn
uvicorn wechat_plugin.wechat_server:app --host 0.0.0.0 --port 8001
```

### Docker独立部署

#### 快速启动

```bash
# 使用启动脚本（推荐）
./start.sh start

# 查看服务状态
./start.sh status

# 查看日志
./start.sh logs

# 停止服务
./start.sh stop
```

#### 手动Docker部署

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑.env文件，设置WECHAT_TOKEN和VERTEX_FLOW_API_URL

# 2. 构建镜像
docker build -t wechat-plugin .

# 3. 运行容器
docker run -d \
  --name wechat-plugin \
  -p 8001:8001 \
  --env-file .env \
  wechat-plugin

# 4. 查看日志
docker logs -f wechat-plugin
```



### Serverless部署

支持多种Serverless平台：

- **Google Cloud Run** - 参考 `serverless/cloudrun/`
- **阿里云SAE** - 参考 `serverless/sae/`
- **AWS Lambda** - 使用 `serverless.yml`
- **腾讯云SCF** - 使用 `serverless_handler.py`

详细部署说明请参考 `serverless/README.md`。

## 使用示例

### 基本对话

用户在微信公众号发送：
```
你好，请介绍一下Vertex Flow
```

插件会调用Vertex Flow API，返回AI生成的回复。

### 图片分析

用户发送图片，插件会自动调用多模态功能分析图片内容。

### 搜索功能

用户询问实时信息时，插件会自动启用搜索功能获取最新信息。

## 监控和日志

### 健康检查

```bash
curl http://localhost:8001/health
```

返回示例：
```json
{
  "status": "ok",
  "message": "微信公众号插件运行正常",
  "config": {
    "wechat_token_set": true,
    "vertex_flow_api_url": "https://api.example.com",
    "webhook_url": "https://your-domain.com/wechat",
    "features": {
      "mcp": true,
      "search": true,
      "multimodal": true,
      "reasoning": false
    }
  }
}
```

### 日志文件

日志文件位置：`logs/wechat_plugin.log`

## 故障排除

### 常见问题

1. **微信验证失败**
   - 检查 `WECHAT_TOKEN` 是否正确
   - 确认服务器地址可以被微信访问
   - 检查防火墙和端口配置

2. **API调用失败**
   - 检查 `VERTEX_FLOW_API_URL` 是否正确
   - 确认Vertex Flow服务正常运行
   - 检查网络连接

3. **消息处理超时**
   - 检查Vertex Flow API响应时间
   - 调整超时配置
   - 检查服务器资源使用情况

### 调试模式

```bash
# 启用调试日志
export LOG_LEVEL=DEBUG
python -m vertex_flow.plugins.wechat.main --reload
```

## 安全建议

1. **使用HTTPS**：生产环境必须使用HTTPS
2. **Token安全**：妥善保管微信Token，不要泄露
3. **API安全**：确保Vertex Flow API有适当的访问控制
4. **日志安全**：避免在日志中记录敏感信息
5. **网络安全**：使用防火墙限制不必要的网络访问

## 开发指南

### 项目结构

```
wechat/
├── __init__.py              # 包初始化
├── main.py                  # 主入口文件
├── config.py                # 配置管理
├── wechat_handler.py        # 微信消息处理
├── message_processor.py     # 消息处理器
├── wechat_server.py         # FastAPI服务器
├── requirements.txt         # 依赖列表
├── .env.example            # 环境变量模板
├── serverless_handler.py   # Serverless适配器
└── serverless/             # Serverless部署配置
    ├── README.md
    ├── cloudrun/
    └── sae/
```

### 扩展功能

要添加新功能，可以：

1. 在 `message_processor.py` 中添加新的消息处理逻辑
2. 在 `wechat_handler.py` 中添加新的消息类型支持
3. 在 `config.py` 中添加新的配置选项
4. 更新 `requirements.txt` 添加新的依赖

## 许可证

本项目采用 MIT 许可证。