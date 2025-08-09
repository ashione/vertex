#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号插件主入口
"""

import argparse
import logging
import sys

import uvicorn

from wechat_plugin.config import config
from wechat_plugin.wechat_server import app

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/wechat_plugin.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='微信公众号插件 for Vertex Flow')
    parser.add_argument('--host', default=config.server_host, help='服务器地址')
    parser.add_argument('--port', type=int, default=config.server_port, help='服务器端口')
    parser.add_argument('--reload', action='store_true', help='启用热重载（开发模式）')
    parser.add_argument('--log-level', default=config.log_level, help='日志级别')
    
    args = parser.parse_args()
    
    # 验证配置
    is_valid, error_msg = config.validate()
    if not is_valid:
        logger.error(f"配置验证失败: {error_msg}")
        logger.error("请检查环境变量配置")
        sys.exit(1)
    
    logger.info("启动微信公众号插件...")
    logger.info(f"服务器地址: {args.host}:{args.port}")
    logger.info(f"Webhook URL: {config.get_webhook_url()}")
    
    try:
        # 启动服务器
        uvicorn.run(
            "wechat_plugin.wechat_server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器启动失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()