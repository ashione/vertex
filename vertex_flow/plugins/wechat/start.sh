#!/bin/bash

# 微信公众号插件启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        exit 1
    fi
}

# 检查环境变量文件
check_env_file() {
    if [ ! -f ".env" ]; then
        print_warning "未找到.env文件，正在创建..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_info "已从.env.example创建.env文件，请编辑.env文件设置必要的环境变量"
        else
            print_error "未找到.env.example文件"
            exit 1
        fi
    fi
}

# 验证必要的环境变量
validate_env() {
    source .env
    
    if [ -z "$WECHAT_TOKEN" ]; then
        print_error "WECHAT_TOKEN未设置，请在.env文件中设置"
        exit 1
    fi
    
    if [ -z "$VERTEX_FLOW_API_URL" ]; then
        print_error "VERTEX_FLOW_API_URL未设置，请在.env文件中设置"
        exit 1
    fi
    
    print_success "环境变量验证通过"
}

# 构建Docker镜像
build_image() {
    print_info "正在构建Docker镜像..."
    docker build -t wechat-plugin .
    print_success "Docker镜像构建完成"
}

# 启动服务
start_service() {
    print_info "正在启动微信公众号插件服务..."
    
    # 停止已存在的容器
    docker stop wechat-plugin 2>/dev/null || true
    docker rm wechat-plugin 2>/dev/null || true
    
    # 启动新容器
    docker run -d \
        --name wechat-plugin \
        --env-file .env \
        -p 8001:8001 \
        -v "$(pwd)/logs:/app/logs" \
        --restart unless-stopped \
        wechat-plugin
    
    print_success "服务启动完成"
}

# 停止服务
stop_service() {
    print_info "正在停止服务..."
    docker stop wechat-plugin 2>/dev/null || true
    docker rm wechat-plugin 2>/dev/null || true
    print_success "服务已停止"
}

# 查看服务状态
status_service() {
    print_info "服务状态:"
    if docker ps | grep -q wechat-plugin; then
        print_success "服务正在运行"
        docker ps --filter name=wechat-plugin --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        print_warning "服务未运行"
    fi
}

# 查看日志
view_logs() {
    print_info "查看服务日志:"
    docker logs -f wechat-plugin
}

# 健康检查
health_check() {
    print_info "正在进行健康检查..."
    
    # 等待服务启动
    sleep 5
    
    if curl -f http://localhost:8001/health > /dev/null 2>&1; then
        print_success "健康检查通过，服务运行正常"
        print_info "服务地址: http://localhost:8001"
        print_info "健康检查: http://localhost:8001/health"
        print_info "微信Webhook: http://localhost:8001/wechat"
    else
        print_error "健康检查失败，请检查服务状态"
        print_info "查看日志: $0 logs"
    fi
}

# 显示帮助信息
show_help() {
    echo "微信公众号插件启动脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start    - 启动服务（默认）"
    echo "  stop     - 停止服务"
    echo "  restart  - 重启服务"
    echo "  status   - 查看服务状态"
    echo "  logs     - 查看服务日志"
    echo "  build    - 重新构建镜像"
    echo "  health   - 健康检查"
    echo "  help     - 显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start    # 启动服务"
    echo "  $0 logs     # 查看日志"
    echo "  $0 health   # 健康检查"
}

# 主函数
main() {
    local command=${1:-start}
    
    case $command in
        "start")
            check_docker
            check_env_file
            validate_env
            build_image
            start_service
            health_check
            ;;
        "stop")
            check_docker
            stop_service
            ;;
        "restart")
            check_docker
            stop_service
            check_env_file
            validate_env
            build_image
            start_service
            health_check
            ;;
        "status")
            check_docker
            status_service
            ;;
        "logs")
            check_docker
            view_logs
            ;;
        "build")
            check_docker
            build_image
            ;;
        "health")
            health_check
            ;;
        "help")
            show_help
            ;;
        *)
            print_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"