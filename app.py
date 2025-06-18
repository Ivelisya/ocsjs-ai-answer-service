# -*- coding: utf-8 -*-
"""
EduBrain AI - 智能题库系统
版本：2.2.0 (巅峰版)
"""
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from sqlalchemy.orm import Session
import time
import logging
import openai
import google.generativeai as genai
from datetime import datetime

from config import Config
from utils import SimpleCache, format_answer_for_ocs, parse_question_and_options, extract_answer, normalize_text
from prompts import build_prompt, build_correction_prompt, JUDGEMENT_PROMPT_TEMPLATE
from models import Base, QARecord, engine, SessionLocal

# --- 配置 ---
MAX_RETRIES = 2
RETRY_DELAY = 1 # 秒

# 配置日志
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ai_answer_service')

# 初始化数据库
def init_database():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建成功。")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}", exc_info=True)
        raise

# 初始化应用
app = Flask(__name__)
CORS(app)
init_database()
cache = SimpleCache(Config.CACHE_EXPIRATION) if Config.ENABLE_CACHE else None

# AI 客户端初始化
client = None
if Config.AI_PROVIDER == 'openai':
    if not Config.OPENAI_API_KEY: raise ValueError("请在 .env 文件中配置 OPENAI_API_KEY")
    client = openai.OpenAI(api_key=Config.OPENAI_API_KEY, base_url=Config.OPENAI_API_BASE)
    logger.info(f"AI 提供商设置为: OpenAI (模型: {Config.OPENAI_MODEL})")
elif Config.AI_PROVIDER == 'gemini':
    if not Config.GEMINI_API_KEY: raise ValueError("请在 .env 文件中配置 GEMINI_API_KEY")
    genai.configure(api_key=Config.GEMINI_API_KEY)
    logger.info(f"AI 提供商设置为: Gemini (模型: {Config.GEMINI_MODEL})")
else:
    raise ValueError(f"无效的 AI_PROVIDER: {Config.AI_PROVIDER}")

start_time = time.time()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_access_token(request):
    if Config.ACCESS_TOKEN:
        token = request.headers.get('X-Access-Token') or request.args.get('token')
        return token == Config.ACCESS_TOKEN
    return True

def call_ai_with_retry(prompt: str, temperature: float) -> str:
    """带重试逻辑的AI调用函数。"""
    model_name = Config.GEMINI_MODEL if Config.AI_PROVIDER == 'gemini' else Config.OPENAI_MODEL
    for attempt in range(MAX_RETRIES + 1):
        try:
            if Config.AI_PROVIDER == 'gemini':
                model = genai.GenerativeModel(model_name)
                generation_config = genai.types.GenerationConfig(max_output_tokens=Config.MAX_TOKENS, temperature=temperature)
                response = model.generate_content(prompt, generation_config=generation_config)
                if not response.candidates or not response.candidates[0].content.parts:
                    raise ValueError("API 返回空内容")
                return "".join(part.text for part in response.candidates[0].content.parts).strip()
            else: # openai
                response = client.chat.completions.create(model=model_name, temperature=temperature, max_tokens=Config.MAX_TOKENS, messages=[{"role": "user", "content": prompt}])
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"AI 调用失败 (尝试 {attempt + 1}/{MAX_RETRIES + 1}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise

