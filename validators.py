# -*- coding: utf-8 -*-
"""
输入验证模块
"""
import re
from typing import Optional


class InputValidator:
    """输入验证器"""
    
    # 最大长度限制
    MAX_QUESTION_LENGTH = 5000
    MAX_OPTIONS_LENGTH = 2000
    MAX_CONTEXT_LENGTH = 10000
    
    # 允许的题目类型
    ALLOWED_TYPES = {"single", "multiple", "judgement", "completion", ""}
    
    @classmethod
    def validate_question(cls, question: str) -> tuple[bool, Optional[str]]:
        """验证问题内容"""
        if not question or not question.strip():
            return False, "问题内容不能为空"
        
        if len(question) > cls.MAX_QUESTION_LENGTH:
            return False, f"问题内容超过最大长度限制({cls.MAX_QUESTION_LENGTH}字符)"
        
        # 检查是否包含恶意内容
        if cls._contains_malicious_content(question):
            return False, "问题内容包含不当内容"
        
        return True, None
    
    @classmethod
    def validate_type(cls, question_type: str) -> tuple[bool, Optional[str]]:
        """验证题目类型"""
        if question_type not in cls.ALLOWED_TYPES:
            return False, f"不支持的题目类型: {question_type}"
        
        return True, None
    
    @classmethod
    def validate_options(cls, options: str) -> tuple[bool, Optional[str]]:
        """验证选项内容"""
        if not options:
            return True, None  # 选项可以为空
        
        if len(options) > cls.MAX_OPTIONS_LENGTH:
            return False, f"选项内容超过最大长度限制({cls.MAX_OPTIONS_LENGTH}字符)"
        
        if cls._contains_malicious_content(options):
            return False, "选项内容包含不当内容"
        
        return True, None
    
    @classmethod
    def validate_context(cls, context: str) -> tuple[bool, Optional[str]]:
        """验证上下文内容"""
        if not context:
            return True, None  # 上下文可以为空
        
        if len(context) > cls.MAX_CONTEXT_LENGTH:
            return False, f"上下文内容超过最大长度限制({cls.MAX_CONTEXT_LENGTH}字符)"
        
        if cls._contains_malicious_content(context):
            return False, "上下文内容包含不当内容"
        
        return True, None
    
    @classmethod
    def _contains_malicious_content(cls, text: str) -> bool:
        """检查是否包含恶意内容"""
        if not text:
            return False

        # 转换为小写进行检测
        text_lower = text.lower()

        # XSS攻击模式
        xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'<iframe[^>]*>.*?</iframe>',
            r'<object[^>]*>.*?</object>',
            r'<embed[^>]*>.*?</embed>',
        ]

        # SQL注入模式
        sql_patterns = [
            r';\s*drop\s+table',
            r';\s*delete\s+from',
            r'union\s+select',
            r'--\s*$',
            r'/\*\*/',
        ]

        # 命令注入模式
        command_patterns = [
            r';\s*rm\s+',
            r';\s*del\s+',
            r';\s*format\s+',
            r'&&\s*rm\s+',
            r'&&\s*del\s+',
        ]

        # 检测所有恶意模式
        all_patterns = xss_patterns + sql_patterns + command_patterns

        for pattern in all_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
                return True

        return False
