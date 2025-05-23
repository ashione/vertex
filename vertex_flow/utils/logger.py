#!/usr/bin/env python3
"""
通用日志工具模块，兼容 LoggerUtil 与 setup_logger/get_logger 两种用法
"""

import logging
from typing import Optional
import sys
from threading import Lock


class LoggerUtil:
    """
    日志工具类，用于方便地创建和获取 logger。

    使用方法：
    >>> logger = LoggerUtil.get_logger('my_logger')
    >>> logger.info('This is an info message.')
    """

    _loggers = {}
    _loggers_lock = Lock()

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["lock"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.lock = Lock()

    @staticmethod
    def get_logger(
        name: str = "default", level: int = logging.INFO, file: Optional[str] = None
    ) -> logging.Logger:
        """
        获取或创建一个 logger。

        :param name: logger 的名称
        :param level: 日志级别，默认为 INFO
        :param file: 日志文件路径，默认为 None 表示控制台输出
        :return: 返回一个 logger 实例
        """
        with LoggerUtil._loggers_lock:
            if name in LoggerUtil._loggers:
                return LoggerUtil._loggers[name]

            logger = logging.getLogger(name)
            logger.setLevel(level)
            handlers = []
            # 创建一个 handler，用于写入日志文件
            if file:
                handler = logging.FileHandler(file)
                handlers.append(handler)
            else:
                # 不指定名字同时输出到控制台和文件。
                handlers.append(logging.FileHandler("app.log"))
                handlers.append(logging.StreamHandler(sys.stdout))

            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - [%(thread)d] %(message)s"
            )
            for handler in handlers:
                handler.setFormatter(formatter)
            for handler in handlers:
                logger.addHandler(handler)

            LoggerUtil._loggers[name] = logger
            return logger


# 兼容 setup_logger 用法
def setup_logger(
    name: str,
    level: int = logging.INFO,
    format_str: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    file_path: Optional[str] = None,
) -> logging.Logger:
    """
    配置并返回一个logger实例
    """
    logger = LoggerUtil.get_logger(name, level=level, file=file_path)
    # 只在首次添加时设置格式
    if not logger.handlers or not any(
        isinstance(h, logging.StreamHandler) for h in logger.handlers
    ):
        formatter = logging.Formatter(format_str)
        for handler in logger.handlers:
            handler.setFormatter(formatter)
    return logger


# 兼容 get_logger 用法
def get_logger(name: str = None) -> logging.Logger:
    """
    获取一个logger实例
    """
    return LoggerUtil.get_logger(name or "default")
