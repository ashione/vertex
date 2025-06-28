#!/bin/bash

# Docker构建脚本
# 支持按branch-commitid命名，并推送到阿里云ACR

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 获取Git信息
get_git_info() {
    # 获取当前分支名
    BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
    
    # 获取当前commit ID（短格式）
    COMMIT_ID=$(git rev-parse --short HEAD)
    
    # 获取完整commit ID
    FULL_COMMIT_ID=$(git rev-parse HEAD)
    
    # 获取标签（如果有）
    TAG=$(git describe --tags --exact-match 2>/dev/null || echo "")
    
    echo "Branch: $BRANCH_NAME"
    echo "Commit ID: $COMMIT_ID"
    echo "Full Commit ID: $FULL_COMMIT_ID"
    echo "Tag: $TAG"
}

# 生成镜像标签
generate_image_tags() {
    local base_name="$1"
    local branch_name="$2"
    local commit_id="$3"
    local tag="$4"
    
    # 生成标签列表
    local tags=()
    
    # 如果有标签，优先使用tag name
    if [ -n "$tag" ]; then
        tags+=("$base_name:$tag")
        tags+=("$base_name:latest")
    else
        # 清理分支名（替换特殊字符，只保留字母数字和连字符）
        local clean_branch=$(echo "$branch_name" | sed 's/[^a-zA-Z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
        
        # 如果清理后的分支名为空，使用默认值
        if [ -z "$clean_branch" ]; then
            clean_branch="unknown"
        fi
        
        # 分支-commit标签
        tags+=("$base_name:$clean_branch-$commit_id")
        tags+=("$base_name:latest")
    fi
    
    echo "${tags[@]}"
}

# 构建Docker镜像
build_image() {
    local dockerfile_path="$1"
    local tags=("${@:2}")
    
    print_info "开始构建Docker镜像..."
    
    # 构建基础命令 - 使用项目根目录作为构建上下文
    local build_cmd="docker build -f $dockerfile_path .."
    
    # 添加所有标签
    for tag in "${tags[@]}"; do
        build_cmd="$build_cmd -t $tag"
    done
    
    print_info "执行命令: $build_cmd"
    
    # 执行构建
    if eval "$build_cmd"; then
        print_success "Docker镜像构建成功"
        return 0
    else
        print_error "Docker镜像构建失败"
        return 1
    fi
}

# 推送到阿里云ACR
push_to_acr() {
    local registry="$1"
    local tags=("${@:2}")
    
    print_info "开始推送到阿里云ACR: $registry"
    
    # 登录ACR
    print_info "登录阿里云ACR..."
    if ! docker login "$registry"; then
        print_error "ACR登录失败"
        return 1
    fi
    
    # 推送所有标签
    for tag in "${tags[@]}"; do
        local acr_tag="$registry/$tag"
        print_info "推送镜像: $tag -> $acr_tag"
        
        # 重新标记镜像
        docker tag "$tag" "$acr_tag"
        
        # 推送镜像
        if docker push "$acr_tag"; then
            print_success "成功推送: $acr_tag"
        else
            print_error "推送失败: $acr_tag"
            return 1
        fi
    done
    
    print_success "所有镜像推送完成"
}

# 显示帮助信息
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help             显示帮助信息"
    echo "  -r, --registry REGISTRY 阿里云ACR注册表地址"
    echo "  -n, --name NAME         镜像名称 (默认: vertex)"
    echo "  -f, --file FILE         Dockerfile路径 (默认: Dockerfile)"
    echo "  --no-push              不推送到ACR"
    echo "  --no-build             不构建镜像（仅推送）"
    echo ""
    echo "Examples:"
    echo "  $0 -r registry.cn-hangzhou.aliyuncs.com/your-namespace"
    echo "  $0 -r registry.cn-hangzhou.aliyuncs.com/your-namespace -n myapp"
    echo "  $0 --no-push  # 仅构建，不推送"
    echo "  $0 --no-build -r registry.cn-hangzhou.aliyuncs.com/your-namespace  # 仅推送"
}

# 主函数
main() {
    # 默认参数
    REGISTRY=""
    IMAGE_NAME="vertex"
    DOCKERFILE="Dockerfile"
    DO_BUILD=true
    DO_PUSH=true
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -n|--name)
                IMAGE_NAME="$2"
                shift 2
                ;;
            -f|--file)
                DOCKERFILE="$2"
                shift 2
                ;;
            --no-push)
                DO_PUSH=false
                shift
                ;;
            --no-build)
                DO_BUILD=false
                shift
                ;;
            *)
                print_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 检查Dockerfile是否存在
    if [ ! -f "$DOCKERFILE" ]; then
        print_error "Dockerfile不存在: $DOCKERFILE"
        exit 1
    fi
    
    # 获取Git信息
    print_info "获取Git信息..."
    get_git_info
    
    # 解析Git信息
    BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
    COMMIT_ID=$(git rev-parse --short HEAD)
    TAG=$(git describe --tags --exact-match 2>/dev/null || echo "")
    
    # 生成镜像标签
    print_info "生成镜像标签..."
    TAGS=($(generate_image_tags "$IMAGE_NAME" "$BRANCH_NAME" "$COMMIT_ID" "$TAG"))
    
    print_info "镜像标签:"
    for tag in "${TAGS[@]}"; do
        echo "  - $tag"
    done
    
    # 构建镜像
    if [ "$DO_BUILD" = true ]; then
        if ! build_image "$DOCKERFILE" "${TAGS[@]}"; then
            exit 1
        fi
    fi
    
    # 推送到ACR
    if [ "$DO_PUSH" = true ]; then
        if [ -z "$REGISTRY" ]; then
            print_warning "未指定ACR注册表地址，跳过推送"
            print_info "使用 -r 参数指定ACR注册表地址"
        else
            if ! push_to_acr "$REGISTRY" "${TAGS[@]}"; then
                exit 1
            fi
        fi
    fi
    
    print_success "Docker操作完成！"
    
    # 显示最终结果
    echo ""
    print_info "构建的镜像标签:"
    for tag in "${TAGS[@]}"; do
        echo "  - $tag"
        if [ -n "$REGISTRY" ] && [ "$DO_PUSH" = true ]; then
            echo "    -> $REGISTRY/$tag"
        fi
    done
}

# 执行主函数
main "$@" 