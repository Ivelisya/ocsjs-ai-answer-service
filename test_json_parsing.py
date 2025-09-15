#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试validate_external_answer函数的JSON解析功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import validate_external_answer

def test_json_parsing():
    """测试JSON格式答案的解析"""
    test_cases = [
        ('["GenericServlet"]', 'completion', '', '在Servlet开发中,当我们要自定义一个Servlet时,可以继承____或HttpServlet...'),
        ('GenericServlet', 'completion', '', '在Servlet开发中,当我们要自定义一个Servlet时,可以继承____或HttpServlet...'),
        ('["A"]', 'single', 'A. 选项A\nB. 选项B', '测试单选题'),
        ('A', 'single', 'A. 选项A\nB. 选项B', '测试单选题'),
    ]

    print("测试validate_external_answer函数的JSON解析功能:")
    print("=" * 60)

    for i, (answer, qtype, options, question) in enumerate(test_cases, 1):
        try:
            result = validate_external_answer(answer, qtype, options, question)
            print(f"测试 {i}: 答案='{answer}' -> 验证结果: {result}")
        except Exception as e:
            print(f"测试 {i}: 答案='{answer}' -> 错误: {e}")

    print("=" * 60)
    print("测试完成")

if __name__ == "__main__":
    test_json_parsing()
