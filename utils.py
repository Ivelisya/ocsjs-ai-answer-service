# -*- coding: utf-8 -*-
"""
工具函数模块
包含缓存管理、答案处理等辅助功能
"""
import hashlib
import json
import re
import time
import threading
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Tuple

from config import Config
from logger import app_logger as logger


class Cache:
    """简单的内存缓存实现"""

    def __init__(self, expiration_seconds: int = 86400):
        self.expiration: int = expiration_seconds
        self._lock = threading.RLock()
        self.memory_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

        # 缓存统计信息
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "total_requests": 0
        }

    def _generate_key(self, question: str, question_type: str, options: str) -> str:
        content = f"{question}|{question_type}|{options}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def get(self, question: str, question_type: str = "", options: str = "") -> Optional[Dict[str, Any]]:
        """获取缓存的完整响应数据"""
        key = self._generate_key(question, question_type, options)
        self.stats["total_requests"] += 1

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

        with self._lock:
            self.memory_cache[key] = (time.time(), response_data)

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self.memory_cache.clear()
            self.stats = {"hits": 0, "misses": 0, "sets": 0, "total_requests": 0}

    def get_size(self) -> int:
        """获取缓存大小"""
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
            "cache_type": "memory"
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
    """
    格式化为 OCS 网课助手 标准响应格式
    参考: { "code": 1, "msg": "成功", "data": "答案内容" }
    """
    response = {
        "code": 1, 
        "msg": "查询成功",
        "data": answer,  # OCS 通常读取 data 或 answer
        "question": question, 
        "answer": answer, # 保留 answer 字段以兼容旧版本
    }
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


def _remove_option_prefix(text: str) -> str:
    """
    移除选项字母前缀（如 A. B. C. D.）
    适配 OCS 的答案匹配逻辑
    """
    if not text:
        return text
    # 匹配 "A." "A、" "A:" "A：" "A " 等格式的前缀
    cleaned = re.sub(r'^[A-Za-z]\s*[.、:：]\s*', '', text.strip())
    return cleaned.strip()


