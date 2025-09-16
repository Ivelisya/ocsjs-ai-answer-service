# -*- coding: utf-8 -*-
"""
工具函数模块
包含缓存管理、答案处理和OpenAI API调用等辅助功能
"""
import hashlib
import json
import re
import time
import threading
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

import redis

from config import Config
from logger import app_logger as logger


class Cache:
    """统一的缓存实现，支持内存和Redis""    if len(answer_parts) == question_count:
        logger.info("答案分割成功，格式化答案")
        formatted_answers = []
        for i, part in enumerate(answer_parts, 1):
            # 保留原始分隔符（句号或分号）
            if part.endswith("。") or part.endswith("；"):
                formatted_answers.append(f"{i}.{part}")
            elif i < question_count and ("。" in answer or "；" in answer):
                # 如果是句号或分号分割的中间部分，添加相应的分隔符
                if "。" in answer and not part.endswith("。"):
                    formatted_answers.append(f"{i}.{part}。")
                elif "；" in answer and not part.endswith("；"):
                    formatted_answers.append(f"{i}.{part}；")
                else:
                    formatted_answers.append(f"{i}.{part.strip()}")
            else:
                formatted_answers.append(f"{i}.{part.strip()}")
        result = "\n".join(formatted_answers)
        logger.info(f"格式化结果: {result}")
        return result_init__(self, expiration_seconds: int = 86400, use_redis: bool = False):
        self.expiration: int = expiration_seconds
        self.use_redis: bool = use_redis and bool(Config.REDIS_URL)
        self._lock = threading.RLock()  # 添加线程锁

        # 缓存统计信息
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "total_requests": 0
        }

        if self.use_redis:
            try:
                self.redis_client: redis.Redis = redis.from_url(Config.REDIS_URL)
                self.redis_client.ping()  # 测试连接
            except redis.ConnectionError:
                logger.warning("Redis连接失败，使用内存缓存")
                self.use_redis = False
                self.memory_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        else:
            self.memory_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    def _generate_key(self, question: str, question_type: str, options: str) -> str:
        content = f"{question}|{question_type}|{options}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def get(self, question: str, question_type: str = "", options: str = "") -> Optional[Dict[str, Any]]:
        """获取缓存的完整响应数据"""
        key = self._generate_key(question, question_type, options)
        self.stats["total_requests"] += 1

        if self.use_redis:
            try:
                value = self.redis_client.get(key)
                if value:
                    self.stats["hits"] += 1
                    # 简化处理，避免异步类型问题
                    try:
                        return json.loads(str(value))
                    except json.JSONDecodeError:
                        return None
                else:
                    self.stats["misses"] += 1
                    return None
            except Exception:
                self.stats["misses"] += 1
                return None
        else:
            with self._lock:
                if key in self.memory_cache:
                    timestamp, value = self.memory_cache[key]
                    if time.time() - timestamp < self.expiration:
                        self.stats["hits"] += 1
                        return value
                    else:
                        # 过期删除
                        del self.memory_cache[key]
                        self.stats["misses"] += 1
                        return None
                else:
                    self.stats["misses"] += 1
                    return None

    def set(self, question: str, response_data: Dict[str, Any], question_type: str = "", options: str = "") -> None:
        """存储完整的响应数据到缓存"""
        key = self._generate_key(question, question_type, options)
        self.stats["sets"] += 1

        if self.use_redis:
            try:
                self.redis_client.setex(key, self.expiration, json.dumps(response_data))
            except redis.ConnectionError:
                pass
        else:
            with self._lock:
                self.memory_cache[key] = (time.time(), response_data)

    def clear(self) -> None:
        """清空缓存"""
        if self.use_redis:
            try:
                self.redis_client.flushdb()
            except redis.ConnectionError:
                pass
        else:
            with self._lock:
                self.memory_cache.clear()

    def get_size(self) -> int:
        """获取缓存大小"""
        if self.use_redis:
            try:
                size = self.redis_client.dbsize()
                return size if isinstance(size, int) else 0
            except Exception:
                return 0
        else:
            with self._lock:
                return len(self.memory_cache)

    def get_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self.stats["total_requests"]
        if total == 0:
            return 0.0
        return (self.stats["hits"] / total) * 100

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "size": self.get_size(),
            "hit_rate": self.get_hit_rate(),
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "sets": self.stats["sets"],
            "total_requests": self.stats["total_requests"],
            "cache_type": "redis" if self.use_redis else "memory"
        }

    def warmup(self, common_questions: List[Tuple[str, str, str]]) -> None:
        """缓存预热"""
        logger.info(f"开始缓存预热，共 {len(common_questions)} 个问题")
        for question, question_type, options in common_questions:
            key = self._generate_key(question, question_type, options)
            if not self.get(question, question_type, options):
                logger.info(f"预热缓存: {question[:50]}...")
                # 这里可以调用实际的AI处理逻辑
                # 为了演示，我们只记录预热操作
                pass
        logger.info("缓存预热完成")


def format_answer_for_ocs(question: str, answer: str, processing_time: Optional[float] = None) -> Dict[str, Any]:
    response = {"code": 1, "question": question, "answer": answer}
    if processing_time is not None:
        response["processing_time"] = f"{processing_time:.2f}秒"
    return response


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


def _is_multi_subquestion(question: str) -> bool:
    """
    检测题目是否包含多个编号的子问题
    """
    if not question or not question.strip():
        return False

    # 检查是否包含多个编号问题的模式（支持换行符和空格分隔）
    patterns = [
        r'\d+\.\s*[^\d]',  # 数字编号后跟非数字内容：1. xxx（但不是1. 2. 3.这样的空内容）
        r'\d+\)\s*[^\d]',  # 括号编号：1) xxx
        r'[（(]\s*\d+\s*[）)]\s*[^\d]',  # 中文括号编号：（1）xxx
    ]

    # 需要至少找到2个有效的编号模式
    matches = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, question))

    # 过滤掉只有数字编号没有内容的模式（如"1. 2. 3."）
    valid_matches = []
    for match in matches:
        # 检查编号后是否有实际内容
        if re.search(r'\d+\.\s*\S', match) or re.search(r'\d+\)\s*\S', match) or re.search(r'[（(]\s*\d+\s*[）)]\s*\S', match):
            valid_matches.append(match)

    if len(valid_matches) >= 2:
        return True

    # 备用方法：简单检查是否有多个数字编号
    digit_dots = re.findall(r'\d+\.', question)
    if len(digit_dots) >= 2:
        # 确保这些编号后有实际内容
        content_after_numbers = re.sub(r'\d+\.\s*', '', question)
        if content_after_numbers.strip():
            return True

    return False


def extract_answer(ai_response: str, question_type: str, question: str = "") -> str:
    """
    从AI响应中提取答案，支持多种格式和分隔符
    """
    logger.info(f"开始提取答案，问题类型: {question_type}")
    logger.info(f"原始AI响应: {ai_response[:500]}...")

    # 首先尝试提取<answer>标签内的内容
    match = re.search(r"<answer>(.*?)</answer>", ai_response, re.DOTALL)
    if match:
        answer = match.group(1).strip()
        logger.info(f"从<answer>标签提取到答案: {answer}")

        # 处理判断题
        if question_type == "judgement":
            return _extract_judgement_answer(answer)

        # 处理多子问题的填空题
        if question_type == "completion" and _is_multi_subquestion(question):
            return _format_multi_subquestion_answer(answer, question)

        # 清理分隔符
        answer = answer.replace("；", "#").replace(";", "#")
        return answer

    # 尝试提取"答案："格式
    if "答案：" in ai_response:
        answer = ai_response.split("答案：")[-1].strip()
        logger.info(f"从'答案：'格式提取到答案: {answer}")

        if question_type == "judgement":
            return _extract_judgement_answer(answer)

        if question_type == "completion" and _is_multi_subquestion(question):
            return _format_multi_subquestion_answer(answer, question)

        return answer

    # 清理<thinking>标签
    cleaned_response = re.sub(r"<thinking>.*?</thinking>", "", ai_response, flags=re.DOTALL).strip()

    # 清理其他可能的标签（如<invalid>等），但保留内容
    cleaned_response = re.sub(r"<[^>]+>(.*?)</[^>]+>", r"\1", cleaned_response, flags=re.DOTALL).strip()

    logger.info(f"清理标签后响应: {cleaned_response[:500]}...")

    if question_type == "judgement":
        return _extract_judgement_answer(cleaned_response)

    # 处理多子问题的填空题
    if question_type == "completion" and _is_multi_subquestion(question):
        return _format_multi_subquestion_answer(cleaned_response, question)

    return cleaned_response


def _extract_judgement_answer(answer: str) -> str:
    """提取判断题答案"""
    answer_lower = answer.lower().strip()
    if answer_lower in ["正确", "对", "是", "true", "yes", "√"]:
        return "正确"
    elif answer_lower in ["错误", "错", "否", "false", "no", "×"]:
        return "错误"
    else:
        # 尝试从回答中提取
        if "正确" in answer or "对" in answer or "是" in answer:
            return "正确"
        elif "错误" in answer or "错" in answer or "否" in answer:
            return "错误"
        else:
            logger.warning(f"无法从判断题回答中提取有效答案: {answer}")
            return "正确"


def _format_multi_subquestion_answer(answer: str, question: str) -> str:
    """
    格式化多子问题的答案，支持多种分隔符
    使用简单直接的方法
    """
    logger.info(f"开始格式化多子问题答案: {answer}")

    # 计算题目中子问题的数量
    question_count = len(re.findall(r'\d+\.', question))
    logger.info(f"题目包含{question_count}个子问题")

    # 如果答案已经很好地格式化了，直接返回
    if _is_already_well_formatted(answer, question_count):
        logger.info("答案已经格式良好，直接返回")
        return answer

    # 尝试分割答案
    answer_parts = _split_answer_smart(answer, question_count)

    if len(answer_parts) == question_count:
        logger.info("答案分割成功，格式化答案")
        formatted_answers = []
        for i, part in enumerate(answer_parts, 1):
            # 保留原始分隔符（句号或分号）
            if part.endswith("。") or part.endswith("；"):
                formatted_answers.append(f"{i}.{part}")
            else:
                formatted_answers.append(f"{i}.{part.strip()}")
        result = "\n".join(formatted_answers)
        logger.info(f"格式化结果: {result}")
        return result
    else:
        logger.warning(f"答案分割失败: 期望{question_count}个，得到{len(answer_parts)}个")
        # 如果分割失败，返回原始答案
        return answer


def _is_already_well_formatted(answer: str, question_count: int) -> bool:
    """
    检查答案是否已经格式良好
    """
    lines = answer.split('\n')
    if len(lines) != question_count:
        return False

    # 检查每行是否以数字开头
    for i, line in enumerate(lines, 1):
        if not line.strip().startswith(f"{i}."):
            return False

    return True


def _split_answer_smart(answer: str, question_count: int) -> List[str]:
    """
    智能分割答案，支持多种分隔符
    """
    logger.info(f"智能分割答案: {answer}")

    # 清理常见前缀
    cleaned_answer = _clean_answer_prefix(answer)
    if cleaned_answer != answer:
        logger.info(f"清理前缀后: {cleaned_answer}")
        answer = cleaned_answer

    # 策略1: 直接按#分割
    if "#" in answer:
        parts = answer.split("#")
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) == question_count:
            logger.info(f"用#分割成功: {parts}")
            return parts

    # 策略2: 按分号分割
    if "；" in answer:
        parts = answer.split("；")
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) == question_count:
            logger.info(f"用；分割成功: {parts}")
            return parts

    # 策略3: 按句号分割（只在有明确分隔的情况下）
    if "。" in answer and re.search(r'。[一-龯a-zA-Z]', answer):
        parts = re.split(r'。(?=[一-龯a-zA-Z])', answer)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) == question_count:
            logger.info(f"用。分割成功: {parts}")
            return parts

    # 策略4: 混合分隔符处理
    if "#" in answer or "；" in answer or ";" in answer:
        parts = _split_mixed_separators(answer)
        if len(parts) >= question_count:
            merged_parts = _merge_excess_parts(parts, question_count)
            if len(merged_parts) == question_count:
                logger.info(f"混合分隔成功: {merged_parts}")
                return merged_parts

    # 策略5: 按空格分割（用于短答案）
    if " " in answer and len(answer.split()) >= question_count:
        words = answer.split()
        if len(words) >= question_count:
            # 平均分配单词
            avg_words = len(words) // question_count
            parts = []
            start = 0
            for i in range(question_count - 1):
                end = start + avg_words
                parts.append(" ".join(words[start:end]))
                start = end
            parts.append(" ".join(words[start:]))
            logger.info(f"按空格分割成功: {parts}")
            return parts

    # 如果所有策略都失败，返回整个答案
    logger.warning("所有分割策略都失败")
    return [answer]


def _split_mixed_separators(answer: str) -> List[str]:
    """
    处理混合分隔符
    """
    # 首先用#分割主要部分
    if "#" in answer:
        primary_parts = answer.split("#")
    else:
        primary_parts = [answer]

    final_parts = []
    for part in primary_parts:
        part = part.strip()
        if not part:
            continue

        # 检查子分隔符
        if "；" in part:
            sub_parts = part.split("；")
            final_parts.extend([p.strip() for p in sub_parts if p.strip()])
        elif ";" in part:
            sub_parts = part.split(";")
            final_parts.extend([p.strip() for p in sub_parts if p.strip()])
        elif "。" in part and re.search(r'。[一-龯a-zA-Z]', part):
            # 处理句号分隔，但要保留句号
            sub_parts = re.split(r'。(?=[一-龯a-zA-Z])', part)
            final_parts.extend([p.strip() + "。" if not p.endswith("。") else p.strip() for p in sub_parts if p.strip()])
        else:
            final_parts.append(part)

    return final_parts


def _clean_answer_prefix(answer: str) -> str:
    """
    清理答案中的常见前缀
    """
    prefixes = [
        r'^经过分析，我认为答案是[：:]?\s*',
        r'^我认为答案是[：:]?\s*',
        r'^所以答案是[：:]?\s*',
        r'^最终答案是[：:]?\s*',
        r'^答案是[：:]?\s+(?!答案)',  # 确保后面不是"答案"字样
        r'^答案[：:]?\s+(?!答案)',  # 确保后面不是"答案"字样
    ]

    for prefix in prefixes:
        match = re.search(prefix, answer, re.IGNORECASE)
        if match:
            return answer[match.end():].strip()

    return answer


def _merge_excess_parts(parts: List[str], question_count: int) -> List[str]:
    """
    合并多余的答案部分
    """
    if len(parts) <= question_count:
        return parts

    # 前question_count-1个部分保持不变
    merged_parts = parts[:question_count-1]

    # 合并剩余部分
    remaining_parts = parts[question_count-1:]
    last_part = "#".join(remaining_parts)
    merged_parts.append(last_part)

    logger.info(f"合并结果: {merged_parts}")
    return merged_parts


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
    except (ValueError, TypeError, AttributeError) as e:
        logger.warning(f"解析阅读理解题失败: {e}")
        return "", text, ""


def validate_external_answer(answer: str, question_type: str, options: str = "", question: str = "") -> bool:
    """
    验证外部题库返回的答案是否有效
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
