from setuptools import setup, find_packages

setup(
    name="vertex",  # 修改项目名称
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
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
            "vertex=app:main",
        ],
    },
)