@app.route('/api/search', methods=['GET', 'POST'])
def search():
    start_req_time = time.time()
    
    if not verify_access_token(request):
        return jsonify({'code': 0, 'msg': '无效的访问令牌'}), 403
    
    try:
        # 统一处理GET和POST请求的数据源
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form
        else: # GET
            data = request.args

        question = normalize_text(data.get('title', ''))
        question_type = data.get('type', '')
        options = normalize_text(data.get('options', ''))
        context = normalize_text(data.get('context'))

        if not question:
            return jsonify({'code': 0, 'msg': '未提供问题内容'})

        # V6.0 弹性适应逻辑：如果options为空，则将question本身作为context，以应对OCS等客户端的特殊情况
        if not options and question_type in ['single', 'multiple']:
            logger.info("检测到选项(options)为空，启用弹性适应策略，将问题(question)作为上下文(context)。")
            context = question

        logger.info(f"接收到问题: '{question[:50]}...' (类型: {question_type})")

        if Config.ENABLE_CACHE and (cached_answer := cache.get(question, question_type, options)):
            logger.info(f"从缓存获取答案 (耗时: {time.time() - start_req_time:.2f}秒)")
            return jsonify(format_answer_for_ocs(question, cached_answer))
        
        model_name = Config.GEMINI_MODEL if Config.AI_PROVIDER == 'gemini' else Config.OPENAI_MODEL
        final_answer_raw = ""

        if question_type == 'judgement':
            logger.info("策略: 单阶段极简 (判断题)")
            prompt = JUDGEMENT_PROMPT_TEMPLATE.format(question=question)
            final_answer_raw = call_ai_with_retry(prompt, 0.0)
        
        else:
            logger.info(f"策略: 单阶段标准 ({question_type})")
            prompt = build_prompt(question, question_type, options, context)
            final_answer_raw = call_ai_with_retry(prompt, Config.TEMPERATURE)

        processed_answer = extract_answer(final_answer_raw, question_type)
        
        if Config.ENABLE_CACHE:
            cache.set(question, processed_answer, question_type, options)
        
        db = next(get_db())
        try:
            record = QARecord(
                question=question, type=question_type, options=options, context=context,
                answer=processed_answer, raw_ai_response=final_answer_raw, model=model_name
            )
            db.add(record)
            db.commit()
        finally:
            db.close()

        logger.info(f"问题处理完成 (耗时: {time.time() - start_req_time:.2f}秒)")
        return jsonify(format_answer_for_ocs(question, processed_answer))
    
    except Exception as e:
        logger.error(f"处理问题时发生严重错误: {e}", exc_info=True)
        return jsonify({'code': 0, 'msg': f'服务内部错误: {str(e)}'})

# 其他路由保持不变...
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok', 'version': '2.2.0', 'ai_provider': Config.AI_PROVIDER,
        'model': Config.GEMINI_MODEL if Config.AI_PROVIDER == 'gemini' else Config.OPENAI_MODEL
    })

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    if not verify_access_token(request):
        return jsonify({'success': False, 'message': '无效的访问令牌'}), 403
    if not Config.ENABLE_CACHE:
        return jsonify({'success': False, 'message': '缓存未启用'})
    cache.clear()
    return jsonify({'success': True, 'message': '缓存已清除'})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    if not verify_access_token(request):
        return jsonify({'success': False, 'message': '无效的访问令牌'}), 403
    
    db = next(get_db())
    try:
        qa_records_count = db.query(QARecord).count()
    finally:
        db.close()

    return jsonify({
        'version': '2.2.0', 'uptime': time.time() - start_time, 'ai_provider': Config.AI_PROVIDER,
        'model': Config.GEMINI_MODEL if Config.AI_PROVIDER == 'gemini' else Config.OPENAI_MODEL,
        'cache_enabled': Config.ENABLE_CACHE, 'cache_size': len(cache.cache) if Config.ENABLE_CACHE else 0,
        'qa_records_count': qa_records_count
    })

@app.route('/dashboard', methods=['GET'])
def dashboard():
    uptime_seconds = time.time() - start_time
    uptime_str = f"{int(uptime_seconds // 86400)}天{int((uptime_seconds % 86400) // 3600)}小时{int((uptime_seconds % 3600) // 60)}分钟"
    
    db = next(get_db())
    try:
        records = db.query(QARecord).order_by(QARecord.id.desc()).limit(100).all()
    finally:
        db.close()

    return render_template(
        'dashboard.html', version="2.2.0", cache_enabled=Config.ENABLE_CACHE,
        cache_size=len(cache.cache) if Config.ENABLE_CACHE else 0,
        ai_provider=Config.AI_PROVIDER,
        model=Config.GEMINI_MODEL if Config.AI_PROVIDER == 'gemini' else Config.OPENAI_MODEL,
        uptime=uptime_str, records=records
    )

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/docs', methods=['GET'])
def docs():
    try:
        import markdown
        with open('api_docs.md', 'r', encoding='utf-8') as f:
            content = f.read()
        html_content = markdown.markdown(content, extensions=['tables'])
        return render_template('docs.html', content=html_content)
    except (ImportError, FileNotFoundError):
        return "API 文档暂时无法加载。"

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)