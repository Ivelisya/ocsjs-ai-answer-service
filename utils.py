# -*- coding: utf-8 -*-
"""
工具函数模块
包含缓存管理、答案处理和OpenAI API调用等辅助功能
"""
import hashlib
import json
import re
from functools import lru_cache
import time
import threading
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

import redis

from config import Config
from logger import app_logger as logger


class Cache:
    """统一的缓存实现，支持内存和Redis"""

    def __init__(self, expiration_seconds: int = 86400, use_redis: bool = False):
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


def _log_extraction(stage: str, details: Dict[str, Any]):
    try:
        from config import Config
        if getattr(Config, 'ENABLE_EXTRACTION_DEBUG_LOG', False):
            logger.info(f"[EXTRACT][{stage}] {details}")
    except Exception:
        pass


@lru_cache(maxsize=512)
def extract_options_from_question(question_text: str) -> List[str]:
    """从题目文本中智能抽取选项列表。

    支持格式示例：
    1. A. xxx B. yyy C. zzz D. www
    2. A、xxx B、yyy C、zzz D、www
    3. （A）xxx （B）yyy （C）zzz （D）www
    4. A) xxx B) yyy C) zzz D) www
    5. 以换行分隔的 A. / B. / C.
    6. 没有标签，空格分隔的 4~6 个短语（最后作为兜底策略）

    返回：去重后的标准化文本列表（不含标签）。
    """
    if not question_text:
        return []

    text = normalize_text(question_text).replace('（', '(').replace('）', ')')
    original_len = len(text)

    # 优先：全局内联标签提取 (A. xxx B. yyy ...) / (A)xxx / A) xxx / A、xxx
    inline_pattern = re.compile(
        r'(?:^|[^A-Za-z0-9])\(?([A-Z])\)?\s*[).、．。:：]?\s*([^A-Z].*?)(?=(?:\s\(?[A-Z]\)?\s*[).、．。:：]|$))'
    )
    candidates: List[Tuple[str, str]] = []
    for m in inline_pattern.finditer(text):
        body = normalize_text(m.group(2))
        if 0 < len(body) <= 120:
            candidates.append((m.group(1), body))
    if len(candidates) >= 2:
        seen = set()
        out: List[str] = []
        for _, b in candidates:
            if b not in seen:
                seen.add(b)
                out.append(b)
        _log_extraction('inline', {'count': len(out), 'text_len': original_len})
        return out

    # 次级：按换行行首标签
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    line_pattern = re.compile(r'^\(?([A-Z])\)?\s*[).、．。:：-]?\s*(.+)$')
    extracted: List[str] = []
    for line in lines:
        m = line_pattern.match(line)
        if m:
            body = normalize_text(m.group(2))
            if 0 < len(body) <= 120:
                extracted.append(body)
    if len(extracted) >= 2:
        seen2 = set(); res: List[str] = []
        for b in extracted:
            if b not in seen2:
                seen2.add(b); res.append(b)
        _log_extraction('lines', {'count': len(res)})
        return res

    # 兜底：空格分隔短语
    if 20 < len(text) < 400 and ' ' in text and '\n' not in text:
        # 尝试找到题干与选项分界：句号/问号/括号后紧跟空格+词序列
        split_idx = -1
        m = re.search(r'[。.?？)]\s+([\u4e00-\u9fa5A-Za-z0-9].+)', text)
        candidate_tail = None
        if m:
            candidate_tail = m.group(1).strip()
        if candidate_tail:
            segs = [s for s in candidate_tail.split(' ') if s]
        else:
            segs = [s for s in text.split(' ') if s]
        if 3 <= len(segs) <= 12 and all(1 <= len(s) <= 16 for s in segs):
            avg = sum(len(s) for s in segs) / len(segs)
            if all(abs(len(s) - avg) <= 10 for s in segs):
                _log_extraction('space_fallback', {'count': len(segs)})
                return segs

    return []


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
    """解析阅读理解题，返回(context, question, options)"""
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

    支持的题目类型：
    - single: 单选题
    - multiple: 多选题
    - judgement: 判断题
    - completion: 填空题

    Args:
        answer: 外部题库返回的答案
        question_type: 题目类型
        options: 选项内容（可选）
        question: 问题内容（可选，用于填空题验证）

    Returns:
        答案是否有效
    """
    try:
        # 输入验证和预处理
        if not isinstance(answer, str) or not isinstance(question_type, str):
            logger.warning(f"无效的输入类型: answer={type(answer)}, question_type={type(question_type)}")
            return False

        answer = answer.strip() if answer else ""
        question_type = question_type.lower().strip() if question_type else ""
        options = options.strip() if options else ""
        question = question.strip() if question else ""

        # 空答案检查
        if not answer:
            logger.debug("答案为空，验证失败")
            return False

        # 标准化答案文本
        try:
            answer_normalized = normalize_text(answer)
        except Exception as e:
            logger.warning(f"答案标准化失败: {e}")
            answer_normalized = answer.lower().strip()

        # 检查是否是"未找到"类型的答案
        if _is_not_found_answer(answer):
            logger.debug("检测到未找到答案模式")
            return False

        # 根据题目类型进行验证
        if question_type == "judgement":
            return _validate_judgement_answer(answer_normalized)

        elif question_type in ["single", "multiple"]:
            return _validate_choice_answer(answer_normalized, question_type, options, question)

        elif question_type == "completion":
            return _validate_completion_answer(answer, question)

        else:
            logger.warning(f"不支持的题目类型: {question_type}")
            # 对于未知类型，默认接受非空答案
            return bool(answer.strip())

    except Exception as e:
        logger.error(f"答案验证过程中发生错误: {e}", exc_info=True)
        # 发生错误时，如果答案非空且看起来合理，则默认接受
        return bool(answer and len(answer.strip()) > 0)


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


def _validate_judgement_answer(answer: str) -> bool:
    """验证判断题答案"""
    valid_answers = [
        "对", "错", "正确", "错误", "true", "false", "√", "×",
        "是", "否", "yes", "no", "对的", "错的", "正确的", "错误的"
    ]

    # 标准化答案进行匹配
    answer_lower = answer.lower().strip()

    # 移除常见的修饰词
    answer_clean = re.sub(r'^(我觉得|我认为|应该是|答案是|结果是)[\s]*', '', answer_lower)

    # 检查是否匹配有效答案
    for valid_answer in valid_answers:
        if valid_answer in answer_clean or answer_clean in valid_answer:
            return True

    # 检查特殊模式
    if re.match(r'^(正确|对|是|true|yes|√)', answer_clean):
        return True
    elif re.match(r'^(错误|错|否|false|no|×)', answer_clean):
        return True

    logger.debug(f"判断题答案不匹配有效模式: {answer}")
    return False


def _validate_choice_answer(answer: str, question_type: str, options: str, question: str) -> bool:
    """验证选择题答案（单选/多选）"""
    try:
        # 解析选项
        label_to_text, option_texts = _parse_options_smart(options, question)

        # 如果没有有效的选项，进行宽松验证
        if not option_texts:
            logger.info("未找到有效选项，进行宽松验证")
            return _validate_answer_relaxed(answer, question_type)

        # 排除判断题误分类的情况
        if _is_judgement_like_answer(answer):
            logger.debug("答案看起来像判断题，跳过选择题验证")
            return False

        # 根据题目类型验证答案
        if question_type == "single":
            return _validate_single_choice(answer, label_to_text, option_texts)
        else:  # multiple
            return _validate_multiple_choice(answer, label_to_text, option_texts)

    except Exception as e:
        logger.warning(f"选择题答案验证失败: {e}")
        # 发生错误时进行宽松验证
        return _validate_answer_relaxed(answer, question_type)


def _parse_options_smart(options: str, question: str) -> Tuple[Dict[str, str], List[str]]:
    """智能解析选项，支持多种格式"""
    try:
        # 方法1: 直接按换行符分割
        if '\n' in options:
            option_lines = [line.strip() for line in options.split('\n') if line.strip()]
        else:
            # 方法2: URL解码后按换行符分割
            import urllib.parse
            decoded_options = urllib.parse.unquote(options)
            if '\n' in decoded_options:
                option_lines = [line.strip() for line in decoded_options.split('\n') if line.strip()]
            else:
                # 方法3: 按空格分割（无标签选项）
                if ' ' in options and len(options.split()) >= 2:
                    option_lines = [opt.strip() for opt in options.split() if opt.strip()]
                else:
                    # 方法4: 尝试从问题中提取选项
                    auto_opts = extract_options_from_question(question)
                    if auto_opts:
                        option_lines = [f"{chr(65+i)}. {opt}" for i, opt in enumerate(auto_opts)]
                    else:
                        option_lines = []

        # 解析选项标签和文本
        label_map = {}
        texts = []

        # 匹配各种选项格式的正则表达式
        patterns = [
            re.compile(r'^([A-Z])\s*[).、．。:：\-]?\s*(.+)$'),  # A. xxx, A) xxx, A、xxx
            re.compile(r'^\(?([A-Z])\)?\s*(.+)$'),  # (A) xxx, A xxx
            re.compile(r'^([A-Z])\s*[．。]\s*(.+)$'),  # A．xxx, A。xxx
        ]

        for line in option_lines:
            parsed = False
            for pattern in patterns:
                match = pattern.match(line)
                if match:
                    label = match.group(1).upper()
                    text = normalize_text(match.group(2))
                    if text:  # 确保文本不为空
                        label_map[label] = text
                        texts.append(text)
                        parsed = True
                        break

            # 如果没有匹配到标签格式，直接作为文本处理
            if not parsed and line:
                text = normalize_text(line)
                if text:
                    texts.append(text)

        # 去重
        texts = list(dict.fromkeys(texts))  # 保持顺序去重

        logger.debug(f"解析选项成功: {len(texts)}个选项, {len(label_map)}个标签")
        return label_map, texts

    except Exception as e:
        logger.warning(f"选项解析失败: {e}")
        return {}, []


def _validate_single_choice(answer: str, label_to_text: Dict[str, str], option_texts: List[str]) -> bool:
    """验证单选题答案"""
    # 标准化答案
    answer_normalized = normalize_text(answer)

    # 方法1: 直接匹配选项文本
    if answer_normalized in option_texts:
        return True

    # 方法2: 匹配选项标签
    if len(answer_normalized) == 1 and answer_normalized.upper() in label_to_text:
        return True

    # 方法3: 匹配选项标签的变体（如"A选项"、"选项A"）
    label_match = re.search(r'[选项]?([A-Z])[选项]?', answer_normalized.upper())
    if label_match and label_match.group(1) in label_to_text:
        return True

    # 方法4: 模糊匹配（答案是选项的子串）
    for option in option_texts:
        if answer_normalized in option and len(answer_normalized) >= 3:
            return True

    logger.debug(f"单选题答案不匹配: {answer}")
    return False


def _validate_multiple_choice(answer: str, label_to_text: Dict[str, str], option_texts: List[str]) -> bool:
    """验证多选题答案"""
    try:
        # 解析答案部分
        parts = _parse_multiple_answer_parts(answer, label_to_text)

        if not parts:
            logger.debug("无法解析多选题答案部分")
            return False

        # 去重
        parts = list(dict.fromkeys(normalize_text(p) for p in parts if p))

        if not parts:
            return False

        # 方法1: 精确匹配所有部分
        option_text_set = set(normalize_text(opt) for opt in option_texts)
        if all(p in option_text_set for p in parts):
            return _check_multiple_count(parts)

        # 方法2: 标签匹配
        if all(len(p) == 1 and p.upper() in label_to_text for p in parts):
            return _check_multiple_count(parts)

        # 方法3: 子串匹配
        matched_options = []
        for part in parts:
            matched = _find_matching_option(part, option_texts)
            if matched:
                matched_options.append(matched)
            else:
                matched_options = []
                break

        if matched_options and len(set(matched_options)) >= 2:
            return True

        # 方法4: 宽松验证（答案格式正确但选项不匹配）
        if len(parts) >= 2:
            valid_parts = [p for p in parts if len(p) >= 2 and not re.match(r'^[^\w\u4e00-\u9fa5]+$', p)]
            if len(valid_parts) >= 2 and sum(len(p) for p in valid_parts) >= 10:
                logger.info(f"外部题库答案格式正确但选项不匹配，接受答案: {answer}")
                return True

        logger.debug(f"多选题答案不匹配: {answer}")
        return False

    except Exception as e:
        logger.warning(f"多选题验证失败: {e}")
        return False


def _parse_multiple_answer_parts(answer: str, label_to_text: Dict[str, str]) -> List[str]:
    """解析多选题答案的各个部分"""
    try:
        # 标准化答案
        answer_normalized = normalize_text(answer)

        # 方法1: 处理紧凑字母串（如"ABD"）
        if re.fullmatch(r'[A-Za-z]{2,}', answer_normalized):
            if all(ch.upper() in label_to_text for ch in answer_normalized):
                return [label_to_text[ch.upper()] for ch in answer_normalized]

        # 方法2: 统一分隔符
        temp = re.sub(r'[，,;/\\|；;\s]', '#', answer_normalized)
        parts = [p.strip() for p in temp.split('#') if p.strip()]

        # 方法3: 处理标签引用
        resolved_parts = []
        for part in parts:
            if len(part) == 1 and part.upper() in label_to_text:
                resolved_parts.append(label_to_text[part.upper()])
            else:
                resolved_parts.append(part)

        return resolved_parts

    except Exception as e:
        logger.warning(f"解析多选题答案部分失败: {e}")
        return []


def _find_matching_option(part: str, option_texts: List[str]) -> Optional[str]:
    """查找匹配的选项"""
    try:
        part_normalized = normalize_text(part)

        # 精确匹配
        for option in option_texts:
            if part_normalized == normalize_text(option):
                return option

        # 子串匹配（长度阈值检查）
        for option in option_texts:
            option_normalized = normalize_text(option)
            if part_normalized in option_normalized:
                if len(part_normalized) >= 6 or (len(part_normalized) >= 4 and len(part_normalized) / len(option_normalized) >= 0.5):
                    return option

        return None

    except Exception as e:
        logger.warning(f"查找匹配选项失败: {e}")
        return None


def _check_multiple_count(parts: List[str]) -> bool:
    """检查多选题答案数量是否合理"""
    try:
        from config import Config
        min_count = getattr(Config, 'MULTIPLE_MIN_COUNT', 2) if getattr(Config, 'ENABLE_STRICT_MULTIPLE_MIN', False) else 2
        return len(set(parts)) >= min_count
    except Exception:
        return len(set(parts)) >= 2


def _validate_completion_answer(answer: str, question: str) -> bool:
    """验证填空题答案"""
    try:
        if not answer.strip() or not question:
            return False

        # 预处理答案（处理JSON格式等）
        processed_answer = _preprocess_completion_answer(answer)

        # 如果无法获取AI验证，使用宽松策略
        try:
            from config import Config
            from app import call_ai_with_retry

            # 构建验证提示
            validation_prompt = f"""请判断以下填空题的答案是否正确：

