# -*- coding: utf-8 -*-
""" 
EduBrain AI - FastAPI Application

说明：
- 这是 Flask -> FastAPI 的迁移入口，保持原有 API 路由兼容（/api/search 等）。
- OpenAPI 文档默认放在 /api/docs（避免与原 /docs 页面冲突）。
"""

from __future__ import annotations

import asyncio
import inspect
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace
from typing import Any, AsyncGenerator, Dict, Optional
from urllib.parse import unquote, parse_qs

import google.generativeai as genai
import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openai import AsyncAzureOpenAI, AsyncOpenAI
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from external_database import ExternalDatabase, get_default_databases
from logger import app_logger as logger
from models import AsyncSessionLocal, QARecord, init_db_async
from prompts import build_prompt
from rate_limiter import RateLimiter
from utils import (
    Cache,
    _clean_answer_for_ocs,
    _preprocess_external_answer,
    extract_answer,
    format_answer_for_ocs,
    normalize_text,
    parse_reading_comprehension,
)
from validators import InputValidator

VERSION = "2.3.1"


# -------------------------
# App state & helpers
# -------------------------

class Metrics:
    def __init__(self) -> None:
        self.request_count: int = 0
        self.total_latency_sec: float = 0.0

    def record(self, latency: float) -> None:
        self.request_count += 1
        self.total_latency_sec += latency

    @property
    def avg_latency_sec(self) -> float:
        if self.request_count <= 0:
            return 0.0
        return self.total_latency_sec / self.request_count


def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # 取第一个
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def verify_access_token(request: Request) -> bool:
    if not Config.ACCESS_TOKEN:
        return True
    # 测试或调试模式放行
    if getattr(request.app.state, "testing", False) or Config.DEBUG:
        return True
    token = request.headers.get("X-Access-Token") or request.query_params.get("token")
    return token == Config.ACCESS_TOKEN


async def require_token(request: Request) -> None:
    if not verify_access_token(request):
        raise HTTPException(status_code=403, detail="无效的访问令牌")


def _get_today_log_file() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join("logs", f"ai_answer_service_{today}.log")


# -------------------------
# AI client init + call
# -------------------------

client: Any = None


def init_ai_client() -> Any:
    global client

    # 尝试验证配置（不在导入阶段中断应用），仅记录状态
    try:
        Config.validate_config()
    except Exception as e:
        logger.warning(f"AI 配置未完成或验证失败: {e}")

    if Config.AI_PROVIDER == "openai":
        if Config.OPENAI_API_KEY:
            client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY, base_url=Config.OPENAI_API_BASE)
            logger.info(f"AI 提供商: OpenAI (模型: {Config.OPENAI_MODEL})")
        else:
            logger.warning("未配置 OPENAI_API_KEY，OpenAI 功能不可用")
    elif Config.AI_PROVIDER == "azure_openai":
        if Config.AZURE_OPENAI_API_KEY and Config.AZURE_OPENAI_ENDPOINT:
            client = AsyncAzureOpenAI(
                api_key=Config.AZURE_OPENAI_API_KEY,
                azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
                api_version=Config.AZURE_OPENAI_API_VERSION,
            )
            logger.info(f"AI 提供商: Azure OpenAI (部署: {Config.AZURE_OPENAI_DEPLOYMENT})")
        else:
            logger.warning("未配置 AZURE_OPENAI_API_KEY 或 AZURE_OPENAI_ENDPOINT，Azure OpenAI 功能不可用")
    elif Config.AI_PROVIDER == "gemini":
        if Config.GEMINI_API_KEY:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            logger.info(f"AI 提供商: Gemini (模型: {Config.GEMINI_MODEL})")
        else:
            logger.warning("未配置 GEMINI_API_KEY，Gemini 功能不可用")
    else:
        raise ValueError(f"无效的 AI_PROVIDER: {Config.AI_PROVIDER}")

    if client is None:
        # 便于测试 patch：client.chat.completions.create
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda *a, **k: None)))

    return client


