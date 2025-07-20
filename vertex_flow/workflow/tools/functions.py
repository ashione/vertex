import datetime
import logging
from typing import Callable, Optional

import pytz

from vertex_flow.utils.logger import LoggerUtil

logger = LoggerUtil.get_logger(__name__)


def today_func(inputs, context=None):
    """获取当前时间，支持多种格式和时区。"""
    format_type = inputs.get("format", "iso")
    timezone_str = inputs.get("timezone", "UTC")
    custom_format = inputs.get("custom_format", "%Y-%m-%d %H:%M:%S")
    try:
        tz = pytz.timezone(timezone_str) if timezone_str.upper() != "UTC" else pytz.UTC
        now = datetime.datetime.now(tz)
        if format_type == "timestamp":
            return int(now.timestamp())
        elif format_type == "timestamp_ms":
            return int(now.timestamp() * 1000)
        elif format_type == "iso":
            return now.isoformat()
        elif format_type == "iso_utc":
            return now.astimezone(pytz.UTC).isoformat()
        elif format_type == "date":
            return now.strftime("%Y-%m-%d")
        elif format_type == "time":
            return now.strftime("%H:%M:%S")
        elif format_type == "datetime":
            return now.strftime("%Y-%m-%d %H:%M:%S")
        elif format_type == "rfc2822":
            return now.strftime("%a, %d %b %Y %H:%M:%S %z")
        elif format_type == "custom":
            return now.strftime(custom_format)
        else:
            return f"Unknown format: {format_type}"
    except Exception as e:
        return f"Error: {e}"


class FunctionTool:
    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        schema: Optional[dict] = None,
        id: Optional[str] = None,
    ):
        self.name = name
        self.id = id or name  # 新增唯一id，默认与name一致
        self.description = description
        self.func = func
        self.schema = schema or {}

    def execute(self, inputs: dict, context=None):
        # 打印工具调用参数
        logger.info(f"Tool '{self.name}' called with inputs: {inputs}")
        if context:
            logger.info(f"Tool '{self.name}' context: {context}")
        return self.func(inputs, context)

    def to_dict(self):
        """Convert the function tool to OpenAI API compatible format"""
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": self.schema},
        }
