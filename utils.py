# -*- coding: utf-8 -*-
"""
工具函数模块
包含缓存管理、答案处理和OpenAI API调用等辅助功能
"""
import json
import time
import os
import hashlib
from typing import Dict, Any, Optional, Tuple

class SimpleCache:
    """简单的内存缓存实现"""
    
    def __init__(self, expiration_seconds: int = 86400):
        """
        初始化缓存
        
        Args:
            expiration_seconds: 缓存过期时间（秒），默认24小时
        """
        self.cache = {}
        self.expiration = expiration_seconds
    
    def _generate_key(self, question: str, question_type: str, options: str) -> str:
        """
        根据问题内容生成缓存键
        
        Args:
            question: 问题内容
            question_type: 问题类型
            options: 选项内容
            
        Returns:
            str: 缓存键
        """
        # 使用问题内容、类型和选项的组合生成哈希键
        content = f"{question}|{question_type}|{options}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get(self, question: str, question_type: str = "", options: str = "") -> Optional[str]:
        """
        从缓存获取答案
        
        Args:
            question: 问题内容
            question_type: 问题类型
            options: 选项内容
            
        Returns:
            Optional[str]: 缓存的答案，如果不存在或已过期则返回None
        """
        key = self._generate_key(question, question_type, options)
        if key in self.cache:
            timestamp, value = self.cache[key]
            # 检查缓存是否过期
            if time.time() - timestamp < self.expiration:
                return value
            # 缓存已过期，删除
            del self.cache[key]
        return None
    
    def set(self, question: str, answer: str, question_type: str = "", options: str = "") -> None:
        """
        设置缓存
        
        Args:
            question: 问题内容
            answer: 答案内容
            question_type: 问题类型
            options: 选项内容
        """
        key = self._generate_key(question, question_type, options)
        self.cache[key] = (time.time(), answer)
    
    def clear(self) -> None:
        """清空所有缓存"""
        self.cache.clear()
    
    def remove_expired(self) -> int:
        """
        删除所有过期的缓存项
        
        Returns:
            int: 删除的缓存项数量
        """
        now = time.time()
        expired_keys = [
            key for key, (timestamp, _) in self.cache.items() 
            if now - timestamp >= self.expiration
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)


def format_answer_for_ocs(question: str, answer: str) -> Dict[str, Any]:
    """
    格式化答案为OCS期望的格式
    
    Args:
        question: 问题内容
        answer: 答案内容
        
    Returns:
        Dict[str, Any]: 格式化后的响应
    """
    return {
        'code': 1,
        'question': question,
        'answer': answer
    }


def parse_question_and_options(question: str, options: str, question_type: str) -> str:
    """
    解析问题和选项，为OpenAI API构建更好的提示
    
    Args:
        question: 问题内容
        options: 选项内容
        question_type: 问题类型（单选、多选、判断、填空）
        
    Returns:
        str: 格式化后的提示
    """
    prompt = f"问题: {question}\n"
    
    # 添加题目类型提示
    type_prompts = {
        "single": "这是一道单选题。",
        "multiple": "这是一道多选题，答案请用#符号分隔。",
        "judgement": "这是一道判断题，需要回答：正确/对/true/√ 或者 错误/错/false/×。",
        "completion": "这是一道填空题。"
    }
    
    if question_type in type_prompts:
        prompt += f"{type_prompts[question_type]}\n"
    
    if options:
        prompt += f"选项:\n{options}\n"
    
    # 移除通用的“请直接给出答案，不要解释。”指令，它将在app.py中统一处理
    return prompt.strip() # strip()确保末尾没有多余的换行符


def extract_answer(ai_response: str, question_type: str) -> str:
    """
    从AI响应中提取并初步格式化答案。
    主要针对多选题，尝试将常见分隔符统一为 '#'。
    
    Args:
        ai_response: AI生成的完整响应
        question_type: 问题类型
        
    Returns:
        str: 提取并格式化后的答案部分
    """
    cleaned_response = ai_response.strip()

    if question_type == "multiple":
        # 如果响应中已经包含 #, 假设格式正确
        if "#" in cleaned_response:
            return cleaned_response
        
        # 尝试替换常见的其他分隔符为 #
        # 顺序很重要，先替换更长的分隔符
        # 替换多个空格为单个空格，便于后续处理
        processed_response = ' '.join(cleaned_response.split())
        
        # 替换 "A, B, C" 或 "A B C" 形式为 "A#B#C"
        # 这里的逻辑是，如果选项是单个字符或短词，并且用空格或逗号分隔
        # 注意：这个替换逻辑可能需要根据实际模型输出进行调整，以避免错误替换
        # 例如，如果答案本身是 "选项 A 和 选项 B"，这个逻辑可能会错误地变成 "选项#A#和#选项#B"
        # 一个更安全的做法是，如果prompt要求模型返回选项内容，那么模型应该返回类似 "内容1#内容2"
        # 如果模型返回的是 "内容1, 内容2" 或 "内容1 内容2"，这里的替换才比较安全。
        
        # 简单的替换：将逗号和空格都视作潜在分隔符
        # 替换逗号为空格，然后统一用#替换空格
        # 这假设选项内容本身不包含逗号或不重要的空格
        temp_response = processed_response.replace(",", " ")
        # 将多个空格合并为一个
        temp_response = ' '.join(temp_response.split())
        # 如果处理后仍有空格（之前不是#分隔），则替换为空格
        if " " in temp_response and "#" not in temp_response : # 只有在没有#且有空格时才替换
             return temp_response.replace(" ", "#")
        
        return processed_response # 如果没有明显的分隔符可以安全替换，返回清理过的响应

    # 对于其他题型，直接返回清理后的响应
    return cleaned_response