def _clean_answer_for_ocs(answer: str, question_type: str, options: str = "") -> str:
    """
    清理答案使其完美适配 OCS 网课助手
    支持：选项字母(A/B/C/D)、选项内容、混合格式
    
    对于复杂选项（如表格、多行内容），直接返回选项字母
    """
    if not answer:
        return answer
    
    answer = answer.strip()
    
    # 预处理 JSON 数组格式（如 '["对"]' -> '对'）
    try:
        parsed = json.loads(answer)
        if isinstance(parsed, list) and len(parsed) > 0:
            answer = str(parsed[0]).strip()
        elif isinstance(parsed, str):
            answer = parsed.strip()
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    
    # 判断题：标准化为 "正确" 或 "错误"
    if question_type == "judgement":
        answer_lower = answer.lower().strip()
        if answer_lower in ["正确", "对", "是", "true", "yes", "√", "right", "correct", "a"]:
            return "正确"
        if answer_lower in ["错误", "错", "否", "false", "no", "×", "wrong", "incorrect", "b"]:
            return "错误"
        # 尝试从文本中提取
        if "正确" in answer or "对" in answer:
            return "正确"
        if "错误" in answer or "错" in answer:
            return "错误"
        return answer
    
    # 单选/多选题：智能处理
    if question_type in ["single", "multiple"]:
        # 检查是否是纯选项字母格式 (如 "A", "B", "A#B#C", "ABC")
        answer_upper = answer.upper().strip()
        
        # 检查选项是否是复杂格式（多行、表格等）
        # 如果选项复杂，直接返回选项字母更安全
        options_are_complex = _are_options_complex(options)
        
        # 处理多选题的多种格式: "A#B#C", "ABC", "A、B、C", "A,B,C"
        if question_type == "multiple":
            # 提取所有选项字母
            letters = re.findall(r'[A-Z]', answer_upper)
            if letters and len(letters) >= 1:
                # 检查是否主要由选项字母组成
                non_letter_content = re.sub(r'[A-Z#,、\s]', '', answer_upper)
                if len(non_letter_content) < len(answer) * 0.3:  # 大部分是字母和分隔符
                    # 对于复杂选项，直接返回字母格式
                    if options_are_complex:
                        return "#".join(sorted(set(letters)))
                    # 尝试将选项字母转换为选项内容
                    if options:
                        converted = _convert_letters_to_content(letters, options)
                        if converted:
                            return converted
                    # 如果无法转换，返回字母格式
                    return "#".join(sorted(set(letters)))
        
        # 处理单选题
        if question_type == "single":
            # 如果答案是单个字母
            if len(answer_upper) == 1 and answer_upper in "ABCDEFGH":
                # 对于复杂选项，直接返回字母
                if options_are_complex:
                    return answer_upper
                # 尝试将选项字母转换为选项内容
                if options:
                    converted = _convert_letters_to_content([answer_upper], options)
                    if converted:
                        return converted
                # 如果无法转换，返回字母
                return answer_upper
            
            # 尝试从答案中提取选项字母
            letter_match = re.search(r'\b([A-D])\b', answer_upper)
            if letter_match:
                letter = letter_match.group(1)
                if options_are_complex:
                    return letter
                if options:
                    converted = _convert_letters_to_content([letter], options)
                    if converted:
                        return converted
                return letter
        
        # 处理包含 # 分隔符的多选答案
        if "#" in answer:
            parts = [_remove_option_prefix(p.strip()) for p in answer.split("#") if p.strip()]
            return "#".join(parts)
        else:
            return _remove_option_prefix(answer)
    
    # 填空题：将多个答案用 # 分隔（OCS 默认支持的分隔符）
    if question_type == "completion":
        # 将常见的分隔符统一转换为 # 分隔符
        # 支持: 逗号、中文逗号、分号、中文分号、换行、空格分隔的多个答案
        separators = [',', '，', '；', '\n', '\r\n']
        result = answer
        for sep in separators:
            if sep in result:
                parts = [p.strip() for p in result.split(sep) if p.strip()]
                if len(parts) > 1:
                    result = "#".join(parts)
                    break
        return result
    
    return answer


def _are_options_complex(options: str) -> bool:
    """
    判断选项是否是复杂格式（表格、多行内容等）
    
    复杂选项的特征：
    - 选项数量与换行数量不匹配（说明某些选项跨多行）
    - 包含表格字符（如多个空格、制表符）
    - 平均每行字符很少（说明是表格格式）
    """
    if not options:
        return False
    
    lines = [line for line in options.split('\n') if line.strip()]
    if len(lines) <= 4:
        return False
    
    # 检查是否有明确的选项前缀
    option_prefixes = 0
    for line in lines:
        if re.match(r'^[A-D]\s*[.、:：\s]', line.strip(), re.IGNORECASE):
            option_prefixes += 1
    
    # 如果换行数远多于选项前缀数量，说明选项是多行的
    if len(lines) > option_prefixes * 2 and option_prefixes > 0:
        return True
    
    # 检查是否包含表格特征（连续空格或制表符）
    for line in lines:
        if re.search(r'\s{3,}', line) or '\t' in line:
            return True
    
    return False


