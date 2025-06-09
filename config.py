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
    OPENAI_API_BASE = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')

    # AI 提供商配置 (openai 或 gemini)
    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()

    # 验证 AI 提供商
    SUPPORTED_AI_PROVIDERS = ["openai", "gemini"]
    if AI_PROVIDER not in SUPPORTED_AI_PROVIDERS:
        raise ValueError(f"不支持的 AI 提供商: '{AI_PROVIDER}'. 支持的提供商包括: {SUPPORTED_AI_PROVIDERS}")

    # Gemini 配置
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")
    
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