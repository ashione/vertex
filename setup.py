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
        "flake8>=6.0.0",
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
        # 网络和HTTP客户端依赖
        "urllib3>=2.0.0",
        "aiohttp>=3.8.0",
        "httpx>=0.24.0",
        "socksio>=1.0.0",
        # 桌面端应用依赖
        "pywebview>=5.4",
        # 异步支持
        "nest-asyncio>=1.6.0",
    ],
    python_requires=">=3.9",
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "pre-commit>=3.0.0",
            "twine>=4.0.0",
            "build>=0.10.0",
        ],
        "rag": [
            "sentence-transformers>=2.2.0",
            "faiss-cpu>=1.7.0",
            "numpy>=1.21.0",
            "PyPDF2>=3.0.0",
            "python-docx>=0.8.11",
            "reportlab>=4.4.2",
        ],
        # Web搜索工具（可选）
        "web-search": [
            "requests>=2.28.2",  # 基础HTTP请求库（已包含在主依赖中）
            # 未来可能添加的搜索相关依赖
            # "beautifulsoup4>=4.12.0",  # 网页解析
            # "lxml>=4.9.0",  # XML解析
        ],
        # 云端向量存储（可选，需要编译grpcio）
        "cloud-vector": [
            "dashvector>=1.0.19",
        ],
        # 桌面端应用（可选）
        "desktop": [
            "pywebview>=5.4",
        ],
        # 缓存和持久化存储
        "memory": [
            "redis>=5.0.0",
            "sqlalchemy>=2.0.0",
            "pymysql>=1.1.0",
        ],
        # 完整功能（包含所有可选依赖）
        "all": [
            "sentence-transformers>=2.2.0",
            "faiss-cpu>=1.7.0",
            "numpy>=1.21.0",
            "PyPDF2>=3.0.0",
            "python-docx>=0.8.11",
            "reportlab>=4.4.2",
            "dashvector>=1.0.19",
            "pywebview>=5.4",
            "requests>=2.28.2",
            "redis>=5.0.0",
            "sqlalchemy>=2.0.0",
            "pymysql>=1.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vertex=vertex_flow.cli:main",
        ],
    },
)
