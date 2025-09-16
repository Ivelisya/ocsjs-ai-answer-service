#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用户最新提供的AI回答格式
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import extract_answer

def test_user_latest_response():
    """测试用户最新提供的AI回答格式"""
    
    # 用户的题目
    question = """1. HttpSession session = req.getSession(); 这一行代码实现什么功能？
2. Cookie[] cookies = req.getCookies(); 这一行代码实现什么功能？
3. resp.addCookie(langCookie); 这一行代码实现什么功能？
4. resp.sendRedirect("cart.jsp"); 这一行代码实现什么功能？
5. 说说这段代码实现主要完成一个什么功能？"""
    
    # 用户最新提供的AI回答（包含思考过程）
    ai_response = """The user wants me to analyze a Java Servlet code and answer five specific questions based on it. This is a completion task, and I need to provide answers for each question, separated by ' '. My primary goal is absolute precision in the answers, especially for the functional descriptions.

I will go through each question one by one.

**Question 1: `HttpSession session = req.getSession();` 这一行代码实现什么功能?**
*   **Analysis**: This line of code is standard in Java Servlets. `req.getSession()` retrieves the current `HttpSession` associated with the request. If no session exists for the current user, it creates a new one. Sessions are crucial for maintaining state across multiple requests from the same user.
*   **Answer Formulation**: 获取与当前请求关联的HttpSession对象，如果不存在则创建一个新的。

**Question 2: `Cookie[] cookies = req.getCookies();` 这一行代码实现什么功能?**
*   **Analysis**: `req.getCookies()` is used to retrieve an array of `Cookie` objects that were sent by the client (browser) with the current HTTP request.
*   **Answer Formulation**: 获取客户端（浏览器）随请求发送过来的所有Cookie对象。

**Question 3: `resp.addCookie(langCookie);` 这一行代码实现什么功能?**
*   **Analysis**: `resp.addCookie()` is used to add a `Cookie` object to the HTTP response. This cookie will then be sent to the client's browser, which will store it and send it back with subsequent requests to the same domain (until it expires or is deleted).
*   **Answer Formulation**: 将一个Cookie对象（langCookie）添加到HTTP响应中，使其发送到客户端（浏览器）并被存储。

**Question 4: `resp.sendRedirect("cart.jsp");` 这一行代码实现什么功能?**
*   **Analysis**: `resp.sendRedirect()` instructs the client's browser to make a new request to a different URL. It sends an HTTP redirect response (usually a 302 status code) with the new URL in the `Location` header. The browser then automatically navigates to that new URL.
*   **Answer Formulation**: 向客户端发送一个重定向响应，指示浏览器跳转到指定的URL（cart.jsp）。

**Question 5: 说说这段代码实现主要完成一个什么功能?**
*   **Analysis**: I need to summarize the entire `doPost` method's functionality.
    1.  **Login Form Processing**: It processes a POST request, likely from a login form, extracting `username` and `password`.
    2.  **Authentication**: It performs a simple, hardcoded authentication check (`admin` / `123456`).
    3.  **Session Management (Success)**: If authentication succeeds, it obtains/creates an `HttpSession` and stores the `username` in it, indicating a logged-in state.
    4.  **Cookie Management (Language Preference)**: It reads existing cookies to find a `userLang` preference. If found, it uses that; otherwise, it defaults to "zh". It then creates/updates this `userLang` cookie with a 30-day expiry and adds it to the response.
    5.  **Redirection (Success)**: Upon successful login, it redirects the user to `cart.jsp`.
    6.  **Error Handling (Failure)**: If authentication fails, it writes "Login failed" directly to the response.
*   **Overall Function**: This code implements a basic user login servlet that authenticates users, manages their session state, handles language preferences using cookies, and redirects them to a specific page upon successful login.
*   **Answer Formulation**: 这段代码实现了一个简单的用户登录功能。它接收用户提交的用户名和密码，进行硬编码验证。如果验证成功，则创建或获取用户会话（HttpSession），将会话属性`user`设置为用户名，并根据用户请求中的Cookie或默认值设置一个语言偏好Cookie（`userLang`），然后将用户重定向到`cart.jsp`页面。如果验证失败，则向客户端输出"Login failed"。

【批判性反思】
*   **绝对精确原则**: 我需要确保我的答案是针对每个问题的完整功能描述，并且避免任何缩写或不精确的词语。
*   **格式遵从**: 答案之间必须使用 ` ` 作为分隔符。
*   **上下文利用**: 没有额外的上下文，只依据提供的代码。
*   **深度思考**: 我已经一步步分析了每行代码和整体逻辑。

Looks good. I will now construct the final answer.获取与当前请求关联的HttpSession对象，如果不存在则创建一个新的。 获取客户端（浏览器）随请求发送过来的所有Cookie对象。 将一个Cookie对象（langCookie）添加到HTTP响应中，使其发送到客户端（浏览器）并被存储。 向客户端发送一个重定向响应，指示浏览器跳转到指定的URL（cart.jsp）。 这段代码实现了一个简单的用户登录功能。它接收用户提交的用户名和密码，进行硬编码验证。如果验证成功，则创建或获取用户会话（HttpSession），将会话属性`user`设置为用户名，并根据用户请求中的Cookie或默认值设置一个语言偏好Cookie（`userLang`），然后将用户重定向到`cart.jsp`页面。如果验证失败，则向客户端输出"Login failed"。"""
    
    print("=== 用户最新提供的AI回答 ===")
    print(ai_response)
    print("\n" + "="*50)
    
    # 提取答案
    result = extract_answer(ai_response, "completion", question)
    
    print("=== 修复后的答案格式 ===")
    print(result)
    print("\n" + "="*50)
    
    # 验证格式
    lines = result.split('\n')
    print(f"答案行数: {len(lines)}")
    
    for i, line in enumerate(lines, 1):
        print(f"{i}. {line}")
        assert line.startswith(f"{i}."), f"第{i}行格式不正确: {line}"
    
    assert len(lines) == 5, f"应该有5行答案，得到{len(lines)}行"
    
    print("\n✅ 用户最新AI回答格式处理测试通过！")
    print("用户现在会看到期望的格式:")
    for i, line in enumerate(lines, 1):
        print(f"  {line}")

if __name__ == "__main__":
    try:
        test_user_latest_response()
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)