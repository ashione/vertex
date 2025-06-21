#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度研究工作流 Gradio 应用
基于 DeepResearchWorkflow 的交互式深度研究分析工具
"""

import argparse
import asyncio
import json
import os
import re
import sys
import threading
from datetime import datetime
from typing import Any, Dict, List, Tuple

import gradio as gr

from vertex_flow.utils.logger import setup_logger
from vertex_flow.workflow.app.deep_research_workflow import DeepResearchWorkflow
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.event_channel import EventType
from vertex_flow.workflow.constants import WORKFLOW_COMPLETE, WORKFLOW_FAILED

# 配置日志
logger = setup_logger(__name__)


class DeepResearchApp:
    """深度研究工作流 Gradio 应用"""
    
    # 类常量：阶段映射配置
    STAGE_MAPPING = {
        "topic_analysis": ("主题分析", "🔍"),
        "research_planning": ("研究规划", "📋"),
        "information_collection": ("信息收集", "📚"),
        "deep_analysis": ("深度分析", "🔬"),
        "cross_validation": ("交叉验证", "✅"),
        "summary_report": ("总结报告", "📄")
    }
    
    # 阶段顺序列表
    STAGE_ORDER = ["topic_analysis", "research_planning", "information_collection", 
                   "deep_analysis", "cross_validation", "summary_report"]
    
    # Markdown检测模式
    MARKDOWN_PATTERNS = [
        r'^#+\s',           # 标题 # ## ###
        r'\*\*.*\*\*',      # 粗体 **text**
        r'\*.*\*',          # 斜体 *text*
        r'^-\s+',           # 列表项 - item
        r'^\d+\.\s+',       # 编号列表 1. item
        r'\[.*\]\(.*\)',    # 链接 [text](url)
        r'```',             # 代码块 ```
        r'`.*`',            # 行内代码 `code`
        r'^\|.*\|',         # 表格 |col1|col2|
        r'^>',              # 引用 > text
    ]
    
    # 界面常量
    CONTENT_PREVIEW_LENGTH = 2000  # 内容预览长度
    STREAM_CONTENT_LENGTH = 1500   # 流式内容显示长度
    FINAL_REPORT_MIN_LENGTH = 100  # 最终报告最小长度
    LONG_TEXT_MIN_LENGTH = 100     # 长文本最小长度
    
    def __init__(self, config_path: str = None):
        """初始化应用"""
        try:
            # 使用提供的配置路径或默认配置
            if config_path is None:
                # 使用环境变量或默认配置路径
                from vertex_flow.workflow.utils import default_config_path
                config_path = default_config_path("llm.yml")
                logger.info(f"使用默认配置路径: {config_path}")
            else:
                config_path = os.path.abspath(config_path)
                logger.info(f"使用指定配置路径: {config_path}")
            
            # 检查配置文件是否存在
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"配置文件不存在: {config_path}")
            
            self.service = VertexFlowService(config_path)
            self.workflow_builder = DeepResearchWorkflow(self.service)
            self.current_workflow = None
            
            # 初始化阶段历史记录
            self.stage_history = {}
            self.completed_stages = set()
            self.current_research_topic = ""
            self.workflow_running = False
            
            self._initialize_llm()
            logger.info("Deep Research 应用初始化成功")
        except Exception as e:
            logger.error(f"Deep Research 应用初始化失败: {e}")
            raise
    
    def _initialize_llm(self):
        """初始化 LLM 模型"""
        try:
            self.llm_model = self.service.get_chatmodel()
            if self.llm_model is None:
                raise ValueError("无法获取聊天模型，请检查配置文件")
            
            try:
                model_name = self.llm_model.model_name()
            except:
                model_name = str(self.llm_model)
            
            logger.info(f"成功初始化聊天模型: {model_name}")
            
        except Exception as e:
            logger.error(f"初始化 LLM 失败: {e}")
            raise
    
    def start_research(self, research_topic: str, save_intermediate: bool, save_final_report: bool, enable_stream: bool):
        """开始深度研究"""
        if not research_topic.strip():
            yield "❌ 请输入研究主题", "", "", [], gr.update()
            return
        
        try:
            # 重置阶段历史记录
            self.stage_history = {}
            self.completed_stages = set()
            self.current_research_topic = research_topic.strip()
            self.workflow_running = True
            
            # 准备输入数据
            input_data = {
                "content": research_topic.strip(),
                "stream": enable_stream,
                "save_intermediate": save_intermediate,
                "save_final_report": save_final_report,
                "env_vars": {},
                "user_vars": {}
            }
            
            logger.info(f"开始深度研究: {research_topic}")
            
            # 创建工作流
            self.current_workflow = self.workflow_builder.create_workflow(input_data)
            
            if enable_stream:
                yield from self._execute_workflow_stream(input_data, research_topic)
            else:
                yield from self._execute_workflow_batch(input_data, research_topic)
                
        except Exception as e:
            error_msg = f"研究执行失败: {str(e)}"
            logger.error(error_msg)
            yield error_msg, "", "", [], gr.update()
    
    def _execute_workflow_stream(self, input_data: Dict[str, Any], research_topic: str):
        """流式执行工作流"""
        try:
            # 先执行工作流（在后台线程中）
            def run_workflow():
                try:
                    self.current_workflow.execute_workflow(input_data, stream=True)
                except Exception as e:
                    logger.error(f"工作流执行错误: {e}")
            
            # 在后台线程中启动工作流
            workflow_thread = threading.Thread(target=run_workflow)
            workflow_thread.daemon = True
            workflow_thread.start()
            
            # 流式获取事件
            yield from self._stream_workflow_events()
                
        except Exception as e:
            error_msg = f"❌ 流式执行失败: {str(e)}"
            logger.error(error_msg)
            yield error_msg, "执行失败", f"执行失败: {str(e)}"
    
    def _stream_workflow_events(self):
        """流式获取工作流事件"""
        # 初始化状态
        progress_log = []
        current_stage = ""
        current_content = ""
        previous_stage_buttons = []
        
        def add_log(message):
            timestamp = datetime.now().strftime('%H:%M:%S')
            progress_log.append(f"[{timestamp}] {message}")
        
        # 使用类的辅助方法
        create_stage_buttons = self._create_stage_buttons
        should_update_stage_selector = self._should_update_stage_selector
        
        add_log("🚀 开始深度研究分析...")
        initial_buttons = create_stage_buttons()
        previous_stage_buttons = initial_buttons.copy()
        yield "🚀 开始深度研究分析...", "准备中", "\n".join(progress_log[-10:]), initial_buttons, gr.update()
        
        async def stream_events():
            nonlocal current_stage, current_content, previous_stage_buttons
            
            try:
                # 监听工作流事件
                async for event in self.current_workflow.astream([EventType.MESSAGES, EventType.VALUES, EventType.UPDATES]):
                    event_type = type(event).__name__
                    logger.info(f"收到事件类型: {event_type}, 内容: {event}")
                    
                    # 处理消息事件（流式输出内容）
                    if 'vertex_id' in event and 'message' in event:
                        vertex_id = event['vertex_id']
                        message = event.get('message', '')
                        status = event.get('status', '')
                        
                        # 检查是否是我们关心的阶段
                        for stage_id, (stage_name, stage_icon) in self.STAGE_MAPPING.items():
                            if stage_id in vertex_id:
                                current_stage = f"{stage_icon} {stage_name}"
                                
                                if status == "start":
                                    add_log(f"开始 {stage_name}...")
                                    current_buttons = create_stage_buttons()
                                    stage_selector_update = gr.update(choices=current_buttons) if should_update_stage_selector(previous_stage_buttons, current_buttons) else gr.update()
                                    if should_update_stage_selector(previous_stage_buttons, current_buttons):
                                        previous_stage_buttons = current_buttons.copy()
                                    yield f"⏳ 正在执行: {stage_name}", current_stage, "\n".join(progress_log[-10:]), current_buttons, stage_selector_update
                                    break
                                elif status == "end":
                                    self.completed_stages.add(stage_id)
                                    add_log(f"完成 {stage_name}")
                                    # 获取完整内容
                                    if stage_id in self.stage_history:
                                        current_content = self.stage_history[stage_id]['content']
                                        logger.info(f"阶段 {stage_name} 完成，内容长度: {len(current_content)}")
                                    current_buttons = create_stage_buttons()
                                    stage_selector_update = gr.update(choices=current_buttons) if should_update_stage_selector(previous_stage_buttons, current_buttons) else gr.update()
                                    if should_update_stage_selector(previous_stage_buttons, current_buttons):
                                        previous_stage_buttons = current_buttons.copy()
                                    yield f"✅ 完成: {stage_name}", current_content[:2000] + "..." if len(current_content) > 2000 else current_content, "\n".join(progress_log[-10:]), current_buttons, stage_selector_update
                                    break
                                elif message:
                                    # 累积当前阶段的内容
                                    if stage_id not in self.stage_history:
                                        self.stage_history[stage_id] = {
                                            'name': stage_name,
                                            'icon': stage_icon,
                                            'content': "",
                                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                        }
                                    self.stage_history[stage_id]['content'] += message
                                    current_content = self.stage_history[stage_id]['content']
                                    
                                    # 显示实时内容（限制长度避免界面卡顿）
                                    display_content = current_content[-1500:] if len(current_content) > 1500 else current_content
                                    
                                    # 为流式内容添加markdown格式提示
                                    if display_content.strip():
                                        # 检测是否为markdown内容
                                        if len(display_content) > 50 and any(re.search(pattern, display_content, re.MULTILINE) for pattern in self.MARKDOWN_PATTERNS):
                                            # 可能是markdown，添加适当的格式
                                            formatted_display = f"### 📝 {stage_name} 进行中...\n\n{display_content}"
                                        else:
                                            # 普通文本，用代码块格式显示
                                            formatted_display = f"### 📝 {stage_name} 进行中...\n\n```\n{display_content}\n```"
                                    else:
                                        formatted_display = f"### 📝 {stage_name} 进行中...\n\n正在生成内容..."
                                    
                                    current_buttons = create_stage_buttons()
                                    stage_selector_update = gr.update(choices=current_buttons) if should_update_stage_selector(previous_stage_buttons, current_buttons) else gr.update()
                                    if should_update_stage_selector(previous_stage_buttons, current_buttons):
                                        previous_stage_buttons = current_buttons.copy()
                                    yield f"⏳ 正在执行: {stage_name}", formatted_display, "\n".join(progress_log[-10:]), current_buttons, stage_selector_update
                                    break
                    
                    # 处理状态事件
                    elif 'status' in event:
                        status = event['status']
                        if status == WORKFLOW_COMPLETE:
                            self.workflow_running = False
                            add_log("✅ 深度研究完成!")
                            # 获取最终结果
                            results = self.current_workflow.result()
                            logger.debug(f"工作流结果: {results}")
                            
                            if results and 'sink' in results:
                                final_report = results['sink'].get('final_report', '没有生成报告')
                                file_path = results['sink'].get('file_path', '')
                                
                                if file_path:
                                    add_log(f"📁 报告已保存到: {file_path}")
                                
                                logger.debug(f"最终报告长度: {len(final_report)}")
                                current_buttons = create_stage_buttons()
                                yield "✅ 深度研究完成!", final_report, "\n".join(progress_log[-10:]), current_buttons, gr.update(choices=current_buttons)
                            else:
                                # 尝试从阶段历史中获取最终报告
                                if 'summary_report' in self.stage_history:
                                    final_report = self.stage_history['summary_report']['content']
                                    add_log(f"从阶段历史获取最终报告，长度: {len(final_report)}")
                                    current_buttons = create_stage_buttons()
                                    yield "✅ 深度研究完成!", final_report, "\n".join(progress_log[-10:]), current_buttons, gr.update(choices=current_buttons)
                                else:
                                    current_buttons = create_stage_buttons()
                                    yield "❌ 工作流执行完成但没有获取到结果", "", "\n".join(progress_log), current_buttons, gr.update(choices=current_buttons)
                            break
                        elif status == WORKFLOW_FAILED:
                            self.workflow_running = False
                            add_log("❌ 工作流执行失败")
                            current_buttons = create_stage_buttons()
                            yield "❌ 工作流执行失败", "", "\n".join(progress_log[-10:]), current_buttons, gr.update(choices=current_buttons)
                            break
                    
                    # 处理值事件（顶点输出）
                    elif 'vertex_id' in event and 'output' in event:
                        vertex_id = event['vertex_id']
                        output = event.get('output', '')
                        
                        # 检查是否是我们关心的阶段
                        for stage_id, (stage_name, stage_icon) in self.STAGE_MAPPING.items():
                            if stage_id in vertex_id and output:
                                # 保存到阶段历史记录
                                self.stage_history[stage_id] = {
                                    'name': stage_name,
                                    'icon': stage_icon,
                                    'content': output,
                                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                }
                                self.completed_stages.add(stage_id)
                                
                                # 显示阶段完成的内容
                                display_content = output[:2000] + "..." if len(output) > 2000 else output
                                add_log(f"✅ {stage_name} 生成了 {len(output)} 字符的内容")
                                current_buttons = create_stage_buttons()
                                stage_selector_update = gr.update(choices=current_buttons) if should_update_stage_selector(previous_stage_buttons, current_buttons) else gr.update()
                                if should_update_stage_selector(previous_stage_buttons, current_buttons):
                                    previous_stage_buttons = current_buttons.copy()
                                yield f"✅ 完成: {stage_name}", display_content, "\n".join(progress_log[-10:]), current_buttons, stage_selector_update
                                break
                    
            except Exception as e:
                logger.error(f"事件流处理错误: {e}")
                add_log(f"❌ 事件处理错误: {str(e)}")
                current_buttons = create_stage_buttons()
                yield f"❌ 事件处理错误: {str(e)}", "", "\n".join(progress_log[-10:]), current_buttons, gr.update(choices=current_buttons)
        
        # 运行异步事件流
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def run_stream():
                async for result in stream_events():
                    yield result
            
            # 由于Gradio需要同步生成器，我们需要同步运行异步代码
            async_gen = run_stream()
            
            async def get_next():
                try:
                    return await async_gen.__anext__()
                except StopAsyncIteration:
                    return None
            
            while True:
                try:
                    result = loop.run_until_complete(get_next())
                    if result is None:
                        break
                    yield result
                except Exception as e:
                    logger.error(f"事件循环错误: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"异步事件流错误: {e}")
            yield f"❌ 异步处理错误: {str(e)}", "", f"异步处理错误: {str(e)}", [], gr.update()
        finally:
            try:
                loop.close()
            except:
                pass
    
    def _execute_workflow_batch(self, input_data: Dict[str, Any], research_topic: str):
        """批量执行工作流"""
        try:
            status_msg = "🚀 开始深度研究分析..."
            yield status_msg, "准备中...", "开始执行深度研究工作流", [], gr.update()
            
            # 执行工作流
            self.current_workflow.execute_workflow(input_data, stream=False)
            
            # 获取结果
            results = self.current_workflow.result()
            
            if results and 'sink' in results:
                final_report = results['sink'].get('final_report', '没有生成报告')
                file_path = results['sink'].get('file_path', '')
                
                completion_msg = "✅ 深度研究完成!"
                if file_path:
                    completion_msg += f"\n📁 报告已保存到: {file_path}"
                
                yield completion_msg, final_report, f"研究完成，生成了 {len(final_report)} 字符的报告", [], gr.update()
            else:
                yield "❌ 工作流执行完成但没有获取到结果", "", "执行完成但结果为空", [], gr.update()
                
        except Exception as e:
            error_msg = f"❌ 批量执行失败: {str(e)}"
            logger.error(error_msg)
            yield error_msg, "", f"执行失败: {str(e)}", [], gr.update()
    
    def get_workflow_status(self):
        """获取当前工作流状态"""
        if self.current_workflow:
            try:
                status = self.current_workflow.status()
                return f"工作流状态: {status}"
            except:
                return "无法获取工作流状态"
        return "没有正在执行的工作流"
    
    def get_stage_content(self, stage_button_text: str) -> str:
        """根据阶段按钮文本获取阶段内容"""
        logger.debug(f"请求查看阶段: {stage_button_text}")
        logger.debug(f"当前阶段历史: {list(self.stage_history.keys())}")
        
        if not stage_button_text or not self.stage_history:
            return "请先运行深度研究工作流"
        
        # 解析按钮文本，提取阶段名称
        for stage_id, stage_info in self.stage_history.items():
            expected_button_text = f"{stage_info['icon']} {stage_info['name']}"
            logger.debug(f"比较: '{expected_button_text}' vs '{stage_button_text}'")
            
            if expected_button_text == stage_button_text:
                logger.debug(f"找到阶段内容，长度: {len(stage_info['content'])}")
                return self._format_stage_content(stage_info, include_metadata=True)
        
        # 如果没有精确匹配，尝试模糊匹配
        for stage_id, stage_info in self.stage_history.items():
            if stage_info['name'] in stage_button_text or stage_button_text in stage_info['name']:
                logger.debug(f"模糊匹配找到阶段内容: {stage_info['name']}")
                return self._format_stage_content(stage_info, include_metadata=True)
        
        # 返回调试信息
        available_stages = [f"{info['icon']} {info['name']}" for info in self.stage_history.values()]
        debug_info = f"未找到阶段内容: {stage_button_text}\n\n"
        debug_info += f"可用阶段:\n" + "\n".join([f"- {stage}" for stage in available_stages])
        debug_info += f"\n\n当前阶段历史记录数量: {len(self.stage_history)}"
        
        return debug_info
    
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
            new_model = self.service.get_chatmodel_by_provider(provider)
            if new_model:
                self.llm_model = new_model
                # 重新初始化工作流构建器
                self.workflow_builder = DeepResearchWorkflow(self.service)
                
                try:
                    model_name = new_model.model_name()
                except:
                    model_name = str(new_model)
                
                logger.info(f"已切换到模型: {provider} - {model_name}")
                return f"✅ 已切换到: {provider} - {model_name}"
            else:
                return f"❌ 无法切换到模型: {provider}"
        except Exception as e:
            logger.error(f"切换模型失败: {e}")
            return f"❌ 切换失败: {str(e)}"
    
    def is_markdown_content(self, content: str) -> bool:
        """智能检测内容是否包含markdown格式"""
        if not content or len(content.strip()) < 10:
            return False
        
        # 使用类常量检测markdown特征
        for pattern in self.MARKDOWN_PATTERNS:
            if re.search(pattern, content, re.MULTILINE):
                return True
        
        # 检测多个换行符（markdown文档特征）
        if content.count('\n\n') >= 2:
            return True
            
        return False
    
    def enhance_markdown_content(self, content: str) -> str:
        """增强markdown内容的显示效果"""
        if not content:
            return content
        
        # 为标题添加适当的间距
        content = re.sub(r'(?<!^)(\n)(#+\s)', r'\n\n\2', content, flags=re.MULTILINE)
        
        # 确保列表项格式正确
        content = re.sub(r'(\n)([•\-\*]\s)', r'\1\n\2', content)
        
        # 确保编号列表格式正确
        content = re.sub(r'(\n)(\d+\.\s)', r'\1\n\2', content)
        
        # 确保代码块前后有空行
        content = re.sub(r'(?<!^)(\n)(```)', r'\n\n\2', content)
        content = re.sub(r'(```.*?```\n)(?!\n)', r'\1\n', content, flags=re.DOTALL)
        
        return content.strip()
    
    def _format_stage_content(self, stage_info: Dict[str, str], include_metadata: bool = True) -> str:
        """格式化阶段内容显示"""
        content = stage_info['content']
        
        if include_metadata:
            formatted_content = f"## {stage_info['icon']} {stage_info['name']}\n\n"
            formatted_content += f"**研究主题:** {self.current_research_topic}\n\n"
            formatted_content += f"**完成时间:** {stage_info['timestamp']}\n\n"
            formatted_content += f"**内容长度:** {len(content)} 字符\n\n"
            formatted_content += "---\n\n"
            formatted_content += content
            return formatted_content
        else:
            return content
    
    def _create_stage_buttons(self) -> List[str]:
        """创建已完成阶段的按钮列表"""
        buttons = []
        logger.debug(f"创建阶段按钮，已完成阶段: {self.completed_stages}")
        logger.debug(f"阶段历史记录: {list(self.stage_history.keys())}")
        
        for stage_id in self.STAGE_ORDER:
            if stage_id in self.completed_stages and stage_id in self.stage_history:
                stage_info = self.stage_history[stage_id]
                button_text = f"{stage_info['icon']} {stage_info['name']}"
                buttons.append(button_text)
                logger.debug(f"添加阶段按钮: {button_text}")
        
        return buttons
    
    def _should_update_stage_selector(self, previous_buttons: List[str], current_buttons: List[str]) -> bool:
        """判断是否需要更新阶段选择器（只有新增阶段时才更新）"""
        return len(current_buttons) > len(previous_buttons)
    
    def _format_content_for_display(self, content: str, format_mode: str, is_final_report: bool = False) -> str:
        """格式化内容用于显示"""
        if format_mode == "Markdown渲染":
            if self.is_markdown_content(content):
                return self.enhance_markdown_content(content)
            elif is_final_report:
                return f"## 📄 研究报告\n\n```text\n{content}\n```"
            elif len(content) > self.LONG_TEXT_MIN_LENGTH:
                return f"```\n{content}\n```"
            else:
                return content
        else:
            return content
    
    def _create_gradio_update_tuple(self, status: str, content: str, progress: str, 
                                   stage_buttons: List[str], format_mode: str,
                                   is_final_report: bool = False) -> tuple:
        """创建标准的Gradio更新元组"""
        if is_final_report:
            formatted_content = self._format_content_for_display(content, format_mode, True)
            if format_mode == "Markdown渲染":
                return (status, "✅ 研究完成", progress, 
                       formatted_content, 
                       gr.update(value=content, visible=False),
                       gr.update(visible=True),
                       gr.update(visible=False),
                       gr.update(choices=stage_buttons))
            else:
                return (status, "✅ 研究完成", progress, 
                       "请切换到原始文本模式查看完整内容", 
                       gr.update(value=content, visible=True),
                       gr.update(visible=False),
                       gr.update(visible=True),
                       gr.update(choices=stage_buttons))
        else:
            stage_md_display = self._format_content_for_display(content, format_mode)
            return (status, stage_md_display, progress, 
                   gr.update(),  # research_report_md
                   gr.update(),  # research_report_text
                   gr.update(visible=True if format_mode == "Markdown渲染" else False),
                   gr.update(value=content, visible=True if format_mode == "原始文本" else False),
                   gr.update(choices=stage_buttons))


def parse_args():
    """解析命令行参数（用于直接运行此文件时）"""
    parser = argparse.ArgumentParser(description="Deep Research Workflow Gradio App")
    parser.add_argument("--host", default="127.0.0.1", help="主机地址")
    parser.add_argument("--port", type=int, default=7861, help="端口号")
    parser.add_argument("--share", action="store_true", help="创建公共链接")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--dev", action="store_true", help="开发模式")
    return parser.parse_args()


def create_gradio_interface(app: DeepResearchApp):
    """创建 Gradio 界面"""
    
    with gr.Blocks(
        title="Deep Research - 深度研究工作流",
        theme=gr.themes.Soft(),
        css="""
        .research-container { 
            max-height: 600px; 
            overflow-y: auto; 
            scroll-behavior: smooth;
        }
        .status-info { 
            background-color: #f0f8ff; 
            padding: 10px; 
            border-radius: 5px; 
            margin: 5px 0; 
        }
        .progress-info {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            white-space: pre-wrap;
        }
        .report-container {
            max-height: 500px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 15px;
            border-radius: 5px;
            background-color: #fafafa;
        }
        /* Markdown渲染样式优化 */
        .report-container h1, .report-container h2, .report-container h3 {
            color: #2563eb;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }
        .report-container h1 {
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 0.3em;
        }
        .report-container h2 {
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 0.2em;
        }
        .report-container ul, .report-container ol {
            padding-left: 1.5em;
            margin: 0.5em 0;
        }
        .report-container li {
            margin: 0.2em 0;
        }
        .report-container blockquote {
            border-left: 4px solid #e5e7eb;
            margin: 1em 0;
            padding-left: 1em;
            color: #6b7280;
        }
        .report-container code {
            background-color: #f3f4f6;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: 'Monaco', 'Consolas', monospace;
        }
        .report-container pre {
            background-color: #1f2937;
            color: #f9fafb;
            padding: 1em;
            border-radius: 5px;
            overflow-x: auto;
        }
        .report-container table {
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }
        .report-container th, .report-container td {
            border: 1px solid #e5e7eb;
            padding: 0.5em;
            text-align: left;
        }
        .report-container th {
            background-color: #f3f4f6;
            font-weight: bold;
        }
        /* 阶段选择器样式 */
        .stage-selector {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 8px;
        }
        .stage-selector label {
            font-weight: 600;
            color: #374151;
        }
        /* 标签页内容样式优化 */
        .gradio-tabs .gradio-tabitem {
            padding: 20px;
        }
        /* 阶段详情显示样式 */
        .stage-detail {
            background-color: #fefefe;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            max-height: 600px;
            overflow-y: auto;
        }
        /* 标签页中的报告容器样式 */
        .gradio-tabs .report-container {
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 20px;
            border-radius: 8px;
            background-color: #fafafa;
            margin-top: 10px;
        }
        """,
    ) as demo:
        
        gr.Markdown("""
        # 🔬 Deep Research - 深度研究工作流
        
        **专业的自动化深度研究分析工具**
        
        本工具通过六个连续的分析阶段，对复杂主题进行全面、深入的研究和分析：
        1. 📊 **主题分析** - 分析研究主题的核心内容和研究范围
        2. 📋 **研究规划** - 制定详细的研究计划和分析框架  
        3. 📚 **信息收集** - 系统性收集基础信息和背景资料
        4. 🔬 **深度分析** - 进行趋势分析和关联分析
        5. ✅ **交叉验证** - 验证关键事实和数据准确性
        6. 📄 **总结报告** - 整合所有研究成果生成完整报告
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                # 主要研究界面
                gr.Markdown("## 🎯 研究配置")
                
                research_topic = gr.Textbox(
                    label="研究主题",
                    placeholder="请输入您想要深度研究的主题，例如：人工智能在医疗领域的应用与发展趋势",
                    lines=3,
                    max_lines=5
                )
                
                with gr.Row():
                    save_intermediate = gr.Checkbox(
                        label="保存中间文档",
                        value=True,
                        info="保存每个阶段的分析结果"
                    )
                    save_final_report = gr.Checkbox(
                        label="保存最终报告",
                        value=True,
                        info="将最终报告保存为文件"
                    )
                    enable_stream = gr.Checkbox(
                        label="流式模式",
                        value=True,
                        info="实时显示分析进度"
                    )
                
                with gr.Row():
                    start_btn = gr.Button("🚀 开始深度研究", variant="primary", scale=2)
                    status_btn = gr.Button("📊 查看状态", scale=1)
                
                # 状态显示
                gr.Markdown("## 📈 执行状态")
                
                status_display = gr.Textbox(
                    label="当前状态",
                    value="等待开始研究...",
                    interactive=False,
                    elem_classes="status-info"
                )
                
                # 当前阶段显示（支持markdown）
                current_stage_md = gr.Markdown(
                    value="**当前阶段:** 未开始",
                    visible=True
                )
                
                current_stage_text = gr.Textbox(
                    label="当前阶段",
                    value="未开始",
                    interactive=False,
                    visible=False
                )
                
                progress_log = gr.Textbox(
                    label="进度日志",
                    value="",
                    interactive=False,
                    lines=8,
                    elem_classes="progress-info"
                )
                
                # 已完成阶段历史查看
                gr.Markdown("## 📋 阶段历史")
                stage_selector = gr.Radio(
                    choices=[],
                    label="已完成阶段",
                    info="点击直接查看阶段详细内容",
                    interactive=True,
                    elem_classes="stage-selector"
                )
            
            with gr.Column(scale=1):
                # 显示格式控制
                gr.Markdown("## 🎨 显示设置")
                
                format_toggle = gr.Radio(
                    choices=["Markdown渲染", "原始文本"],
                    value="Markdown渲染",
                    label="报告显示格式",
                    info="选择研究报告的显示格式"
                )
                
                # 模型配置和管理
                gr.Markdown("## ⚙️ 模型配置")
                
                # 安全获取当前模型名称
                try:
                    current_model_name = app.llm_model.model_name()
                except:
                    current_model_name = str(app.llm_model)
                
                model_info = gr.Markdown(f"**当前模型:** {current_model_name}")
                
                model_list = gr.Dropdown(
                    label="可用模型",
                    choices=app.get_available_models(),
                    interactive=False,
                    info="系统中配置的所有模型"
                )
                
                provider_input = gr.Textbox(
                    placeholder="输入提供商名称切换模型",
                    label="切换模型",
                    info="例如: deepseek, openai, ollama"
                )
                
                switch_btn = gr.Button("切换模型")
                
                switch_result = gr.Textbox(
                    label="切换结果",
                    interactive=False,
                    lines=2
                )
                
        
        # 内容显示区域 - 使用标签页组织
        with gr.Tabs():
            with gr.TabItem("📄 研究报告"):
                # Markdown渲染显示区域
                research_report_md = gr.Markdown(
                    value="研究报告将在这里显示...",
                    elem_classes="report-container",
                    visible=True
                )
                
                # 原始文本显示区域  
                research_report_text = gr.Textbox(
                    label="深度研究报告（原始文本）",
                    value="研究报告将在这里显示...",
                    interactive=False,
                    lines=20,
                    elem_classes="report-container",
                    visible=False
                )
            
            with gr.TabItem("🔍 阶段详情"):
                stage_detail_display = gr.Markdown(
                    value="点击左侧阶段按钮查看详细内容...",
                    elem_classes="report-container"
                )
        
        # 使用示例
        with gr.Accordion("💡 使用示例", open=False):
            gr.Markdown("""
            ### 研究主题示例：
            
            **科技类：**
            - 人工智能在医疗领域的应用与发展趋势
            - 区块链技术在金融科技中的创新应用
            - 量子计算技术的发展现状与未来展望
            - 可持续能源技术的发展趋势
            
            **商业类：**
            - 新零售模式的发展趋势与挑战
            - 远程办公对企业管理模式的影响
            - 数字化转型在传统制造业的应用
            
            **社会类：**
            - 老龄化社会的挑战与应对策略
            - 数字鸿沟对社会公平的影响
            - 在线教育的发展趋势与质量保障
            
            ### 使用建议：
            1. 📝 **明确主题**：选择具体、有针对性的研究主题
            2. ⚙️ **选择模式**：建议开启流式模式查看实时进度
            3. 💾 **保存设置**：建议保存中间文档和最终报告
            4. 🎨 **显示格式**：智能识别Markdown格式，自动渲染标题、列表、代码块等
            5. ⏰ **耐心等待**：深度研究需要较长时间，请耐心等待
            
            ### 💡 Markdown支持特性：
            - ✅ **自动检测**：智能识别内容中的Markdown格式
            - ✅ **样式渲染**：支持标题、粗体、斜体、列表、代码块等
            - ✅ **表格支持**：自动渲染表格格式
            - ✅ **代码高亮**：代码块自动语法高亮
            - ✅ **双模式**：可在Markdown渲染和原始文本间切换
            """)
        
        # 事件绑定
        def handle_start_research(topic, save_inter, save_final, stream_mode, format_mode):
            """处理开始研究事件"""
            for result in app.start_research(topic, save_inter, save_final, stream_mode):
                if len(result) == 5:
                    status, stage_or_report, progress, stage_buttons, _ = result
                    if "完成!" in status and len(stage_or_report) > 100:  # 这是最终报告
                        # 根据格式模式决定显示方式
                        if format_mode == "Markdown渲染":
                            # 智能检测和增强markdown
                            if app.is_markdown_content(stage_or_report):
                                enhanced_content = app.enhance_markdown_content(stage_or_report)
                                yield (status, "✅ 研究完成", progress, 
                                      enhanced_content, 
                                      gr.update(value=stage_or_report, visible=False),
                                      gr.update(visible=True),
                                      gr.update(visible=False),
                                      gr.update(choices=stage_buttons))
                            else:
                                # 不是markdown，显示为普通文本但用markdown组件显示
                                formatted_content = f"## 📄 研究报告\n\n```text\n{stage_or_report}\n```"
                                yield (status, "✅ 研究完成", progress, 
                                      formatted_content, 
                                      gr.update(value=stage_or_report, visible=False),
                                      gr.update(visible=True),
                                      gr.update(visible=False),
                                      gr.update(choices=stage_buttons))
                        else:
                            # 原始文本模式
                            yield (status, "✅ 研究完成", progress, 
                                  "请切换到原始文本模式查看完整内容", 
                                  gr.update(value=stage_or_report, visible=True),
                                  gr.update(visible=False),
                                  gr.update(visible=True),
                                  gr.update(choices=stage_buttons))
                    else:  # 这是进度更新或中间阶段内容
                        # 智能处理当前阶段的内容显示
                        stage_display = stage_or_report
                        stage_md_display = stage_or_report
                        
                        if format_mode == "Markdown渲染" and stage_or_report:
                            # 如果是markdown格式模式，检测内容格式
                            if app.is_markdown_content(stage_or_report):
                                stage_md_display = app.enhance_markdown_content(stage_or_report)
                            elif len(stage_or_report) > 100:
                                # 长文本用代码块包装
                                stage_md_display = f"```\n{stage_or_report}\n```"
                            else:
                                # 短文本直接显示
                                stage_md_display = stage_or_report
                        
                        # 返回8个值来匹配所有outputs
                        yield (status, stage_md_display, progress, 
                              gr.update(),  # research_report_md
                              gr.update(),  # research_report_text
                              gr.update(visible=True if format_mode == "Markdown渲染" else False),  # current_stage_md
                              gr.update(value=stage_display, visible=True if format_mode == "原始文本" else False),  # current_stage_text
                              gr.update(choices=stage_buttons))  # stage_selector - 不重置用户选择
                else:
                    # 错误情况，返回8个值
                    yield (result[0], "", "", 
                          gr.update(), gr.update(), 
                          gr.update(), gr.update(), gr.update())
        
        def handle_status_check():
            """处理状态查询事件"""
            return app.get_workflow_status()
        
        def handle_model_switch(provider):
            """处理模型切换事件"""
            if not provider.strip():
                return "❌ 请输入提供商名称", model_info.value
            
            result = app.switch_model(provider)
            
            # 更新模型信息
            try:
                new_model_name = app.llm_model.model_name()
            except:
                new_model_name = str(app.llm_model)
            
            new_model_info = f"**当前模型:** {new_model_name}"
            return result, new_model_info
        
        def handle_format_toggle(format_mode, current_md_content, current_text_content):
            """处理格式切换事件"""
            if format_mode == "Markdown渲染":
                return (gr.update(visible=True), gr.update(visible=False),
                       gr.update(visible=True), gr.update(visible=False))
            else:
                return (gr.update(visible=False), gr.update(visible=True),
                       gr.update(visible=False), gr.update(visible=True))
        
        def handle_stage_selection(stage_selection):
            """处理阶段选择事件，直接显示内容"""
            logger.info(f"阶段选择事件触发，选择: {stage_selection}, 工作流运行状态: {app.workflow_running}")
            
            if not stage_selection:
                return "点击左侧阶段按钮查看详细内容..."
            
            # 无论工作流是否运行，都允许查看已完成的阶段内容
            content = app.get_stage_content(stage_selection)
            logger.info(f"获取到阶段内容，长度: {len(content)}")
            
            # 如果工作流正在运行，在内容顶部添加提示信息
            if app.workflow_running:
                status_note = "## 🔍 查看已完成阶段内容\n\n> ⏳ **提示:** 工作流正在运行中，以下是已完成阶段的内容\n\n---\n\n"
                content = status_note + content
            
            return content
        
        # 绑定事件
        start_btn.click(
            handle_start_research,
            inputs=[research_topic, save_intermediate, save_final_report, enable_stream, format_toggle],
            outputs=[status_display, current_stage_md, progress_log, research_report_md, research_report_text, current_stage_md, current_stage_text, stage_selector],
            show_progress="minimal"
        )
        
        status_btn.click(
            handle_status_check,
            outputs=[status_display]
        )
        
        switch_btn.click(
            handle_model_switch,
            inputs=[provider_input],
            outputs=[switch_result, model_info]
        )
        
        # 格式切换事件
        format_toggle.change(
            handle_format_toggle,
            inputs=[format_toggle, research_report_md, research_report_text],
            outputs=[research_report_md, research_report_text, current_stage_md, current_stage_text]
        )
        
        # 阶段选择事件 - 直接触发内容显示
        stage_selector.change(
            handle_stage_selection,
            inputs=[stage_selector],
            outputs=[stage_detail_display]
        )
    
    return demo


def main():
    """主函数"""
    args = parse_args()
    
    try:
        # 初始化应用
        logger.info("正在初始化 Deep Research 应用...")
        app = DeepResearchApp(args.config)
        
        # 创建 Gradio 界面
        demo = create_gradio_interface(app)
        
        # 启动应用
        logger.info(f"启动 Deep Research 应用在 {args.host}:{args.port}")
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