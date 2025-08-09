#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号服务器
处理微信公众号的消息接收和回复
"""

import asyncio
import logging
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

try:
    from .config import config
    from .message_processor import MessageProcessor
    from .wechat_handler import WeChatHandler
except ImportError:
    from config import config
    from message_processor import MessageProcessor
    from wechat_handler import WeChatHandler

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title="WeChat Plugin for Vertex Flow", version="1.0.0")

# 初始化组件
wechat_handler = WeChatHandler(
    token=config.wechat_token,
    encoding_aes_key=config.wechat_encoding_aes_key,
    app_id=config.wechat_app_id,
    message_mode=config.wechat_message_mode
)
message_processor = MessageProcessor(
    api_base_url=config.vertex_flow_api_url,
    default_workflow=config.default_workflow
)


@app.get("/")
async def wechat_verify(request: Request):
    """微信服务器验证和根路径处理"""
    try:
        # 获取验证参数
        signature = request.query_params.get('signature', '')
        timestamp = request.query_params.get('timestamp', '')
        nonce = request.query_params.get('nonce', '')
        echostr = request.query_params.get('echostr', '')
        
        # 如果有微信验证参数，进行验证
        if signature and timestamp and nonce and echostr:
            logger.info(f"收到微信验证请求: signature={signature}, timestamp={timestamp}, nonce={nonce}")
            
            # 验证签名
            if wechat_handler.verify_signature(signature, timestamp, nonce):
                logger.info("微信签名验证成功")
                return PlainTextResponse(echostr)
            else:
                logger.warning("微信签名验证失败")
                raise HTTPException(status_code=403, detail="签名验证失败")
        else:
            # 没有验证参数，返回基本信息
            return {
                "message": "微信公众号插件 for Vertex Flow",
                "version": "1.0.0",
                "webhook_url": config.get_webhook_url(),
                "health_check": "/health"
            }
            
    except HTTPException:
        # 重新抛出HTTPException，不要转换为500错误
        raise
    except Exception as e:
        logger.error(f"微信验证过程中发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="验证过程中发生错误")


@app.post("/")
async def wechat_message(request: Request):
    """处理微信消息"""
    import asyncio
    
    try:
        # 设置5秒超时，避免微信重试
        return await asyncio.wait_for(_process_wechat_message(request), timeout=4.5)
    except asyncio.TimeoutError:
        logger.warning("消息处理超时，返回空响应避免微信重试")
        return PlainTextResponse("", status_code=200)
    except Exception as e:
        logger.error(f"处理微信消息时发生错误: {str(e)}")
        # 返回空响应，避免微信重复推送
        return PlainTextResponse("", status_code=200)


async def _process_wechat_message(request: Request):
    """内部消息处理函数"""
    try:
        # 获取验证参数
        signature = request.query_params.get('signature', '')
        timestamp = request.query_params.get('timestamp', '')
        nonce = request.query_params.get('nonce', '')
        msg_signature = request.query_params.get('msg_signature', '')  # 安全模式需要
        
        # 获取消息内容
        xml_data = await request.body()
        xml_str = xml_data.decode('utf-8')
        
        logger.info(f"收到微信消息: {xml_str[:200]}...")  # 只记录前200字符
        
        # 安全模式下使用msg_signature验证，明文模式使用signature验证
        if wechat_handler.secure_mode:
            # 安全模式：需要提取Encrypt字段进行验证
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(xml_str)
                encrypt_elem = root.find('Encrypt')
                encrypt_msg = encrypt_elem.text if encrypt_elem is not None else None
                
                if not encrypt_msg:
                    logger.warning("安全模式下未找到加密消息")
                    raise HTTPException(status_code=403, detail="消息格式错误")
                
                # 使用msg_signature验证
                verify_signature = msg_signature if msg_signature else signature
                if not wechat_handler.verify_signature(verify_signature, timestamp, nonce, encrypt_msg):
                    logger.warning("微信消息签名验证失败（安全模式）")
                    raise HTTPException(status_code=403, detail="签名验证失败")
            except ET.ParseError:
                logger.error("XML解析失败")
                raise HTTPException(status_code=400, detail="消息格式错误")
        else:
            # 明文模式：跳过签名验证（仅用于测试）
            if config.wechat_message_mode == 'plaintext':
                logger.info("明文模式：跳过签名验证（测试模式）")
            else:
                # 使用原有验证逻辑
                if not wechat_handler.verify_signature(signature, timestamp, nonce):
                    logger.warning("微信消息签名验证失败（明文模式）")
                    raise HTTPException(status_code=403, detail="签名验证失败")
        
        # 解析消息
        message = wechat_handler.parse_xml_message(xml_str)
        if not message:
            logger.error("消息解析失败")
            return PlainTextResponse("")
        
        # 检查解析错误
        if 'Error' in message:
            logger.error(f"消息解析错误: {message['Error']}")
            return PlainTextResponse("")
        
        # 提取消息信息
        to_user, from_user, msg_type, content = wechat_handler.extract_message_info(message)
        
        logger.info(f"消息类型: {msg_type}, 发送者: {from_user}, 内容: {content[:100]}...")
        
        # 检查消息类型是否支持
        if not wechat_handler.is_supported_message_type(msg_type):
            logger.warning(f"不支持的消息类型: {msg_type}")
            reply_content = "抱歉，暂时只支持文本消息。"
            reply_xml = wechat_handler.create_text_reply(from_user, to_user, reply_content, timestamp, nonce)
            return PlainTextResponse(reply_xml, status_code=200, media_type="text/xml; charset=utf-8")
        
        # 处理文本消息
        if msg_type == 'text':
            # 检查消息长度
            if len(content) > config.max_message_length:
                reply_content = f"消息太长了，请控制在{config.max_message_length}字符以内。"
                reply_xml = wechat_handler.create_text_reply(from_user, to_user, reply_content, timestamp, nonce)
                return PlainTextResponse(reply_xml, status_code=200, media_type="text/xml; charset=utf-8")
            
            # 处理消息并获取AI回复
            ai_response = await message_processor.process_message(
                user_id=from_user,
                content=content
            )
            
            # 更新用户会话
            message_processor.update_user_session(from_user, content, ai_response)
            
            # 创建回复
            reply_xml = wechat_handler.create_text_reply(from_user, to_user, ai_response, timestamp, nonce)
            
            logger.info(f"回复用户 {from_user}: {ai_response[:100]}...")
            
            return PlainTextResponse(reply_xml, media_type="application/xml")
        
        # 处理图片消息（如果启用多模态）
        elif msg_type == 'image' and config.enable_multimodal:
            pic_url = message.get('PicUrl', '')
            if pic_url:
                ai_response = await message_processor.process_message(
                    user_id=from_user,
                    content="请分析这张图片",
                    image_url=pic_url
                )
                
                reply_xml = wechat_handler.create_text_reply(from_user, to_user, ai_response, timestamp, nonce)
                return PlainTextResponse(reply_xml, status_code=200, media_type="text/xml; charset=utf-8")
            else:
                reply_content = "图片处理失败，请重新发送。"
                reply_xml = wechat_handler.create_text_reply(from_user, to_user, reply_content, timestamp, nonce)
                return PlainTextResponse(reply_xml, status_code=200, media_type="text/xml; charset=utf-8")
        
        # 其他消息类型的默认回复
        else:
            reply_content = "收到您的消息，但暂时只支持文本消息处理。"
            reply_xml = wechat_handler.create_text_reply(from_user, to_user, reply_content, timestamp, nonce)
            return PlainTextResponse(reply_xml, status_code=200, media_type="text/xml; charset=utf-8")
            
    except Exception as e:
        logger.error(f"内部消息处理错误: {str(e)}")
        # 抛出异常让外层处理
        raise


@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查配置
        is_valid, error_msg = config.validate()
        if not is_valid:
            return {"status": "error", "message": f"配置错误: {error_msg}"}
        
        # 检查Vertex Flow API连接
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{config.vertex_flow_api_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        return {
                            "status": "error", 
                            "message": f"Vertex Flow API不可用，状态码: {response.status}"
                        }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"无法连接到Vertex Flow API: {str(e)}"
            }
        
        return {
            "status": "ok",
            "message": "微信公众号插件运行正常",
            "config": {
                "wechat_token_set": bool(config.wechat_token),
                "wechat_message_mode": config.wechat_message_mode,
                "wechat_encryption_enabled": bool(wechat_handler.crypto),
                "vertex_flow_api_url": config.vertex_flow_api_url,
                "webhook_url": config.get_webhook_url(),
                "features": {
                    "mcp": config.enable_mcp,
                    "search": config.enable_search,
                    "multimodal": config.enable_multimodal,
                    "reasoning": config.enable_reasoning
                }
            }
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {"status": "error", "message": f"健康检查失败: {str(e)}"}





# 定期清理过期会话
async def cleanup_sessions():
    """定期清理过期会话"""
    while True:
        try:
            message_processor.clear_expired_sessions(config.session_timeout)
            await asyncio.sleep(3600)  # 每小时清理一次
        except Exception as e:
            logger.error(f"清理会话时发生错误: {str(e)}")
            await asyncio.sleep(3600)


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("微信公众号插件启动中...")
    
    # 验证配置
    is_valid, error_msg = config.validate()
    if not is_valid:
        logger.error(f"配置验证失败: {error_msg}")
        raise RuntimeError(f"配置验证失败: {error_msg}")
    
    logger.info("配置验证通过")
    logger.info(f"配置信息:\n{config}")
    
    # 启动会话清理任务
    asyncio.create_task(cleanup_sessions())
    
    logger.info("微信公众号插件启动完成")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    logger.info("微信公众号插件正在关闭...")