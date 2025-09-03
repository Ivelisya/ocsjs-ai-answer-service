#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示外部题库优先级逻辑的测试脚本
"""

import requests
import json
import time

def test_external_db_priority():
    """测试外部题库优先级逻辑"""

    base_url = "http://localhost:5000"
    test_cases = [
        {
            "name": "外部题库启用 - 有效答案",
            "params": {"title": "测试问题1", "type": "single"},
            "expected": "应该优先查询外部题库，找到有效答案则返回"
        },
        {
            "name": "外部题库启用 - 未找到消息",
            "params": {"title": "测试问题2", "type": "single"},
            "expected": "应该查询外部题库，返回'未找到'消息则使用AI"
        },
        {
            "name": "外部题库启用 - 未命中",
            "params": {"title": "测试问题3", "type": "single"},
            "expected": "应该查询外部题库，未找到则使用AI"
        },
        {
            "name": "外部题库禁用",
            "params": {"title": "测试问题4", "type": "single"},
            "expected": "外部题库未启用，直接使用AI"
        }
    ]

    print("🔍 外部题库优先级逻辑演示")
    print("=" * 50)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试案例 {i}: {test_case['name']}")
        print(f"预期行为: {test_case['expected']}")
        print(f"请求参数: {test_case['params']}")

        try:
            response = requests.get(f"{base_url}/api/search", params=test_case['params'])
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 1:
                    print("✅ 成功: 获得答案")
                    print(f"答案: {result.get('answer', 'N/A')[:50]}...")
                else:
                    print("❌ 失败: API返回错误")
                    print(f"错误信息: {result.get('msg', '未知错误')}")
            else:
                print(f"❌ HTTP错误: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络错误: {e}")
        except Exception as e:
            print(f"❌ 其他错误: {e}")

        time.sleep(1)  # 避免请求过于频繁

    print("\n" + "=" * 50)
    print("🎯 逻辑总结:")
    print("1. 首先尝试外部题库查询")
    print("2. 如果外部题库找到有效答案，直接返回")
    print("3. 如果外部题库返回'未找到'消息，识别为未找到，继续使用AI")
    print("4. 如果外部题库未找到答案或查询失败，使用AI")
    print("5. 如果外部题库功能未启用，直接使用AI")
    print("\n📝 '未找到'消息识别模式:")
    print("- 非常抱歉")
    print("- 题目搜索不到")
    print("- 未找到")
    print("- 没有找到")
    print("- 搜索不到")
    print("- 抱歉")
    print("- sorry")
    print("- not found")
    print("- no answer")
    print("- 无法找到")
    print("- 查询失败")
    print("- 暂无答案")

if __name__ == "__main__":
    test_external_db_priority()
