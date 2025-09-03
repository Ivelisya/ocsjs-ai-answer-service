#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EduBrain AI - Python 启动脚本
自动设置环境变量并启动应用
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_python_path():
    """设置Python路径"""
    # 获取当前脚本所在目录
    current_dir = Path(__file__).parent.absolute()

    # Python安装路径（根据实际情况修改）
    python_paths = [
        r"C:\Users\20212\AppData\Local\Programs\Python\Python310",
        r"C:\Python310",
        r"C:\Python39",
        # 添加其他可能的Python路径
    ]

    # 检查Python路径是否存在
    python_exe = None
    for path in python_paths:
        python_path = Path(path) / "python.exe"
        if python_path.exists():
            python_exe = str(python_path)
            break

    if python_exe:
        print(f"找到Python: {python_exe}")
        # 将Python路径添加到系统PATH
        os.environ['PATH'] = str(Path(python_exe).parent) + os.pathsep + os.environ.get('PATH', '')
        return python_exe
    else:
        print("未找到Python安装，请手动设置PATH或修改脚本中的python_paths")
        return None

def check_requirements():
    """检查依赖是否已安装"""
    try:
        import flask
        import aiohttp
        import google.generativeai
        print("✅ 依赖检查通过")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        return False

def main():
    """主函数"""
    print("EduBrain AI - 启动脚本")
    print("=" * 30)

    # 设置Python路径
    python_exe = setup_python_path()
    if not python_exe:
        sys.exit(1)

    # 检查依赖
    if not check_requirements():
        sys.exit(1)

    # 设置工作目录
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # 启动应用
    print("🚀 启动 EduBrain AI 服务...")
    try:
        # 使用subprocess启动，避免路径问题
        cmd = [python_exe, "app.py"]
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
