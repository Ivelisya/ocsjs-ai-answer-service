#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面测试套件：多子问题答案格式修复
包含所有可能的测试场景和边界情况
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import extract_answer, _is_multi_subquestion


class TestComprehensiveMultiSubQuestion:
    """全面测试多子问题答案格式修复功能"""

    # ===== 多子问题检测测试 =====

    def test_detect_multi_subquestion_numbered(self):
        """测试数字编号的多子问题检测"""
        questions = [
            "1. 问题1？ 2. 问题2？",
            "1.问题1 2.问题2 3.问题3",
            "1) 问题1？ 2) 问题2？",
            "（1）问题1 （2）问题2",
            "1.问题1\n2.问题2\n3.问题3",
            "1)问题1\n2)问题2",
        ]

        for question in questions:
            assert _is_multi_subquestion(question), f"应该检测到多子问题: {question}"

    def test_detect_single_question(self):
        """测试单一问题不被误检"""
        questions = [
            "这是一道单选题？",
            "请回答以下问题：",
            "选择正确的答案",
            "1. 这是一个问题",  # 只有一个问题
            "问题：",  # 没有编号
        ]

        for question in questions:
            assert not _is_multi_subquestion(question), f"不应该检测为多子问题: {question}"

    def test_detect_edge_cases(self):
        """测试边界情况"""
        # 空字符串
        assert not _is_multi_subquestion("")
        
        # 只有数字没有点号
        assert not _is_multi_subquestion("1 2 3")
        
        # 点号后没有内容
        assert not _is_multi_subquestion("1. 2. 3.")
        
        # 只有一个数字编号
        assert not _is_multi_subquestion("1. 这是一个问题")    # ===== 答案提取测试 =====

    def test_extract_answer_with_answer_tags(self):
        """测试带<answer>标签的答案提取"""
        ai_response = """<answer>答案1#答案2#答案3</answer>"""
        question = "1.问题1 2.问题2 3.问题3"

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 3
        assert lines[0] == "1.答案1"
        assert lines[1] == "2.答案2"
        assert lines[2] == "3.答案3"

    def test_extract_answer_with_answer_separator(self):
        """测试带答案：分隔符的答案提取"""
        ai_response = """答案：答案1#答案2#答案3"""
        question = "1.问题1 2.问题2 3.问题3"

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 3
        assert lines[0] == "1.答案1"
        assert lines[1] == "2.答案2"
        assert lines[2] == "3.答案3"

    def test_extract_answer_direct_text(self):
        """测试直接文本答案（无标签）"""
        ai_response = """答案1#答案2#答案3"""
        question = "1.问题1 2.问题2 3.问题3"

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 3
        assert lines[0] == "1.答案1"
        assert lines[1] == "2.答案2"
        assert lines[2] == "3.答案3"

    def test_extract_answer_sentence_separated(self):
        """测试句号分隔的答案"""
        ai_response = """答案1。答案2。答案3。"""
        question = "1.问题1 2.问题2 3.问题3"

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 3
        assert lines[0] == "1.答案1。"
        assert lines[1] == "2.答案2。"
        assert lines[2] == "3.答案3。"

    def test_extract_answer_space_separated(self):
        """测试空格分隔的答案"""
        ai_response = """答案1 答案2 答案3"""
        question = "1.问题1 2.问题2 3.问题3"

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 3
        assert lines[0].startswith("1.")
        assert lines[1].startswith("2.")
        assert lines[2].startswith("3.")

    # ===== 复杂答案处理测试 =====

    def test_extract_answer_with_semicolon(self):
        """测试包含分号的答案"""
        ai_response = """答案1；答案2；答案3"""
        question = "1.问题1 2.问题2 3.问题3"

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 3
        assert lines[0] == "1.答案1；"
        assert lines[1] == "2.答案2；"
        assert lines[2] == "3.答案3"

    def test_extract_answer_complex_content(self):
        """测试包含复杂内容的答案"""
        ai_response = """获取当前HTTP会话对象，如果不存在则创建一个新的会话#获取客户端随请求发送的所有Cookie对象数组#将指定的Cookie对象添加到HTTP响应中，使其发送到客户端浏览器并被存储#将HTTP响应重定向到指定的URL（cart.jsp），浏览器将自动跳转#这段代码实现了一个完整的用户登录验证功能，包括会话管理、Cookie处理和页面重定向"""
        question = "1.问题1 2.问题2 3.问题3 4.问题4 5.问题5"

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 5
        for i, line in enumerate(lines, 1):
            assert line.startswith(f"{i}."), f"第{i}行格式错误: {line}"

    def test_extract_answer_uneven_parts(self):
        """测试答案部分数量不匹配的情况"""
        ai_response = """答案1#答案2#答案3#答案4#答案5#答案6"""
        question = "1.问题1 2.问题2 3.问题3"  # 只有3个问题

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        # 应该合并多余的部分到最后一个答案
        assert len(lines) == 3
        assert lines[0] == "1.答案1"
        assert lines[1] == "2.答案2"
        assert "答案3#答案4#答案5#答案6" in lines[2]

    def test_extract_answer_few_parts(self):
        """测试答案部分数量少于问题数量的情况"""
        ai_response = """答案1#答案2"""
        question = "1.问题1 2.问题2 3.问题3 4.问题4 5.问题5"

        result = extract_answer(ai_response, "completion", question)

        # 应该返回原始答案，不进行格式化
        assert result == "答案1#答案2"

    # ===== 不同题目类型测试 =====

    def test_extract_answer_judgement_unchanged(self):
        """测试判断题不受影响"""
        ai_response = """<answer>正确</answer>"""
        question = "1.问题1 2.问题2"

        result = extract_answer(ai_response, "judgement", question)
        assert result == "正确"

    def test_extract_answer_single_choice_unchanged(self):
        """测试单选题不受影响"""
        ai_response = """<answer>选项A</answer>"""
        question = "1.问题1 2.问题2"

        result = extract_answer(ai_response, "single", question)
        assert result == "选项A"

    def test_extract_answer_multiple_choice_unchanged(self):
        """测试多选题不受影响"""
        ai_response = """<answer>选项A#选项B</answer>"""
        question = "1.问题1 2.问题2"

        result = extract_answer(ai_response, "multiple", question)
        assert result == "选项A#选项B"

    # ===== 特殊格式测试 =====

    def test_extract_answer_with_thinking_tags(self):
        """测试包含<thinking>标签的答案"""
        ai_response = """<thinking>让我分析一下这个问题</thinking>答案1#答案2#答案3"""
        question = "1.问题1 2.问题2 3.问题3"

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 3
        assert lines[0] == "1.答案1"
        assert lines[1] == "2.答案2"
        assert lines[2] == "3.答案3"

    def test_extract_answer_with_final_answer_marker(self):
        """测试包含最终答案标记的回答"""
        ai_response = """经过分析，我认为答案是：答案1#答案2#答案3"""
        question = "1.问题1 2.问题2 3.问题3"

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 3
        assert lines[0] == "1.答案1"
        assert lines[1] == "2.答案2"
        assert lines[2] == "3.答案3"

    # ===== 边界情况测试 =====

    def test_extract_answer_empty_response(self):
        """测试空回答"""
        ai_response = ""
        question = "1.问题1 2.问题2"

        result = extract_answer(ai_response, "completion", question)
        assert result == ""

    def test_extract_answer_no_separator(self):
        """测试没有分隔符的长文本"""
        ai_response = """这是一个很长的答案，没有明显的分割点，但应该被处理"""
        question = "1.问题1 2.问题2"

        result = extract_answer(ai_response, "completion", question)
        # 应该返回原始文本
        assert result == ai_response

    def test_extract_answer_only_numbers(self):
        """测试只有数字的答案"""
        ai_response = """1#2#3"""
        question = "1.问题1 2.问题2 3.问题3"

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 3
        assert lines[0] == "1.1"
        assert lines[1] == "2.2"
        assert lines[2] == "3.3"

    # ===== 实际用户案例测试 =====

    def test_user_real_case_1(self):
        """用户实际案例1：Java Servlet代码分析"""
        question = """1. HttpSession session = req.getSession(); 这一行代码实现什么功能？
2. Cookie[] cookies = req.getCookies(); 这一行代码实现什么功能？
3. resp.addCookie(langCookie); 这一行代码实现什么功能？
4. resp.sendRedirect("cart.jsp"); 这一行代码实现什么功能？
5. 说说这段代码实现主要完成一个什么功能？"""

        ai_response = """获取与当前请求关联的HttpSession对象，如果不存在则创建一个新的。 获取客户端（浏览器）随请求发送过来的所有Cookie对象。 将一个Cookie对象（langCookie）添加到HTTP响应中，使其发送到客户端（浏览器）并被存储。 向客户端发送一个重定向响应，指示浏览器跳转到指定的URL（cart.jsp）。 这段代码实现了一个简单的用户登录功能。它接收用户提交的用户名和密码，进行硬编码验证。如果验证成功，则创建或获取用户会话（HttpSession），将会话属性`user`设置为用户名，并根据用户请求中的Cookie或默认值设置一个语言偏好Cookie（`userLang`），然后将用户重定向到`cart.jsp`页面。如果验证失败，则向客户端输出"Login failed"。"""

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 5
        for i, line in enumerate(lines, 1):
            assert line.startswith(f"{i}."), f"第{i}行格式错误: {line}"

        # 验证具体内容
        assert "HttpSession对象" in lines[0]
        assert "Cookie对象" in lines[1]
        assert "HTTP响应" in lines[2]
        assert "重定向响应" in lines[3]
        assert "用户登录功能" in lines[4]

    def test_user_real_case_2(self):
        """用户实际案例2：带#分隔符的答案"""
        question = """1. 问题1？
2. 问题2？
3. 问题3？"""

        ai_response = """答案1#答案2#答案3"""

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 3
        assert lines[0] == "1.答案1"
        assert lines[1] == "2.答案2"
        assert lines[2] == "3.答案3"

    def test_user_real_case_3(self):
        """用户实际案例3：复杂内容答案"""
        question = """1. Python中如何定义函数？
2. 如何调用函数？
3. 函数的参数是什么？"""

        ai_response = """使用def关键字定义函数，后跟函数名和参数列表#使用函数名加括号调用函数，可以传递参数#函数参数是函数定义时括号内的变量，用于接收调用时传递的值"""

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 3
        assert "def关键字" in lines[0]
        assert "函数名加括号" in lines[1]
        assert "函数参数" in lines[2]  # 修正：检查实际内容而不是"参数列表"

    # ===== 错误处理测试 =====

    def test_extract_answer_invalid_format(self):
        """测试无效格式的处理"""
        ai_response = """<invalid>答案</invalid>"""
        question = "1.问题1 2.问题2"

        result = extract_answer(ai_response, "completion", question)
        # 应该返回清理后的文本
        assert result == "答案"

    def test_extract_answer_mixed_separators(self):
        """测试混合分隔符的处理"""
        ai_response = """答案1#答案2；答案3。答案4"""
        question = "1.问题1 2.问题2 3.问题3 4.问题4"

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 4
        assert lines[0] == "1.答案1"
        assert lines[1] == "2.答案2；"
        assert lines[2] == "3.答案3。"
        assert lines[3] == "4.答案4"

    # ===== 性能和稳定性测试 =====

    def test_extract_answer_long_content(self):
        """测试长内容的处理"""
        long_answer = "#".join([f"答案{i}" for i in range(1, 21)])  # 20个答案
        question = " ".join([f"{i}.问题{i}？" for i in range(1, 21)])

        result = extract_answer(long_answer, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 20
        for i, line in enumerate(lines, 1):
            assert line.startswith(f"{i}."), f"第{i}行格式错误: {line}"

    def test_extract_answer_special_characters(self):
        """测试特殊字符的处理"""
        ai_response = """答案1（包含中文括号）#答案2"包含引号"#答案3'包含单引号'#答案4<包含尖括号>#答案5&包含和号"""
        question = "1.问题1 2.问题2 3.问题3 4.问题4 5.问题5"

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 5
        for i, line in enumerate(lines, 1):
            assert line.startswith(f"{i}."), f"第{i}行格式错误: {line}"

    def test_extract_answer_unicode_content(self):
        """测试Unicode字符的处理"""
        ai_response = """函数定义#类继承#异常处理#文件操作#网络编程"""
        question = "1.Python函数 2.Python类 3.Python异常 4.Python文件 5.Python网络"

        result = extract_answer(ai_response, "completion", question)
        lines = result.split('\n')

        assert len(lines) == 5
        assert "函数定义" in lines[0]
        assert "类继承" in lines[1]
        assert "异常处理" in lines[2]
        assert "文件操作" in lines[3]
        assert "网络编程" in lines[4]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])