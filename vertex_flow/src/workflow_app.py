#!/usr/bin/env python3
"""
基于 Workflow LLM Vertex 的主应用入口
使用统一配置系统和 LLM Vertex 实现聊天功能
"""

import argparse
import asyncio
import threading
import time
from typing import List, Tuple

import gradio as gr

from vertex_flow.utils.logger import setup_logger
from vertex_flow.workflow.constants import ENABLE_STREAM, SHOW_REASONING, SHOW_REASONING_KEY, SYSTEM, USER
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.workflow import WorkflowContext

# MCP support imports
try:
    from vertex_flow.workflow.vertex.mcp_llm_vertex import MCPLLMVertex

    MCP_AVAILABLE = True
except ImportError as e:
    MCP_AVAILABLE = False
    print(f"MCP功能不可用: {e}")

# 配置日志
logger = setup_logger(__name__)


class WorkflowChatApp:
    """基于 Workflow LLM Vertex 的聊天应用"""

    def __init__(self, config_path: str = None):
        """初始化应用"""
        logger.info(f" workflow chat app {config_path}")
        self.service = VertexFlowService(config_file=config_path) if config_path else VertexFlowService()
        self.llm_model = None
        self.context = WorkflowContext()
        self.tools_enabled = False
        self.available_tools = []
        self.mcp_enabled = False
        self.mcp_manager = None

        # 初始化各个组件
        self._initialize_llm()
        self._initialize_tools()
        self._initialize_mcp()

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

            # 初始化Web搜索工具 - 尝试多种搜索服务
            web_search_tool = self._initialize_web_search_tool()
            if web_search_tool:
                self.available_tools.append(web_search_tool)

            logger.info(f"已初始化 {len(self.available_tools)} 个工具")
        except Exception as e:
            logger.error(f"初始化工具失败: {e}")
            self.available_tools = []

    def _initialize_web_search_tool(self):
        """初始化Web搜索工具，尝试多种搜索服务"""
        # 优先级列表：serpapi -> duckduckgo(免费) -> bocha -> searchapi -> bing
        search_providers = ["serpapi", "duckduckgo", "bocha", "searchapi", "bing"]

        for provider in search_providers:
            try:
                web_search_tool = self.service.get_web_search_tool(provider)
                logger.info(f"Web搜索工具已启用 - 使用{provider}服务")
                return web_search_tool
            except Exception as e:
                logger.debug(f"{provider}搜索服务初始化失败: {e}")
                continue

        # 如果所有服务都失败，记录警告
        logger.warning("所有Web搜索服务初始化失败，请检查配置或启用至少一个搜索服务")
        return None

    def _initialize_mcp(self):
        """初始化MCP功能"""
        try:
            # 检查service配置是否启用MCP
            if self.service.is_mcp_enabled():
                logger.info("检测到MCP配置已启用，开始初始化MCP...")

                # 立即初始化MCP管理器
                self.mcp_manager = self.service.get_mcp_manager()

                if self.mcp_manager:
                    self.mcp_enabled = True
                    logger.info("MCP功能初始化成功")

                    # 启动时检查MCP工具可用性
                    self._check_mcp_tools_startup()
                else:
                    logger.warning("MCP管理器初始化失败")
            else:
                logger.info("MCP功能未启用")

        except Exception as e:
            logger.error(f"MCP初始化失败: {e}")
            self.mcp_enabled = False
            self.mcp_manager = None

    def _check_mcp_tools_startup(self):
        """检查MCP工具在启动时的可用性（简化版）"""
        if not self.mcp_enabled or not self.mcp_manager:
            return

        try:

            def run_mcp_check():
                """在独立线程中运行MCP检查"""
                try:
                    # 等待MCP管理器完全初始化
                    max_init_wait = 10  # 最多等待10秒初始化
                    init_wait_interval = 0.5
                    init_waited = 0

                    while not self.mcp_manager._initialized and init_waited < max_init_wait:
                        logger.info(f"等待MCP管理器初始化... ({init_waited:.1f}s/{max_init_wait}s)")
                        time.sleep(init_wait_interval)
                        init_waited += init_wait_interval

                    if not self.mcp_manager._initialized:
                        logger.warning("MCP管理器初始化超时")
                        return

                    logger.info("MCP管理器已初始化 ✅")

                    # 简单检查连接状态，不获取工具
                    connected_clients = self.mcp_manager.get_connected_clients()

                    if connected_clients:
                        logger.info(
                            f"✅ 启动检查成功 - 发现 {len(connected_clients)} 个已连接的MCP客户端: {', '.join(connected_clients)}"
                        )
                        logger.info("💡 MCP工具已准备就绪，可在聊天中使用")
                    else:
                        logger.warning("⚠️ 未发现已连接的MCP客户端")

                except Exception as e:
                    logger.error(f"MCP工具启动检查失败: {e}")

            # 在独立线程中运行检查，避免阻塞主线程
            check_thread = threading.Thread(target=run_mcp_check, daemon=True)
            check_thread.start()

        except Exception as e:
            logger.error(f"启动MCP工具检查失败: {e}")

    def check_mcp_availability(self) -> bool:
        """检查MCP功能是否可用"""
        return self.mcp_enabled

    def get_mcp_manager(self):
        """获取MCP管理器"""
        return self.mcp_manager

    def _create_llm_vertex(
        self,
        system_prompt: str,
        enable_reasoning: bool = False,
        show_reasoning: bool = SHOW_REASONING,
        enable_mcp: bool = False,
    ):
        """创建 LLM Vertex 实例，支持MCP增强"""
        if self.llm_model is None:
            raise ValueError("LLM模型未初始化")

        # 根据工具启用状态决定是否传递工具
        tools = self.available_tools if self.tools_enabled else []

        # 记录MCP状态
        mcp_manager = self.get_mcp_manager()
        logger.info(
            f"创建LLM Vertex - MCP启用: {enable_mcp}, MCP可用: {MCP_AVAILABLE}, MCP管理器: {mcp_manager is not None}"
        )

        # 如果启用MCP且MCP功能可用，使用MCPLLMVertex
        if enable_mcp and MCP_AVAILABLE and mcp_manager:
            try:
                return MCPLLMVertex(
                    id="mcp_chat_llm",
                    name="MCP增强聊天LLM",
                    model=self.llm_model,
                    params={
                        SYSTEM: system_prompt,
                        USER: [],  # 空的用户消息列表，因为我们会通过 conversation_history 传递
                        ENABLE_STREAM: True,  # 启用流模式
                        "enable_reasoning": enable_reasoning,  # 启用思考过程
                        SHOW_REASONING_KEY: show_reasoning,  # 显示思考过程
                    },
                    tools=tools,  # 传递工具列表
                )
            except Exception as e:
                logger.warning(f"创建MCP增强LLM失败，回退到标准LLM: {e}")
                # 回退到标准LLM
                pass

        # 使用标准LLM Vertex
        return LLMVertex(
            id="chat_llm",
            name="聊天LLM",
            model=self.llm_model,
            params={
                SYSTEM: system_prompt,
                USER: [],  # 空的用户消息列表，因为我们会通过 conversation_history 传递
                ENABLE_STREAM: True,  # 启用流模式
                "enable_reasoning": enable_reasoning,  # 启用思考过程
                SHOW_REASONING_KEY: show_reasoning,  # 显示思考过程
            },
            tools=tools,  # 传递工具列表
        )

    def chat_with_vertex(self, message, history, system_prompt, enable_reasoning=False, show_reasoning=SHOW_REASONING):
        """使用 LLM Vertex 进行聊天（流式输出），支持多模态输入和思考过程"""
        # MCP启用状态使用预初始化的结果
        enable_mcp = self.mcp_enabled

        # 添加调试信息，显示当前使用的模型
        try:
            current_model_name = self.llm_model.model_name() if self.llm_model else "未知"
            logger.info(f"当前使用的模型: {current_model_name}, MCP启用: {enable_mcp}")
        except:
            logger.info(f"当前使用的模型: {self.llm_model}, MCP启用: {enable_mcp}")

        # 支持多模态输入：message可以是str或dict
        if isinstance(message, dict):
            # 多模态输入
            text = message.get("text", "")
            image_url = message.get("image_url")
            if not text and not image_url:
                yield "", history
                return
            inputs = {
                "conversation_history": history,
                "current_message": text,
            }
            if image_url:
                inputs["image_url"] = image_url
        else:
            # 兼容原有字符串输入
            if not message.strip():
                yield "", history
                return
            inputs = {
                "conversation_history": history,
                "current_message": message,
            }
        try:
            # 创建新的 LLM Vertex 实例（每次对话使用新实例避免状态污染）
            llm_vertex = self._create_llm_vertex(system_prompt, enable_reasoning, show_reasoning, enable_mcp)
            # 先进行消息重定向处理
            llm_vertex.messages_redirect(inputs, self.context)
            # 使用流式聊天方法
            for chunk in self._stream_chat_with_gradio_format(llm_vertex, inputs, self.context, message, history):
                yield chunk
        except Exception as e:
            error_msg = f"聊天错误: {str(e)}"
            logger.error(error_msg)
            import traceback

            logger.error(f"错误详情: {traceback.format_exc()}")
            new_history = history + [(str(message), error_msg)]
            yield "", new_history

    def _stream_chat_with_gradio_format(self, llm_vertex, inputs, context, message, history):
        """统一的流式聊天方法，返回Gradio格式的结果"""
        response_parts = []
        # 确保传递给Gradio的消息格式正确
        if isinstance(message, dict):
            display_message = message.get("text", "")
            if message.get("image_url"):
                display_message += " [图片]"
        else:
            display_message = str(message)

        # 确保history不为None
        if history is None:
            history = []

        new_history = history + [(display_message, "")]

        try:
            # 直接使用流式输出模式
            logger.info("使用流式输出模式")
            chunk_count = 0
            reasoning_header_added = False
            answer_header_added = False
            is_reasoning_phase = True

            for chunk in llm_vertex.chat_stream_generator(inputs, context):
                if chunk:
                    chunk_count += 1

                    # 检查是否是推理模式且需要显示推理过程
                    enable_reasoning = getattr(llm_vertex, "enable_reasoning", False)
                    show_reasoning = getattr(llm_vertex, "show_reasoning", False)

                    if enable_reasoning and show_reasoning and not reasoning_header_added:
                        # 添加推理模式头部
                        response_parts.append("🧠 **启用推理模式** - 您将看到AI的完整思考过程\n\n")
                        response_parts.append("🤔 **思考过程：**\n")
                        reasoning_header_added = True

                    # 检测是否从推理阶段转换到回答阶段
                    # 简单的启发式：如果chunk包含较多连续的非特殊字符，可能是最终答案的开始
                    if (
                        enable_reasoning
                        and show_reasoning
                        and is_reasoning_phase
                        and reasoning_header_added
                        and not answer_header_added
                        and chunk_count > 10
                        and len(chunk.strip()) > 5
                        and not any(marker in chunk for marker in ["思考", "分析", "考虑", "推理"])
                    ):
                        # 添加分隔符和最终答案头部
                        response_parts.append("\n\n" + "=" * 50 + "\n")
                        response_parts.append("💡 **最终回答：**\n\n")
                        answer_header_added = True
                        is_reasoning_phase = False

                    response_parts.append(chunk)
                    current_response = "".join(response_parts)
                    new_history[-1] = (display_message, current_response)
                    yield "", new_history
            logger.info(f"流式输出完成，共收到 {chunk_count} 个chunk")

        except Exception as e:
            logger.error(f"流式聊天错误: {str(e)}")
            import traceback

            logger.error(f"错误详情: {traceback.format_exc()}")
            error_msg = f"聊天处理错误: {str(e)}"
            new_history[-1] = (display_message, error_msg)
            yield "", new_history

        final_response = "".join(response_parts) if response_parts else new_history[-1][1]
        logger.info(f"用户: {display_message[:150]}... | 助手: {final_response[:150]}...")

    def get_available_providers(self) -> List[str]:
        """获取可用的提供商列表"""
        try:
            config = self.service._config
            if not isinstance(config, dict):
                return ["配置格式错误"]

            llm_config = config.get("llm", {})
            if not isinstance(llm_config, dict):
                return ["LLM配置格式错误"]

            providers = []
            for provider, provider_config in llm_config.items():
                if isinstance(provider_config, dict):
                    enabled = provider_config.get("enabled", False)
                    status = "✅" if enabled else "❌"
                    providers.append(f"{status} {provider}")
            return providers
        except Exception as e:
            logger.error(f"获取提供商列表失败: {e}")
            return ["配置加载失败"]

    def get_models_by_provider(self, provider: str) -> List[str]:
        """根据提供商获取对应的模型列表"""
        try:
            config = self.service._config
            if not isinstance(config, dict):
                return ["配置格式错误"]

            llm_config = config.get("llm", {})
            if not isinstance(llm_config, dict):
                return ["LLM配置格式错误"]

            provider_config = llm_config.get(provider, {})
            if not provider_config:
                return [f"未找到提供商: {provider}"]

            models = []
            provider_enabled = provider_config.get("enabled", False)

            # 支持多模型结构
            if "models" in provider_config:
                models_list = provider_config["models"]
                for model_config in models_list:
                    if isinstance(model_config, dict):
                        model_name = model_config.get("name", "unknown")
                        model_enabled = model_config.get("enabled", False)
                        is_default = model_config.get("default", False)
                        status = "✅" if (provider_enabled and model_enabled) else "❌"
                        default_mark = " (默认)" if is_default else ""
                        models.append(f"{status} {model_name}{default_mark}")
            else:
                # 旧格式：使用model-name
                model_name = provider_config.get("model-name", provider)
                status = "✅" if provider_enabled else "❌"
                models.append(f"{status} {model_name}")

            return models
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return ["配置加载失败"]

    def switch_model_by_provider_and_name(self, provider: str, model_name: str = None) -> str:
        """根据提供商和模型名称切换模型"""
        try:
            # 对于Ollama，先检查服务是否可用
            if provider.lower() == "ollama":
                if not self._check_ollama_service():
                    return "❌ Ollama服务不可用，请确保Ollama正在运行并监听在http://localhost:11434"

            # 如果指定了模型名称，使用它；否则使用默认模型
            new_model = self.service.get_chatmodel_by_provider(provider, model_name)
            if new_model:
                self.llm_model = new_model

                # 安全获取模型名称
                try:
                    actual_model_name = new_model.model_name()
                except:
                    actual_model_name = str(new_model)

                logger.info(f"已切换到模型: {provider} - {actual_model_name}")
                return f"✅ 已切换到: {provider} - {actual_model_name}"
            else:
                return f"❌ 无法切换到模型: {provider}"
        except Exception as e:
            error_msg = f"❌ 切换模型失败: {str(e)}"
            logger.error(error_msg)
            return error_msg

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

    def _check_ollama_service(self) -> bool:
        """检查Ollama服务是否可用"""
        try:
            import requests

            response = requests.get("http://localhost:11434/api/version", timeout=3)
            return response.status_code == 200
        except:
            return False


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="基于 Workflow LLM Vertex 的聊天应用")
    parser.add_argument("--port", type=int, default=7860, help="Gradio Web UI 端口")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Web UI 主机地址")
    parser.add_argument("--share", action="store_true", help="启用 Gradio 分享链接")
    parser.add_argument("--config", "-c", help="指定配置文件路径")
    return parser.parse_args()


