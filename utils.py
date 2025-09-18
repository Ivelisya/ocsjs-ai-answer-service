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
        # 选择题：需要答案与选项匹配；多选题可以包含多个选项
        if not answer:
            return False

        # 如果缺少或疑似无效 options，尝试从 question 中抽取
        original_options = options
        if (not options) or ("\n" not in options and len(options.strip().split()) <= 1):
            auto_opts = extract_options_from_question(question or "")
            if auto_opts:
                options = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(auto_opts)])
                logger.info(f"自动从题干提取选项: {auto_opts}")

        if not options:
            return False

        # 排除判断题特有的答案（外部题库误分类的情况）
        judgement_answers = ["对", "错", "正确", "错误", "true", "false", "√", "×", "是", "否", "yes", "no"]
        if answer.lower() in [ans.lower() for ans in judgement_answers]:
            return False

        def _parse_options_block(opt_str: str) -> Tuple[Dict[str, str], List[str]]:
            option_lines_local = [line.strip() for line in opt_str.split('\n') if line.strip()]
            label_map: Dict[str, str] = {}
            texts: List[str] = []
            pattern = re.compile(r'^([A-Z])\s*[).、．。:：-]?\s*(.+)$')
            for ln in option_lines_local:
                mm = pattern.match(ln)
                if mm:
                    label = mm.group(1)
                    body = normalize_text(mm.group(2))
                    label_map[label] = body
                    texts.append(body)
                else:
                    texts.append(normalize_text(ln))
            return label_map, texts

        label_to_text, option_texts = _parse_options_block(options)

        # 兼容：整串选项使用空格分隔且没有换行/标签的情况
        # 例如: "第一次世界大战 清朝灭亡 第一次鸦片战争 八国联军侵华战争"
        if (
            len(option_texts) == 1 and option_texts[0] and " " in options.strip() and "\n" not in options.strip()
        ):
            space_split = [seg.strip() for seg in option_texts[0].split(" ") if seg.strip()]
            if len(space_split) >= 2:
                option_texts = space_split  # label_to_text 保持空

        answer_normalized = normalize_text(answer)

        # 如果是单选题，允许：
        # 1. 直接是选项文本
        # 2. 只有字母（A/B/...) 代表选项标签
        if question_type == "single":
            if answer_normalized in option_texts:
                return True
            if len(answer_normalized) == 1 and answer_normalized.upper() in label_to_text:
                return True
            # 额外：如果答案拆分后多个片段全部属于选项，也允许（防止外部题库多余空格）
            if " " in answer_normalized and all(p in option_texts for p in answer_normalized.split()):
                return True
            return False

        # 多选题：允许多种分隔符（#, 空格, 逗号, 中文逗号, 分号, /, |），以及紧凑字母串如"ABD"
        # 先处理紧凑字母串
        if re.fullmatch(r'[A-Za-z]{2,}', answer_normalized) and all(ch.upper() in label_to_text for ch in answer_normalized):
            parts = [label_to_text[ch.upper()] for ch in answer_normalized]
        else:
            # 替换常见分隔符为统一的 '#'
            temp = re.sub(r'[，,;/\\|；;]', '#', answer_normalized)
            # 将多个空白视为分隔符
            temp = re.sub(r'\s+', '#', temp)
            parts = [p for p in temp.split('#') if p]

            # 如果部分是单个字母标签，替换为对应文本
            resolved_parts = []
            for p in parts:
                if len(p) == 1 and p.upper() in label_to_text:
                    resolved_parts.append(label_to_text[p.upper()])
                else:
                    resolved_parts.append(p)
            parts = resolved_parts

        # 去重保持集合逻辑
        parts = [normalize_text(p) for p in parts if p]
        if not parts:
            return False

        # 所有部分都必须是合法选项文本
        option_text_set = set(option_texts)
        if all(p in option_text_set for p in parts):
            # 严格模式：检查最少选择数
            try:
                from config import Config
                if (
                    question_type == 'multiple' and
                    getattr(Config, 'ENABLE_STRICT_MULTIPLE_MIN', False) and
                    len(set(parts)) < getattr(Config, 'MULTIPLE_MIN_COUNT', 2)
                ):
                    return False
            except Exception:
                pass
            return True
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
