import logging
from typing import Callable, Optional


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
        logging.info(f"Tool '{self.name}' called with inputs: {inputs}")
        if context:
            logging.info(f"Tool '{self.name}' context: {context}")
        return self.func(inputs, context)

    def to_dict(self):
        """Convert the function tool to OpenAI API compatible format"""
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": self.schema},
        }
