#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EduBrain AI 问答系统 - 功能测试题目生成器
用于测试和验证系统的各项功能
"""
import json
import random
from typing import List, Dict, Any

class TestQuestionGenerator:
    """测试题目生成器"""

    def __init__(self):
        self.test_questions = {
            "single": [
                {
                    "title": "以下哪项不是Python的基本数据类型？",
                    "type": "single",
                    "options": "A. int\nB. str\nC. list\nD. function",
                    "expected_answer": "D"
                },
                {
                    "title": "在Python中，以下哪个语句用于输出信息？",
                    "type": "single",
                    "options": "A. input()\nB. print()\nC. len()\nD. type()",
                    "expected_answer": "B"
                },
                {
                    "title": "以下哪种循环结构在Python中不存在？",
                    "type": "single",
                    "options": "A. for循环\nB. while循环\nC. do-while循环\nD. 递归",
                    "expected_answer": "C"
                }
            ],
            "multiple": [
                {
                    "title": "以下哪些是Python的合法变量名？",
                    "type": "multiple",
                    "options": "A. _name\nB. 2var\nC. my-var\nD. class_name",
                    "expected_answer": "A,D"
                },
                {
                    "title": "在Python中，以下哪些是不可变类型？",
                    "type": "multiple",
                    "options": "A. 列表\nB. 字符串\nC. 字典\nD. 元组",
                    "expected_answer": "B,D"
                }
            ],
            "judgement": [
                {
                    "title": "Python中的变量名区分大小写",
                    "type": "judgement",
                    "options": "",
                    "expected_answer": "正确"
                },
                {
                    "title": "在Python中，缩进不是强制要求的",
                    "type": "judgement",
                    "options": "",
                    "expected_answer": "错误"
                },
                {
                    "title": "Python支持面向对象编程",
                    "type": "judgement",
                    "options": "",
                    "expected_answer": "正确"
                }
            ]
        }

    def generate_test_questions(self, count: int = 5) -> List[Dict[str, Any]]:
        """生成指定数量的测试题目"""
        all_questions = []
        for question_type, questions in self.test_questions.items():
            all_questions.extend(questions)

        # 随机选择题目
        selected_questions = random.sample(all_questions, min(count, len(all_questions)))

        return selected_questions

    def save_test_questions(self, filename: str = "test_questions.json"):
        """保存测试题目到文件"""
        test_data = {
            "description": "EduBrain AI 问答系统功能测试题目",
            "version": "1.0",
            "questions": self.generate_test_questions(10)
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 测试题目已保存到 {filename}")

    def print_test_questions(self, count: int = 5):
        """打印测试题目"""
        questions = self.generate_test_questions(count)

        print("🎯 EduBrain AI 问答系统 - 功能测试题目")
        print("=" * 50)

        for i, q in enumerate(questions, 1):
            print(f"\n📝 题目 {i}:")
            print(f"题目: {q['title']}")
            print(f"类型: {q['type']}")
            if q['options']:
                print(f"选项:\n{q['options']}")
            print(f"预期答案: {q['expected_answer']}")
            print("-" * 30)

def create_api_test_script():
    """创建API测试脚本"""
    test_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EduBrain AI API 测试脚本
"""
import requests
import json
import time

def test_api_endpoint(base_url: str = "http://localhost:5000"):
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
                timeout=30
            )

            print(f"状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("✅ 请求成功"                if result.get("code") == 0:
                    print(f"❌ 业务错误: {result.get('msg', '未知错误')}")
                else:
                    print("📝 AI回答:"                    print(result)
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
'''

    with open("test_api_manual.py", 'w', encoding='utf-8') as f:
        f.write(test_script)

    print("✅ API测试脚本已创建: test_api_manual.py")

def main():
    """主函数"""
    print("🎯 EduBrain AI 问答系统 - 测试题目生成器")
    print("=" * 50)

    generator = TestQuestionGenerator()

    # 生成并显示测试题目
    print("\n📋 生成的测试题目:")
    generator.print_test_questions(5)

    # 保存测试题目
    generator.save_test_questions()

    # 创建API测试脚本
    create_api_test_script()

    print("\n📖 使用说明:")
    print("1. 确保 Flask 应用正在运行 (python app.py)")
    print("2. 运行测试脚本: python test_api_manual.py")
    print("3. 检查网络连接和 API 配置")
    print("4. 如果仍有问题，请检查防火墙和代理设置")

if __name__ == "__main__":
    main()
