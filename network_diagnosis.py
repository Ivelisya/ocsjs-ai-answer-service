#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络连接诊断脚本
用于检查 Gemini API 的网络连接问题
"""
import socket
import requests
import time
import subprocess
import sys
import os

def test_network_connectivity():
    """测试网络连接"""
    print("🌐 网络连接诊断")
    print("=" * 30)

    # 测试基本网络连接
    try:
        print("🔍 测试基本网络连接...")
        response = requests.get("https://www.google.com", timeout=10)
        print("✅ 基本网络连接正常")
    except Exception as e:
        print(f"❌ 基本网络连接失败: {str(e)}")
        return False

    # 测试 DNS 解析
    try:
        print("🔍 测试 DNS 解析...")
        ip = socket.gethostbyname("generativelanguage.googleapis.com")
        print(f"✅ DNS 解析成功: generativelanguage.googleapis.com -> {ip}")
    except Exception as e:
        print(f"❌ DNS 解析失败: {str(e)}")
        return False

    # 测试 Gemini API 端口连接
    try:
        print("🔍 测试 Gemini API 端口连接...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex(("generativelanguage.googleapis.com", 443))
        sock.close()

        if result == 0:
            print("✅ Gemini API 端口连接正常")
        else:
            print("❌ Gemini API 端口连接失败")
            return False
    except Exception as e:
        print(f"❌ 端口连接测试失败: {str(e)}")
        return False

    return True

def test_firewall_settings():
    """检查防火墙设置"""
    print("\n🔥 防火墙检查")
    print("=" * 30)

    try:
        if os.name == 'nt':  # Windows
            print("🔍 检查 Windows 防火墙...")
            result = subprocess.run(
                ["netsh", "advfirewall", "show", "allprofiles"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if "BlockInbound" in result.stdout:
                print("⚠️  发现防火墙规则可能阻止连接")
            else:
                print("✅ 防火墙设置正常")
        else:
            print("ℹ️  非 Windows 系统，跳过防火墙检查")
    except Exception as e:
        print(f"❌ 防火墙检查失败: {str(e)}")

def test_proxy_settings():
    """检查代理设置"""
    print("\n🌍 代理设置检查")
    print("=" * 30)

    # 检查环境变量
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    proxy_found = False

    for var in proxy_vars:
        value = os.getenv(var)
        if value:
            print(f"⚠️  发现代理设置: {var} = {value}")
            proxy_found = True

    if not proxy_found:
        print("✅ 未发现代理设置")
    else:
        print("💡 如果使用代理，请确保代理服务器正常工作")

def provide_solutions():
    """提供解决方案"""
    print("\n🔧 解决方案建议")
    print("=" * 30)

    solutions = [
        "1. 检查网络连接是否正常",
        "2. 尝试更换网络环境（例如使用手机热点）",
        "3. 检查防火墙设置，确保允许 Python 访问网络",
        "4. 如果使用代理，请检查代理配置",
        "5. 尝试使用 VPN 连接",
        "6. 检查系统时间是否正确",
        "7. 尝试重启计算机",
        "8. 如果问题持续，考虑使用 OpenAI 作为替代方案"
    ]

    for solution in solutions:
        print(f"   {solution}")

def main():
    """主函数"""
    print("🔬 EduBrain AI - 网络诊断工具")
    print("用于排查 Gemini API 连接问题")
    print("=" * 50)

    # 运行各项测试
    network_ok = test_network_connectivity()
    test_firewall_settings()
    test_proxy_settings()

    print("\n📊 诊断结果")
    print("=" * 30)
    if network_ok:
        print("✅ 网络连接诊断通过")
        print("💡 如果仍然无法使用 AI 功能，可能需要：")
        print("   - 检查 API 密钥是否正确")
        print("   - 验证账户是否有足够的 API 调用额度")
        print("   - 尝试更换 AI 提供商（OpenAI）")
    else:
        print("❌ 网络连接存在问题")
        provide_solutions()

    print("\n🎯 下一步操作：")
    print("1. 运行: python test_api_manual.py 测试 API 功能")
    print("2. 如果仍有问题，请提供具体的错误信息")

if __name__ == "__main__":
    main()