def can_answer_match_options(answer: str, options: str, question_type: str) -> bool:
    """
    验证答案是否能够匹配选项
    
    对于选择题，答案必须是：
    1. 选项字母（A/B/C/D）
    2. 选项内容的一部分
    3. 与某个选项高度相似
    
    Args:
        answer: 清理后的答案
        options: 选项文本
        question_type: 题目类型
        
    Returns:
        答案是否能匹配选项
    """
    if not answer:
        return False
    
    # 判断题不需要匹配选项
    if question_type == "judgement":
        return True
    
    # 填空题和简答题不需要匹配选项
    if question_type in ["completion", "short_answer", "essay"]:
        return True
    
    # 如果没有选项，无法验证
    if not options:
        return True
    
    answer = answer.strip()
    answer_upper = answer.upper()
    
    # 检查是否是选项字母
    if len(answer_upper) <= 4:
        # 提取所有字母
        letters = re.findall(r'[A-D]', answer_upper)
        if letters:
            return True
    
    # 解析选项内容
    option_lines = [line.strip() for line in options.split('\n') if line.strip()]
    option_contents = []
    
    for line in option_lines:
        # 移除选项前缀如 "A. " "B、"
        content = re.sub(r'^[A-Z]\s*[.、:：\s]\s*', '', line, flags=re.IGNORECASE)
        if content:
            option_contents.append(content.strip().lower())
    
    # 检查答案是否与某个选项内容匹配
    answer_lower = answer.lower()
    
    for content in option_contents:
        # 完全匹配
        if answer_lower == content:
            return True
        # 答案包含选项内容
        if content in answer_lower:
            return True
        # 选项内容包含答案（答案是选项的关键部分）
        if len(answer_lower) >= 3 and answer_lower in content:
            return True
        # 高度相似（去除空格和标点后比较）
        answer_clean = re.sub(r'[\s\.,，。、]', '', answer_lower)
        content_clean = re.sub(r'[\s\.,，。、]', '', content)
        if answer_clean and content_clean:
            if answer_clean == content_clean:
                return True
            # 前缀匹配
            if len(answer_clean) >= 5 and content_clean.startswith(answer_clean):
                return True
    
    # 答案太长且不匹配任何选项，可能是错误答案
    if len(answer) > 20:
        logger.warning(f"答案无法匹配任何选项: [{answer[:50]}...]")
        return False
    
    # 短答案可能是关键词，放行
    return True


def _convert_letters_to_content(letters: List[str], options: str) -> Optional[str]:
    """
    将选项字母转换为选项内容
    
    Args:
        letters: 选项字母列表，如 ['A', 'B', 'C']
        options: 选项文本，每行一个选项
        
    Returns:
        转换后的选项内容（用 # 连接），如果无法转换返回 None
    """
    if not options or not letters:
        return None
    
    # 解析选项
    option_map = {}
    option_lines = [line.strip() for line in options.split('\n') if line.strip()]
    
    for i, line in enumerate(option_lines):
        # 尝试匹配 "A. xxx" 或 "A、xxx" 或 "A xxx" 格式
        match = re.match(r'^([A-Z])\s*[.、:：\s]\s*(.+)$', line, re.IGNORECASE)
        if match:
            letter = match.group(1).upper()
            content = match.group(2).strip()
            option_map[letter] = content
        else:
            # 如果没有字母前缀，按顺序分配 A, B, C...
            letter = chr(ord('A') + i)
            option_map[letter] = line
    
    # 转换
    contents = []
    for letter in letters:
        if letter.upper() in option_map:
            contents.append(option_map[letter.upper()])
        else:
            return None  # 无法找到对应选项
    
    return "#".join(contents) if contents else None


