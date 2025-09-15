# -*- coding: utf-8 -*-
"""
工具函数模块
包含缓存管理、答案处理和OpenAI API调用等辅助功能
"""
import hashlib
import re
import time
import threading
import unicodedata
from typing import Any, Dict, Optional, Tuple

import redis

from config import Config
from logger import app_logger as logger


class Cache:
    """统一的缓存实现，支持内存和Redis"""

    def __init__(self, expiration_seconds: int = 86400, use_redis: bool = False):
        self.expiration: int = expiration_seconds
        self.use_redis: bool = use_redis and Config.REDIS_URL
        self._lock = threading.RLock()  # 添加线程锁
        
        if self.use_redis:
            try:
                self.redis_client: redis.Redis = redis.from_url(Config.REDIS_URL)
                self.redis_client.ping()  # 测试连接
            except redis.ConnectionError:
                logger.warning("Redis连接失败，使用内存缓存")
                self.use_redis = False
                self.memory_cache: Dict[str, Tuple[float, str]] = {}
        else:
            self.memory_cache: Dict[str, Tuple[float, str]] = {}

    def _generate_key(self, question: str, question_type: str, options: str) -> str:
        content = f"{question}|{question_type}|{options}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def get(self, question: str, question_type: str = "", options: str = "") -> Optional[str]:
        key = self._generate_key(question, question_type, options)
        if self.use_redis:
            try:
                value = self.redis_client.get(key)
                return value.decode("utf-8") if value else None
            except redis.ConnectionError:
                return None
        else:
            with self._lock:
                if key in self.memory_cache:
                    timestamp, value = self.memory_cache[key]
                    if time.time() - timestamp < self.expiration:
                        return value
                    del self.memory_cache[key]
                return None

    def set(self, question: str, answer: str, question_type: str = "", options: str = "") -> None:
        key = self._generate_key(question, question_type, options)
        if self.use_redis:
            try:
                self.redis_client.setex(key, self.expiration, answer)
            except redis.ConnectionError:
                pass
        else:
            with self._lock:
                self.memory_cache[key] = (time.time(), answer)

    def clear(self) -> None:
        if self.use_redis:
            try:
                self.redis_client.flushdb()
            except redis.ConnectionError:
                pass
        else:
            with self._lock:
                self.memory_cache.clear()

    def get_size(self) -> int:
        if self.use_redis:
            try:
                return self.redis_client.dbsize()
            except redis.ConnectionError:
                return 0
        else:
            with self._lock:
                return len(self.memory_cache)


def format_answer_for_ocs(question: str, answer: str) -> Dict[str, Any]:
    return {"code": 1, "question": question, "answer": answer}


def parse_question_and_options(question: str, options: str, question_type: str) -> str:
    prompt = f"问题: {question}\n"
    type_prompts = {
        "single": "这是一道单选题。",
        "multiple": "这是一道多选题，答案请用#符号分隔。",
        "judgement": "这是一道判断题，需要回答：正确/对/true/√ 或者 错误/错/false/×。",
        "completion": "这是一道填空题。",
    }
    if question_type in type_prompts:
        prompt += f"{type_prompts[question_type]}\n"
    if options:
        prompt += f"选项:\n{options}\n"
    return prompt.strip()


def normalize_text(text: str) -> str:
    """
    文本标准化函数
    优化Unicode处理和性能
    """
    if not text:
        return ""

    # 使用更高效的Unicode标准化
    text = unicodedata.normalize("NFKC", text)

    # 合并连续空白字符
    text = re.sub(r"\s+", " ", text)

    # 去除首尾空白
    return text.strip()


