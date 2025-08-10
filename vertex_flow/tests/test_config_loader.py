import os
from pathlib import Path

from vertex_flow.config.config_loader import ConfigLoader


def test_load_default_config_includes_openai_and_mcp(monkeypatch):
    """Ensure default config contains OpenAI provider, gpt-oss model and MCP settings."""
    # Remove env var to force default config loading
    monkeypatch.delenv("VERTEX_FLOW_CONFIG", raising=False)

    loader = ConfigLoader()
    # Point to non-existing user config to trigger default template load
    loader.user_config_dir = Path("/nonexistent")
    loader.user_config_file = loader.user_config_dir / "llm.yml"
    loader.user_mcp_file = loader.user_config_dir / "mcp.yml"

    config = loader.load_config()

    # OpenAI provider is included in llm section
    assert "openai" in config.get("llm", {})
    # gpt-oss model is present under openrouter provider
    openrouter_models = config["llm"].get("openrouter", {}).get("models", [])
    assert any(m.get("name") == "openai/gpt-oss" for m in openrouter_models)
    # MCP configuration is merged from separate file
    assert config.get("mcp", {}).get("enabled") is True
