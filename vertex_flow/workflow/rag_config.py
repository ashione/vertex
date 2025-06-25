import os

import yaml
from ruamel.yaml import YAML, RoundTripRepresenter

from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.utils import timer_decorator

logging = LoggerUtil.get_logger()


@timer_decorator
def read_yaml_config(filepath):
    """读取YAML配置文件并返回内容"""
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
            logging.info(f"成功读取配置文件 {filepath}")
            return config
    except FileNotFoundError:
        logging.error(f"错误：文件 {filepath} 不存在。")
        return None
    except Exception as e:
        logging.error(f"无法读取配置文件 {filepath}: {e}")
        return None


@timer_decorator
def read_yaml_config_env_placeholder(filepath):
    # 初始化 YAML 解析器
    yaml = YAML()

    # 自定义代表器来处理占位符
    def represent_scalar(self, tag, value, style=None):
        if style is None:
            if ":" in value:
                style = "|"
            else:
                style = self.default_style

        node = RoundTripRepresenter.represent_scalar(self, tag, value, style)
        return node

    RoundTripRepresenter.represent_scalar = represent_scalar

    # 加载 YAML 文件
    with open(filepath, "r", encoding="utf-8") as stream:
        config = yaml.load(stream)

    # 定义一个函数来递归地替换占位符
    def resolve_placeholders(data, env=os.environ):
        if isinstance(data, dict):
            return {k: resolve_placeholders(v, env) for k, v in data.items()}
        elif isinstance(data, list):
            return [resolve_placeholders(item, env) for item in data]
        elif isinstance(data, str):
            import re

            pattern = r"\$\{([^\}]+)\}"

            def replace(match):
                placeholder = match.group(1)
                parts = placeholder.split(":")
                if len(parts) > 1:
                    default_value = ":".join(parts[1:])
                    var_name = parts[0]
                    var_name_replaced = var_name.replace(".", "_")
                    var_name_replaced_uppper = var_name_replaced.upper()
                    logging.debug(
                        "env var %s or %s or %s, default value : %s",
                        var_name,
                        var_name_replaced,
                        var_name_replaced_uppper,
                        default_value,
                    )
                    # Try to get value from environment variables in order:
                    # 1. Original variable name
                    # 2. Variable name with dots replaced by underscores
                    # 3. Uppercase version of #2
                    # 4. If none found, use default value
                    env_value = (
                        env.get(var_name)
                        or env.get(var_name_replaced)
                        or env.get(var_name_replaced_uppper)
                        or default_value
                    )
                    return env_value
                else:
                    return env.get(parts[0], placeholder)

            return re.sub(pattern, replace, data)
        else:
            return data

    # 替换占位符
    return resolve_placeholders(config)
