#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试实际API调用
"""

import requests
import json

def test_api_call():
    """测试实际的API调用"""

    # 测试实际的API调用
    url = 'http://localhost:5000/api/search'
    data = {
        'title': '1. HttpSession session = req.getSession(); 这一行代码实现什么功能？ 2. Cookie[] cookies = req.getCookies(); 这一行代码实现什么功能？ 3. resp.addCookie(langCookie); 这一行代码实现什么功能？ 4. resp.sendRedirect("cart.jsp"); 这一行代码实现什么功能？ 5. 说说这段代码实现主要完成一个什么功能？',
        'type': 'completion',
        'options': ''
    }

    try:
        response = requests.post(url, json=data)
        result = response.json()
        print('API响应:')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print()
        print('答案内容:')
        print(repr(result.get('answer', '')))
        print()
        print('答案格式化输出:')
        print(result.get('answer', ''))

        # 检查答案格式
        answer = result.get('answer', '')
        if '\n' in answer:
            print("\n✅ API返回的答案包含换行符 - 格式正确")
            lines = answer.split('\n')
            print(f"行数: {len(lines)}")
            for i, line in enumerate(lines, 1):
                print(f"  {i}: {line}")
        else:
            print("\n❌ API返回的答案不包含换行符 - 格式错误")

    except Exception as e:
        print(f'请求失败: {e}')

if __name__ == "__main__":
    test_api_call()