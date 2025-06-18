# -*- coding: utf-8 -*-
"""
AI 提示词优化探索存档 (2025-06-18)
此文件存档了从 V2.2 (82.5% 准确率) 到 V3.2 (66.67% 准确率) 的一系列失败的提示词优化尝试。
记录于此，以供未来参考。

--- V3.0 ---
思路: 大一统Prompt，为所有题型提供高质量、带思考过程的Few-Shot示例，废除判断题极简模板。
结果: 准确率下降到 69.70%。判断题、单选题准确率暴跌。
结论: 过度设计，复杂的指令和示例干扰了模型对简单问题的判断。

--- V3.1 ---
思路: 回归混合策略。恢复判断题极简模板，但为其他题型提供更通用的基础示例。
结果: 准确率 69.70%。判断题准确率回升，但填空题准确率暴跌。
结论: 修复了判断题，但破坏了填空题。原因是替换掉了高质量的、能处理特殊字符和上下文的填空题示例。

--- V3.2 (当前文件内容) ---
思路: 融合精华。在V3.1的混合策略基础上，恢复V3.0中高质量的填空题和带上下文填空题示例。
结果: 准确率 66.67%。整体准确率进一步下降。
结论: 复杂的Few-Shot组合可能产生了不可预知的负面化学反应。回归到最开始的稳定版本是唯一选择。
"""

# --- V3.2 的代码 ---
# -*- coding: utf-8 -*-
"""
AI 提示词模块 (v3.2 - 融合精华版)
"""
# --- 1. 基础指令模板 (System Prompt) ---
SYSTEM_PROMPT = """# AI 角色与任务
你是一位顶级的AI知识引擎与推理专家。你的核心任务是针对用户提出的任何问题，进行严谨、深入的分析，并提供一个绝对准确的答案。

# 核心指令
1.  **绝对精确原则 (Absolute Precision Principle)**: 这是最高指令。你的最终答案必须与问题选项或标准答案的**完整文本一字不差地、100%完全匹配**。这包括所有的标点、空格、大小写和特殊字符。绝对禁止任何形式的简化、修改、补充、或同义词替换。
    *   **警告**: 任何偏离原文的答案都将被视为完全错误！
    *   **正面示例**: 如果标准答案是“艾伦·图灵”，你的答案必须是“艾伦·图灵”，而不是“图灵”。
    *   **正面示例**: 如果标准答案是“The string "aaa".”，你的答案必须是“The string "aaa".”，而不是“The string "aaa"”。
    *   **负面示例**: 如果正确选项是“A. 人工智能(AI)”，你的答案必须是“人工智能(AI)”，而不是“人工智能”或“AI”。
    *   **负面示例**: 如果答案是“ls -l”，你的答案必须是“ls -l”，而不是“ls-l”。
2.  **上下文利用**: 如果输入中提供了`上下文`信息，你的推理和答案应优先基于该信息。
3.  **深度思考 (Deep Thinking)**: 在 `<thinking>` 标签内，你必须进行一步步、有条理的思考。展示你的完整推理链。
4.  **最终答案 (Final Answer)**: 在 `<answer>` 标签内，只提供最终的、确切的答案。
5.  **格式遵从 (Strict Formatting)**: `<answer>` 标签内的输出必须严格遵守【答案格式指南】。

# 答案格式指南
-   **单选题**: 输出选项的**完整文本**。
-   **多选题**: 输出所有正确选项的**完整文本**，并用井号 `#` 作为唯一的分隔符。
-   **判断题**: 只能输出 `正确` 或 `错误`。
-   **填空题**: 输出需要填入的**完整内容**。如果题目有多个独立的空，用 `#` 分隔。
"""