def create_gradio_interface(app: WorkflowChatApp):
    """创建 Gradio 界面"""

    # 默认系统提示
    default_system_prompt = (
        "你是一个友好、聪明且乐于助人的AI助手。"
        "请根据用户的问题提供准确、有用的回答。"
        "如果不确定答案，请诚实地说明。"
        "\n\n🛠️ 你可以使用以下工具来协助用户："
        "\n\n📡 **网络搜索工具 (Web Search)**"
        "\n- 当用户询问最新新闻、实时信息、股价、天气等时，请主动使用搜索功能"
        "\n- 当需要查证事实、获取准确数据时，建议进行网络搜索"
        "\n- 搜索后请基于搜索结果提供准确、有用的回答"
        "\n- 支持多种搜索引擎：DuckDuckGo、SerpAPI、SearchAPI等"
        "\n\n💻 **命令行工具 (Command Line)**"
        "\n- 可以执行系统命令、查看文件、运行脚本等"
        "\n- 支持的命令如：ls, pwd, python, git, ps, grep等"
        "\n- 具有安全防护，会自动拦截危险命令"
        "\n- 适用于：文件操作、系统查询、开发调试、环境检查"
        "\n\n💰 **金融工具 (Finance)**"
        "\n- 查询股票价格、市场数据、财经新闻"
        "\n- 支持股票代码查询、价格走势分析"
        "\n- 获取实时金融市场信息"
        "\n\n🧮 **数学计算工具 (Calculate)**"
        "\n- 执行数学运算和表达式计算"
        "\n- 支持基本四则运算、括号优先级"
        "\n- 安全的数学表达式求值"
        "\n\n📝 **文本处理工具 (Text Processing)**"
        "\n- 文本统计：字数统计、字符计数"
        "\n- 文本转换：大小写转换、文本反转"
        "\n- 文本分析和格式化处理"
        "\n\n🔗 **MCP工具集成 (Model Context Protocol)**"
        "\n- 如果配置了MCP客户端，可以访问额外的工具和资源"
        "\n- 支持文件系统访问、数据库查询、外部API调用等"
        "\n- MCP工具会自动加载并可通过function calling使用"
        "\n\n💡 **使用建议：**"
        "\n- 根据用户需求主动选择最适合的工具"
        "\n- 多个工具可以组合使用解决复杂问题"
        "\n- 使用工具前可以简单说明将要执行的操作"
        "\n- 工具执行后请解释结果并提供有用的见解"
    )

    with gr.Blocks(
        title="Vertex Chat - 基于 Workflow LLM",
        theme=gr.themes.Soft(),
        css="""
        .chat-container { 
            max-height: 600px; 
            overflow-y: auto; 
            scroll-behavior: smooth;
        }
        .model-info { 
            background-color: #f0f0f0; 
            padding: 10px; 
            border-radius: 5px; 
            margin: 5px 0; 
        }
        /* 自动滚动到底部的样式 */
        .chatbot { 
            height: 500px !important; 
            overflow-y: auto !important;
            scroll-behavior: smooth !important;
        }
        .chatbot .wrap {
            height: 100% !important;
        }
        .chatbot .message-wrap {
            scroll-margin-bottom: 20px;
        }
        /* 强制滚动的CSS动画 */
        @keyframes scrollToBottom {
            to {
                scroll-behavior: smooth;
                overflow-anchor: none;
            }
        }
        .auto-scroll {
            animation: scrollToBottom 0.3s ease-out;
        }
        """,
        js="""
        function() {
            console.log('🚀 初始化流式聊天自动滚动功能...');
            
            let scrollContainer = null;
            let isUserScrolling = false;
            let scrollTimeout = null;
            let autoScrollEnabled = true; // 控制自动滚动是否启用
            
            // 查找并缓存聊天滚动容器
            function findScrollContainer() {
                if (scrollContainer && document.contains(scrollContainer)) {
                    return scrollContainer;
                }
                
                console.log('🔍 开始搜索滚动容器...');
                
                // 首先打印所有聊天框元素，帮助调试
                const chatbotElements = document.querySelectorAll('.chatbot');
                console.log('📋 找到聊天框元素数量:', chatbotElements.length);
                chatbotElements.forEach((el, index) => {
                    console.log(`聊天框 ${index}:`, el, 'innerHTML长度:', el.innerHTML.length);
                });
                
                // 扩展的选择器列表，包含更多可能性
                const selectors = [
                    // Gradio 4.x 常见结构
                    '.chatbot > div > div.overflow-y-auto',
                    '.chatbot .overflow-y-auto',
                    '.chatbot > div:first-child > div:first-child',
                    '.chatbot > div:first-child',
                    '.chatbot > div',
                    '.chatbot div[class*="overflow"]',
                    '.chatbot div[style*="overflow"]',
                    '.chatbot div[style*="scroll"]',
                    
                    // 通用容器
                    'gradio-chatbot .overflow-y-auto',
                    'gradio-chatbot > div',
                    '[data-testid="chatbot"] .overflow-y-auto',
                    '[data-testid="chatbot"] > div',
                    
                    // 高度相关
                    '.chatbot .h-full',
                    '.chatbot div[style*="height"]',
                    
                    // 最后的备选方案
                    '.chatbot',
                    'gradio-chatbot'
                ];
                
                console.log('🧭 将尝试以下选择器:', selectors);
                
                for (let i = 0; i < selectors.length; i++) {
                    const selector = selectors[i];
                    const elements = document.querySelectorAll(selector);
                    console.log(`选择器 "${selector}" 找到 ${elements.length} 个元素`);
                    
                    for (let j = 0; j < elements.length; j++) {
                        const element = elements[j];
                        if (element) {
                            const hasScroll = element.scrollHeight > element.clientHeight;
                            const computedStyle = window.getComputedStyle(element);
                            const overflowY = computedStyle.overflowY;
                            
                            console.log(`  元素 ${j}:`, {
                                tagName: element.tagName,
                                className: element.className,
                                scrollHeight: element.scrollHeight,
                                clientHeight: element.clientHeight,
                                hasScroll: hasScroll,
                                overflowY: overflowY,
                                element: element
                            });
                            
                            // 更宽松的条件：有滚动或者是可滚动容器
                            if (hasScroll || overflowY === 'auto' || overflowY === 'scroll' || element.scrollHeight > 100) {
                                scrollContainer = element;
                                console.log('✅ 找到滚动容器:', selector, '元素:', element);
                                console.log('📏 容器尺寸:', {
                                    scrollHeight: element.scrollHeight,
                                    clientHeight: element.clientHeight,
                                    scrollTop: element.scrollTop,
                                    overflowY: overflowY
                                });
                                return scrollContainer;
                            }
                        }
                    }
                }
                
                // 如果还是找不到，尝试直接查找聊天框内的任何div
                console.log('🚨 常规方法失败，尝试查找聊天框内的所有div...');
                const allChatDivs = document.querySelectorAll('.chatbot div, gradio-chatbot div');
                console.log('找到聊天框内div数量:', allChatDivs.length);
                
                for (let i = 0; i < allChatDivs.length; i++) {
                    const div = allChatDivs[i];
                    if (div && div.scrollHeight > 50) { // 非常宽松的条件
                        console.log('🎯 备用方案找到容器:', div);
                        scrollContainer = div;
                        return scrollContainer;
                    }
                }
                
                console.log('❌ 完全未找到滚动容器');
                console.log('🔧 DOM结构调试信息:');
                console.log('document.body:', document.body);
                console.log('所有带class的元素:', document.querySelectorAll('[class]').length);
                return null;
            }
            
            // 强制滚动到底部
            function forceScrollToBottom() {
                const container = findScrollContainer();
                if (container) {
                    container.scrollTop = container.scrollHeight;
                    console.log('📜 执行滚动:', container.scrollTop, '/', container.scrollHeight);
                    return true;
                }
                return false;
            }
            
            // 强制滚动到顶部（用于清除对话）
            function forceScrollToTop() {
                const container = findScrollContainer();
                if (container) {
                    container.scrollTop = 0;
                    console.log('📜 执行滚动到顶部');
                    return true;
                }
                return false;
            }
            
            // 平滑滚动到底部
            function smoothScrollToBottom() {
                const container = findScrollContainer();
                if (container) {
                    container.scrollTo({
                        top: container.scrollHeight,
                        behavior: 'smooth'
                    });
                    // 备用强制滚动
                    setTimeout(() => {
                        if (container.scrollTop < container.scrollHeight - container.clientHeight - 50) {
                            container.scrollTop = container.scrollHeight;
                        }
                    }, 300);
                    return true;
                }
                return false;
            }
            
            // 检查是否应该自动滚动
            function shouldAutoScroll() {
                if (!autoScrollEnabled) {
                    console.log('🛑 自动滚动已禁用');
                    return false;
                }
                
                if (isUserScrolling) {
                    console.log('🤚 用户正在滚动，跳过自动滚动');
                    return false;
                }
                
                const container = findScrollContainer();
                if (!container) {
                    console.log('❌ 未找到滚动容器');
                    return false;
                }
                
                // 修复：在流式输出时始终自动滚动，除非用户明确向上滚动了很多
                const scrollTop = container.scrollTop;
                const scrollHeight = container.scrollHeight;
                const clientHeight = container.clientHeight;
                const maxScroll = scrollHeight - clientHeight;
                
                console.log('📏 容器尺寸信息:', {
                    scrollTop,
                    scrollHeight,
                    clientHeight,
                    maxScroll,
                    containerTag: container.tagName,
                    containerClass: container.className
                });
                
                // 如果内容高度小于容器高度，仍然允许滚动（流式输出中内容会增加）
                if (maxScroll <= 0) {
                    console.log('📏 内容未超出容器，但允许滚动（流式输出）');
                    return true; // 改为true，允许流式输出时的滚动
                }
                
                // 如果用户滚动到了很上面（超过30%），则暂停自动滚动
                const scrollPercentage = scrollTop / maxScroll;
                const shouldPause = scrollPercentage < 0.7; // 如果滚动位置在前70%，暂停自动滚动
                
                if (shouldPause) {
                    console.log('📍 用户滚动到较上方位置，暂停自动滚动', {
                        scrollTop,
                        maxScroll,
                        percentage: Math.round(scrollPercentage * 100) + '%'
                    });
                    return false;
                }
                
                console.log('✅ 允许自动滚动', {
                    scrollTop,
                    maxScroll,
                    percentage: Math.round(scrollPercentage * 100) + '%'
                });
                return true;
            }
            
            // 监听内容变化的Observer
            function setupContentObserver() {
                const observer = new MutationObserver(function(mutations) {
                    let contentChanged = false;
                    
                    mutations.forEach(function(mutation) {
                        // 检测文本内容变化（流式更新）
                        if (mutation.type === 'characterData') {
                            contentChanged = true;
                        }
                        // 检测子元素变化（新消息）
                        else if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                            contentChanged = true;
                        }
                        // 检测属性变化（可能影响滚动）
                        else if (mutation.type === 'attributes') {
                            contentChanged = true;
                        }
                    });
                    
                    if (contentChanged && autoScrollEnabled && shouldAutoScroll()) {
                        console.log('🔄 内容变化检测，执行自动滚动');
                        // 立即滚动 - 使用多种方法
                        const scrolled = forceScrollToBottom() || bruteForceScroll();
                        
                        if (!scrolled) {
                            console.log('⚠️ 立即滚动失败，延迟重试...');
                            // 延迟滚动作为备用
                            setTimeout(() => {
                                if (autoScrollEnabled && shouldAutoScroll()) {
                                    const retryScrolled = forceScrollToBottom() || bruteForceScroll() || fallbackScroll();
                                    if (retryScrolled) {
                                        console.log('✅ 延迟滚动成功');
                                    } else {
                                        console.log('❌ 所有滚动方法都失败了');
                                    }
                                }
                            }, 100);
                        } else {
                            console.log('✅ 立即滚动成功');
                        }
                    } else if (contentChanged && !autoScrollEnabled) {
                        console.log('🛑 内容变化检测，但自动滚动已禁用');
                    }
                });
                
                // 监听整个聊天框区域
                const chatbotElements = document.querySelectorAll('.chatbot, gradio-chatbot, [data-testid="chatbot"]');
                chatbotElements.forEach(element => {
                    observer.observe(element, {
                        childList: true,
                        subtree: true,
                        characterData: true,
                        attributes: false // 减少不必要的触发
                    });
                    console.log('📋 开始监听聊天框:', element.tagName);
                });
                
                return observer;
            }
            
            // 监听用户滚动行为
            function setupScrollListener() {
                document.addEventListener('scroll', function(e) {
                    if (e.target.closest && e.target.closest('.chatbot')) {
                        isUserScrolling = true;
                        console.log('👆 用户手动滚动');
                        
                        // 清除之前的超时
                        if (scrollTimeout) {
                            clearTimeout(scrollTimeout);
                        }
                        
                        // 3秒后恢复自动滚动
                        scrollTimeout = setTimeout(() => {
                            isUserScrolling = false;
                            console.log('✅ 恢复自动滚动');
                        }, 3000);
                    }
                }, true);
            }
            
            // 定时强制滚动（流式聊天的强力保障）
            function setupPeriodicScroll() {
                setInterval(() => {
                    if (autoScrollEnabled && !isUserScrolling && shouldAutoScroll()) {
                        // 尝试多种滚动方法
                        const scrolled = forceScrollToBottom() || 
                                       bruteForceScroll() || 
                                       fallbackScroll();
                        
                        if (scrolled) {
                            console.log('🎯 定时滚动成功');
                        }
                    }
                }, 500); // 每500ms检查一次，确保流式内容及时滚动
            }
            
            // 暴力滚动方法：直接滚动所有可能的容器
            function bruteForceScroll() {
                console.log('💪 执行暴力滚动...');
                let scrolled = false;
                
                // 获取所有可能包含滚动内容的元素
                const allElements = [
                    ...document.querySelectorAll('.chatbot'),
                    ...document.querySelectorAll('.chatbot *'),
                    ...document.querySelectorAll('gradio-chatbot'),
                    ...document.querySelectorAll('gradio-chatbot *'),
                    ...document.querySelectorAll('[class*="chat"]'),
                    ...document.querySelectorAll('div')
                ];
                
                for (const element of allElements) {
                    if (element && element.scrollHeight > element.clientHeight) {
                        const oldScrollTop = element.scrollTop;
                        element.scrollTop = element.scrollHeight;
                        if (element.scrollTop !== oldScrollTop) {
                            console.log('💪 暴力滚动成功:', element);
                            scrolled = true;
                        }
                    }
                }
                
                return scrolled;
            }
            
            // 最后的备用滚动方法
            function fallbackScroll() {
                console.log('🆘 执行备用滚动方法...');
                
                // 尝试滚动窗口本身
                const oldScrollY = window.scrollY;
                window.scrollTo(0, document.body.scrollHeight);
                if (window.scrollY !== oldScrollY) {
                    console.log('🆘 窗口滚动成功');
                    return true;
                }
                
                // 尝试滚动body和html
                const targets = [document.body, document.documentElement];
                for (const target of targets) {
                    if (target) {
                        target.scrollTop = target.scrollHeight;
                        console.log('🆘 尝试滚动:', target.tagName);
                    }
                }
                
                return false;
            }
            
            // 初始化所有功能
            function initialize() {
                console.log('⚙️ 初始化自动滚动系统...');
                console.log('📅 时间:', new Date().toLocaleTimeString());
                console.log('🌐 document.readyState:', document.readyState);
                console.log('📄 DOM元素总数:', document.querySelectorAll('*').length);
                
                // 查找滚动容器
                const foundContainer = findScrollContainer();
                
                if (foundContainer) {
                    console.log('🎉 成功找到滚动容器，继续初始化...');
                    
                    // 设置内容监听
                    setupContentObserver();
                    
                    // 设置滚动监听
                    setupScrollListener();
                    
                    // 设置定时滚动
                    setupPeriodicScroll();
                    
                    // 初始滚动
                    setTimeout(() => {
                        forceScrollToBottom();
                    }, 500);
                    
                    console.log('✅ 自动滚动系统初始化完成');
                } else {
                    console.log('⏳ 未找到滚动容器，将在2秒后重试...');
                    setTimeout(() => {
                        console.log('🔄 重试初始化滚动系统...');
                        initialize();
                    }, 2000);
                }
            }
            
            // 手动查找容器的函数（用于调试）
            function debugFindContainer() {
                console.log('🐛 手动调试查找容器...');
                findScrollContainer();
            }
            
            // 禁用自动滚动（清除对话时使用）
            function disableAutoScroll() {
                autoScrollEnabled = false;
                console.log('🛑 自动滚动已禁用');
            }
            
            // 启用自动滚动（开始新对话时使用）
            function enableAutoScroll() {
                autoScrollEnabled = true;
                console.log('✅ 自动滚动已启用');
                // 启用后立即滚动到底部
                setTimeout(() => {
                    if (autoScrollEnabled) {
                        forceScrollToBottom();
                    }
                }, 100);
            }
            
            // 暴露到全局，便于手动调试和清除对话时使用
            window.debugScrollContainer = debugFindContainer;
            window.scrollToTop = forceScrollToTop;
            window.scrollToBottom = forceScrollToBottom;
            window.disableAutoScroll = disableAutoScroll;
            window.enableAutoScroll = enableAutoScroll;
            
            // 等待DOM准备就绪
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', initialize);
            } else {
                setTimeout(initialize, 500);
            }
            
            // 窗口大小变化时重新滚动
            window.addEventListener('resize', () => {
                setTimeout(forceScrollToBottom, 200);
            });
        }
        """,
    ) as demo:

        gr.Markdown(
            """
        # 🤖 Vertex Chat
        ### 基于 Workflow LLM Vertex 的智能聊天助手
        
        使用统一配置系统，支持多种 LLM 提供商
        """
        )

        with gr.Row():
            with gr.Column(scale=3):
                # 聊天界面
                chatbot = gr.Chatbot(
                    label="对话",
                    height=500,
                    container=True,
                    elem_classes=["chat-container"],
                    show_copy_button=True,  # 显示复制按钮
                    bubble_full_width=False,  # 消息气泡不占满宽度，更美观
                )

                with gr.Row():
                    msg = gr.Textbox(placeholder="输入您的问题...", lines=1, scale=4, container=False)
                    image_url_input = gr.Textbox(placeholder="粘贴图片URL（可选）", label="图片URL", lines=1, scale=3)
                    send_btn = gr.Button("发送", variant="primary", scale=1, size="sm")

                with gr.Row():
                    clear_btn = gr.Button("清除对话", variant="secondary")

            with gr.Column(scale=1):
                # 配置面板
                gr.Markdown("### ⚙️ 配置")

                system_prompt = gr.Textbox(
                    label="系统提示", value=default_system_prompt, lines=4, placeholder="自定义系统提示词..."
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

                model_info = gr.Markdown(f"**当前模型:** {current_model}", elem_classes=["model-info"])

                # 模型切换 - 先选择提供商，再选择模型
                gr.Markdown("#### 选择提供商")
                provider_dropdown = gr.Dropdown(
                    label="提供商",
                    choices=app.get_available_providers(),
                    interactive=True,
                    info="选择提供商后显示对应的模型",
                    allow_custom_value=False,
                )

                gr.Markdown("#### 选择模型")
                model_dropdown = gr.Dropdown(
                    label="模型", choices=[], interactive=True, info="选择要使用的具体模型", allow_custom_value=False
                )

                with gr.Row():
                    switch_btn = gr.Button("切换模型", variant="primary", scale=1)
                    refresh_btn = gr.Button("刷新", variant="secondary", scale=1)

                switch_result = gr.Textbox(label="切换结果", interactive=False, lines=2)

                # 手动输入模式（保留兼容性）
                with gr.Accordion("🔧 手动输入模式", open=False):
                    provider_input = gr.Textbox(
                        placeholder="输入提供商名称 (如: deepseek)", label="手动输入提供商", scale=4
                    )
                    manual_switch_btn = gr.Button("手动切换", scale=1)

                # Ollama本地模型管理
                gr.Markdown("### 🏠 本地模型(Ollama)")

                with gr.Row():
                    refresh_ollama_btn = gr.Button("刷新模型列表", scale=1)

                ollama_models = gr.Dropdown(
                    label="可用的Ollama模型",
                    choices=app.get_ollama_models(),
                    interactive=False,
                    info="已安装的本地模型",
                )

                # 工具管理
                gr.Markdown("### 🛠️ 工具管理")

                tools_enabled = gr.Checkbox(
                    label="启用Function Tools", value=app.tools_enabled, info="允许AI助手使用工具执行任务"
                )

                available_tools_display = gr.Dropdown(
                    label="可用工具",
                    choices=[f"{tool.name}: {tool.description}" for tool in app.available_tools],
                    interactive=False,
                    info=f"共有 {len(app.available_tools)} 个工具可用",
                )

                # 思考过程管理
                gr.Markdown("### 🤔 思考过程")

                enable_reasoning = gr.Checkbox(
                    label="启用思考过程", value=False, info="让AI显示推理过程（支持DeepSeek R1等模型）"
                )

                # MCP管理
                gr.Markdown("### 🔗 MCP集成")

                # MCP可用性检查
                mcp_available = app.check_mcp_availability() if MCP_AVAILABLE else False
                mcp_status_text = "✅ MCP功能可用" if mcp_available else "❌ MCP功能不可用"
                if not MCP_AVAILABLE:
                    mcp_status_text += " (模块未安装)"
                elif not mcp_available:
                    mcp_status_text += " (配置缺失)"

                mcp_status = gr.Markdown(f"**状态:** {mcp_status_text}")

                # 命令行工具测试区域
                with gr.Accordion("🖥️ 命令行工具测试", open=False):
                    cmd_input = gr.Textbox(label="命令", placeholder="例如: ls -la, python --version, pwd", lines=1)
                    cmd_execute_btn = gr.Button("执行命令", variant="secondary")
                    cmd_result = gr.JSON(label="执行结果", visible=True)

        # 事件绑定
        def respond(message, history, sys_prompt, image_url, enable_reasoning_val):
            multimodal_inputs = {}
            # 文本
            if message:
                multimodal_inputs["text"] = message
            # 图片URL处理
            if image_url and image_url.strip():
                # 验证图片URL
                url = image_url.strip()
                if "discordapp.com" in url or "discord.com" in url:
                    # Discord图片可能不被支持，给出提示
                    yield "", history + [(message or "", "⚠️ Discord图片链接可能不被支持，请尝试其他方式。")]
                    return
                elif "cdn.discordapp.com" in url:
                    # Discord CDN图片
                    yield "", history + [(message or "", "⚠️ Discord CDN图片链接可能不被支持，请尝试其他方式。")]
                    return
                else:
                    multimodal_inputs["image_url"] = url

            # 传递给chat_with_vertex - MCP状态由配置自动决定
            try:
                for result in app.chat_with_vertex(
                    multimodal_inputs, history, sys_prompt, enable_reasoning_val, enable_reasoning_val
                ):
                    # 确保输入框始终为空字符串，保持可输入状态
                    if isinstance(result, tuple) and len(result) == 2:
                        yield "", result[1]  # 输入框清空，更新聊天历史
                    else:
                        yield "", result  # 兼容其他格式
            except Exception as e:
                error_msg = f"处理失败: {str(e)}"
                if "500" in str(e) and multimodal_inputs.get("image_url"):
                    error_msg = "图片处理失败，可能是图片格式不支持或链接无效。请尝试：\n1. 使用其他图片\n2. 检查图片链接是否有效\n3. 确保图片格式为常见格式（JPG、PNG等）"
                yield "", history + [(message or "", error_msg)]

        def clear_conversation():
            """清除对话历史并重置滚动位置"""
            return [], ""  # 同时清空聊天历史和输入框

        def update_models_by_provider(selected_provider):
            """根据选择的提供商更新模型列表"""
            if not selected_provider:
                return gr.Dropdown(choices=[])

            # 移除状态图标获取纯提供商名称
            provider = selected_provider.replace("✅ ", "").replace("❌ ", "")
            models = app.get_models_by_provider(provider)
            return gr.Dropdown(choices=models)

        def switch_model_by_provider_and_model(selected_provider, selected_model):
            """根据提供商和模型切换"""
            if not selected_provider:
                return "❌ 请先选择提供商", model_info.value

            if not selected_model:
                return "❌ 请选择模型", model_info.value

            # 移除状态图标获取纯名称
            provider = selected_provider.replace("✅ ", "").replace("❌ ", "")
            model = selected_model.replace("✅ ", "").replace("❌ ", "")

            # 如果模型名称包含"(默认)"标记，移除它
            if " (默认)" in model:
                model = model.replace(" (默认)", "")

            # 检查模型是否可用
            if not selected_model.startswith("✅"):
                return f"❌ 模型 {model} 当前不可用", model_info.value

            result = app.switch_model_by_provider_and_name(provider, model)

            # 安全获取新模型名称
            new_model_name = "未知"
            if app.llm_model:
                try:
                    new_model_name = app.llm_model.model_name()
                except:
                    new_model_name = str(app.llm_model)

            new_model_info = f"**当前模型:** {new_model_name}"
            return result, new_model_info

        def refresh_provider_list():
            """刷新提供商列表"""
            return gr.Dropdown(choices=app.get_available_providers())

        def manual_switch_model(manual_provider):
            """手动切换模型（兼容性）"""
            if not manual_provider:
                return "❌ 请输入提供商名称", model_info.value

            result = app.switch_model_by_provider_and_name(manual_provider)

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

        def get_mcp_status():
            """获取MCP状态信息"""
            if not MCP_AVAILABLE:
                return "❌ MCP功能不可用 (模块未安装)"

            mcp_available = app.check_mcp_availability()
            if not mcp_available:
                return "❌ MCP功能不可用 (配置缺失)"

            # 获取更详细的状态信息
            status_parts = ["✅ MCP功能可用"]

            if app.get_mcp_manager():
                try:
                    # 可以添加更多状态检查
                    status_parts.append("- MCP管理器已初始化")
                except Exception as e:
                    status_parts.append(f"- MCP管理器错误: {e}")
            else:
                status_parts.append("- MCP管理器未初始化")

            return "\n".join(status_parts)

        # 绑定发送消息事件（支持流式输出）
        msg.submit(
            respond,
            inputs=[msg, chatbot, system_prompt, image_url_input, enable_reasoning],
            outputs=[msg, chatbot],
            show_progress="minimal",
        )
        send_btn.click(
            respond,
            inputs=[msg, chatbot, system_prompt, image_url_input, enable_reasoning],
            outputs=[msg, chatbot],
            show_progress="minimal",
        )

        # JavaScript事件处理 - 单独绑定以避免干扰主要功能
        msg.submit(
            js="""
            function() {
                console.log('💬 开始新对话，启用自动滚动');
                if (window.enableAutoScroll) {
                    window.enableAutoScroll();
                } else {
                    console.log('⚠️ enableAutoScroll函数未找到');
                }
            }
        """
        )
        send_btn.click(
            js="""
            function() {
                console.log('💬 开始新对话，启用自动滚动');
                if (window.enableAutoScroll) {
                    window.enableAutoScroll();
                } else {
                    console.log('⚠️ enableAutoScroll函数未找到');
                }
            }
        """
        )

        # 绑定清除对话事件
        clear_btn.click(clear_conversation, outputs=[chatbot, msg])

        # JavaScript事件处理 - 单独绑定以避免干扰主要功能
        clear_btn.click(
            js="""
            function() {
                console.log('🧹 清除对话，禁用自动滚动');
                
                // 禁用自动滚动
                if (window.disableAutoScroll) {
                    window.disableAutoScroll();
                } else {
                    console.log('⚠️ disableAutoScroll函数未找到');
                }
                
                // 滚动到顶部（只执行一次，不再重复）
                function scrollToTopOnce() {
                    // 使用全局函数
                    if (window.scrollToTop) {
                        window.scrollToTop();
                        console.log('✅ 使用全局函数滚动到顶部');
                        return;
                    }
                    
                    // 备用方案
                    const chatbot = document.querySelector('.chatbot');
                    if (chatbot) {
                        const scrollContainer = chatbot.querySelector('div[style*="overflow"], .overflow-y-auto') || chatbot.querySelector('div');
                        if (scrollContainer) {
                            scrollContainer.scrollTop = 0;
                            console.log('✅ 使用备用方案滚动到顶部');
                        }
                    }
                    
                    // 全局滚动重置
                    document.body.scrollTop = 0;
                    document.documentElement.scrollTop = 0;
                    window.scrollTo(0, 0);
                }
                
                // 延迟执行滚动到顶部，确保DOM更新完成
                setTimeout(scrollToTopOnce, 100);
                
                console.log('🎯 清除对话完成，自动滚动已禁用');
            }
        """
        )

        # 绑定提供商选择事件 - 更新模型列表
        provider_dropdown.change(update_models_by_provider, inputs=[provider_dropdown], outputs=[model_dropdown])

        # 绑定模型切换事件
        switch_btn.click(
            switch_model_by_provider_and_model,
            inputs=[provider_dropdown, model_dropdown],
            outputs=[switch_result, model_info],
        )

        # 绑定刷新事件
        refresh_btn.click(refresh_provider_list, outputs=[provider_dropdown])

        # 绑定手动切换事件
        manual_switch_btn.click(manual_switch_model, inputs=[provider_input], outputs=[switch_result, model_info])

        # 绑定Ollama模型刷新事件
        refresh_ollama_btn.click(refresh_ollama_models, outputs=[ollama_models])

        # 绑定工具启用切换事件
        tools_enabled.change(toggle_tools, inputs=[tools_enabled], outputs=[])

        # 绑定命令执行事件
        cmd_execute_btn.click(execute_command_test, inputs=[cmd_input], outputs=[cmd_result])

    return demo


def main():
    """主函数"""
    args = parse_args()

    try:
        # 初始化应用
        logger.info("正在初始化 Vertex Chat 应用...")
        app = WorkflowChatApp(config_path=args.config)

        # 创建 Gradio 界面
        demo = create_gradio_interface(app)

        # 启动应用
        logger.info(f"启动 Vertex Chat 应用在 {args.host}:{args.port}")
        demo.launch(server_name=args.host, server_port=args.port, share=args.share, show_error=True)

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
