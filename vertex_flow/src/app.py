#!/usr/bin/env python3
"""
主应用入口
"""

import argparse

import gradio as gr

from vertex_flow.utils.logger import setup_logger

from .chat_util import format_history
from .model_client import ModelClient
from .native_client import OllamaClient

# 配置日志
logger = setup_logger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="本地运行 Qwen-7B 模型")
    parser.add_argument("--host", type=str, default="http://localhost:11434", help="Ollama 服务地址")
    parser.add_argument("--port", type=int, default=7860, help="Gradio Web UI 端口")
    parser.add_argument("--api-key", type=str, default="", help="API密钥")
    parser.add_argument("--api-base", type=str, default="https://api.openai.com/v1", help="API基础URL")
    parser.add_argument(
        "--model",
        type=str,
        default="local-qwen",
        help="模型名称 (local-qwen表示本地模型，其他为API模型)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    logger.info(f"启动应用，参数: {vars(args)}")

    # 检查连接
    if args.model == "local-qwen":
        client = OllamaClient(host=args.host, model="qwen:7b")
        if not client.check_connection():
            logger.error(f"无法连接到 Ollama 服务 {args.host}")
            print(f"错误: 无法连接到 Ollama 服务 {args.host}")
            print("请确保 Ollama 服务正在运行，您可以通过以下命令启动:")
            print("1. 手动启动 Ollama 应用")
            print("2. 或运行: python scripts/setup_ollama.py")
            return
        logger.info(f"成功连接到 Ollama 服务，使用模型: qwen:7b")

    logger.info(f"成功初始化，使用模型: {args.model}")

    # 系统提示
    system_prompt = (
        "你是一个友好、聪明且乐于助人的AI助手，基于Qwen-7B大型语言模型。尽可能提供有帮助、安全和真实的回答。"
    )

    # 定义聊天函数
    def chat(message, history, context=None, client=None, use_system_prompt=False):
        if not message.strip():
            return "", history, context

        full_history = []
        if history:
            full_history = history.copy()

        history_prompt = format_history(full_history) if full_history else ""
        full_prompt = (
            f"{history_prompt}\n\nHuman: {message}\nAssistant: " if history_prompt else f"Human: {message}\nAssistant: "
        )

        response = ""
        if use_system_prompt:
            for chunk in client.generate(full_prompt, system=system_prompt, context=context):
                response = chunk
                yield "", history + [(message, response)], context
        else:
            for chunk in client.generate(full_prompt, history):
                response = chunk
                yield "", history + [(message, response)], context

    # 创建 Gradio 界面
    # 修改Gradio界面
    with gr.Blocks(title="本地 Qwen-7B 聊天") as demo:
        gr.Markdown("# 本地 Qwen-7B 聊天助手")

        with gr.Row():
            model = gr.Textbox(
                label="模型名称",
                value=args.model,
                placeholder="输入模型名称 (local-qwen表示本地模型)",
            )

        # 新增 system_prompt 输入框
        system_prompt_box = gr.Textbox(
            label="System Prompt",
            value=system_prompt,
            placeholder="自定义系统提示词（可选）",
            lines=2,
        )

        api_params = gr.Accordion("API参数配置", open=False, visible=False)
        with api_params:
            api_key = gr.Textbox(label="API密钥", type="password", value="")
            api_base = gr.Textbox(label="API基础URL", value="https://api.openai.com/v1")

        # 根据模型类型显示/隐藏API参数
        def toggle_api_params(model_name):
            return gr.update(visible=model_name != "local-qwen")

        model.change(fn=toggle_api_params, inputs=model, outputs=api_params)

        # 使用变量保存当前模式的状态
        current_mode = gr.State(args.model)

        def update_current_mode(model_name):
            return model_name

        model.change(fn=update_current_mode, inputs=model, outputs=current_mode)

        chatbot = gr.Chatbot(height=500)
        msg = gr.Textbox(placeholder="输入您的问题...", lines=3, interactive=True)
        send = gr.Button("发送")  # 新增发送按钮
        clear = gr.Button("清除对话")

        context_state = gr.State([])

        # 修改 process_message，增加 system_prompt 参数
        def process_message(message, history, context, model, api_key, api_base, user_system_prompt):
            logger.info(f"收到用户消息: {message[:50]}..., model : {model}")
            try:
                # 使用用户自定义的 system_prompt，如果未填写则用默认
                sys_prompt = user_system_prompt if user_system_prompt.strip() else system_prompt
                if model == "local-qwen":
                    client = OllamaClient(host=args.host, model="qwen:7b")
                    gen = chat(
                        message,
                        history,
                        context,
                        client=client,
                        use_system_prompt=True,
                        sys_prompt=sys_prompt,
                    )
                else:
                    if not api_key:
                        yield "错误: 请提供API密钥", history, context
                        return
                    client = ModelClient(api_key=api_key, base_url=api_base, model=model)
                    gen = chat(
                        message,
                        history,
                        context,
                        client=client,
                        use_system_prompt=False,
                        sys_prompt=sys_prompt,
                    )

                for msg_out, history_out, context_out in gen:
                    yield msg_out, history_out, context_out

                return "", history_out, context_out
            except Exception as e:
                logger.error(f"处理消息时出错: {str(e)}")
                yield f"错误: {str(e)}", history, context
            except StopIteration:
                logger.warning("生成回复时遇到StopIteration")
                return "", history, context

        # 修改 chat 函数，支持 sys_prompt 参数
        def chat(
            message,
            history,
            context=None,
            client=None,
            use_system_prompt=False,
            sys_prompt=None,
        ):
            if not message.strip():
                return "", history, context

            full_history = []
            if history:
                full_history = history.copy()

            history_prompt = format_history(full_history) if full_history else ""
            full_prompt = (
                f"{history_prompt}\n\nHuman: {message}\nAssistant: "
                if history_prompt
                else f"Human: {message}\nAssistant: "
            )

            response = ""
            if use_system_prompt:
                for chunk in client.generate(full_prompt, system=sys_prompt, context=context):
                    response = chunk
                    yield "", history + [(message, response)], context
            else:
                for chunk in client.generate(full_prompt, history):
                    response = chunk
                    yield "", history + [(message, response)], context

        # 修改 submit 和 click 事件，增加 system_prompt_box 作为输入
        msg_submit = msg.submit(
            fn=process_message,
            inputs=[
                msg,
                chatbot,
                context_state,
                current_mode,
                api_key,
                api_base,
                system_prompt_box,
            ],
            outputs=[msg, chatbot, context_state],
            api_name="chat",
        ).then(lambda: None, None, None, queue=False)

        send.click(
            fn=process_message,
            inputs=[
                msg,
                chatbot,
                context_state,
                current_mode,
                api_key,
                api_base,
                system_prompt_box,
            ],
            outputs=[msg, chatbot, context_state],
            api_name="chat",
        )

        clear.click(lambda: ([], []), None, [chatbot, context_state], queue=False)

    # 启动 Gradio 界面
    print(f"启动 Gradio Web UI，访问地址: http://localhost:{args.port}")
    demo.queue().launch(server_name="0.0.0.0", server_port=args.port, share=False)


if __name__ == "__main__":
    main()
