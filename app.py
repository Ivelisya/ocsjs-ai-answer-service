# -*- coding: utf-8 -*-
"""
EduBrain AI - 智能题库系统
基于 OpenAI API 的智能题库服务，提供兼容 OCS 接口的智能答题功能
作者：ivekasy
版本：1.1.0
"""
from flask import Flask, request, jsonify, make_response, render_template
from flask_cors import CORS
import os
import time
import logging
import openai
import google.generativeai as genai # 新增 Gemini 导入
from google.generativeai.types import HarmCategory, HarmBlockThreshold # 新增导入，用于安全设置 (保留以方便调试安全设置)
import json
from datetime import datetime

from config import Config
from utils import SimpleCache, format_answer_for_ocs, parse_question_and_options, extract_answer

# 配置日志
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ai_answer_service')

# 初始化应用
app = Flask(__name__)
CORS(app)  # 启用CORS支持

# 初始化缓存
cache = SimpleCache(Config.CACHE_EXPIRATION) if Config.ENABLE_CACHE else None

# 验证 API 密钥
if Config.AI_PROVIDER == 'openai':
    if not Config.OPENAI_API_KEY:
        logger.critical("AI_PROVIDER 设置为 openai，但未设置 OpenAI API 密钥。请在 .env 文件中配置 OPENAI_API_KEY。")
        raise ValueError("请设置环境变量 OPENAI_API_KEY")
    # 初始化OpenAI客户端
    client = openai.OpenAI(
        api_key=Config.OPENAI_API_KEY,
        base_url=Config.OPENAI_API_BASE
    )
    logger.info(f"AI 提供商设置为: OpenAI (模型: {Config.OPENAI_MODEL})")
elif Config.AI_PROVIDER == 'gemini':
    if not Config.GEMINI_API_KEY:
        logger.critical("AI_PROVIDER 设置为 gemini，但未设置 Gemini API 密钥。请在 .env 文件中配置 GEMINI_API_KEY。")
        raise ValueError("请设置环境变量 GEMINI_API_KEY")
    # 配置Gemini客户端
    genai.configure(api_key=Config.GEMINI_API_KEY)
    # Gemini 模型实例将在需要时创建
    logger.info(f"AI 提供商设置为: Gemini (模型: {Config.GEMINI_MODEL})")
else:
    logger.critical(f"无效的 AI_PROVIDER 配置: {Config.AI_PROVIDER}。请设置为 'openai' 或 'gemini'。")
    raise ValueError(f"无效的 AI_PROVIDER: {Config.AI_PROVIDER}")

# 问答记录存储（实际应用中可以使用数据库）
qa_records = []
MAX_RECORDS = 100  # 最多保存100条记录
start_time = time.time()

def verify_access_token(request):
    """验证访问令牌（如果配置了的话）"""
    if Config.ACCESS_TOKEN:
        token = request.headers.get('X-Access-Token') or request.args.get('token')
        if not token or token != Config.ACCESS_TOKEN:
            return False
    return True

