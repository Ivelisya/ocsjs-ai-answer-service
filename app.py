# -*- coding: utf-8 -*-
"""
EduBrain AI - 智能题库系统
基于 OpenAI API 的智能题库服务，提供兼容 OCS 接口的智能答题功能
作者：Lynn
版本：1.1.0
"""
from flask import Flask, request, jsonify, make_response, render_template
from flask_cors import CORS
import os
import time
import logging
import openai
import google.generativeai as genai # 新增 Gemini 导入
from google.generativeai.types import HarmCategory, HarmBlockThreshold # 新增导入，用于安全设置
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
                    {"role": "system", "content": "你是一个专业的考试答题助手。请直接回答答案，不要解释。选择题只回答选项的内容(如：地球)；多选题用#号分隔答案,只回答选项的内容(如中国#世界#地球)；判断题只回答: 正确/对/true/√ 或 错误/错/false/×；填空题直接给出答案。"},
                    {"role": "user", "content": prompt}
                ]
            )
            ai_answer = response.choices[0].message.content.strip()

        elif Config.AI_PROVIDER == 'gemini':
            # 调用Gemini API
            model = genai.GenerativeModel(Config.GEMINI_MODEL)
            
            # 构建更结构化的 Prompt for Gemini
            prompt_parts = [
                "角色：你是一个专业的AI考试答题助手。",
                "核心任务：根据提供的问题和选项，直接给出最准确的答案。",
                "通用输出格式：请不要包含任何解释、分析或额外说明，只输出答案本身。",
                "---",
                "特定题型输出格式指南：",
                "- 单选题：直接回答选项的文本内容 (例如：如果正确答案是B选项“地球”，则回答“地球”)。",
                "- 多选题：务必使用#号分隔每个正确选项的文本内容 (例如：中国#世界#地球)。确保每个部分都是选项的实际文本。",
                "- 判断题：仅回答“正确”或“错误”。（也可以是“对”/“错”，“true”/“false”，“√”/“×”中的一种，但优先使用“正确”或“错误”）",
                "- 填空题：直接给出填空的内容，多个空用#号分隔。",
                "---",
                "现在，请回答以下问题：",
            ]

            question_type_description_map = {
                "single": "单选题",
                "multiple": "多选题",
                "judgement": "判断题",
                "completion": "填空题",
                "": "未指定类型" # 处理空类型的情况
            }
            q_type_desc = question_type_description_map.get(question_type, "未指定类型")

            prompt_parts.append(f"题目类型: {q_type_desc}")
            prompt_parts.append(f"问题: {question}") # 使用从request获取的原始question

            if options: # 使用从request获取的原始options
                prompt_parts.append(f"选项:\n{options}")
            
            prompt_parts.append("---")
            prompt_parts.append("答案：") # 引导模型直接输出答案

            full_prompt = "\n".join(prompt_parts)
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
            # 检查是否有候选答案，并处理可能的安全阻止等情况
            if response.candidates and response.candidates[0].content.parts:
                ai_answer = "".join(part.text for part in response.candidates[0].content.parts).strip()
            elif response.prompt_feedback and response.prompt_feedback.block_reason:
                 logger.warning(f"Gemini API 请求因 prompt feedback 被阻止。原因: {response.prompt_feedback.block_reason_message}. Feedback: {response.prompt_feedback}")
                 return jsonify({'code': 0, 'msg': f'Gemini API 请求被阻止: {response.prompt_feedback.block_reason_message}. 请检查应用日志获取详细反馈。'})
            else:
                # 详细记录为何没有得到有效答案
                logger.warning("Gemini API 未返回有效答案。")
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    logger.warning(f"Gemini API Prompt Feedback: {response.prompt_feedback}")
                if hasattr(response, 'candidates') and response.candidates:
                    logger.warning(f"Gemini API Candidates (可能为空或内容被过滤): {response.candidates}")
                else:
                    logger.warning("Gemini API Response 不包含 candidates 属性或 candidates 为空。")
                
                # 尝试从 response.text 获取原始文本，如果存在的话 (某些情况下错误信息可能在这里)
                try:
                    raw_text = response.text
                    logger.warning(f"Gemini API raw response text: {raw_text[:500]}...") # 只记录前500字符
                except AttributeError:
                    logger.warning("Gemini API response 对象没有 text 属性。")

                ai_answer = "抱歉，AI未能生成有效答案。请检查应用日志获取详细信息。" # 更新了默认错误信息

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
        'version': '1.0.0',
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
        'version': '1.0.0',
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