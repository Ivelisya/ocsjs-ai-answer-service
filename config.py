# -*- coding: utf-8 -*-
"""
配置文件
"""
import os

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


# 基础配置
class Config:
    # 服务配置
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

    # OpenAI配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    # OpenAI API Base URL，如果不设置则使用默认值
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

    # AI 提供商配置 (openai 或 gemini)
    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()

    # 验证 AI 提供商
    SUPPORTED_AI_PROVIDERS = ["openai", "gemini"]
    if AI_PROVIDER not in SUPPORTED_AI_PROVIDERS:
        raise ValueError(f"不支持的 AI 提供商: '{AI_PROVIDER}'. 支持的提供商包括: {SUPPORTED_AI_PROVIDERS}")

    # Gemini 配置
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    # 使用稳定版本而不是预览版本
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    @classmethod
    def validate_config(cls):
        """验证配置的有效性"""
        errors = []

        # 检查AI提供商配置
        if cls.AI_PROVIDER not in cls.SUPPORTED_AI_PROVIDERS:
            errors.append(f"不支持的AI提供商: '{cls.AI_PROVIDER}'，支持的提供商: {cls.SUPPORTED_AI_PROVIDERS}")

        # 检查API密钥配置
        if cls.AI_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            errors.append("使用OpenAI时必须设置OPENAI_API_KEY环境变量")
        elif cls.AI_PROVIDER == "gemini" and not cls.GEMINI_API_KEY:
            errors.append("使用Gemini时必须设置GEMINI_API_KEY环境变量")

        # 检查端口范围
        if not (1 <= cls.PORT <= 65535):
            errors.append(f"端口号必须在1-65535之间，当前值: {cls.PORT}")

        # 检查缓存过期时间
        if cls.CACHE_EXPIRATION < 0:
            errors.append(f"缓存过期时间不能为负数，当前值: {cls.CACHE_EXPIRATION}")

        # 检查速率限制参数
        if cls.ENABLE_RATE_LIMIT:
            if cls.RATE_LIMIT_MAX_REQUESTS <= 0:
                errors.append(f"速率限制最大请求数必须大于0，当前值: {cls.RATE_LIMIT_MAX_REQUESTS}")
            if cls.RATE_LIMIT_TIME_WINDOW <= 0:
                errors.append(f"速率限制时间窗口必须大于0，当前值: {cls.RATE_LIMIT_TIME_WINDOW}")

        # 检查外部数据库超时时间
        if cls.EXTERNAL_DATABASE_TIMEOUT <= 0:
            errors.append(f"外部数据库超时时间必须大于0，当前值: {cls.EXTERNAL_DATABASE_TIMEOUT}")

        if errors:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_msg)

        return True

    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # 安全配置（可选）
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", None)

    # 响应配置
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 100000))
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))

    # 缓存配置
    ENABLE_CACHE = os.getenv("ENABLE_CACHE", "True").lower() == "true"
    CACHE_EXPIRATION = int(os.getenv("CACHE_EXPIRATION", 86400))  # 默认缓存24小时
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # 数据库配置
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db/dev.db")  # 默认使用SQLite方便开发

    # 安全功能配置（可选）
    ENABLE_RATE_LIMIT = os.getenv("ENABLE_RATE_LIMIT", "False").lower() == "true"
    ENABLE_INPUT_VALIDATION = os.getenv("ENABLE_INPUT_VALIDATION", "False").lower() == "true"
    
    # 外部题库配置（可选）
    ENABLE_EXTERNAL_DATABASE = os.getenv("ENABLE_EXTERNAL_DATABASE", "True").lower() == "true"
    EXTERNAL_DATABASE_TIMEOUT = int(os.getenv("EXTERNAL_DATABASE_TIMEOUT", 10))  # 查询超时时间（秒）
    
    # 速率限制配置
    RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", 100))
    RATE_LIMIT_TIME_WINDOW = int(os.getenv("RATE_LIMIT_TIME_WINDOW", 3600))
