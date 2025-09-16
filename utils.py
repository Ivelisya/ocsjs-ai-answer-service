import re
import json
import logging
from typing import List, Tuple, Dict, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

def extract_answer(ai_response: str, question_type: str, question: str = "") -> str:
    """
    从AI响应中提取答案，支持多种格式和分隔符
    """
    logger.info(f"开始提取答案，问题类型: {question_type}")
    logger.info(f"原始AI响应: {ai_response}")

    # 清理思考标签
    cleaned_response = _clean_thinking_tags(ai_response)
    logger.info(f"清理标签后响应: {cleaned_response}")

    if question_type == "judgement":
        return _extract_judgement_answer(cleaned_response)
    elif question_type == "single":
        return _extract_single_choice_answer(cleaned_response)
    elif question_type == "multiple":
        return _extract_multiple_choice_answer(cleaned_response)
    elif question_type == "completion":
        # 检查是否是多子问题
        if _is_multi_subquestion(question):
            return _format_multi_subquestion_answer(cleaned_response, question)
        else:
            return cleaned_response.strip()
    else:
        return cleaned_response.strip()

def _clean_thinking_tags(response: str) -> str:
    """
    清理AI响应中的思考标签
    """
    # 移除<thinking>标签及其内容
    response = re.sub(r"<thinking>.*?</thinking>", "", response, flags=re.DOTALL)
    # 移除<answer>标签，保留内容
    response = re.sub(r"<answer>(.*?)</answer>", r"\1", response, flags=re.DOTALL)
    return response.strip()

def _extract_judgement_answer(answer: str) -> str:
    """
    提取判断题答案
    """
    answer_lower = answer.lower().strip()
    if answer_lower in ["正确", "对", "是", "true", "yes", "√"]:
        return "正确"
    elif answer_lower in ["错误", "错", "否", "false", "no", "×"]:
        return "错误"
    else:
        return answer.strip()

def _extract_single_choice_answer(answer: str) -> str:
    """
    提取单选题答案
    """
    # 查找选项格式
    match = re.search(r"[A-Z][.、:]\s*[^A-Z]*", answer)
    if match:
        return match.group(0).strip()
    return answer.strip()

def _extract_multiple_choice_answer(answer: str) -> str:
    """
    提取多选题答案
    """
    # 查找多个选项
    options = re.findall(r"[A-Z][.、:]\s*[^A-Z]*", answer)
    if options:
        return " ".join([opt.strip() for opt in options])
    return answer.strip()

def _is_multi_subquestion(question: str) -> bool:
    """
    判断是否是多子问题
    """
    # 查找数字编号的子问题
    matches = re.findall(r"\d+\.", question)
    return len(matches) >= 2

def _format_multi_subquestion_answer(answer: str, question: str) -> str:
    """
    格式化多子问题的答案，支持多种分隔符
    """
    logger.info(f"开始格式化多子问题答案: {answer}")

    # 计算题目中子问题的数量
    question_count = len(re.findall(r"\d+\.", question))
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
            # 保留原始分隔符（句号或分号），但只有中间部分才需要
            if part.endswith("。") and i < question_count:
                formatted_answers.append(f"{i}.{part}")
            elif part.endswith("；") and i < question_count:
                formatted_answers.append(f"{i}.{part}")
            else:
                # 移除末尾的分隔符（如果是最后一个部分）
                clean_part = part.rstrip("。；")
                formatted_answers.append(f"{i}.{clean_part}")
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
    lines = answer.split("\n")
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
    if "。" in answer and re.search(r"。[一-龯a-zA-Z]", answer):
        parts = re.split(r"。(?=[一-龯a-zA-Z])", answer)
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
    logger.info(f"开始混合分隔符处理: {answer}")
    # 首先用#分割主要部分
    if "#" in answer:
        primary_parts = answer.split("#")
    else:
        primary_parts = [answer]

    logger.info(f"主要部分: {primary_parts}")

    final_parts = []
    for part in primary_parts:
        part = part.strip()
        logger.info(f"处理部分: '{part}'")
        if not part:
            continue

        # 检查子分隔符
        if "；" in part:
            logger.info(f"用；分割: {part}")
            sub_parts = part.split("；")
            logger.info(f"；分割结果: {sub_parts}")
            # 递归处理每个子部分
            for j, sub_part in enumerate(sub_parts):
                sub_part = sub_part.strip()
                if sub_part:
                    if j < len(sub_parts) - 1:  # 不是最后一个
                        final_parts.append(sub_part + "；")
                    else:
                        final_parts.append(sub_part)
        elif ";" in part:
            sub_parts = part.split(";")
            final_parts.extend([p.strip() for p in sub_parts if p.strip()])
        elif "。" in part and re.search(r"。[一-龯a-zA-Z]", part):
            logger.info(f"用。分割: {part}")
            sub_parts = re.split(r"。(?=[一-龯a-zA-Z])", part)
            logger.info(f"。分割结果: {sub_parts}")
            # 为中间部分添加分隔符
            for j, p in enumerate(sub_parts):
                p = p.strip()
                if p:
                    if j < len(sub_parts) - 1:  # 不是最后一个
                        final_parts.append(p + "。")
                    else:
                        final_parts.append(p)
        else:
            logger.info(f"直接添加: {part}")
            final_parts.append(part)

    logger.info(f"混合分隔最终结果: {final_parts}")
    return final_parts

def _clean_answer_prefix(answer: str) -> str:
    """
    清理答案中的常见前缀
    """
    prefixes = [
        r"^经过分析，我认为答案是[：:]?\s*",
        r"^我认为答案是[：:]?\s*",
        r"^所以答案是[：:]?\s*",
        r"^最终答案是[：:]?\s*",
        r"^答案是[：:]?\s+(?!答案)",  # 确保后面不是"答案"字样
        r"^答案[：:]?\s+(?!答案)",  # 确保后面不是"答案"字样
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
    if len(parts) == question_count:
        return parts

    if len(parts) < question_count:
        # 如果部分数量少于问题数量，保持不变
        return parts

    # 如果部分数量多于问题数量，进行合并
    # 前question_count-1个部分保持不变
    merged_parts = parts[:question_count-1]

    # 合并剩余部分
    remaining_parts = parts[question_count-1:]
    last_part = "#".join(remaining_parts)
    merged_parts.append(last_part)

    logger.info(f"合并结果: {merged_parts}")
    return merged_parts

# 其他函数保持不变...
def normalize_text(text: str) -> str:
    """标准化文本"""
    if not text:
        return ""
    return text.strip()

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
        option_lines = [line.strip() for line in options.split("\n") if line.strip()]
        for line in option_lines:
            # 提取选项文字部分（去掉A. B. 等前缀）
            match = re.match(r"^[A-Z]\s*[.、:]\s*(.+)$", line)
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
                logger.info(f"解析外部题库JSON答案: \'{answer}\' -> \'{processed_answer}\'")
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
                # 如果无法导入AI验证模块（例如在独立测试中），跳过AI验证
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
