#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多子问题识别
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import _is_multi_subquestion
import re

def test_multi_subquestion_detection():
    """测试多子问题识别"""

    # 测试题目
    question = '1. HttpSession session = req.getSession(); 这一行代码实现什么功能？ 2. Cookie[] cookies = req.getCookies(); 这一行代码实现什么功能？ 3. resp.addCookie(langCookie); 这一行代码实现什么功能？ 4. resp.sendRedirect("cart.jsp"); 这一行代码实现什么功能？ 5. 说说这段代码实现主要完成一个什么功能？'

    print("=== 测试题目 ===")
    print(question)
    print()

    result = _is_multi_subquestion(question)
    print(f'题目是否被识别为多子问题: {result}')
    print()

    # 检查正则表达式匹配
    patterns = [
        r'\d+\.\s*.*?\n.*?\d+\.',  # 数字编号：1. xxx 2. xxx
        r'\d+\)\s*.*?\n.*?\d+\)',  # 括号编号：1) xxx 2) xxx
        r'[（(]\s*\d+\s*[）)]\s*.*?\n.*?[（(]\s*\d+\s*[）)]',  # 中文括号编号：（1）xxx （2）xxx
    ]

    for i, pattern in enumerate(patterns):
        matches = re.findall(pattern, question, re.MULTILINE | re.DOTALL)
        print(f'模式{i+1}匹配结果: {matches}')

    # 检查题目中的数字点号
    digit_dots = re.findall(r'\d+\.', question)
    print(f'题目中的数字点号: {digit_dots}')
    print(f'数字点号数量: {len(digit_dots)}')

if __name__ == "__main__":
    test_multi_subquestion_detection()