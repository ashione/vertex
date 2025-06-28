# Docker Makefile
# 简化Docker操作的Makefile

.PHONY: help build build-dev push run run-dev clean logs

# 默认目标
help:
	@echo "Docker 操作命令:"
	@echo "  build      - 构建生产镜像（轻量级，不包含RAG等需要编译的功能）"
	@echo "  build-dev  - 构建开发镜像"
	@echo "  push       - 推送到ACR (需要设置ACR_REGISTRY)"
	@echo "  run        - 运行生产容器"
	@echo "  run-dev    - 运行开发容器"
	@echo "  clean      - 清理镜像和容器"
	@echo "  logs       - 查看容器日志"
	@echo ""
	@echo "环境变量:"
	@echo "  ACR_REGISTRY - 阿里云ACR注册表地址"
	@echo "  IMAGE_NAME   - 镜像名称 (默认: vertex)"
	@echo ""
	@echo "镜像说明:"
	@echo "  - 生产镜像: 轻量级版本，仅包含基础功能，不包含需要编译的依赖"
	@echo "  - 开发镜像: 支持热重载，包含开发工具"
	@echo ""
	@echo "注意: 当前Docker镜像不包含以下功能（需要编译的依赖）:"
	@echo "  - RAG系统 (faiss-cpu, sentence-transformers)"
	@echo "  - 云端向量存储 (dashvector)"

# 构建whl包
wheel:
	mkdir -p ./dist
	cd .. && python -m pip install build && python -m build
	cp ../dist/vertex-0.1.0-py3-none-any.whl ./dist/

# 构建生产镜像（轻量级，不包含需要编译的依赖）
build: wheel
	@echo "构建生产镜像（轻量级，不包含RAG等需要编译的功能）..."
	./build.sh --no-push

# 构建开发镜像
build-dev:
	@echo "构建开发镜像..."
	docker build -f Dockerfile.dev -t vertex:dev .

# 推送到ACR
push:
	@if [ -z "$(ACR_REGISTRY)" ]; then \
		echo "错误: 请设置ACR_REGISTRY环境变量"; \
		echo "例如: make push ACR_REGISTRY=registry.cn-hangzhou.aliyuncs.com/your-namespace"; \
		exit 1; \
	fi
	@echo "推送到ACR: $(ACR_REGISTRY)"
	./build.sh -r $(ACR_REGISTRY)

# 运行生产容器
run:
	@echo "运行生产容器..."
	@if [ -z "$$(docker images -q vertex:dockerize 2>/dev/null)" ]; then \
		echo "错误: 镜像不存在，请先运行 'make build' 构建镜像"; \
		exit 1; \
	fi
	docker run -d --name vertex-app \
		-p 7860:7860 \
		-v $(PWD)/../config:/app/config:ro \
		-v $(PWD)/../vertex_flow/config:/app/vertex_flow/config:ro \
		vertex:dockerize

# 运行开发容器
run-dev:
	@echo "运行开发容器..."
	@if [ -z "$$(docker images -q vertex:dev 2>/dev/null)" ]; then \
		echo "错误: 开发镜像不存在，请先运行 'make build-dev' 构建开发镜像"; \
		exit 1; \
	fi
	docker run -d --name vertex-dev \
		-p 7861:7860 \
		-v $(PWD)/../vertex_flow:/app/vertex_flow \
		-v $(PWD)/../config:/app/config:ro \
		-v $(PWD)/../vertex_flow/config:/app/vertex_flow/config:ro \
		vertex:dev

# 使用Docker Compose运行
compose-up:
	@echo "使用Docker Compose启动服务..."
	docker-compose -f docker-compose.yml up -d

compose-up-dev:
	@echo "使用Docker Compose启动开发环境..."
	docker-compose -f docker-compose.yml --profile dev up -d

compose-down:
	@echo "停止Docker Compose服务..."
	docker-compose -f docker-compose.yml down

compose-logs:
	@echo "查看Docker Compose日志..."
	docker-compose -f docker-compose.yml logs -f

# 查看容器日志
logs:
	@echo "查看容器日志..."
	@if docker ps -q -f name=vertex-app | grep -q .; then \
		docker logs -f vertex-app; \
	elif docker ps -q -f name=vertex-dev | grep -q .; then \
		docker logs -f vertex-dev; \
	else \
		echo "没有找到运行中的vertex容器"; \
	fi

# 清理镜像和容器
clean:
	@echo "清理Docker资源..."
	@docker stop vertex-app vertex-dev 2>/dev/null || true
	@docker rm vertex-app vertex-dev 2>/dev/null || true
	@docker rmi vertex:dockerize vertex:dev 2>/dev/null || true
	@docker rmi $$(docker images -q vertex 2>/dev/null) 2>/dev/null || true
	@echo "清理完成"

# 进入容器
shell:
	@if docker ps -q -f name=vertex-app | grep -q .; then \
		docker exec -it vertex-app /bin/bash; \
	elif docker ps -q -f name=vertex-dev | grep -q .; then \
		docker exec -it vertex-dev /bin/bash; \
	else \
		echo "没有找到运行中的vertex容器"; \
	fi

# 查看容器状态
status:
	@echo "Docker容器状态:"
	@docker ps -a --filter name=vertex

# 测试镜像
test:
	@echo "测试生产镜像..."
	@docker run --rm vertex:dockerize python -c "import vertex_flow; print('✅ 生产镜像测试通过')"

test-dev:
	@echo "测试开发镜像..."
	@docker run --rm vertex:dev python -c "import vertex_flow; print('✅ 开发镜像测试通过')"

# 显示镜像信息
info:
	@echo "镜像信息:"
	@docker images | grep vertex

# 比较镜像大小
size:
	@echo "镜像大小比较:"
	@docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep vertex 