def extract_answer(ai_response: str, question_type: str, options: str = "") -> str:
    """
    从 AI 响应中提取答案
    
    Args:
        ai_response: AI 的原始响应
        question_type: 题目类型
        options: 选项内容（用于将选项字母转换为选项内容）
    """
    # 兼容新提示词：优先尝试解析 JSON 输出
    if ai_response:
        raw = ai_response.strip()

        # 去掉常见的代码块包裹
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw).strip()

        def _extract_from_json(text: str) -> Optional[str]:
            try:
                obj = json.loads(text)
            except Exception:
                return None

            if isinstance(obj, dict) and "answer" in obj:
                val = obj.get("answer")
                return "" if val is None else str(val)
            return None

        json_answer = _extract_from_json(raw)
        if json_answer is None:
            # 尝试截取首个 JSON 对象
            l = raw.find("{")
            r = raw.rfind("}")
            if l != -1 and r != -1 and r > l:
                json_answer = _extract_from_json(raw[l : r + 1])

        # 如果成功解析到 JSON 格式（即使 answer 为空），使用解析结果
        if json_answer is not None:
            if json_answer.strip():
                answer = normalize_text(json_answer)
                if "；" in answer or ";" in answer:
                    answer = answer.replace("；", "#").replace(";", "#")
                
                # 使用 OCS 兼容的清理函数
                return _clean_answer_for_ocs(answer, question_type, options)
            else:
                # JSON 解析成功但 answer 为空，返回空字符串（而不是原始 JSON）
                return ""

    match = re.search(r"<answer>(.*?)</answer>", ai_response, re.DOTALL)
    if match:
        answer = match.group(1).strip()
        if "#" in answer or "；" in answer or ";" in answer:
            answer = answer.replace("；", "#").replace(";", "#")
        
        # 使用 OCS 兼容的清理函数
        return _clean_answer_for_ocs(answer, question_type, options)
    
    if "答案：" in ai_response:
        answer = ai_response.split("答案：")[-1].strip()
        if "；" in answer or ";" in answer:
            answer = answer.replace("；", "#").replace(";", "#")
        return _clean_answer_for_ocs(answer, question_type, options)
    
    cleaned_response = re.sub(r"<thinking>.*?</thinking>", "", ai_response, flags=re.DOTALL).strip()
    
    # If not Judgement, use the cleaned response as the answer candidate
    answer = cleaned_response
    
    # --- Post-Processing: Cleaning ---
    if answer:
        # 1. Strip Markdown Code Blocks from the answer text itself (double safety)
        if "```" in answer:
             answer = re.sub(r"```.*?```", "", answer, flags=re.DOTALL).strip()
             answer = re.sub(r"```", "", answer).strip()

        # 2. For Completion questions: Remove list numbering "1. ", "2. " if present
        if question_type == "completion" or question_type == "unknown":
            # Replace "1. Answer" with "Answer"
            # Replace newlines with spaces or commas if they look like a list
            lines = answer.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                # Remove leading "1.", "1)", "1、"
                line = re.sub(r"^\d+[\.\)、]\s*", "", line)
                if line:
                    cleaned_lines.append(line)
            
            if len(cleaned_lines) > 1:
                answer = " ".join(cleaned_lines)
            elif len(cleaned_lines) == 1:
                answer = cleaned_lines[0]

    # 最终使用 OCS 兼容的清理函数
    return _clean_answer_for_ocs(answer, question_type, options) if answer else ""


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


def _preprocess_external_answer(answer: str) -> str:
    """
    预处理外部题库返回的答案，处理 JSON 数组等格式
    如 '["对"]' -> '对', '["错误"]' -> '错误'
    也处理答案中包含题目文本的情况
    """
    if not answer:
        return answer
    
    answer = answer.strip()
    
    # 去除 answer= 或 answer=' 等前缀（可能由题库返回或日志污染）
    answer_prefix_patterns = [
        r"^answer\s*=\s*['\"]?",  # answer= 或 answer='
        r"^答案\s*[=：:]\s*['\"]?",  # 答案= 或 答案：
    ]
    for prefix_pattern in answer_prefix_patterns:
        answer = re.sub(prefix_pattern, '', answer, flags=re.IGNORECASE)
    
    # 去除结尾的引号（如果开头的引号被移除了）
    if answer.endswith("'") or answer.endswith('"'):
        answer = answer[:-1]
    
    answer = answer.strip()
    
    # 尝试解析 JSON 格式
    try:
        parsed = json.loads(answer)
        if isinstance(parsed, list) and len(parsed) > 0:
            # 如果是数组，取第一个元素
            return str(parsed[0]).strip()
        elif isinstance(parsed, str):
            return parsed.strip()
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    
    # 如果答案包含题目文本，尝试提取真正的答案
    # 常见格式: "题目内容...答案：xxx" 或 "题目内容...正确答案是xxx"
    answer_patterns = [
        r'答案[：:]\s*(.+?)(?:\s*$|\n)',
        r'正确答案[是为：:]\s*(.+?)(?:\s*$|\n)',
        r'选\s*([A-D])\s*(?:$|\n|[。.])',
        r'应选\s*([A-D])\s*(?:$|\n|[。.])',
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, answer, re.IGNORECASE | re.DOTALL)
        if match:
            extracted = match.group(1).strip()
            if extracted:
                return extracted
    
    return answer


