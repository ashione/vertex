#!/usr/bin/env python3
"""
设置和准备 Ollama 中的 Qwen-7B 模型
"""

import argparse
import json
import subprocess
import sys
import time

import requests


def parse_args():
    parser = argparse.ArgumentParser(description="设置 Ollama 中的 Qwen-7B 模型")
    parser.add_argument("--model", type=str, default="qwen:7b", help="Ollama 模型名称")
    return parser.parse_args()


def check_ollama_installed():
    """检查 Ollama 是否已安装"""
    try:
        subprocess.run(
            ["ollama", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def install_ollama_instructions():
    """显示 Ollama 安装说明"""
    print("Ollama 未安装。请先安装 Ollama:")
    print("\n在 macOS 上安装 Ollama:")
    print("1. 访问 https://ollama.com/download")
    print("2. 下载 macOS 安装包并安装")
    print("3. 安装后重新运行此脚本\n")
    sys.exit(1)


def check_model_exists(model_name):
    """检查模型是否已存在于 Ollama 中"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return model_name in result.stdout
    except subprocess.SubprocessError:
        return False


def pull_model(model_name):
    """从 Ollama 仓库拉取模型"""
    print(f"正在拉取 {model_name} 模型...")
    try:
        process = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # 实时输出下载进度
        for line in iter(process.stdout.readline, ""):
            print(line, end="")

        process.wait()
        if process.returncode != 0:
            print(f"拉取模型失败，返回码: {process.returncode}")
            return False

        return True
    except subprocess.SubprocessError as e:
        print(f"拉取模型时发生错误: {e}")
        return False


def check_ollama_service():
    """检查 Ollama 服务是否运行"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        return response.status_code == 200
    except requests.RequestException:
        return False


def start_ollama_service():
    """启动 Ollama 服务"""
    print("启动 Ollama 服务...")
    try:
        # 在 macOS 上启动 Ollama
        subprocess.Popen(["open", "-a", "Ollama"])

        # 等待服务启动
        for _ in range(10):
            if check_ollama_service():
                print("Ollama 服务已启动")
                return True
            print("等待 Ollama 服务启动...")
            time.sleep(2)

        print("Ollama 服务启动超时")
        return False
    except subprocess.SubprocessError as e:
        print(f"启动 Ollama 服务时发生错误: {e}")
        return False


def main():
    args = parse_args()
    model_name = args.model

    # 检查 Ollama 是否已安装
    if not check_ollama_installed():
        install_ollama_instructions()

    # 检查 Ollama 服务是否运行
    if not check_ollama_service():
        if not start_ollama_service():
            print("无法启动 Ollama 服务，请手动启动后重试")
            sys.exit(1)

    # 检查模型是否已存在
    if check_model_exists(model_name):
        print(f"模型 {model_name} 已存在于 Ollama 中")
    else:
        # 拉取模型
        if not pull_model(model_name):
            print(f"拉取模型 {model_name} 失败")
            sys.exit(1)
        print(f"模型 {model_name} 已成功安装到 Ollama 中")

    print("\n设置完成！现在可以运行应用程序了:")
    print("python src/app.py")


if __name__ == "__main__":
    main()
