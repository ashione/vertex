#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桌面端应用封装器
使用PyWebView封装Gradio应用，提供原生桌面体验
"""

import os
import sys
import threading
import time
from typing import Optional

try:
    import webview

    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False
    print("警告: PyWebView未安装，桌面端功能不可用")
    print("安装命令: uv add pywebview")

from vertex_flow.utils.logger import setup_logger

logger = setup_logger(__name__)


class DesktopApp:
    """桌面端应用封装器"""

    def __init__(self, config_path: Optional[str] = None, app_type: str = "deep_research"):
        """初始化桌面应用"""
        if not WEBVIEW_AVAILABLE:
            raise ImportError("PyWebView未安装，无法启动桌面端应用")

        self.config_path = config_path
        self.app_type = app_type
        self.app = None
        self.gradio_app = None
        self.webview_window = None
        self.server_thread = None
        self.server_url = None

    def _start_gradio_server(self, host: str = "127.0.0.1", port: int = 7860):
        """在后台线程中启动Gradio服务器"""
        try:
            if self.app_type == "deep_research":
                # 启动Deep Research应用
                from vertex_flow.src.deep_research_app import DeepResearchApp, create_gradio_interface

                self.app = DeepResearchApp(self.config_path)
                self.gradio_app = create_gradio_interface(self.app)
            elif self.app_type == "workflow_app":
                # 启动Workflow应用
                from vertex_flow.src.workflow_app import WorkflowChatApp, create_gradio_interface

                self.app = WorkflowChatApp(self.config_path)
                self.gradio_app = create_gradio_interface(self.app)
            else:
                raise ValueError(f"不支持的应用类型: {self.app_type}")

            # 启动Gradio服务器
            self.server_url = f"http://{host}:{port}"
            logger.info(f"启动Gradio服务器: {self.server_url}")

            # 在后台线程中启动服务器
            self.gradio_app.launch(
                server_name=host,
                server_port=port,
                share=False,  # 桌面端不需要分享
                debug=False,  # 桌面端不需要调试模式
                show_error=False,  # 不显示错误页面
                quiet=True,  # 静默模式
                inbrowser=False,  # 不自动打开浏览器
                prevent_thread_lock=True,  # 防止线程锁定
            )

        except Exception as e:
            logger.error(f"启动Gradio服务器失败: {e}")
            raise

    def start_desktop_app(
        self,
        host: str = "127.0.0.1",
        port: int = 7860,
        window_title: str = "Vertex - AI工作流系统",
        window_width: int = 1200,
        window_height: int = 800,
    ):
        """启动桌面应用"""
        try:
            # 启动Gradio服务器
            self.server_thread = threading.Thread(target=self._start_gradio_server, args=(host, port), daemon=True)
            self.server_thread.start()

            # 等待服务器启动
            logger.info("等待Gradio服务器启动...")
            time.sleep(3)  # 给服务器一些启动时间

            # 创建PyWebView窗口
            logger.info("创建桌面窗口...")
            self.webview_window = webview.create_window(
                title=window_title,
                url=self.server_url,
                width=window_width,
                height=window_height,
                resizable=True,
                text_select=True,
                confirm_close=False,
                background_color="#ffffff",
            )

            # 启动桌面应用
            logger.info("启动桌面应用...")
            webview.start(debug=False, gui="cef")  # 使用CEF作为后端

        except Exception as e:
            logger.error(f"启动桌面应用失败: {e}")
            raise

    def stop_desktop_app(self):
        """停止桌面应用"""
        try:
            if self.webview_window:
                self.webview_window.destroy()
            if self.gradio_app:
                # 尝试停止Gradio服务器
                try:
                    self.gradio_app.close()
                except:
                    pass
            logger.info("桌面应用已停止")
        except Exception as e:
            logger.error(f"停止桌面应用失败: {e}")


def create_desktop_app(
    config_path: Optional[str] = None,
    host: str = "127.0.0.1",
    port: int = 7860,
    window_title: str = "Vertex - AI工作流系统",
    window_width: int = 1200,
    window_height: int = 800,
    app_type: str = "deep_research",
) -> DesktopApp:
    """创建并启动桌面应用"""
    desktop_app = DesktopApp(config_path, app_type)
    desktop_app.start_desktop_app(host, port, window_title, window_width, window_height)
    return desktop_app


def main():
    """主函数 - 用于直接运行桌面应用"""
    import argparse

    parser = argparse.ArgumentParser(description="Vertex Desktop App")
    parser.add_argument("--host", default="127.0.0.1", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=7860, help="服务器端口")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--title", default="Vertex - AI工作流系统", help="窗口标题")
    parser.add_argument("--width", type=int, default=1200, help="窗口宽度")
    parser.add_argument("--height", type=int, default=800, help="窗口高度")
    parser.add_argument(
        "--app-type", choices=["deep_research", "workflow_app"], default="deep_research", help="应用类型"
    )

    args = parser.parse_args()

    try:
        if not WEBVIEW_AVAILABLE:
            print("❌ PyWebView未安装")
            print("请运行: uv add pywebview")
            sys.exit(1)

        print(f"🚀 启动Vertex桌面应用 ({args.app_type})...")
        desktop_app = create_desktop_app(
            config_path=args.config,
            host=args.host,
            port=args.port,
            window_title=args.title,
            window_width=args.width,
            window_height=args.height,
            app_type=args.app_type,
        )

    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