def extract_answer(ai_response: str, question_type: str) -> str:
    match = re.search(r"<answer>(.*?)</answer>", ai_response, re.DOTALL)
    if match:
        answer = match.group(1).strip()
        if "#" in answer or "；" in answer or ";" in answer:
            answer = answer.replace("；", "#").replace(";", "#")
        
        # 特殊处理判断题：确保只返回"正确"或"错误"
        if question_type == "judgement":
            answer_lower = answer.lower().strip()
            if answer_lower in ["正确", "对", "是", "true", "yes", "√"]:
                return "正确"
            elif answer_lower in ["错误", "错", "否", "false", "no", "×"]:
                return "错误"
            else:
                # 如果不是标准答案，尝试从回答中提取
                if "正确" in answer or "对" in answer or "是" in answer:
                    return "正确"
                elif "错误" in answer or "错" in answer or "否" in answer:
                    return "错误"
                else:
                    # 默认返回"正确"，但记录警告
                    logger.warning(f"无法从判断题回答中提取有效答案: {answer}")
                    return "正确"
        
        return answer
    
    if "答案：" in ai_response:
        answer = ai_response.split("答案：")[-1].strip()
        # 同样处理判断题
        if question_type == "judgement":
            answer_lower = answer.lower().strip()
            if answer_lower in ["正确", "对", "是", "true", "yes", "√"]:
                return "正确"
            elif answer_lower in ["错误", "错", "否", "false", "no", "×"]:
                return "错误"
            else:
                if "正确" in answer or "对" in answer or "是" in answer:
                    return "正确"
                elif "错误" in answer or "错" in answer or "否" in answer:
                    return "错误"
                else:
                    logger.warning(f"无法从判断题回答中提取有效答案: {answer}")
                    return "正确"
        return answer
    
    cleaned_response = re.sub(r"<thinking>.*?</thinking>", "", ai_response, flags=re.DOTALL).strip()
    
    # 处理判断题的特殊情况
    if question_type == "judgement":
        cleaned_lower = cleaned_response.lower().strip()
        if cleaned_lower in ["正确", "对", "是", "true", "yes", "√"]:
            return "正确"
        elif cleaned_lower in ["错误", "错", "否", "false", "no", "×"]:
            return "错误"
        else:
            if "正确" in cleaned_response or "对" in cleaned_response or "是" in cleaned_response:
                return "正确"
            elif "错误" in cleaned_response or "错" in cleaned_response or "否" in cleaned_response:
                return "错误"
            else:
                logger.warning(f"无法从判断题回答中提取有效答案: {cleaned_response}")
                return "正确"
    
    return cleaned_response


def parse_reading_comprehension(text: str) -> Tuple[str, str, str]:
    try:
        match = re.search(r"\(\d+\)\s*\(", text)
        if not match:
            parts = text.split("\n\n")
            if len(parts) > 1:
                context = "\n\n".join(parts[:-1])
                question_part = parts[-1]
            else:
                return "", text, ""
        else:
            context_end_index = match.start()
            context = text[:context_end_index].strip()
            question_part = text[context_end_index:].strip()

        context = re.sub(r".*Reading Comprehension.*?(\d+ points\)|points\))\s*",
                        "", context, flags=re.IGNORECASE).strip()

        options_match = re.search(r"\sA\.", question_part)
        if options_match:
            question_end_index = options_match.start()
            question = question_part[:question_end_index].strip()
            options = question_part[question_end_index:].strip()
        else:
            question = question_part
            options = ""

        question = re.sub(r"\s*\(Single Choice.*?\)\s*", "", question).strip()

        return context, question, options
    except Exception:
        return "", text, ""


