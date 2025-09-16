#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修改后的答案处理逻辑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import extract_answer

def test_fixed_logic():
    """测试修改后的答案处理逻辑"""

    # 模拟AI返回的答案（用#分隔）
    ai_response = '获取当前请求的会话对象，如果会话不存在则创建一个新的会话。#获取客户端随当前请求发送过来的所有Cookie对象。#将一个Cookie对象添加到响应中，以便发送给客户端浏览器。#将客户端重定向到指定的URL（"cart.jsp"）。#这段代码主要实现会话管理、Cookie处理（例如设置用户语言偏好）以及页面重定向到购物车页面。'

    question = '1. HttpSession session = req.getSession(); 这一行代码实现什么功能？ 2. Cookie[] cookies = req.getCookies(); 这一行代码实现什么功能？ 3. resp.addCookie(langCookie); 这一行代码实现什么功能？ 4. resp.sendRedirect("cart.jsp"); 这一行代码实现什么功能？ 5. 说说这段代码实现主要完成一个什么功能？'

    print("=== 模拟AI回答 ===")
    print(ai_response)
    print("\n" + "="*50)

    result = extract_answer(ai_response, 'completion', question)

    print("=== 处理结果 ===")
    print(repr(result))
    print("\n" + "="*50)

    print("=== 格式化输出 ===")
    print(result)
    print("\n" + "="*50)

    # 检查答案格式
    if '\n' in result:
        print("✅ 结果包含换行符 - 格式正确")
        lines = result.split('\n')
        print(f"行数: {len(lines)}")
        for i, line in enumerate(lines, 1):
            print(f"  {i}: {line}")
            if not line.startswith(f"{i}."):
                print(f"❌ 第{i}行格式不正确")
            else:
                print(f"✅ 第{i}行格式正确")
    else:
        print("❌ 结果不包含换行符 - 格式错误")

if __name__ == "__main__":
    test_fixed_logic()