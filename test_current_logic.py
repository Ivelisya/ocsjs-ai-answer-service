#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试当前答案处理逻辑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import extract_answer

def test_current_logic():
    """测试当前答案处理逻辑"""

    # 测试AI回答
    ai_response = '获取与当前请求关联的HttpSession对象，如果不存在则创建一个新的。 获取客户端（浏览器）随请求发送过来的所有Cookie对象。 将一个Cookie对象（langCookie）添加到HTTP响应中，使其发送到客户端（浏览器）并被存储。 向客户端发送一个重定向响应，指示浏览器跳转到指定的URL（cart.jsp）。 这段代码实现了一个简单的用户登录功能。它接收用户提交的用户名和密码，进行硬编码验证。如果验证成功，则创建或获取用户会话（HttpSession），将会话属性user设置为用户名，并根据用户请求中的Cookie或默认值设置一个语言偏好Cookie（userLang），然后将用户重定向到cart.jsp页面。如果验证失败，则向客户端输出Login failed。'

    question = '''1. HttpSession session = req.getSession(); 这一行代码实现什么功能？
2. Cookie[] cookies = req.getCookies(); 这一行代码实现什么功能？
3. resp.addCookie(langCookie); 这一行代码实现什么功能？
4. resp.sendRedirect("cart.jsp"); 这一行代码实现什么功能？
5. 说说这段代码实现主要完成一个什么功能？'''

    print("=== 原始AI回答 ===")
    print(ai_response)
    print("\n" + "="*50)

    result = extract_answer(ai_response, 'completion', question)

    print("=== 处理结果 ===")
    print(repr(result))
    print("\n" + "="*50)

    print("=== 格式化输出 ===")
    print(result)
    print("\n" + "="*50)

    # 检查是否包含换行符
    if '\n' in result:
        print("✅ 结果包含换行符 - 格式正确")
        lines = result.split('\n')
        print(f"行数: {len(lines)}")
        for i, line in enumerate(lines, 1):
            print(f"  {i}: {line}")
    else:
        print("❌ 结果不包含换行符 - 格式错误")

if __name__ == "__main__":
    test_current_logic()