MAX_RETRIES = 2
RETRY_DELAY = 1


async def call_ai_with_retry_async(prompt: str, temperature: float) -> str:
    if Config.AI_PROVIDER == "gemini":
        model_name = Config.GEMINI_MODEL
    elif Config.AI_PROVIDER == "azure_openai":
        model_name = Config.AZURE_OPENAI_DEPLOYMENT
    else:
        model_name = Config.OPENAI_MODEL

    for attempt in range(MAX_RETRIES + 1):
        try:
            if Config.AI_PROVIDER == "gemini":
                model = genai.GenerativeModel(model_name)
                generation_config = genai.types.GenerationConfig(
                    max_output_tokens=Config.MAX_TOKENS, temperature=temperature
                )

                def _generate_content():
                    return model.generate_content(prompt, generation_config=generation_config)

                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(None, _generate_content)
                if not getattr(response, "candidates", None) or not response.candidates[0].content.parts:
                    raise ValueError("API 返回空内容")
                return "".join(part.text for part in response.candidates[0].content.parts).strip()

            # openai / azure_openai
            if client is None:
                raise ValueError(f"{Config.AI_PROVIDER} 客户端不可用")

            if Config.AI_PROVIDER == "azure_openai":
                resp = client.chat.completions.create(
                    model=model_name,
                    temperature=temperature,
                    max_completion_tokens=Config.MAX_TOKENS,
                    messages=[{"role": "user", "content": prompt}],
                )
            else:
                resp = client.chat.completions.create(
                    model=model_name,
                    temperature=temperature,
                    max_tokens=Config.MAX_TOKENS,
                    messages=[{"role": "user", "content": prompt}],
                )

            response = await resp if inspect.isawaitable(resp) else resp

            try:
                return response.choices[0].message.content.strip()
            except Exception:
                if isinstance(response, str):
                    return response.strip()
                content = getattr(response, "content", None)
                if isinstance(content, str):
                    return content.strip()
                return ""

        except (ConnectionError, TimeoutError, ValueError) as e:
            logger.warning(f"AI 调用失败 (尝试 {attempt + 1}/{MAX_RETRIES + 1}): {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise
        except Exception as e:
            logger.warning(f"AI 调用失败 (尝试 {attempt + 1}/{MAX_RETRIES + 1}): {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise


def call_ai_with_retry(prompt: str, temperature: float) -> str:
    return asyncio.run(call_ai_with_retry_async(prompt, temperature))


# -------------------------
# External DB + cache
# -------------------------

cache: Optional[Cache] = Cache(Config.CACHE_EXPIRATION) if Config.ENABLE_CACHE else None

rate_limiter: Optional[RateLimiter] = None
if Config.ENABLE_RATE_LIMIT:
    rate_limiter = RateLimiter(max_requests=Config.RATE_LIMIT_MAX_REQUESTS, time_window=Config.RATE_LIMIT_TIME_WINDOW)

external_db: Optional[ExternalDatabase] = None


def get_external_db(request: Request) -> Optional[ExternalDatabase]:
    global external_db

    if external_db is None and Config.ENABLE_EXTERNAL_DATABASE and not getattr(request.app.state, "testing", False):
        external_db = ExternalDatabase(get_default_databases(), timeout=Config.EXTERNAL_DATABASE_TIMEOUT)
        logger.info("外部题库查询已启用")
    return external_db


# -------------------------
# DB operations
# -------------------------

async def save_qa_record_async(
    question: str,
    question_type: str,
    options: str,
    answer: str,
    context: str = "",
    raw_ai_response: str = "",
    model: str = "",
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            record = QARecord(
                question=question,
                type=question_type,
                options=options,
                answer=answer,
                context=context,
                raw_ai_response=raw_ai_response,
                model=model,
            )
            session.add(record)
            await session.commit()
    except Exception as e:
        logger.error(f"保存问答记录失败: {e}")


async def count_qa_records(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(QARecord))
    return int(result.scalar() or 0)


# -------------------------
# FastAPI app
# -------------------------

metrics = Metrics()
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # startup
    init_ai_client()
    try:
        await init_db_async()
        logger.info("数据库表(异步)初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")

    # 测试用例可能在创建 TestClient 前设置 app.state.testing=True
    if not hasattr(app.state, "testing"):
        app.state.testing = False
    yield

    # shutdown
    # 当前 ExternalDatabase 未强制持有长连接，无需关闭


app = FastAPI(
    title="EduBrain AI Answer Service",
    version=VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS - 允许所有跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # 当 allow_origins=["*"] 时，credentials 必须为 False
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Static + Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# 请求日志中间件 - 将URL编码转换为可读中文
@app.middleware("http")
async def log_requests_readable(request: Request, call_next):
    """将请求日志转换为可读的中文格式"""
    start = time.time()
    method = request.method
    path = request.url.path
    
    # 跳过静态文件和favicon请求
    if path.startswith("/static") or path == "/favicon.ico":
        return await call_next(request)
    
    # 对 /api/search 的 GET 请求使用特殊格式
    if path == "/api/search" and method == "GET":
        query_string = str(request.url.query)
        
        if query_string:
            # 解码 URL 参数
            decoded_query = unquote(query_string)
            params = parse_qs(decoded_query)
            
            # 提取关键参数
            title = params.get('title', [''])[0][:80]  # 截取前80字符
            qtype = params.get('type', ['未知'])[0]
            
            # 题型映射
            type_map = {
                'single': '单选题',
                'multiple': '多选题', 
                'judgement': '判断题',
                'completion': '填空题',
                'short_answer': '简答题'
            }
            qtype_cn = type_map.get(qtype, qtype)
            
            print(f"\n{'='*60}")
            print(f"[收到请求] [{method}] /api/search")
            print(f"[题目] {title}{'...' if len(params.get('title', [''])[0]) > 80 else ''}")
            print(f"[题型] {qtype_cn}")
            print(f"{'='*60}")
        
        response = await call_next(request)
        # 不在这里打印完成信息，由处理函数打印详细的答案信息
        return response
    
    # 其他请求：先记录收到请求
    if path.startswith("/api"):
        print(f"[请求] [{method}] {path}")
    
    response = await call_next(request)
    elapsed = time.time() - start
    
    # 记录响应
    if path.startswith("/api"):
        status = response.status_code
        print(f"[响应] [{method}] {path} - {status} - {elapsed:.3f}s")
    
    return response


# -------------------------
# Pages
# -------------------------

# 健康检查（支持 HEAD 请求，用于 OCS 探测服务是否在线）
@app.head("/")
@app.head("/api/search")
async def head_check():
    return Response(status_code=200)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    # 统计信息走前端异步拉取，这里只返回页面
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/docs", response_class=HTMLResponse)
async def docs_page(request: Request):
    return templates.TemplateResponse("docs.html", {"request": request})


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


# -------------------------
# API endpoints
# -------------------------

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "version": VERSION,
        "ai_provider": Config.AI_PROVIDER,
        "model": Config.GEMINI_MODEL if Config.AI_PROVIDER == "gemini" else Config.OPENAI_MODEL,
    }


@app.get("/api/stats")
async def get_stats(request: Request, _: None = Depends(require_token)):
    async with AsyncSessionLocal() as session:
        try:
            qa_records_count = await count_qa_records(session)
        except Exception:
            qa_records_count = 0

    cache_hit_rate = cache.get_hit_rate() if (Config.ENABLE_CACHE and cache) else 0.0

    return {
        "version": VERSION,
        "uptime": time.time() - start_time,
        "ai_provider": Config.AI_PROVIDER,
        "model": (
            Config.GEMINI_MODEL if Config.AI_PROVIDER == "gemini"
            else Config.AZURE_OPENAI_DEPLOYMENT if Config.AI_PROVIDER == "azure_openai"
            else Config.OPENAI_MODEL
        ),
        "cache_enabled": Config.ENABLE_CACHE,
        "cache_size": cache.get_size() if (Config.ENABLE_CACHE and cache) else 0,
        "qa_records_count": qa_records_count,
        "rate_limit_enabled": Config.ENABLE_RATE_LIMIT,
        "input_validation_enabled": Config.ENABLE_INPUT_VALIDATION,
        "external_database_enabled": Config.ENABLE_EXTERNAL_DATABASE,
        # 新增实时指标
        "request_count": metrics.request_count,
        "avg_latency_ms": round(metrics.avg_latency_sec * 1000, 2),
        "cache_hit_rate": round(cache_hit_rate, 2),
    }


@app.get("/api/cache/stats")
async def get_cache_stats(request: Request, _: None = Depends(require_token)):
    if not Config.ENABLE_CACHE or cache is None:
        return {"success": False, "message": "缓存未启用或未初始化"}

    try:
        stats = cache.get_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"获取缓存统计信息失败: {e}")
        return JSONResponse({"success": False, "message": "获取统计信息失败"}, status_code=500)


@app.post("/api/cache/clear")
async def clear_cache(request: Request, _: None = Depends(require_token)):
    if not Config.ENABLE_CACHE or cache is None:
        return {"success": True, "code": 1, "message": "缓存未启用"}

    try:
        cache.clear()
        return {"success": True, "code": 1, "message": "缓存已清空"}
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        return JSONResponse({"success": False, "message": "清除缓存失败"}, status_code=500)


@app.get("/api/qa-records")
async def get_qa_records(
    request: Request,
    page: int = 1,
    per_page: int = 10,
    q: str = "",
    _: None = Depends(require_token),
):
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 10

    offset = (page - 1) * per_page

    async with AsyncSessionLocal() as session:
        try:
            stmt = select(QARecord)
            if q:
                # SQLite 兼容：使用 contains 进行模糊匹配
                stmt = stmt.where(QARecord.question.contains(q))

            count_stmt = select(func.count()).select_from(stmt.subquery())
            count_result = await session.execute(count_stmt)
            total_count = int(count_result.scalar() or 0)

            result = await session.execute(stmt.order_by(QARecord.time.desc()).offset(offset).limit(per_page))
            records = result.scalars().all()

            records_data = [
                {
                    "id": r.id,
                    "question": r.question,
                    "answer": r.answer,
                    "question_type": r.type,
                    "timestamp": r.time.isoformat() if r.time is not None else None,
                    "ai_provider": "unknown",
                    "model": r.model,
                }
                for r in records
            ]

            return {
                "success": True,
                "records": records_data,
                "total_count": total_count,
                "page": page,
                "per_page": per_page,
                "total_pages": (total_count + per_page - 1) // per_page,
            }
        except Exception as e:
            logger.error(f"查询问答记录失败: {e}")
            return JSONResponse({"success": False, "message": "查询失败"}, status_code=500)


@app.post("/api/qa-records/clear")
async def clear_qa_records(request: Request, _: None = Depends(require_token)):
    async with AsyncSessionLocal() as session:
        try:
            count_before = await count_qa_records(session)
            await session.execute(QARecord.__table__.delete())
            await session.commit()
            return {
                "success": True,
                "message": f"成功清除 {count_before} 条问答记录",
                "cleared_count": count_before,
            }
        except Exception as e:
            await session.rollback()
            logger.error(f"清除问答记录失败: {e}")
            return JSONResponse({"success": False, "message": "清除失败"}, status_code=500)


@app.get("/api/external-databases")
async def get_external_databases(request: Request, _: None = Depends(require_token)):
    try:
        databases = get_default_databases()
        return {
            "success": True,
            "enabled": Config.ENABLE_EXTERNAL_DATABASE,
            "databases": databases,
            "count": len(databases),
        }
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.post("/api/external-databases/test")
async def test_external_database(request: Request, _: None = Depends(require_token)):
    if not Config.ENABLE_EXTERNAL_DATABASE:
        return JSONResponse({"success": False, "message": "外部题库功能未启用"}, status_code=400)

    data = {}
    if request.headers.get("content-type", "").lower().startswith("application/json"):
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    title = data.get("title", "")
    options = data.get("options", "")
    question_type = data.get("type", "")

    if not title:
        return JSONResponse({"success": False, "message": "请提供测试题目"}, status_code=400)

    ext_db = get_external_db(request)
    if not ext_db:
        return JSONResponse({"success": False, "message": "外部题库未初始化"}, status_code=400)

    try:
        found, q, a = await ext_db.query_all_databases(title, options, question_type)
        return {
            "success": True,
            "found": found,
            "question": q,
            "answer": a,
            "message": "外部题库查询成功" if found else "未找到答案",
        }
    except Exception as e:
        logger.error(f"测试外部题库时出错: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": f"查询失败: {str(e)}"}, status_code=500)


@app.api_route("/api/search", methods=["GET", "POST"])
async def search(request: Request, background_tasks: BackgroundTasks):
    start_req_time = time.time()

    if not verify_access_token(request):
        return JSONResponse({"code": 0, "msg": "无效的访问令牌"}, status_code=403)

    # 速率限制
    if Config.ENABLE_RATE_LIMIT and rate_limiter:
        client_ip = _get_client_ip(request)
        allowed, rate_limit_msg = rate_limiter.is_allowed(client_ip)
        if not allowed:
            return JSONResponse({"code": 0, "msg": rate_limit_msg}, status_code=429)

    try:
        # 统一处理 GET/POST
        data: Dict[str, Any]
        if request.method == "POST":
            ctype = request.headers.get("content-type", "").lower()
            if ctype.startswith("application/json"):
                data = await request.json()
            else:
                form = await request.form()
                data = dict(form)
        else:
            data = dict(request.query_params)

        raw_question = data.get("title", "")
        question_type = data.get("type", "")
        options = normalize_text(data.get("options", ""))
        context = normalize_text(data.get("context"))

        if not raw_question:
            return {"code": 0, "msg": "未提供问题内容"}

        # 输入验证
        if Config.ENABLE_INPUT_VALIDATION:
            valid, error_msg = InputValidator.validate_question(raw_question)
            if not valid:
                return {"code": 0, "msg": error_msg}

            valid, error_msg = InputValidator.validate_type(question_type)
            if not valid:
                return {"code": 0, "msg": error_msg}

            valid, error_msg = InputValidator.validate_options(options)
            if not valid:
                return {"code": 0, "msg": error_msg}

            valid, error_msg = InputValidator.validate_context(context)
            if not valid:
                return {"code": 0, "msg": error_msg}

        # 阅读理解
        if "reading comprehension" in raw_question.lower() or "阅读题" in raw_question:
            logger.info("检测到阅读理解题，启用专用解析器。")
            context, question, options = parse_reading_comprehension(raw_question)
            question_type = "single"
        else:
            question = normalize_text(raw_question)

        # 弹性适应：options 为空
        if not options and question_type in ["single", "multiple"]:
            context = question

        # 缓存
        if Config.ENABLE_CACHE and cache:
            cached_response = cache.get(question, question_type, options)
            if cached_response:
                latency = time.time() - start_req_time
                metrics.record(latency)
                return cached_response

        # 外部题库优先（直接使用外部题库答案，不进行选项匹配验证）
        if Config.ENABLE_EXTERNAL_DATABASE:
            ext_db = get_external_db(request)
            if ext_db:
                try:
                    found, ext_question, ext_answer = await ext_db.query_all_databases(question, options, question_type)
                    if found and ext_answer and not ext_db._is_not_found_answer(ext_answer):
                        logger.info(f"外部题库查询成功 - 直接使用外部题库答案")
                        
                        # 预处理外部答案（处理 JSON 数组格式、answer= 前缀等）
                        ext_answer = _preprocess_external_answer(ext_answer)
                        
                        # 使用 OCS 兼容清理函数处理答案（格式化，不做验证）
                        cleaned_answer = _clean_answer_for_ocs(ext_answer, question_type, options)
                        
                        external_question = ext_question or question

                        latency = time.time() - start_req_time
                        metrics.record(latency)

                        # --- Console Logging for External DB ---
                        print(f"\n{'─'*60}")
                        print(f"[外部题库命中]")
                        print(f"[耗时] {latency:.2f} 秒")
                        print(f"[答案] {cleaned_answer}")
                        print(f"{'─'*60}\n")
                        # ----------------------------------------

                        background_tasks.add_task(
                            save_qa_record_async,
                            external_question,
                            question_type,
                            options,
                            cleaned_answer,
                            context,
                            "",
                            "external_db",
                        )

                        response_data = format_answer_for_ocs(external_question, cleaned_answer, latency)
                        if Config.ENABLE_CACHE and cache:
                            background_tasks.add_task(cache.set, external_question, response_data, question_type, options)

                        return response_data
                    else:
                        logger.info("外部题库未找到匹配答案，将使用 AI 搜索")
                except Exception as e:
                    logger.warning(f"外部题库查询失败: {e}")

        # AI 搜索
        url = data.get("url", "")
        platform = ""
        if "chaoxing.com" in url or "erya" in url:
            platform = "chaoxing"
        elif "zhihuishu.com" in url:
            platform = "zhihuishu"
        elif "icourse163.org" in url:
            platform = "mooc"
        elif "icve.com.cn" in url:
            platform = "icve"

        prompt = build_prompt(question, question_type, options, context, platform=platform)
        final_answer_raw = await call_ai_with_retry_async(prompt, 1.0)
        processed_answer = extract_answer(final_answer_raw, question_type, options)

        if not processed_answer:
            return {"code": 0, "msg": "AI 返回的答案为空，请重试"}

        latency = time.time() - start_req_time
        metrics.record(latency)

        # --- Console Logging for User Visibility ---
        print(f"\n{'─'*60}")
        print(f"[AI 回答完成]")
        print(f"[耗时] {latency:.2f} 秒")
        print(f"[答案] {processed_answer}")
        print(f"{'─'*60}\n")
        # -------------------------------------------

        model_name = Config.GEMINI_MODEL if Config.AI_PROVIDER == "gemini" else Config.OPENAI_MODEL

        background_tasks.add_task(
            save_qa_record_async,
            question,
            question_type,
            options,
            processed_answer,
            context,
            final_answer_raw,
            model_name,
        )

        response_data = format_answer_for_ocs(question, processed_answer, latency)
        if Config.ENABLE_CACHE and cache:
            background_tasks.add_task(cache.set, question, response_data, question_type, options)

        return response_data

    except (ValueError, TypeError) as e:
        logger.error(f"请求参数错误: {e}")
        return {"code": 0, "msg": "请求参数格式错误"}
    except Exception as e:
        logger.error(f"处理问题时发生严重错误: {e}", exc_info=True)
        return {"code": 0, "msg": "服务内部错误，请稍后重试"}


@app.get("/api/logs/stream")
async def stream_logs(request: Request):
    """Server-Sent Events: 持续推送日志新增行（无需token验证，便于dashboard访问）。"""

    log_file = _get_today_log_file()

    async def event_generator():
        last_size = 0
        # 发送初始连接成功消息
        yield {"data": "[系统] 日志流连接成功"}
        
        while True:
            if await request.is_disconnected():
                break

            try:
                if os.path.exists(log_file):
                    size = os.path.getsize(log_file)
                    if size < last_size:
                        last_size = 0
                    if size > last_size:
                        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                            f.seek(last_size)
                            chunk = f.read()
                            last_size = f.tell()
                        for line in chunk.splitlines():
                            if line.strip():
                                yield {"data": line}
            except Exception:
                pass

            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host=Config.HOST, 
        port=Config.PORT, 
        reload=Config.DEBUG,
        access_log=False,  # 禁用原始访问日志，使用自定义中文日志
        log_level="warning"  # 只显示警告和错误
    )
