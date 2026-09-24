#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
超星学习通自动化系统 - 增强启动脚本
自动启动服务器、打开浏览器并登录题库管理界面
"""

import os
import sys
import time
import subprocess
import platform
import urllib.request
import json
from pathlib import Path

# 配置
CHROME_PROFILE = "Default"  # jiahao001 对应的配置文件目录
TIKU_PORT = 8002
CHAOXING_URL = "https://i.chaoxing.com/base?ws=1&t=1790138632014"
TIKU_URL = f"http://localhost:{TIKU_PORT}"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

def find_chrome():
    """查找 Chrome 浏览器路径"""
    if platform.system() == "Windows":
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
    elif platform.system() == "Darwin":  # macOS
        paths = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    else:  # Linux
        paths = ["google-chrome", "chrome", "chromium-browser", "chromium"]

    for path in paths:
        if os.path.exists(path) or subprocess.run(["which", path], capture_output=True).returncode == 0:
            return path
    return None

def check_server(port, timeout=30):
    """检查服务器是否就绪"""
    print(f"等待服务器启动 (端口 {port})...", end="", flush=True)
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/api/stats", timeout=1)
            print(" ✓")
            return True
        except:
            print(".", end="", flush=True)
            time.sleep(1)

    print(" ✗")
    return False

def start_server():
    """启动题库服务器"""
    print("\n[1/4] 启动题库服务器...")

    tiku_dir = Path(__file__).parent / "tiku"
    if not tiku_dir.exists():
        print(f"❌ 错误: 未找到题库目录 {tiku_dir}")
        return None

    venv_python = tiku_dir / "venv" / "Scripts" / "python.exe"
    if platform.system() != "Windows":
        venv_python = tiku_dir / "venv" / "bin" / "python"

    if not venv_python.exists():
        print(f"❌ 错误: 虚拟环境未安装 {venv_python}")
        print("请先运行: python -m venv venv && pip install -r requirements.txt")
        return None

    main_py = tiku_dir / "main.py"
    if not main_py.exists():
        print(f"❌ 错误: 未找到 main.py {main_py}")
        return None

    # 启动服务器
    env = os.environ.copy()
    env["PORT"] = str(TIKU_PORT)

    process = subprocess.Popen(
        [str(venv_python), str(main_py)],
        cwd=str(tiku_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
    )

    # 等待服务器就绪
    if check_server(TIKU_PORT):
        print(f"✓ 题库服务器已启动: {TIKU_URL}")
        return process
    else:
        print("❌ 服务器启动超时")
        process.terminate()
        return None

def open_browser(chrome_path):
    """打开 Chrome 浏览器"""
    print("\n[2/4] 打开题库管理界面...")

    # 打开题库管理界面（带自动登录参数）
    login_url = f"{TIKU_URL}/#/login?auto=1&user={ADMIN_USERNAME}&pass={ADMIN_PASSWORD}"

    try:
        subprocess.Popen(
            [chrome_path, f"--profile-directory={CHROME_PROFILE}", login_url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"✓ 题库管理界面已打开: {TIKU_URL}")
        time.sleep(2)
    except Exception as e:
        print(f"❌ 打开题库界面失败: {e}")

    print("\n[3/4] 打开学习通界面...")
    try:
        subprocess.Popen(
            [chrome_path, f"--profile-directory={CHROME_PROFILE}", CHAOXING_URL],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"✓ 学习通界面已打开: {CHAOXING_URL}")
    except Exception as e:
        print(f"❌ 打开学习通界面失败: {e}")

def print_instructions():
    """打印使用说明"""
    print("\n" + "="*50)
    print("启动完成！")
    print("="*50)
    print(f"\n服务信息:")
    print(f"  题库服务器: {TIKU_URL}")
    print(f"  API 接口:   {TIKU_URL}/api/search")
    print(f"  API 文档:   {TIKU_URL}/docs")
    print(f"  学习通界面: {CHAOXING_URL}")
    print(f"  Chrome 配置: {CHROME_PROFILE}")

    print(f"\n使用说明:")
    print(f"  1. 题库管理界面已自动打开并登录")
    print(f"  2. 学习通界面已自动打开")
    print(f"  3. 确保已在 Tampermonkey 中安装用户脚本")
    print(f"  4. 在脚本设置中配置题库地址: {TIKU_URL}/api/search")

    print(f"\n默认登录账号:")
    print(f"  用户名: {ADMIN_USERNAME}")
    print(f"  密码:   {ADMIN_PASSWORD}")
    print("\n按 Ctrl+C 停止服务器并退出\n")

def main():
    """主函数"""
    print("="*50)
    print("超星学习通自动化系统 - 启动脚本")
    print("="*50)

    # 查找 Chrome
    print("\n[0/4] 检查环境...")
    chrome_path = find_chrome()
    if not chrome_path:
        print("❌ 错误: 未找到 Chrome 浏览器")
        print("请安装 Google Chrome 或修改脚本中的路径")
        return 1
    print(f"✓ 找到 Chrome: {chrome_path}")

    # 启动服务器
    server_process = start_server()
    if not server_process:
        return 1

    # 打开浏览器
    open_browser(chrome_path)

    # 打印说明
    print("\n[4/4] 完成配置")
    print_instructions()

    # 等待用户退出
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n正在关闭服务器...")
        server_process.terminate()
        server_process.wait(timeout=5)
        print("✓ 服务器已关闭")
        print("再见！")

    return 0

if __name__ == "__main__":
    sys.exit(main())
