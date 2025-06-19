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
import re
import unicodedata

class SimpleCache:
    """简单的内存缓存实现"""
    
    def __init__(self, expiration_seconds: int = 86400):
        self.cache = {}
        self.expiration = expiration_seconds
    
    def _generate_key(self, question: str, question_type: str, options: str) -> str:
        content = f"{question}|{question_type}|{options}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get(self, question: str, question_type: str = "", options: str = "") -> Optional[str]:
        key = self._generate_key(question, question_type, options)
        if key in self.cache:
            timestamp, value = self.cache[key]
            if time.time() - timestamp < self.expiration:
                return value
            del self.cache[key]
        return None
    
    def set(self, question: str, answer: str, question_type: str = "", options: str = "") -> None:
        key = self._generate_key(question, question_type, options)
        self.cache[key] = (time.time(), answer)
    
    def clear(self) -> None:
        self.cache.clear()
    
    def remove_expired(self) -> int:
        now = time.time()
        expired_keys = [
            key for key, (timestamp, _) in self.cache.items() 
            if now - timestamp >= self.expiration
        ]
        for key in expired_keys:
            del self.cache[key]
        return len(expired_keys)

def format_answer_for_ocs(question: str, answer: str) -> Dict[str, Any]:
    return {
        'code': 1,
        'question': question,
        'answer': answer
    }

def parse_question_and_options(question: str, options: str, question_type: str) -> str:
    prompt = f"问题: {question}\n"
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
    return prompt.strip()

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_answer(ai_response: str, question_type: str) -> str:
    match = re.search(r'<answer>(.*?)</answer>', ai_response, re.DOTALL)
    if match:
        answer = match.group(1).strip()
        if '#' in answer or '；' in answer or ';' in answer:
             answer = answer.replace('；', '#').replace(';', '#')
        return answer
    if "答案：" in ai_response:
        return ai_response.split("答案：")[-1].strip()
    cleaned_response = re.sub(r'<thinking>.*?</thinking>', '', ai_response, flags=re.DOTALL).strip()
    return cleaned_response

def parse_reading_comprehension(text: str) -> Tuple[str, str, str]:
    try:
        match = re.search(r'\(\d+\)\s*\(', text)
        if not match:
            parts = text.split('\n\n')
            if len(parts) > 1:
                context = '\n\n'.join(parts[:-1])
                question_part = parts[-1]
            else:
                return "", text, ""
        else:
            context_end_index = match.start()
            context = text[:context_end_index].strip()
            question_part = text[context_end_index:].strip()

        context = re.sub(r'.*Reading Comprehension.*?\d+\.\d+ points\)\s*', '', context, flags=re.IGNORECASE).strip()

        options_match = re.search(r'\sA\.', question_part)
        if options_match:
            question_end_index = options_match.start()
            question = question_part[:question_end_index].strip()
            options = question_part[question_end_index:].strip()
        else:
            question = question_part
            options = ""
            
        question = re.sub(r'\s*\(Single Choice.*?\)\s*', '', question).strip()

        return context, question, options
    except Exception:
        return "", text, ""