async def validate_external_answer(answer: str, question_type: str, options: str = "", question: str = "", ai_validator: Optional[Callable] = None) -> bool:
    """
    验证外部题库返回的答案是否有效
    
    Args:
        answer: 外部题库返回的答案
        question_type: 题目类型
        options: 选项内容
        question: 问题内容（用于填空题验证）
        ai_validator: 可选的AI验证回调函数，接收(prompt, temperature)参数
        
    Returns:
        答案是否有效
    """
    if not answer:
        return False
    
    # 预处理 JSON 数组等格式
    answer = _preprocess_external_answer(answer)
    answer = normalize_text(answer)
    
    # 检查是否是"未找到"或"未收录"类型的答案
    if _is_not_found_answer(answer):
        return False
    
    if question_type == "judgement":
        # 判断题：只能是"对"或"错"及其变体
        valid_answers = ["对", "错", "正确", "错误", "true", "false", "√", "×", "是", "否", "yes", "no"]
        return answer.lower() in [ans.lower() for ans in valid_answers]
    
    elif question_type in ["single", "multiple"]:
        # 单选题和多选题：宽松验证，只要答案非空且不是"未找到"类型即可
        if not answer:
            return False
            
        # 排除判断题特有的答案（避免题型混淆）
        judgement_answers = ["对", "错", "正确", "错误", "true", "false", "√", "×", "是", "否", "yes", "no"]
        if answer.lower().strip() in [ans.lower() for ans in judgement_answers]:
            return False
        
        # 如果有选项，尝试验证答案是否与选项匹配
        if options:
            option_lines = [line.strip() for line in options.split('\n') if line.strip()]
            answer_normalized = normalize_text(answer).lower()
            
            for line in option_lines:
                line_normalized = normalize_text(line).lower()
                # 提取选项字母和内容
                match = re.match(r'^([A-Z])\s*[.、:：]\s*(.+)$', line, re.IGNORECASE)
                if match:
                    option_letter = match.group(1).upper()
                    option_text = normalize_text(match.group(2)).lower()
                    
                    # 匹配方式1: 答案是选项字母（如 "A", "B", "A#B#C"）
                    answer_letters = re.findall(r'[A-Z]', answer.upper())
                    if option_letter in answer_letters:
                        return True
                    
                    # 匹配方式2: 答案包含选项内容（模糊匹配）
                    if option_text in answer_normalized or answer_normalized in option_text:
                        return True
                    
                    # 匹配方式3: 精确匹配选项文字
                    if option_text == answer_normalized:
                        return True
        
        # 如果没有选项或无法匹配，只要答案不为空就视为有效（信任外部题库）
        return len(answer.strip()) > 0
    
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
            if ai_validator:
                # 构建验证提示词
                validation_prompt = f"请判断以下填空题的答案是否正确：\n\n问题：{question}\n答案：{processed_answer}\n\n请回答：这个答案是否正确？只回答'正确'或'错误'。"

                try:
                    validation_result = await ai_validator(validation_prompt, 0.0)
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
                        
                except Exception as ai_error:
                    # 如果AI调用失败，默认认为真
                    logger.warning(f"AI验证调用失败: {ai_error}，默认填空题答案有效")
                    return True
            else:
                # 如果没有验证器，默认信任外部题库的非空答案
                return True
                
        except Exception as e:
            logger.error(f"填空题答案验证失败: {e}")
            # 验证失败时，默认认为答案有效（避免因为验证错误而拒绝有效答案）
            return True
    
    # 对于未知题型，默认信任外部题库的非空答案
    return len(answer.strip()) > 0


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