@app.route('/api/search', methods=['GET', 'POST'])
def search():
    """
    处理OCS发送的搜索请求，使用OpenAI API生成答案
    GET请求: 从URL参数获取问题
    POST请求: 从请求体获取问题
    
    参数:
        title: 问题内容
        type: 问题类型 (single-单选, multiple-多选, judgement-判断, completion-填空)
        options: 选项内容
        
    返回:
        成功: {'code': 1, 'question': '问题', 'answer': 'AI生成的答案'}
        失败: {'code': 0, 'msg': '错误信息'}
    """
    start_time = time.time()
    
    # 验证访问令牌（如果配置了的话）
    if not verify_access_token(request):
        return jsonify({
            'code': 0,
            'msg': '无效的访问令牌'
        }), 403
    
    try:
        # 根据请求方法获取问题内容
        if request.method == 'GET':
            question = request.args.get('title', '')
            question_type = request.args.get('type', '')
            options = request.args.get('options', '')
        else:  # POST
            content_type = request.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                data = request.get_json()
                question = data.get('title', '')
                question_type = data.get('type', '')
                options = data.get('options', '')
            else:
                # 处理表单数据
                question = request.form.get('title', '')
                question_type = request.form.get('type', '')
                options = request.form.get('options', '')
        
        # 记录接收到的问题
        logger.info(f"接收到问题: '{question[:50]}...' (类型: {question_type})")
        
        # 如果没有提供问题，返回错误
        if not question:
            logger.warning("未提供问题内容")
            return jsonify({
                'code': 0,
                'msg': '未提供问题内容'
            })
        
        # 检查缓存中是否有此问题的答案
        if Config.ENABLE_CACHE:
            cached_answer = cache.get(question, question_type, options)
            if cached_answer:
                logger.info(f"从缓存获取答案 (耗时: {time.time() - start_time:.2f}秒)")
                return jsonify(format_answer_for_ocs(question, cached_answer))
        
        # 构建发送给OpenAI的提示
        prompt = parse_question_and_options(question, options, question_type)
        ai_answer = ""

        if Config.AI_PROVIDER == 'openai':
            # 调用OpenAI API
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                temperature=Config.TEMPERATURE,
                max_tokens=Config.MAX_TOKENS,
                messages=[
                    {"role": "system", "content": """
# 角色
你是一个高级AI推理引擎，专门解决各种考试题目。

# 核心指令
你的任务是生成一个包含思考过程和最终答案的结构化响应。
即使信息不完整，你也必须根据上下文和你的知识库，给出你认为最有可能的答案。**永远不要拒绝回答**。

# 输出结构
你必须严格按照以下XML格式输出，不得包含任何在此结构之外的文本：
<thinking>
在这里逐步展示你的推理过程。
1.  **分析题干**: 拆解问题，理解其核心要求。
2.  **评估选项/知识**: 分析每个选项的正确性，或者调动你的知识库来寻找答案。
3.  **得出结论**: 基于分析，确定最可能的答案。
</thinking>
<answer>
在这里放置最终答案，并严格遵守下方针对不同题型的格式要求。
</answer>

---
# 最终答案格式指南 (在 <answer> 标签内使用)

-   **单选题 (single)**: 直接返回正确选项的文本。
    *   *示例*: `苹果`
-   **多选题 (multiple)**: 返回所有正确选项的文本，用井号 `#` 分隔。
    *   *示例*: `中国#日本`
-   **判断题 (judgement)**: 仅返回 "正确" 或 "错误"。
    *   *示例*: `错误`
-   **填空题 (completion)**: 直接返回需要填写的**完整、连续**的内容。除非题目中明确有多个分离的填空处（例如 `___和___`），否则不要使用 `#` 分隔。
    *   *示例 (单个答案)*: 问题是 "新中国成立于何时？"，答案应为 `1949年10月1日`。
    *   *示例 (多个空)*: 问题是 "中国的首都是___，最大的城市是___。"，答案应为 `北京#上海`。
---
"""},
                    {"role": "user", "content": prompt}
                ]
            )
            ai_answer = response.choices[0].message.content.strip()

        elif Config.AI_PROVIDER == 'gemini':
            # 调用Gemini API
            model = genai.GenerativeModel(Config.GEMINI_MODEL)
            
            # 构建更结构化的 Prompt for Gemini
            # --- 全面优化的 Gemini Prompt ---
            # 1. 角色定义：清晰定义AI的角色和能力。
            # 2. 核心指令：明确任务目标和行为准则。
            # 3. 格式总览：提供一个所有题型通用的格式总结。
            # 4. Few-Shot示例：为每种题型提供清晰的输入输出示例，这是提升准确率的关键。
            # 5. 异常处理：指导模型在遇到不确定问题时的行为。
            # 6. 动态内容注入：将实际问题动态插入到结构化模板中。
            # 新的 Gemini 提示词，强制输出 <thinking> 和 <answer>
            prompt_template = """# 任务：严格按照XML格式输出思考过程和答案

# 指令
1.  **思考**: 在 `<thinking>` 标签内，展示你的推理步骤。
2.  **回答**: 在 `<answer>` 标签内，提供最终答案。
3.  **不确定性**: 即使不完全确定，也要给出最可能的答案。**永远不要拒绝回答**。
4.  **格式**: `<answer>` 标签内的内容必须严格遵守题型格式指南。

# 答案格式指南
-   **单选题**: `选项文本`
-   **多选题**: `文本1#文本2`
-   **判断题**: `正确` 或 `错误`
-   **填空题**: 返回**完整、连续**的内容。仅当题目中有多个分离的填空处时才使用 `#` 分隔。
    *   *示例 (单个答案)*: `1949年10月1日`
    *   *示例 (多个空)*: `北京#上海`

---
# 开始处理

<thinking>
1.  **识别题型**: 这是一个 {type}。
2.  **分析题干**: 我需要分析问题“{question}”。
3.  **评估选项/知识**: {options_analysis}
4.  **得出结论**: 基于以上分析，我认为最可能的答案是...
</thinking>
<answer>
</answer>"""

            question_type_description_map = {
                "single": "单选题",
                "multiple": "多选题",
                "judgement": "判断题",
                "completion": "填空题",
                "": "未指定类型"
            }
            q_type_desc = question_type_description_map.get(question_type, "未指定类型")

            # 为 Gemini 构建更具体的思考指令
            options_analysis_prompt = "我将运用我的知识库来寻找答案。"
            if options:
                options_analysis_prompt = f"我将评估以下选项：\n{options}"

            # 动态填充模板
            filled_prompt = prompt_template.format(
                type=q_type_desc,
                question=question,
                options_analysis=options_analysis_prompt
            )

            # 最终呈现给模型的完整 prompt
            full_prompt = f"""# 任务：严格按照XML格式输出思考过程和答案

# 指令
1.  **思考**: 在 `<thinking>` 标签内，展示你的推理步骤。
2.  **回答**: 在 `<answer>` 标签内，提供最终答案。
3.  **不确定性**: 即使不完全确定，也要给出最可能的答案。**永远不要拒绝回答**。
4.  **格式**: `<answer>` 标签内的内容必须严格遵守题型格式指南。

# 答案格式指南
-   **单选题**: `选项文本`
-   **多选题**: `文本1#文本2`
-   **判断题**: `正确` 或 `错误`
-   **填空题**: 返回**完整、连续**的内容。仅当题目中有多个分离的填空处时才使用 `#` 分隔。
    *   *示例 (单个答案)*: `1949年10月1日`
    *   *示例 (多个空)*: `北京#上海`

---
# 开始处理

{filled_prompt}
"""
            logger.debug(f"Gemini full_prompt: {full_prompt}") # 记录完整的prompt用于调试

            # Gemini API 的 generation_config 对应 OpenAI 的 temperature, max_tokens 等
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=Config.MAX_TOKENS,
                temperature=Config.TEMPERATURE
            )
            
            # --- 调试用的安全设置：全部允许 ---
            # safety_settings_for_debugging = {
            #     HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            #     HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            #     HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            #     HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            # }
            
            response = model.generate_content(
                full_prompt,
                generation_config=generation_config
                # safety_settings=safety_settings_for_debugging # 如果需要测试宽松安全设置，取消此行注释
            )
            # --- 增强的 Gemini 响应处理 ---
            try:
                # 检查是否有有效的候选内容
                if response.candidates and response.candidates[0].content.parts:
                    ai_answer = "".join(part.text for part in response.candidates[0].content.parts).strip()
                
                # 检查是否有其他终止原因
                else:
                    finish_reason = "UNKNOWN"
                    if response.candidates:
                        finish_reason = response.candidates[0].finish_reason.name
                    
                    if finish_reason == "MAX_TOKENS":
                        msg = "AI响应因达到最大令牌数而被截断。已增加默认值，如仍出现此问题，请尝试在 .env 文件中进一步增加 MAX_TOKENS。"
                        logger.warning(msg)
                        # 即使被截断，也尝试从 response.text 中获取部分内容，因为它可能包含部分答案
                        try:
                            ai_answer = response.text
                        except ValueError:
                            ai_answer = "响应被截断，且无有效内容返回。"
                    
                    elif response.prompt_feedback and response.prompt_feedback.block_reason:
                        msg = f"Gemini API 请求因 prompt feedback 被阻止: {response.prompt_feedback.block_reason_message}"
                        logger.warning(f"{msg}. Feedback: {response.prompt_feedback}")
                        return jsonify({'code': 0, 'msg': msg})
                    
                    else:
                        msg = "Gemini API 未返回有效答案。"
                        logger.warning(f"{msg} Finish Reason: {finish_reason}. Candidates: {response.candidates}")
                        ai_answer = f"抱歉，AI未能生成有效答案 (原因: {finish_reason})。"

            except Exception as e:
                # 捕获所有可能的响应解析错误，包括 response.text 的 ValueError
                logger.error(f"解析Gemini响应时发生未知错误: {e}", exc_info=True)
                logger.error(f"原始响应对象: {response}")
                ai_answer = "抱歉，解析AI响应时发生内部错误。"

        else:
            logger.error(f"未知的 AI_PROVIDER: {Config.AI_PROVIDER}")
            return jsonify({'code': 0, 'msg': 'AI服务配置错误'})

        # 处理答案格式
        processed_answer = extract_answer(ai_answer, question_type)
        
        # 保存到缓存
        if Config.ENABLE_CACHE:
            cache.set(question, processed_answer, question_type, options)
        
        # 保存问答记录
        current_time = datetime.now()
        qa_records.append({
            'time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'timestamp': current_time.isoformat(),
            'question': question,
            'type': question_type,
            'options': options,
            'answer': processed_answer
        })
        if len(qa_records) > MAX_RECORDS:
            qa_records.pop(0)
        
        # 记录处理时间
        process_time = time.time() - start_time
        logger.info(f"问题处理完成 (耗时: {process_time:.2f}秒)")
        
        # 返回符合OCS格式的响应
        return jsonify(format_answer_for_ocs(question, processed_answer))
    
    except Exception as e:
        # 记录异常
        logger.error(f"处理问题时发生错误: {str(e)}", exc_info=True)
        
        # 捕获所有异常并返回错误信息
        return jsonify({
            'code': 0,
            'msg': f'发生错误: {str(e)}'
        })

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'message': 'AI题库服务运行正常',
        'version': '1.1.0',
        'cache_enabled': Config.ENABLE_CACHE,
        'ai_provider': Config.AI_PROVIDER,
        'model': Config.OPENAI_MODEL if Config.AI_PROVIDER == 'openai' else Config.GEMINI_MODEL
    })

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """清除缓存接口"""
    # 验证访问令牌
    if not verify_access_token(request):
        return jsonify({
            'success': False,
            'message': '无效的访问令牌'
        }), 403
    
    if not Config.ENABLE_CACHE:
        return jsonify({
            'success': False,
            'message': '缓存未启用'
        })
    
    cache.clear()
    return jsonify({
        'success': True,
        'message': '缓存已清除'
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取服务统计信息"""
    # 验证访问令牌
    if not verify_access_token(request):
        return jsonify({
            'success': False,
            'message': '无效的访问令牌'
        }), 403
    
    stats = {
        'version': '1.1.0',
        'uptime': time.time() - start_time,
        'ai_provider': Config.AI_PROVIDER,
        'model': Config.OPENAI_MODEL if Config.AI_PROVIDER == 'openai' else Config.GEMINI_MODEL,
        'cache_enabled': Config.ENABLE_CACHE,
        'cache_size': len(cache.cache) if Config.ENABLE_CACHE else 0,
        'qa_records_count': len(qa_records)
    }
    
    return jsonify(stats)

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """仪表盘 - 显示问答记录和系统状态"""
    uptime_seconds = time.time() - start_time
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    uptime_str = f"{days}天{hours}小时{minutes}分钟"
    
    return render_template(
        'dashboard.html',
        version="1.1.0",
        cache_enabled=Config.ENABLE_CACHE,
        cache_size=len(cache.cache) if Config.ENABLE_CACHE else 0,
        ai_provider=Config.AI_PROVIDER,
        model=Config.OPENAI_MODEL if Config.AI_PROVIDER == 'openai' else Config.GEMINI_MODEL,
        uptime=uptime_str,
        records=qa_records
    )

@app.route('/', methods=['GET'])
def index():
    """首页 - 显示Web界面"""
    return render_template('index.html')

@app.route('/docs', methods=['GET'])
def docs():
    """API文档页面"""
    with open('api_docs.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用markdown库将文档转换为HTML（需要安装：pip install markdown）
    try:
        import markdown
        html_content = markdown.markdown(content, extensions=['tables'])
        
        return f"""
        <html>
            <head>
                <title>AI题库服务 - API文档</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                    h1, h2, h3 {{ color: #2c3e50; }}
                    .container {{ max-width: 800px; margin: 0 auto; }}
                    code {{ background: #e0e0e0; padding: 2px 4px; border-radius: 3px; }}
                    pre {{ background: #f4f4f4; padding: 10px; border-radius: 4px; overflow-x: auto; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; }}
                    th {{ background-color: #f4f4f4; }}
                </style>
            </head>
            <body>
                <div class="container">
                    {html_content}
                </div>
            </body>
        </html>
        """
    except ImportError:
        # 如果没有安装markdown库，则返回纯文本
        return f"""
        <html>
            <head>
                <title>AI题库服务 - API文档</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                    h1 {{ color: #333; }}
                    .container {{ max-width: 800px; margin: 0 auto; }}
                    pre {{ background: #f4f4f4; padding: 10px; border-radius: 4px; overflow-x: auto; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>AI题库服务 - API文档</h1>
                    <pre>{content}</pre>
                </div>
            </body>
        </html>
        """

if __name__ == '__main__':
    # 开启应用
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)