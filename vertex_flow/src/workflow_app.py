#!/usr/bin/env python3
"""
基于 Workflow LLM Vertex 的主应用入口
使用统一配置系统和 LLM Vertex 实现聊天功能
"""

import argparse
from typing import List, Tuple

import gradio as gr

from vertex_flow.utils.logger import setup_logger
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.constants import SYSTEM, USER, ENABLE_STREAM
from vertex_flow.workflow.workflow import WorkflowContext

# 配置日志
logger = setup_logger(__name__)


class WorkflowChatApp:
    """基于 Workflow LLM Vertex 的聊天应用"""
    
    def __init__(self):
        """初始化应用"""
        self.service = VertexFlowService()
        self.llm_model = None
        self.context = WorkflowContext()
        self.tools_enabled = False
        self.available_tools = []
        self._initialize_llm()
        self._initialize_tools()
        
    def _initialize_llm(self):
        """初始化 LLM 模型和 Vertex"""
        try:
            # 获取聊天模型
            self.llm_model = self.service.get_chatmodel()
            if self.llm_model is None:
                raise ValueError("无法获取聊天模型，请检查配置文件")
            
            # 安全获取模型名称
            try:
                model_name = self.llm_model.model_name()
            except:
                model_name = str(self.llm_model)
            
            logger.info(f"成功初始化聊天模型: {model_name}")
            
        except Exception as e:
            logger.error(f"初始化 LLM 失败: {e}")
            raise
    
    def _initialize_tools(self):
        """初始化可用的工具"""
        try:
            # 初始化命令行工具
            command_line_tool = self.service.get_command_line_tool()
            self.available_tools.append(command_line_tool)
            
            # 可以添加其他工具
            # web_search_tool = self.service.get_web_search_tool()
            # self.available_tools.append(web_search_tool)
            
            # finance_tool = self.service.get_finance_tool()
            # self.available_tools.append(finance_tool)
            
            logger.info(f"已初始化 {len(self.available_tools)} 个工具")
        except Exception as e:
            logger.error(f"初始化工具失败: {e}")
            self.available_tools = []
    
    def _create_llm_vertex(self, system_prompt: str):
        """创建 LLM Vertex 实例"""
        if self.llm_model is None:
            raise ValueError("LLM模型未初始化")
        
        # 根据工具启用状态决定是否传递工具
        tools = self.available_tools if self.tools_enabled else []
        
        return LLMVertex(
            id="chat_llm",
            name="聊天LLM",
            model=self.llm_model,
            params={
                SYSTEM: system_prompt,
                USER: [],  # 空的用户消息列表，因为我们会通过 conversation_history 传递
                ENABLE_STREAM: True,  # 启用流模式
            },
            tools=tools  # 传递工具列表
        )
    
    def chat_with_vertex(self, message: str, history: List[Tuple[str, str]], system_prompt: str):
        """使用 LLM Vertex 进行聊天（流式输出）"""
        if not message.strip():
            yield "", history
            return
        
        try:
            # 创建新的 LLM Vertex 实例（每次对话使用新实例避免状态污染）
            llm_vertex = self._create_llm_vertex(system_prompt)
            
            # 直接传递对话历史和当前消息给 LLM Vertex
            inputs = {
                "conversation_history": history,  # 传递对话历史列表
                "current_message": message        # 传递当前用户消息
            }
            
            # 先进行消息重定向处理
            llm_vertex.messages_redirect(inputs, self.context)
            
            # 使用统一的流式聊天方法
            response_parts = []
            new_history = history + [(message, "")]
            
            for chunk in self._stream_chat_with_gradio_format(llm_vertex, inputs, self.context, message, history):
                yield chunk
            
        except Exception as e:
            error_msg = f"聊天错误: {str(e)}"
            logger.error(error_msg)
            new_history = history + [(message, error_msg)]
            yield "", new_history
    
    def _stream_chat_with_gradio_format(self, llm_vertex, inputs, context, message, history):
        """统一的流式聊天方法，返回Gradio格式的结果"""
        response_parts = []
        new_history = history + [(message, "")]
        
        for chunk in llm_vertex.chat_stream_generator(inputs, context):
            if chunk:
                response_parts.append(chunk)
                current_response = "".join(response_parts)
                new_history[-1] = (message, current_response)
                yield "", new_history
        
        final_response = "".join(response_parts)
        logger.info(f"用户: {message[:50]}... | 助手: {final_response[:50]}...")
    

    
    def get_available_models(self) -> List[str]:
        """获取可用的模型列表"""
        try:
            config = self.service._config
            if not isinstance(config, dict):
                return ["配置格式错误"]
                
            llm_config = config.get("llm", {})
            if not isinstance(llm_config, dict):
                return ["LLM配置格式错误"]
                
            models = []
            for provider, provider_config in llm_config.items():
                if isinstance(provider_config, dict):
                    model_name = provider_config.get("model-name", provider)
                    enabled = provider_config.get("enabled", False)
                    status = "✅" if enabled else "❌"
                    models.append(f"{status} {provider}: {model_name}")
            return models
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return ["配置加载失败"]
    
    def switch_model(self, provider: str) -> str:
        """切换模型提供商"""
        try:
            # 对于Ollama，先检查服务是否可用
            if provider.lower() == "ollama":
                if not self._check_ollama_service():
                    return "❌ Ollama服务不可用，请确保Ollama正在运行并监听在http://localhost:11434"
            
            new_model = self.service.get_chatmodel_by_provider(provider)
            if new_model:
                self.llm_model = new_model
                
                # 安全获取模型名称
                try:
                    model_name = new_model.model_name()
                except:
                    model_name = str(new_model)
                
                logger.info(f"已切换到模型: {provider} - {model_name}")
                return f"✅ 已切换到: {provider} - {model_name}"
            else:
                return f"❌ 无法切换到模型: {provider}"
        except Exception as e:
            error_msg = f"❌ 切换模型失败: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _check_ollama_service(self) -> bool:
        """检查Ollama服务是否可用"""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/version", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def get_ollama_models(self) -> List[str]:
        """获取可用的Ollama模型列表"""
        try:
            if not self._check_ollama_service():
                return ["Ollama服务不可用"]
            
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = []
                for model in data.get("models", []):
                    name = model.get("name", "unknown")
                    size = model.get("size", 0)
                    size_mb = size / (1024 * 1024) if size else 0
                    models.append(f"{name} ({size_mb:.1f}MB)")
                return models if models else ["没有找到已安装的模型"]
            else:
                return ["无法获取模型列表"]
        except Exception as e:
            logger.error(f"获取Ollama模型列表失败: {e}")
            return [f"获取失败: {str(e)}"]


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="基于 Workflow LLM Vertex 的聊天应用")
    parser.add_argument("--port", type=int, default=7860, help="Gradio Web UI 端口")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Web UI 主机地址")
    parser.add_argument("--share", action="store_true", help="启用 Gradio 分享链接")
    return parser.parse_args()


