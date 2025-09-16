#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单API测试
"""

import requests
import json
import time

def test_api():
    """测试API"""

    # 等待服务器启动
    time.sleep(2)

    url = 'http://localhost:5000/api/search'
    data = {
        'title': '1. HttpSession session = req.getSession(); 这一行代码实现什么功能？ 2. Cookie[] cookies = req.getCookies(); 这一行代码实现什么功能？ 3. resp.addCookie(langCookie); 这一行代码实现什么功能？ 4. resp.sendRedirect("cart.jsp"); 这一行代码实现什么功能？ 5. 说说这段代码实现主要完成一个什么功能？',
        'type': 'completion',
        'options': ''
    }

    try:
        print("发送API请求...")
        response = requests.post(url, json=data, timeout=30)
        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("\n=== API响应 ===")
            print(json.dumps(result, ensure_ascii=False, indent=2))

            answer = result.get('answer', '')
            print(f"\n=== 答案内容 ===")
            print(repr(answer))

            print(f"\n=== 答案格式化输出 ===")
            print(answer)

            # 检查答案格式
            if '\n' in answer:
                print("\n✅ 答案包含换行符 - 格式正确")
                lines = answer.split('\n')
                print(f"行数: {len(lines)}")
                for i, line in enumerate(lines, 1):
                    print(f"  {i}: {line}")
            else:
                print("\n❌ 答案不包含换行符 - 格式错误")
        else:
            print(f"请求失败: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f'请求异常: {e}')

if __name__ == "__main__":
    test_api()