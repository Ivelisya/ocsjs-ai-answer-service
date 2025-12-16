# -*- coding: utf-8 -*-
"""AI 提示词模块 (v9.0 - 无限Token/拟人化/严格格式)

目标：
- 不计成本追求最高准确率 (Infinite Token Mode)
- 强制拟人化输出 (Human-like)
- 严禁 Markdown 格式 (No Markdown)
- 完美适配 OCS 网课助手答案解析
"""

# --- 1. 核心系统提示词 (Infinite Token System Prompt) ---
SYSTEM_PROMPT_V9 = """You are an expert exam solver for Chinese online education platforms.

Output Format (MUST be valid JSON):
{
    "thinking": "Step-by-step reasoning in Chinese...", 
    "answer": "最终答案内容"
}

CRITICAL RULES FOR OCS COMPATIBILITY:
1. **NO MARKDOWN**: The "answer" field MUST be plain text only. Never use **bold**, `code`, or any markdown.

2. **SINGLE CHOICE (单选题)**:
   - Return ONLY the option content text (去掉选项字母前缀)
   - Example: If correct is "A. 拆分是指将数据集按照一些标准拆分为若干个组", return: "拆分是指将数据集按照一些标准拆分为若干个组"
   - Do NOT include "A.", "B." prefix in answer

3. **MULTIPLE CHOICE (多选题)**:
   - Join correct option contents with '#' separator (不要选项字母)
   - Example: "选项一内容#选项二内容#选项三内容"
   - Do NOT include option letter prefixes

4. **JUDGEMENT (判断题)**:
   - MUST return exactly "正确" or "错误" (Chinese only)
   - Never return "对/错", "true/false", or other variants

5. **COMPLETION/FILL-IN (填空题)**:
   - Return answer content directly
   - Multiple blanks: separate with spaces or commas naturally
   - Never number the answers

6. **HUMAN-LIKE ANSWER STYLE (拟人化答题风格)**:
   - 绝对禁止使用 "中文(English)" 这种中英文对照格式
   - 禁止出现类似 "时间(time)"、"分组(groupby)"、"数据(data)" 的格式
   - 只使用纯中文或纯英文，不要混合注释
   - 答案要像真人手写，简洁自然
   - 例如：正确答案是 "分组" 而不是 "分组(groupby)"
   - 例如：正确答案是 "时间" 而不是 "时间(time)"

Thinking Process:
- Carefully read the question and all options
- Analyze each option's correctness
- For single choice, find THE BEST answer
- For multiple choice, find ALL correct answers
- Output clean answer text without option letters
"""

# 默认使用 v9
SYSTEM_PROMPT = SYSTEM_PROMPT_V9

# --- 2. 针对性提示词模板 ---

# 单选题模板
SINGLE_CHOICE_TEMPLATE = """Task: 单选题 (Single Choice)
Question: {question}
Context: {context}
Options:
{options}

Instructions: 
- 分析所有选项，选出最佳答案
- 如果选项内容简短（少于50字），返回选项内容文字（不含字母前缀）
- 如果选项内容复杂（如表格、代码输出等），直接返回选项字母（如 A、B、C、D）
- 例如选项是 "A. 操作系统"，返回 "操作系统"
- 例如选项是复杂表格，返回 "C"
"""

# 多选题模板
MULTIPLE_CHOICE_TEMPLATE = """Task: 多选题 (Multiple Choice)
Question: {question}
Context: {context}
Options:
{options}

Instructions:
- 分析所有选项，选出所有正确答案
- 用 # 号连接多个正确选项的内容（不要包含选项字母前缀）
- 例如: "选项一内容#选项二内容#选项三内容"
"""

# 判断题模板
JUDGEMENT_TEMPLATE = """Task: 判断题 (Judgement)
Question: {question}
Context: {context}

Instructions:
- 判断题目陈述是否正确
- 只能返回 "正确" 或 "错误" 两个字
- 不要返回其他任何内容
"""

# 填空/主观题模板
COMPLETION_TEMPLATE = """Task: 填空题/主观题 (Completion/Subjective)
Question: {question}
Context: {context}
Options: {options}

Instructions:
- 直接给出答案内容
- 不要使用序号（不要 "1." "2."）
- 多个空格用逗号或空格自然分隔
- DO NOT include the question text.
- Just output the answer content naturally.
- 【重要】禁止使用 "中文(English)" 格式，只用纯中文或纯英文
- 例如：答案是 "分组" 不是 "分组(groupby)"
"""

# 填空题答案验证模板
COMPLETION_VERIFY_TEMPLATE = """你是一个严格的答案验证专家。

题目：{question}

候选答案：{answer}

请判断这个答案是否正确。只需要回复 "正确" 或 "错误"，不要有任何其他内容。

判断标准：
1. 答案内容是否准确
2. 答案是否完整回答了问题
3. 如果答案明显是错误的或不相关的，返回 "错误"
4. 如果答案基本正确（允许表述略有不同），返回 "正确"
"""


# --- 3. 平台特定指令 ---
PLATFORM_INSTRUCTIONS = {
    "chaoxing": "Platform: Chaoxing (超星). Prioritize standard database answers.",
    "zhihuishu": "Platform: Zhihuishu (智慧树). Pay attention to subtle option differences.",
    "mooc": "Platform: MOOC. Focus on course-specific details.",
    "icve": "Platform: ICVE (职教云). Practice-oriented questions.",
}

def build_prompt(question: str, question_type: str, options: str, context: str = "", platform: str = "") -> str:
    """
    Constructs the prompt based on the question type and platform.
    """
    base_prompt = SYSTEM_PROMPT.strip()
    
    # 获取平台特定指令
    platform_key = platform.lower() if platform else ""
    platform_instruction = ""
    for key, instruction in PLATFORM_INSTRUCTIONS.items():
        if key in platform_key:
            platform_instruction = f"\n# {instruction}\n"
            break
            
    # 清理输入
    question = question.strip() if question else ""
    options = options.strip() if options else ""
    context = context.strip() if context else ""
    q_type = question_type.lower() if question_type else "unknown"

    # 如果有 context (来自 Userscript 的富文本)，优先展示 Context
    # 并在 prompt 中强调 Context 的重要性
    if context:
        base_prompt += "\n[IMPORTANT: Use the provided 'Context' as the primary source of truth.]"

    # 选择模板
    if "judgement" in q_type or "判断" in q_type:
        template = JUDGEMENT_TEMPLATE
    elif "multiple" in q_type or "多选" in q_type:
        template = MULTIPLE_CHOICE_TEMPLATE
    elif "single" in q_type or "单选" in q_type:
        template = SINGLE_CHOICE_TEMPLATE
    else:
        # Default to completion for unknowns
        template = COMPLETION_TEMPLATE

    return f"{base_prompt}{platform_instruction}\n{template.format(question=question, options=options, context=context)}"

# 保持向后兼容
JUDGEMENT_PROMPT_TEMPLATE = JUDGEMENT_TEMPLATE