def create_gradio_interface(app: WorkflowChatApp):
    """创建 Gradio 界面"""
    
    # 默认系统提示
    default_system_prompt = (
        "你是一个友好、聪明且乐于助人的AI助手。"
        "请根据用户的问题提供准确、有用的回答。"
        "如果不确定答案，请诚实地说明。"
    )
    
    with gr.Blocks(
        title="Vertex Chat - 基于 Workflow LLM",
        theme=gr.themes.Soft(),
        css="""
        .chat-container { max-height: 600px; overflow-y: auto; }
        .model-info { background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin: 5px 0; }
        """
    ) as demo:
        
        gr.Markdown("""
        # 🤖 Vertex Chat
        ### 基于 Workflow LLM Vertex 的智能聊天助手
        
        使用统一配置系统，支持多种 LLM 提供商
        """)
        
        with gr.Row():
            with gr.Column(scale=3):
                # 聊天界面
                chatbot = gr.Chatbot(
                    label="对话",
                    height=500,
                    container=True,
                    elem_classes=["chat-container"]
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="输入您的问题...",
                        lines=2,
                        scale=4,
                        container=False
                    )
                    send_btn = gr.Button("发送", variant="primary", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("清除对话", variant="secondary")
                    
            with gr.Column(scale=1):
                # 配置面板
                gr.Markdown("### ⚙️ 配置")
                
                system_prompt = gr.Textbox(
                    label="系统提示",
                    value=default_system_prompt,
                    lines=4,
                    placeholder="自定义系统提示词..."
                )
                
                # 模型信息
                gr.Markdown("### 🔧 模型信息")
                
                # 安全获取当前模型名称
                current_model = "未知"
                if app.llm_model:
                    try:
                        current_model = app.llm_model.model_name()
                    except:
                        current_model = str(app.llm_model)
                
                model_info = gr.Markdown(
                    f"**当前模型:** {current_model}",
                    elem_classes=["model-info"]
                )
                
                # 可用模型列表
                available_models = gr.Dropdown(
                    label="可用模型",
                    choices=app.get_available_models(),
                    interactive=False,
                    info="配置文件中的所有模型"
                )
                
                # 模型切换 - 使用下拉选择 + 手动输入两种方式
                with gr.Row():
                    provider_dropdown = gr.Dropdown(
                        label="选择提供商",
                        choices=["deepseek", "openrouter", "tongyi", "moonshoot", "ollama"],
                        scale=2,
                        allow_custom_value=True
                    )
                    switch_btn = gr.Button("切换", scale=1)
                
                with gr.Row():
                    provider_input = gr.Textbox(
                        placeholder="或手动输入提供商名称 (如: deepseek)",
                        label="手动输入提供商",
                        scale=4,
                        visible=True
                    )
                
                switch_result = gr.Textbox(
                    label="切换结果",
                    interactive=False,
                    lines=2
                )
                
                # Ollama本地模型管理
                gr.Markdown("### 🏠 本地模型(Ollama)")
                
                with gr.Row():
                    refresh_ollama_btn = gr.Button("刷新模型列表", scale=1)
                
                ollama_models = gr.Dropdown(
                    label="可用的Ollama模型",
                    choices=app.get_ollama_models(),
                    interactive=False,
                    info="已安装的本地模型"
                )
                
                # 工具管理
                gr.Markdown("### 🛠️ 工具管理")
                
                tools_enabled = gr.Checkbox(
                    label="启用Function Tools",
                    value=app.tools_enabled,
                    info="允许AI助手使用工具执行任务"
                )
                
                available_tools_display = gr.Dropdown(
                    label="可用工具",
                    choices=[f"{tool.name}: {tool.description}" for tool in app.available_tools],
                    interactive=False,
                    info=f"共有 {len(app.available_tools)} 个工具可用"
                )
                
                # 命令行工具测试区域
                with gr.Accordion("🖥️ 命令行工具测试", open=False):
                    cmd_input = gr.Textbox(
                        label="命令",
                        placeholder="例如: ls -la, python --version, pwd",
                        lines=1
                    )
                    cmd_execute_btn = gr.Button("执行命令", variant="secondary")
                    cmd_result = gr.JSON(
                        label="执行结果",
                        visible=True
                    )
        
        # 事件绑定
        def respond(message, history, sys_prompt):
            # For streaming chat, we need to iterate through the generator
            for result in app.chat_with_vertex(message, history, sys_prompt):
                yield result
        
        def clear_conversation():
            return []
        
        def switch_model_handler(dropdown_provider, manual_provider):
            # 优先使用下拉选择的值，如果为空则使用手动输入的值
            provider = dropdown_provider if dropdown_provider else manual_provider
            if not provider:
                return "❌ 请选择或输入提供商名称", model_info.value
            
            result = app.switch_model(provider)
            
            # 安全获取新模型名称
            new_model_name = "未知"
            if app.llm_model:
                try:
                    new_model_name = app.llm_model.model_name()
                except:
                    new_model_name = str(app.llm_model)
            
            new_model_info = f"**当前模型:** {new_model_name}"
            return result, new_model_info
        
        def refresh_ollama_models():
            """刷新Ollama模型列表"""
            return gr.Dropdown(choices=app.get_ollama_models())
        
        def toggle_tools(enabled):
            """切换工具启用状态"""
            app.tools_enabled = enabled
            status = "✅ 已启用" if enabled else "❌ 已禁用"
            logger.info(f"工具状态已更改: {status}")
            return f"工具状态: {status}"
        
        def execute_command_test(command):
            """测试执行命令"""
            if not command.strip():
                return {"error": "请输入命令"}
            
            try:
                # 直接使用命令行工具
                if app.available_tools:
                    cmd_tool = app.available_tools[0]  # 第一个工具应该是命令行工具
                    result = cmd_tool.execute({"command": command})
                    return result
                else:
                    return {"error": "命令行工具未初始化"}
            except Exception as e:
                return {"error": f"执行失败: {str(e)}"}
        
        # 绑定发送消息事件（支持流式输出）
        msg.submit(
            respond,
            inputs=[msg, chatbot, system_prompt],
            outputs=[msg, chatbot],
            show_progress="minimal"
        )
        
        send_btn.click(
            respond,
            inputs=[msg, chatbot, system_prompt],
            outputs=[msg, chatbot],
            show_progress="minimal"
        )
        
        # 绑定清除对话事件
        clear_btn.click(
            clear_conversation,
            outputs=[chatbot]
        )
        
        # 绑定模型切换事件 - 支持两种输入方式
        switch_btn.click(
            switch_model_handler,
            inputs=[provider_dropdown, provider_input],
            outputs=[switch_result, model_info]
        )
        
        # 绑定Ollama模型刷新事件
        refresh_ollama_btn.click(
            refresh_ollama_models,
            outputs=[ollama_models]
        )
        
        # 绑定工具启用切换事件
        tools_enabled.change(
            toggle_tools,
            inputs=[tools_enabled],
            outputs=[]
        )
        
        # 绑定命令执行事件
        cmd_execute_btn.click(
            execute_command_test,
            inputs=[cmd_input],
            outputs=[cmd_result]
        )
    
    return demo


def main():
    """主函数"""
    args = parse_args()
    
    try:
        # 初始化应用
        logger.info("正在初始化 Vertex Chat 应用...")
        app = WorkflowChatApp()
        
        # 创建 Gradio 界面
        demo = create_gradio_interface(app)
        
        # 启动应用
        logger.info(f"启动 Vertex Chat 应用在 {args.host}:{args.port}")
        demo.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            show_error=True
        )
        
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        print(f"❌ 启动失败: {e}")
        print("\n请检查:")
        print("1. 配置文件是否正确 (vertex_flow/config/llm.yml)")
        print("2. 是否有启用的 LLM 提供商")
        print("3. API 密钥是否配置正确")
        return 1


if __name__ == "__main__":
    exit(main()) 