#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EduBrain AI API 测试脚本
"""
import requests
import json
import time

def test_api_endpoint(base_url: str = "http://localhost:8000"):
    """测试API端点"""

    test_questions = [
        {
            "title": "Python中如何定义一个函数？",
            "type": "single",
            "options": "A. function myFunc()\nB. def myFunc()\nC. func myFunc()\nD. define myFunc()"
        },
        {
            "title": "以下哪些是Python的关键字？",
            "type": "multiple",
            "options": "A. if\nB. then\nC. else\nD. for"
        },
        {
            "title": "Python支持多线程编程",
            "type": "judgement",
            "options": ""
        },
        {
            "title": "Python中的列表是___的（有序/无序）",
            "type": "completion",
            "options": "",
            "context": "【题型】completion\n【题目】Python中的列表是___的（有序/无序）\n【选项】"
        },
        {
            "title": "这幅图展示了什么数据结构？",
            "type": "single",
            "options": "A. 数组\nB. 链表\nC. 二叉树\nD. 图",
            "context": "【题型】single\n【题目】这幅图展示了什么数据结构？![img](https://example.com/binary_tree.png)\n【选项】A. 数组\nB. 链表\nC. 二叉树\nD. 图"
        },
        {
            "title": "Reading Comprehension (2 points) Python is an interpreted, high-level, general-purpose programming language. Created by Guido van Rossum and first released in 1991. \n\n(1) Who created Python?",
            "type": "single",
            "options": "A. James Gosling\nB. Guido van Rossum\nC. Dennis Ritchie\nD. Bjarne Stroustrup",
            "context": ""
        }
    ]

    print("🚀 开始测试 EduBrain AI API...")
    print(f"📡 目标地址: {base_url}")
    print("=" * 50)

    for i, question in enumerate(test_questions, 1):
        print(f"\n🔍 测试题目 {i}:")
        print(f"题目: {question['title']}")

        try:
            # 发送请求
            response = requests.post(
                f"{base_url}/api/search",
                json=question,
                headers={"Content-Type": "application/json"},
                timeout=120
            )

            print(f"状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("✅ 请求成功")
                if result.get("code") == 0:
                    print(f"❌ 业务错误: {result.get('msg', '未知错误')}")
                else:
                    print("📝 AI回答:")
                    print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"❌ HTTP错误: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"❌ 网络错误: {str(e)}")
        except Exception as e:
            print(f"❌ 其他错误: {str(e)}")

        time.sleep(1)  # 避免请求过于频繁

    print("\n🎉 API测试完成!")

if __name__ == "__main__":
    test_api_endpoint()
