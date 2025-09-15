#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EduBrain AI API 测试脚本
"""
import requests
import json
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_api_endpoint(base_url: str = "http://localhost:5000"):
    """测试API端点"""

    test_questions = [
        {
            "title": "Python中如何定义一个函数？",
            "type": "single",
            "options": "A. function myFunc()\nB. def myFunc()\nC. func myFunc()\nD. define myFunc()"
        },
        {
            "title": "以下哪些是Python的关键字？",
            "type": "multiple",
            "options": "A. if\nB. then\nC. else\nD. for"
        },
        {
            "title": "Python支持多线程编程",
            "type": "judgement",
            "options": ""
        }
    ]

    logger.info("🚀 开始测试 EduBrain AI API...")
    logger.info(f"📡 目标地址: {base_url}")
    logger.info("=" * 50)

    for i, question in enumerate(test_questions, 1):
        logger.info(f"🔍 测试题目 {i}:")
        logger.info(f"题目: {question['title']}")

        try:
            # 发送请求
            response = requests.post(
                f"{base_url}/api/search",
                json=question,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            logger.info(f"状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                logger.info("✅ 请求成功")
                if result.get("code") == 0:
                    logger.error(f"❌ 业务错误: {result.get('msg', '未知错误')}")
                else:
                    logger.info("📝 AI回答:")
                    logger.info(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                logger.error(f"❌ HTTP错误: {response.text}")

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 网络错误: {str(e)}")
        except Exception as e:
            logger.error(f"❌ 其他错误: {str(e)}")

        time.sleep(1)  # 避免请求过于频繁

    logger.info("🎉 API测试完成!")

if __name__ == "__main__":
    test_api_endpoint()