问题：{question}
答案：{processed_answer}

请回答：这个答案是否正确？只回答"正确"或"错误"。"""

            validation_result = call_ai_with_retry(validation_prompt, 0.0)
            validation_result = normalize_text(validation_result)

            if validation_result in ["正确", "对", "是", "true", "yes"]:
                return True
            elif validation_result in ["错误", "错", "否", "false", "no"]:
                return False
            else:
                logger.warning(f"AI验证结果不明确: {validation_result}")
                return True

        except ImportError:
            logger.warning("无法导入AI验证模块，使用宽松策略")
            return True
        except Exception as e:
            logger.error(f"填空题AI验证失败: {e}")
            return True

    except Exception as e:
        logger.error(f"填空题验证失败: {e}")
        return True


def _preprocess_completion_answer(answer: str) -> str:
    """预处理填空题答案"""
    try:
        # 尝试解析JSON格式
        parsed = json.loads(answer)
        if isinstance(parsed, list) and len(parsed) > 0:
            return str(parsed[0])
        elif isinstance(parsed, str):
            return parsed
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    return answer


def _validate_answer_relaxed(answer: str, question_type: str) -> bool:
    """宽松验证答案（当没有有效选项时使用）"""
    try:
        if not answer.strip():
            return False

        # 对于多选题，检查是否有分隔符
        if question_type == "multiple":
            separators = ['#', '，', ',', '；', ';', '/', '\\', '|', ' ']
            has_separator = any(sep in answer for sep in separators)
            if has_separator:
                parts = re.split(r'[#,，,；;/\\|\s]+', answer)
                valid_parts = [p.strip() for p in parts if p.strip() and len(p.strip()) >= 2]
                return len(valid_parts) >= 2

        # 对于单选题，检查答案长度
        elif question_type == "single":
            return len(answer.strip()) >= 2

        return True

    except Exception as e:
        logger.warning(f"宽松验证失败: {e}")
        return bool(answer.strip())


def _is_judgement_like_answer(answer: str) -> bool:
    """检查答案是否看起来像判断题"""
    judgement_keywords = [
        "对", "错", "正确", "错误", "true", "false", "√", "×",
        "是", "否", "yes", "no", "对的", "错的"
    ]

    answer_lower = answer.lower().strip()
    return any(keyword in answer_lower for keyword in judgement_keywords)
