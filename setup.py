from setuptools import find_packages, setup

setup(
    name="vertex",
    version="0.1.0",
    packages=find_packages(),  # 手动添加 workflow
    include_package_data=True,
    install_requires=[
        "autopep8>=2.3.2",
        "black>=25.1.0",
        "flake8>=7.2.0",
        "isort>=6.0.1",
        "requests>=2.28.2",
        "gradio>=3.50.0",
        "python-dotenv>=0.21.0",
        "openai>=1.0.0",
        "tqdm>=4.65.0",
        "dashvector",
        "dashscope",
        "langchain-core>=0.1.0",
        "langchain-community>=0.0.1",
        "ruamel.yaml>=0.18.10",
        "flask>=2.0.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "vertex=vertex_flow.src.app:main",
            "vertex-workflow=vertex_flow.workflow.app.app:main",  # 新增 entrypoint
        ],
    },
)
