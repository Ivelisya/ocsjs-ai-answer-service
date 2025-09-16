#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新增测试：多子问题答案格式修复的测试
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import extract_answer, _is_multi_subquestion


class TestMultiSubQuestion:
    """测试多子问题答案格式修复功能"""

    def test_is_multi_subquestion_detection(self):
        """测试多子问题检测"""
        # 用户的真实多子问题案例
        multi_question = """1. HttpSession session = req.getSession(); 这一行代码实现什么功能？
2. Cookie[] cookies = req.getCookies(); 这一行代码实现什么功能？
3. resp.addCookie(langCookie); 这一行代码实现什么功能？
4. resp.sendRedirect("cart.jsp"); 这一行代码实现什么功能？
5. 说说这段代码实现主要完成一个什么功能？"""

        assert _is_multi_subquestion(multi_question) == True

        # 单一问题
        single_question = "在Python中，以下哪个语句用于输出信息？"
        assert _is_multi_subquestion(single_question) == False

        # 括号编号
        parentheses_question = """1) 第一个问题？
2) 第二个问题？"""
        assert _is_multi_subquestion(parentheses_question) == True

    def test_extract_answer_multi_question_format(self):
        """测试多子问题答案格式转换"""
        # 模拟AI返回的答案（用#分隔）
        ai_response = """<answer>获取当前HTTP会话对象，如果不存在则创建一个新的会话#获取客户端随请求发送的所有Cookie#将一个Cookie添加到HTTP响应中，使其发送给客户端#将客户端重定向到指定的URL#这段代码实现了登录验证功能</answer>"""

        multi_question = """1. 问题1？
2. 问题2？
3. 问题3？
4. 问题4？
5. 问题5？"""

        result = extract_answer(ai_response, "completion", multi_question)
        
        # 验证格式
        lines = result.split('\n')
        assert len(lines) == 5, f"应该有5行答案，得到{len(lines)}行"
        
        for i, line in enumerate(lines, 1):
            assert line.startswith(f"{i}."), f"第{i}行应该以'{i}.'开始，实际是: {line}"

    def test_extract_answer_single_question_unchanged(self):
        """测试单一问题答案不被格式化"""
        ai_response = "<answer>print()</answer>"
        single_question = "在Python中，以下哪个语句用于输出信息？"
        
        result = extract_answer(ai_response, "completion", single_question)
        assert result == "print()", "单一问题答案不应该被格式化"

    def test_extract_answer_non_completion_unchanged(self):
        """测试非填空题类型不受影响"""
        ai_response = "<answer>选项A#选项B</answer>"
        multi_question = """1. 问题1？
2. 问题2？"""
        
        # 多选题格式应该保持不变
        result = extract_answer(ai_response, "multiple", multi_question)
        assert result == "选项A#选项B", "多选题答案格式不应该被改变"

    def test_extract_answer_complex_last_answer(self):
        """测试包含复杂最后答案的情况"""
        ai_response = """<answer>答案1#答案2#答案3#这是一个很长的答案，包含标点符号、分号；以及其他复杂内容</answer>"""
        
        multi_question = """1. 问题1？
2. 问题2？
3. 问题3？
4. 问题4？"""
        
        result = extract_answer(ai_response, "completion", multi_question)
        lines = result.split('\n')
        
        assert len(lines) == 4, f"应该有4行答案，得到{len(lines)}行"
        assert lines[0] == "1.答案1"
        assert lines[1] == "2.答案2"
        assert lines[2] == "3.答案3"
        assert "这是一个很长的答案" in lines[3]

    def test_user_real_case_scenario(self):
        """测试用户提供的真实案例"""
        # 这是用户实际遇到的情况
        question = """1. HttpSession session = req.getSession(); 这一行代码实现什么功能？
2. Cookie[] cookies = req.getCookies(); 这一行代码实现什么功能？
3. resp.addCookie(langCookie); 这一行代码实现什么功能？
4. resp.sendRedirect("cart.jsp"); 这一行代码实现什么功能？
5. 说说这段代码实现主要完成一个什么功能？"""

        # 预期的AI回答格式
        ai_response = """<answer>获取当前HTTP会话对象，如果不存在则创建一个新的会话#获取客户端随请求发送的所有Cookie#将一个Cookie添加到HTTP响应中，使其发送给客户端#将客户端重定向到指定的URL（"cart.jsp"）#这段代码实现了一个简单的用户登录验证功能。成功登录后，它会创建用户会话，处理语言偏好Cookie，并将用户重定向到cart.jsp页面；登录失败则显示错误信息</answer>"""

        result = extract_answer(ai_response, "completion", question)
        
        # 验证用户期望的格式：每行一个答案，带序号
        lines = result.split('\n')
        assert len(lines) == 5
        
        expected_starts = [
            "1.获取当前HTTP会话对象",
            "2.获取客户端随请求发送的所有Cookie", 
            "3.将一个Cookie添加到HTTP响应中",
            "4.将客户端重定向到指定的URL",
            "5.这段代码实现了一个简单的用户登录验证功能"
        ]
        
        for i, (line, expected_start) in enumerate(zip(lines, expected_starts)):
            assert line.startswith(expected_start), f"第{i+1}行格式不正确: {line}"

    def test_actual_ai_response_format(self):
        """测试实际AI回答格式（空格分隔的文本）"""
        # 这是用户实际遇到的AI回答格式（没有<answer>标签，用空格分隔）
        ai_response = """获取当前请求的会话对象（HttpSession），如果不存在则创建一个新的会话。 获取所有随当前请求从客户端发送到服务器的Cookie对象数组。 将指定的Cookie对象添加到HTTP响应中，使其发送到客户端浏览器。 将HTTP响应重定向到指定的URL（cart.jsp），浏览器将加载新的页面。 这段代码实现了一个简单的用户登录验证功能，成功登录后会设置用户会话、处理语言偏好Cookie并重定向到购物车页面，失败则提示登录失败。"""
        
        question = """1. HttpSession session = req.getSession(); 这一行代码实现什么功能？
2. Cookie[] cookies = req.getCookies(); 这一行代码实现什么功能？
3. resp.addCookie(langCookie); 这一行代码实现什么功能？
4. resp.sendRedirect("cart.jsp"); 这一行代码实现什么功能？
5. 说说这段代码实现主要完成一个什么功能？"""
        
        result = extract_answer(ai_response, "completion", question)
        
        # 验证格式转换
        lines = result.split('\n')
        assert len(lines) == 5, f"应该有5行答案，得到{len(lines)}行"
        
        # 验证每行都有正确的序号
        for i, line in enumerate(lines, 1):
            assert line.startswith(f"{i}."), f"第{i}行应该以'{i}.'开始，实际是: {line}"
        
        # 验证内容包含关键词
        assert "HttpSession" in lines[0]
        assert "Cookie" in lines[1] 
        assert "HTTP响应" in lines[2]
        assert "重定向" in lines[3]
        assert "登录验证功能" in lines[4]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])