# --- 2. Few-Shot 示例库 (融合精华版) ---
EXAMPLES = {
    "single": """
<example>
<user_input>
问题: 下列哪个不是Python的内置数据类型？
类型: single
选项:
A. list
B. tuple
C. dict
D. array
</user_input>
<ai_response>
<thinking>
1.  **问题分析**: 找出不属于Python内置数据类型的选项。
2.  **知识检索**:
    *   `list` (列表) 是Python的内置数据类型。
    *   `tuple` (元组) 是Python的内置数据类型。
    *   `dict` (字典) 是Python的内置数据类型。
    *   `array` (数组) 不是Python的核心内置数据类型，它需要从 `array` 模块导入。
3.  **结论**: `array` 不是内置数据类型。
</thinking>
<answer>array</answer>
</ai_response>
</example>
""",
    "multiple": """
<example>
<user_input>
问题: 以下哪些是HTTP的请求方法？
类型: multiple
选项:
A. GET
B. POST
C. SEND
D. PUSH
</user_input>
<ai_response>
<thinking>
1.  **问题分析**: 识别哪些是标准的HTTP请求方法。
2.  **知识检索**:
    *   GET 是标准的HTTP请求方法，用于请求数据。
    *   POST 是标准的HTTP请求方法，用于提交数据。
    *   SEND 不是标准的HTTP请求方法。
    *   PUSH 不是标准的HTTP请求方法（虽然HTTP/2中有Server Push，但它不是一个客户端请求方法）。
3.  **结论**: GET 和 POST 是正确的。
4.  **格式化输出**: 用 `#` 连接答案。
</thinking>
<answer>GET#POST</answer>
</ai_response>
</example>
""",
    "completion": """
<example>
<user_input>
问题: 在Git版本控制系统中，用于将一个分支的修改合并到另一个分支，但会创建一个新的合并提交记录的命令是____；而将一个分支的提交历史在另一个分支上重放的命令是____。
类型: completion
</user_input>
<ai_response>
<thinking>
1.  **问题分析**: 这是一个填空题，需要填写两个Git命令。
2.  **知识检索**:
    *   第一个空描述的是标准的合并行为，会产生一个合并提交（merge commit）。这个命令是 `git merge`。
    *   第二个空描述的是将一系列提交应用到另一个分支顶部的行为，这被称为“变基”。这个命令是 `git rebase`。
3.  **答案组合**: 第一个空是 `git merge`，第二个空是 `git rebase`。
4.  **格式化输出**: 用 `#` 分隔两个答案。
</thinking>
<answer>git merge#git rebase</answer>
</ai_response>
</example>
""",
    "completion_with_context": """
<example>
<user_input>
问题: 输出的值为？
类型: completion
上下文:
String str = "Hello, World!";
String newStr = str.replace('o', 'a');
System.out.println(newStr);
</user_input>
<ai_response>
<thinking>
1.  **问题分析**: 这是一个代码填空题，需要根据给出的Java代码上下文，确定最终的输出。
2.  **代码执行分析**:
    *   `String str = "Hello, World!";` 初始化一个字符串。
    *   `String newStr = str.replace('o', 'a');` 调用 `replace` 方法，将字符串 `str` 中所有的 'o' 字符替换为 'a' 字符。
    *   "Hello, World!" 中的 'o' 有两个，分别在 "Hello" 和 "World" 中。
    *   替换后，字符串变为 "Hella, Warld!"。
    *   `System.out.println(newStr);` 将会打印这个新字符串。
3.  **最终答案确认**: 输出内容为 `Hella, Warld!`。
</thinking>
<answer>Hella, Warld!</answer>
</ai_response>
</example>
"""
}

def build_prompt(question: str, question_type: str, options: str, context: str = None) -> str:
    """根据问题类型和上下文智能构建提示词"""
    example_key = question_type
    # 如果是带上下文的填空题，使用专用示例
    if question_type == "completion" and context:
        example_key = "completion_with_context"
        
    example = EXAMPLES.get(example_key)

    user_input_section = f"问题: {question}\n类型: {question_type or '未指定'}\n"
    if context:
        user_input_section += f"上下文:\n{context}\n"
    if options:
        user_input_section += f"选项:\n{options}\n"
        
    # 只有在找到示例时才添加示例部分
    if example:
        return f"{SYSTEM_PROMPT}\n{example}\n---\n# 当前任务\n{user_input_section}<ai_response>\n"
    else:
        return f"{SYSTEM_PROMPT}\n---\n# 当前任务\n{user_input_section}<ai_response>\n"


# --- 自我修正提示词 ---
CORRECTION_SYSTEM_PROMPT = """# 角色: 顶级考官
# 任务: 审查AI学生的答卷，进行批判性评估和修正。
# 指令:
1.  **审查**: 仔细阅读 `<original_question>` 和 `<student_response>`。
2.  **批判**: 在 `<thinking>` 标签内，对学生的思考和答案进行挑剔的分析。检查逻辑、精确性（标点、大小写、全名等）。
3.  **修正**: 在 `<answer>` 标签内，给出完美的答案，严格遵守原始格式指南。
"""

def build_correction_prompt(original_question: str, student_response: str) -> str:
    return f"{CORRECTION_SYSTEM_PROMPT}\n# 待审查任务\n<original_question>\n{original_question}\n</original_question>\n<student_response>\n{student_response}\n</student_response>"

# --- 判断题专用极简提示词 (v3.1 回归) ---
JUDGEMENT_PROMPT_TEMPLATE = """# 任务: 严格按照问题进行分析，只输出“正确”或“错误”这两个词的其中一个，不要有任何其他内容。
# 问题: {question}
"""