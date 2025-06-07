import builtins
import importlib
import inspect
import json
import os
import re
import time
from abc import ABC
from typing import Callable, Dict, Type

from vertex_flow.utils.logger import LoggerUtil

logging = LoggerUtil.get_logger()


def timer_decorator(func):
    """装饰器：打印函数执行所需时间"""

    def wrapper(*args, **kwargs):
        """
        装饰器函数，用于计算并记录函数执行时间。

        参数:
        *args -- 位置参数，允许接受任意数量的位置参数。
        **kwargs -- 关键字参数，允许接受任意数量的关键字参数。

        返回:
        result -- 执行被装饰函数后的返回值。
        """
        start_time = time.time()  # 记录开始时间
        result = func(*args, **kwargs)  # 执行函数
        end_time = time.time()  # 记录结束时间
        elapsed_time = end_time - start_time  # 计算耗时
        # 记录函数执行耗时信息到日志
        logging.info(f"{func.__name__} 函数执行耗时: {elapsed_time:.6f} 秒")
        return result

    return wrapper


@timer_decorator
def read_file(filepath):
    """读取文件内容并返回"""
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        print(f"错误：文件 {filepath} 不存在。")
        return None
    except Exception as e:
        print(f"无法读取文件 {filepath}: {e}")
        return None


def env_str(key):
    return "{{env.var." + key + "}}"


def compatiable_env_str(key):
    return "{{#env." + key + "#}}"


def var_str(key):
    return "{{user.var." + key + "}}"


safe_globals = {
    "__builtins__": {
        "int": int,
        "float": float,
        "str": str,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "bool": bool,
        "enumerate": enumerate,
        "zip": zip,
        "filter": filter,
        "map": map,
        "range": range,
        "len": len,
        "sum": sum,
        "min": min,
        "max": max,
        "print": print,
        "abs": abs,
        "round": round,
        "sorted": sorted,
        "any": any,
        "all": all,
        "reversed": reversed,
        "type": type,
        "callable": callable,
        "isinstance": isinstance,
        "getattr": getattr,
        "setattr": setattr,
        "delattr": delattr,
        "hasattr": hasattr,
        "id": id,
        "hash": hash,
        "chr": chr,
        "ord": ord,
        "bin": bin,
        "hex": hex,
        "oct": oct,
        "divmod": divmod,
        "pow": pow,
        "next": next,
        "iter": iter,
        "compile": compile,
        "eval": eval,
        "exec": exec,
        "globals": globals,
        "locals": locals,
        "input": input,
        "open": open,
        "exit": exit,
        "quit": quit,
        "help": help,
        "dir": dir,
        "super": super,
        "classmethod": classmethod,
        "staticmethod": staticmethod,
        "property": property,
        "object": object,
        "str": str,
        "repr": repr,
        "format": format,
        "exec": exec,
        "delattr": delattr,
        "getattr": getattr,
        "hasattr": hasattr,
        "setattr": setattr,
        "vars": vars,
        "id": id,
        "__import__": __import__,
        "issubclass": issubclass,
        "isinstance": isinstance,
        "callable": callable,
        "super": super,
        "type": type,
        "open": lambda *args, **kwargs: None,  # Disable file operations
        "exit": lambda *args, **kwargs: None,  # Disable exit
        "quit": lambda *args, **kwargs: None,  # Disable quit
        "json": json,
        "re": re,
    },
    "builtins": builtins,
}

DEFAULT_CONFIG_PATH_KEY = "CONFIG_PATH"
DEFAULT_CONFIG_FILE_KEY = "CONFIG_FILE"


