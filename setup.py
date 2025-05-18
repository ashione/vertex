from setuptools import setup, find_packages

setup(
    name="vertex_flow",  # 项目名称改为 vertex_flow
    version="0.1.0",
    packages=find_packages(),  # 手动添加 workflow
    include_package_data=True,
    install_requires=[
        "requests>=2.28.2",
        "gradio>=3.50.0",
        "python-dotenv>=0.21.0",
        "openai>=1.0.0",
        "tqdm>=4.65.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "vertex=vertex_flow.src.app:main",
            "vertex-workflow=vertex_flow.workflow.app.app:main",  # 新增 entrypoint
        ],
    },
)