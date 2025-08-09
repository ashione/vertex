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

from wechat_plugin.config import config
from wechat_plugin.message_processor import MessageProcessor
from wechat_plugin.wechat_handler import WeChatHandler

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title="WeChat Plugin for Vertex Flow", version="1.0.0")

# 初始化组件
wechat_handler = WeChatHandler(config.wechat_token)
message_processor = MessageProcessor(
    api_base_url=config.vertex_flow_api_url,
    default_workflow=config.default_workflow
)


@app.get("/wechat")
async def wechat_verify(request: Request):
    """微信服务器验证"""
    try:
        # 获取验证参数
        signature = request.query_params.get('signature', '')
        timestamp = request.query_params.get('timestamp', '')
        nonce = request.query_params.get('nonce', '')
        echostr = request.query_params.get('echostr', '')
        
        logger.info(f"收到微信验证请求: signature={signature}, timestamp={timestamp}, nonce={nonce}")
        
        # 验证签名
        if wechat_handler.verify_signature(signature, timestamp, nonce):
            logger.info("微信签名验证成功")
            return PlainTextResponse(echostr)
        else:
            logger.warning("微信签名验证失败")
            raise HTTPException(status_code=403, detail="签名验证失败")
            
    except HTTPException:
        # 重新抛出HTTPException，不要转换为500错误
        raise
    except Exception as e:
        logger.error(f"微信验证过程中发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="验证过程中发生错误")


@app.post("/wechat")
async def wechat_message(request: Request):
    """处理微信消息"""
    try:
        # 获取验证参数
        signature = request.query_params.get('signature', '')
        timestamp = request.query_params.get('timestamp', '')
        nonce = request.query_params.get('nonce', '')
        
        # 验证签名
        if not wechat_handler.verify_signature(signature, timestamp, nonce):
            logger.warning("微信消息签名验证失败")
            raise HTTPException(status_code=403, detail="签名验证失败")
        
        # 获取消息内容
        xml_data = await request.body()
        xml_str = xml_data.decode('utf-8')
        
        logger.info(f"收到微信消息: {xml_str[:200]}...")  # 只记录前200字符
        
        # 解析消息
        message = wechat_handler.parse_xml_message(xml_str)
        if not message:
            logger.error("消息解析失败")
            return PlainTextResponse("")
        
        # 提取消息信息
        to_user, from_user, msg_type, content = wechat_handler.extract_message_info(message)
        
        logger.info(f"消息类型: {msg_type}, 发送者: {from_user}, 内容: {content[:100]}...")
        
        # 检查消息类型是否支持
        if not wechat_handler.is_supported_message_type(msg_type):
            logger.warning(f"不支持的消息类型: {msg_type}")
            reply_content = "抱歉，暂时只支持文本消息。"
            reply_xml = wechat_handler.create_text_reply(from_user, to_user, reply_content)
            return PlainTextResponse(reply_xml, media_type="application/xml")
        
        # 处理文本消息
        if msg_type == 'text':
            # 检查消息长度
            if len(content) > config.max_message_length:
                reply_content = f"消息太长了，请控制在{config.max_message_length}字符以内。"
                reply_xml = wechat_handler.create_text_reply(from_user, to_user, reply_content)
                return PlainTextResponse(reply_xml, media_type="application/xml")
            
            # 处理消息并获取AI回复
            ai_response = await message_processor.process_message(
                user_id=from_user,
                content=content
            )
            
            # 更新用户会话
            message_processor.update_user_session(from_user, content, ai_response)
            
            # 创建回复
            reply_xml = wechat_handler.create_text_reply(from_user, to_user, ai_response)
            
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
                
                reply_xml = wechat_handler.create_text_reply(from_user, to_user, ai_response)
                return PlainTextResponse(reply_xml, media_type="application/xml")
            else:
                reply_content = "图片处理失败，请重新发送。"
                reply_xml = wechat_handler.create_text_reply(from_user, to_user, reply_content)
                return PlainTextResponse(reply_xml, media_type="application/xml")
        
        # 其他消息类型的默认回复
        else:
            reply_content = "收到您的消息，但暂时只支持文本消息处理。"
            reply_xml = wechat_handler.create_text_reply(from_user, to_user, reply_content)
            return PlainTextResponse(reply_xml, media_type="application/xml")
            
    except Exception as e:
        logger.error(f"处理微信消息时发生错误: {str(e)}")
        # 返回空响应，避免微信重复推送
        return PlainTextResponse("")


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


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "微信公众号插件 for Vertex Flow",
        "version": "1.0.0",
        "webhook_url": config.get_webhook_url(),
        "health_check": "/health"
    }


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