def default_config_path(file_path):
    # 默认配置路径
    base_path = os.path.join(os.path.dirname(__file__), "..", "config")

    try:
        # 检查环境变量是否存在
        if DEFAULT_CONFIG_PATH_KEY in os.environ:
            env_path = os.environ[DEFAULT_CONFIG_PATH_KEY]
            logging.info(f"Using environment variable {env_path}")
            # 检查环境变量是否为绝对路径且存在
            if env_path and os.path.isabs(env_path) and os.path.isdir(env_path):
                base_path = env_path
        # 检查 CONFIG_FILE 环境变量
        elif DEFAULT_CONFIG_FILE_KEY in os.environ:
            env_file = os.environ[DEFAULT_CONFIG_FILE_KEY]
            logging.info(f"Using environment variable CONFIG_FILE {env_file}")
            # 检查环境变量是否为绝对路径且存在
            if env_file and os.path.isabs(env_file) and os.path.isfile(env_file):
                # 如果是文件路径，直接返回该文件路径
                return os.path.normpath(env_file)
        else:
            logging.info(f"Using default path {base_path}")
    except Exception as e:
        # 处理环境变量处理过程中可能出现的异常
        logging.error(f"Error processing environment variable: {e}")

    # 返回规范化的路径
    return os.path.normpath(os.path.join(base_path, file_path))


def is_lambda(task: Callable) -> bool:
    task_name = (task.__name__ if hasattr(task, "__name__") else str(task),)
    if isinstance(task_name, str):
        return task_name == "<lambda>"
    elif isinstance(task_name, tuple):
        return task_name[0] == "<lambda>"
    return False


def get_task_module_and_function_name(task: Callable) -> Dict:
    return {
        "type": "function",
        "name": task.__name__ if hasattr(task, "__name__") else str(task),
        "module": task.__module__ if hasattr(task, "__module__") else None,
    }


def load_function_from_name(module_name: str, function_name: str) -> Callable:
    """
    动态加载指定模块中的函数。

    :param module_name: 模块名称
    :param function_name: 函数名称
    :return: 加载的函数对象
    """
    try:
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)
        if isinstance(function, tuple):
            return function[0]
        return function
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Failed to import function {function_name} from module {module_name}: {e}")


def load_task_from_data(task_data):
    """
    根据 task_data 动态加载 task。

    :param task_data: 包含 task 信息的字典
    :return: 加载后的 task 对象
    """
    if isinstance(task_data, dict) and task_data.get("type") == "function":
        module_name = task_data["module"]
        function_name = task_data["name"]
        try:
            task = load_function_from_name(module_name, function_name)
            return task
        except (ImportError, AttributeError) as e:
            logging.error(f"Failed to import function {function_name} from module {module_name}: {e}")
            raise e
    return None


def is_method_of_class(func, cls):
    """
    判断一个callable是否属于某个类或其子类的方法。

    参数:
        func (callable): 需要检查的callable对象。
        cls (type): 目标类。

    返回:
        bool: 如果callable属于该类或其子类的方法，则返回True；否则返回False。
    """
    if not callable(func):
        return False

    # 检查是否为绑定方法
    if hasattr(func, "__self__") and isinstance(func.__self__, cls):
        return True

    # 获取类及其所有子类
    classes_to_check = [cls] + cls.__subclasses__()

    for c in classes_to_check:
        # 获取类的所有方法名
        method_names = set(inspect.getmembers(c, predicate=inspect.isfunction)) | set(
            inspect.getmembers(c, predicate=inspect.ismethod)
        )
        method_names = {name for name, _ in method_names}

        # 如果func的名字在这些方法名中，并且func的类型是函数或方法
        if hasattr(func, "__name__") and func.__name__ in method_names:
            return True

    return False


# 全局工厂注册表
factory_registry: Dict[str, Type[ABC]] = {}


def factory_creator(cls):
    """
    装饰器，用于将子类注册到全局工厂注册表中，并通过元编程的方式织入 __init_subclass__ 方法。
    """
    if not issubclass(cls, ABC):
        raise ValueError(f"Class {cls.__name__} is not an abstract base class.")

    # 定义 __init_subclass__ 方法
    def custom_init_subclass(subclass, **kwargs):
        super(cls, subclass).__init_subclass__(**kwargs)
        factory_registry[subclass.__name__.lower()] = subclass

    # 将 __init_subclass__ 方法织入到类中
    cls.__init_subclass__ = classmethod(custom_init_subclass)

    return cls


def create_instance(class_name: str, **kwargs) -> ABC:
    """
    根据类名从全局工厂注册表中获取类并实例化。
    """
    class_name_lower = class_name.lower()
    if class_name_lower not in factory_registry:
        raise ValueError(f"No class named {class_name} found in the factory registry.")
    logging.info(f"Creating instance of {class_name}")
    return factory_registry[class_name_lower](**kwargs)