def validate_external_answer(answer: str, question_type: str, options: str = "", question: str = "") -> bool:
    """
    验证外部题库返回的答案是否有效
    
    Args:
        answer: 外部题库返回的答案
        question_type: 题目类型
        options: 选项内容
        question: 问题内容（用于填空题验证）
        
    Returns:
        答案是否有效
    """
    if not answer:
        return False
    
    answer = normalize_text(answer)
    
    # 检查是否是"未找到"或"未收录"类型的答案
    if _is_not_found_answer(answer):
        return False
    
    if question_type == "judgement":
        # 判断题：只能是"对"或"错"及其变体
        valid_answers = ["对", "错", "正确", "错误", "true", "false", "√", "×", "是", "否", "yes", "no"]
        return answer.lower() in [ans.lower() for ans in valid_answers]
    
    elif question_type in ["single", "multiple"]:
        # 单选题和多选题：答案必须与选项中的文字匹配
        if not answer or not options:
            return False
            
        # 排除判断题特有的答案
        judgement_answers = ["对", "错", "正确", "错误", "true", "false", "√", "×", "是", "否", "yes", "no"]
        if answer.lower() in [ans.lower() for ans in judgement_answers]:
            return False
        
        # 检查答案是否与选项中的文字匹配
        option_lines = [line.strip() for line in options.split('\n') if line.strip()]
        for line in option_lines:
            # 提取选项文字部分（去掉A. B. 等前缀）
            match = re.match(r'^[A-Z]\s*[.、:]\s*(.+)$', line)
            if match:
                option_text = normalize_text(match.group(1))
                answer_normalized = normalize_text(answer)
                # 要求精确匹配，不能是部分匹配
                if option_text == answer_normalized:
                    return True
        
        # 如果没有找到匹配，则答案无效
        return False
    
    elif question_type == "completion":
        # 填空题：需要将问题和答案作为一个完整的句子，传给AI判断是否正确
        if not answer.strip() or not question:
            return False
            
        # 预处理外部题库返回的答案：如果答案是JSON格式的数组，提取第一个元素
        processed_answer = answer
        try:
            import json
            # 尝试解析JSON格式的答案
            parsed_answer = json.loads(answer)
            if isinstance(parsed_answer, list) and len(parsed_answer) > 0:
                # 如果是数组，取第一个元素作为答案
                processed_answer = str(parsed_answer[0])
                logger.info(f"解析外部题库JSON答案: '{answer}' -> '{processed_answer}'")
            elif isinstance(parsed_answer, str):
                # 如果是字符串，直接使用
                processed_answer = parsed_answer
        except (json.JSONDecodeError, ValueError, TypeError):
            # 如果不是JSON格式，使用原始答案
            pass
            
        try:
            # 构建验证提示词
            validation_prompt = f"""请判断以下填空题的答案是否正确：

问题：{question}
答案：{processed_answer}

请回答：这个答案是否正确？只回答"正确"或"错误"。"""

            # 延迟导入，避免在模块加载时就初始化应用
            try:
                from config import Config
                from app import call_ai_with_retry
                
                validation_result = call_ai_with_retry(validation_prompt, 0.0)
                validation_result = normalize_text(validation_result)
                
                # 检查AI的判断结果
                if validation_result in ["正确", "对", "是", "true", "yes"]:
                    return True
                elif validation_result in ["错误", "错", "否", "false", "no"]:
                    return False
                else:
                    # 如果AI判断不明确，默认认为答案有效（避免过度严格）
                    logger.warning(f"AI验证结果不明确: {validation_result}，默认认为答案有效")
                    return True
                    
            except ImportError as import_error:
                # 如果无法导入app模块（例如在独立测试中），跳过AI验证
                logger.warning(f"无法导入AI验证模块: {import_error}，跳过填空题AI验证")
                # 在无法进行AI验证的情况下，默认认为答案有效
                return True
                
        except Exception as e:
            logger.error(f"填空题答案验证失败: {e}")
            # 验证失败时，默认认为答案有效（避免因为验证错误而拒绝有效答案）
            return True
    
    return False


def _is_not_found_answer(answer: str) -> bool:
    """
    判断答案是否表示"未找到"或"未收录"
    
    Args:
        answer: 答案字符串
        
    Returns:
        是否表示未找到
    """
    if not answer:
        return True
        
    # 转换为小写进行匹配
    answer_lower = answer.lower().strip()
    
    # 常见的"未找到"或"未收录"表达
    not_found_patterns = [
        "非常抱歉",
        "题目搜索不到",
        "未找到",
        "没有找到",
        "搜索不到",
        "抱歉",
        "sorry",
        "not found",
        "no answer",
        "无法找到",
        "查询失败",
        "暂无答案",
        "暂未收录",
        "暂未收录该题目",
        "暂未收录该题目答案",
        "题库中未找到",
        "数据库中未找到",
        "未收录此题",
        "此题暂未收录",
        "题目暂未收录",
        "答案暂未收录",
        "暂无此题答案",
        "题库暂未收录",
        "未收录",
        "未收录此题目",
        "题目未收录",
        "答案未收录"
    ]
    
    return any(pattern in answer_lower for pattern in not_found_patterns)
