from setuptools import find_packages, setup

setup(
    name="vertex",
    version="0.1.0",
    packages=find_packages(),  # 手动添加 workflow
    include_package_data=True,
    install_requires=[
        # 代码质量工具
        "autopep8>=2.3.2",
        "black>=25.1.0",
        "flake8>=7.2.0",
        "isort>=6.0.1",
        # 基础依赖
        "requests>=2.28.2",
        "PySocks>=1.7.1",
        # Web UI 依赖
        "gradio==4.40.0",
        "gradio-client==1.2.0",
        "fastapi==0.112.2",
        "pydantic==2.10.6",
        "starlette==0.38.6",
        "uvicorn==0.30.6",
        # 环境配置
        "python-dotenv>=0.21.0",
        # 实用工具
        "tqdm>=4.65.0",
        "openai>=1.0.0",
        "websockets>=10.0,<13.0",
        # AI服务相关依赖
        "dashscope>=1.23.4",
        "ruamel-yaml>=0.18.14",
        # RAG系统依赖
        "sentence-transformers>=2.2.0",
        "faiss-cpu>=1.7.0",
        "numpy>=1.21.0",
        # 文档处理依赖
        "PyPDF2>=3.0.0",
        "python-docx>=0.8.11",
        "reportlab>=4.4.2",
        # 网络和HTTP客户端依赖
        "urllib3>=2.0.0",
        "aiohttp>=3.8.0",
        "httpx>=0.24.0",
        "socksio>=1.0.0",
        # 桌面端应用依赖
        "pywebview>=5.4",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "vertex=vertex_flow.cli:main",
        ],
    },
)
