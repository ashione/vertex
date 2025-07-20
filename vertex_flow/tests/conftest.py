#!/usr/bin/env python3
"""
测试配置文件
"""
import os
import tempfile

import pytest
import yaml


@pytest.fixture(scope="session")
def test_config():
    """创建测试配置"""
    config = {
        "workflow": {
            "default_model": "qwen-turbo-latest",
            "enable_stream": True,
            "enable_reasoning": False,
            "dify": {"root-path": "config/"},
        },
        "models": {"qwen-turbo-latest": {"type": "tongyi", "name": "qwen-turbo-latest", "api_key": "sk-test-mock-key"}},
        "llm": {
            "deepseek": {
                "sk": "-YOUR_DEEPSEEK_API_KEY",
                "enabled": "false",
                "base_url": "https://api.deepseek.com",
                "models": [{"name": "deepseek-chat", "enabled": "false"}],
            },
            "tongyi": {
                "sk": "-YOUR_TONGYI_API_KEY",
                "enabled": "false",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "models": [{"name": "qwen-max", "enabled": "true"}],
            },
            "openrouter": {
                "sk": "-YOUR_OPENROUTER_API_KEY",
                "enabled": "false",
                "base_url": "https://openrouter.ai/api/v1",
                "models": [],
            },
            "ollama": {"sk": "-ollama-local", "enabled": "false", "base-url": "http://localhost:11434", "models": []},
            "doubao": {
                "sk": "-YOUR_DOUBAO_API_KEY",
                "enabled": "false",
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "models": [],
            },
            "other": {"enabled": "false", "models": []},
            "mcp": {"enabled": True, "clients": {}},
        },
    }

    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(config, f)
        config_path = f.name

    # 设置环境变量
    os.environ["VERTEX_FLOW_CONFIG"] = config_path
    os.environ["TEST_MODE"] = "mock"

    yield config_path

    # 清理
    os.unlink(config_path)
    if "VERTEX_FLOW_CONFIG" in os.environ:
        del os.environ["VERTEX_FLOW_CONFIG"]
    if "TEST_MODE" in os.environ:
        del os.environ["TEST_MODE"]


@pytest.fixture(autouse=True)
def setup_test_environment():
    """设置测试环境"""
    # 设置测试模式
    os.environ["TEST_MODE"] = "mock"
    yield
    # 清理
    if "TEST_MODE" in os.environ:
        del os.environ["TEST_MODE"]
