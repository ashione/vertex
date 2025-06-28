# Docker 部署指南

本项目提供了完整的Docker化支持，包括本地开发、测试和生产部署。

## 目录结构

```
docker/
├── Dockerfile          # 主Dockerfile
├── .dockerignore       # Docker忽略文件
├── build.sh           # 构建脚本
├── docker-compose.yml # Docker Compose配置
└── README.md          # 本文档
```

## 快速开始

### 1. 本地构建和运行

```bash
# 构建镜像
docker build -f docker/Dockerfile -t vertex:latest .

# 运行容器
docker run -p 7860:7860 vertex:latest
```

### 2. 使用Docker Compose

```bash
# 启动生产环境
docker-compose -f docker/docker-compose.yml up -d

# 启动开发环境
docker-compose -f docker/docker-compose.yml --profile dev up -d

# 查看日志
docker-compose -f docker/docker-compose.yml logs -f

# 停止服务
docker-compose -f docker/docker-compose.yml down
```

### 3. 使用构建脚本

```bash
# 给脚本执行权限
chmod +x docker/build.sh

# 仅构建镜像（不推送）
./docker/build.sh --no-push

# 构建并推送到阿里云ACR
./docker/build.sh -r registry.cn-hangzhou.aliyuncs.com/your-namespace

# 指定镜像名称
./docker/build.sh -r registry.cn-hangzhou.aliyuncs.com/your-namespace -n myapp
```

## 构建脚本功能

### 自动标签生成

构建脚本会根据Git信息自动生成以下标签：

- `vertex:latest` - 最新版本（仅在有Git标签时）
- `vertex:v1.0.0` - 版本标签（如果有Git标签）
- `vertex:main-abc1234` - 分支-commit标签
- `vertex:main` - 分支标签
- `vertex:abc1234` - commit标签

### 支持的参数

```bash
./docker/build.sh [OPTIONS]

Options:
  -h, --help             显示帮助信息
  -r, --registry REGISTRY 阿里云ACR注册表地址
  -n, --name NAME         镜像名称 (默认: vertex)
  -f, --file FILE         Dockerfile路径 (默认: docker/Dockerfile)
  --no-push              不推送到ACR
  --no-build             不构建镜像（仅推送）
```

## 阿里云ACR配置

### 1. 创建ACR实例

1. 登录阿里云控制台
2. 进入容器镜像服务ACR
3. 创建命名空间和镜像仓库

### 2. 配置访问凭证

```bash
# 登录ACR
docker login registry.cn-hangzhou.aliyuncs.com

# 输入用户名和密码（在ACR控制台获取）
```

### 3. 推送镜像

```bash
# 使用构建脚本自动推送
./docker/build.sh -r registry.cn-hangzhou.aliyuncs.com/your-namespace/your-repo

# 手动推送
docker tag vertex:latest registry.cn-hangzhou.aliyuncs.com/your-namespace/your-repo:latest
docker push registry.cn-hangzhou.aliyuncs.com/your-namespace/your-repo:latest
```

## CI/CD集成

### GitHub Actions

在`.github/workflows/`目录下创建Docker构建工作流：

```yaml
name: Docker Build and Push

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to Aliyun ACR
      uses: docker/login-action@v3
      with:
        registry: registry.cn-hangzhou.aliyuncs.com
        username: ${{ secrets.ACR_USERNAME }}
        password: ${{ secrets.ACR_PASSWORD }}
    
    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./docker/Dockerfile
        push: true
        tags: |
          registry.cn-hangzhou.aliyuncs.com/your-namespace/vertex:${{ github.sha }}
          registry.cn-hangzhou.aliyuncs.com/your-namespace/vertex:${{ github.ref_name }}-${{ github.sha }}
          registry.cn-hangzhou.aliyuncs.com/your-namespace/vertex:${{ github.ref_name }}
```

### 环境变量配置

在GitHub仓库的Settings > Secrets中添加：

- `ACR_USERNAME`: 阿里云ACR用户名
- `ACR_PASSWORD`: 阿里云ACR密码

## 配置文件管理

### 开发环境

```bash
# 挂载本地配置文件
docker run -v $(pwd)/config:/app/config:ro -p 7860:7860 vertex:latest
```

### 生产环境

```bash
# 使用环境变量
docker run -e CONFIG_FILE=/app/config/llm.yml -p 7860:7860 vertex:latest

# 或使用配置文件
docker run -v /path/to/config:/app/config:ro -p 7860:7860 vertex:latest
```

## 多阶段构建（可选）

如果需要更小的镜像，可以使用多阶段构建：

```dockerfile
# 构建阶段
FROM python:3.12-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# 运行阶段
FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY vertex_flow/ ./vertex_flow/

ENV PATH=/root/.local/bin:$PATH
CMD ["python", "-m", "vertex_flow.cli"]
```

## 故障排除

### 常见问题

1. **构建失败**
   ```bash
   # 检查Dockerfile语法
   docker build --no-cache -f docker/Dockerfile .
   ```

2. **推送失败**
   ```bash
   # 检查ACR登录状态
   docker login registry.cn-hangzhou.aliyuncs.com
   ```

3. **容器启动失败**
   ```bash
   # 查看容器日志
   docker logs <container_id>
   
   # 进入容器调试
   docker exec -it <container_id> /bin/bash
   ```

### 性能优化

1. **使用.dockerignore**：减少构建上下文大小
2. **多阶段构建**：减少最终镜像大小
3. **缓存优化**：合理使用Docker层缓存

## 安全建议

1. **使用非root用户**：Dockerfile中已配置
2. **最小化镜像**：使用slim版本基础镜像
3. **扫描漏洞**：定期扫描镜像安全漏洞
4. **更新依赖**：定期更新基础镜像和依赖包

## 监控和日志

```bash
# 查看容器资源使用
docker stats

# 查看容器日志
docker logs -f <container_id>

# 健康检查
curl http://localhost:7860/health
``` 