import pytest
import json
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from main import app, call_ai_with_retry_async
from utils import extract_answer
from config import Config
import asyncio

@pytest.fixture
def client():
    """测试客户端"""
    # 显式设置测试模式，避免 lifespan 中初始化外部资源
    app.state.testing = True
    with TestClient(app) as client:
        yield client

class TestUtils:
    """测试工具函数"""
    # format_answer_for_ocs, extract_answer 等工具函数测试与框架无关，直接保留逻辑即可
    
    def test_extract_answer_simple(self):
        """测试简单答案提取"""
        ai_response = "答案：北京"
        result = extract_answer(ai_response, "single")
        assert result == "北京"

    def test_extract_answer_with_tags(self):
        """测试带标签的答案提取"""
        ai_response = "一些思考<answer>上海</answer>其他内容"
        result = extract_answer(ai_response, "single")
        assert result == "上海"

class TestAPI:
    """测试API端点"""

    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert 'version' in data

    def test_search_endpoint_missing_title(self, client):
        """测试搜索端点缺少标题"""
        # FastAPI 会将 query params 校验失败返回 422 还是业务逻辑校验返回 200?
        # 根据 main.py 代码：
        # raw_question = data.get("title", "")
        # if not raw_question: return {"code": 0, "msg": "未提供问题内容"}
        # 所以应该是 200 OK + code 0
        response = client.get('/api/search')
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert '未提供问题内容' in data['msg']

    @patch('main.call_ai_with_retry_async')
    def test_search_endpoint_success(self, mock_ai_call, client):
        """测试搜索端点成功情况"""
        # 模拟异步调用返回值
        async def mock_return(*args, **kwargs):
            return "<answer>北京</answer>"
        
        mock_ai_call.side_effect = mock_return

        response = client.get('/api/search?title=中国的首都是哪里&type=single&options=A.北京')
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 1
        assert data['answer'] == '北京'

    def test_cache_clear_endpoint(self, client):
        """测试缓存清除端点"""
        # 注意：需要 verify_access_token=False 或者 mock token
        # main.py 中 clear_cache 依赖 require_token
        # require_token 检查 app.state.testing，如果为 True 则跳过 token 检查
        # client fixture 中已设置 app.state.testing = True
        response = client.post('/api/cache/clear')
        assert response.status_code == 200
        data = response.json()
        # 如果缓存未启用(message="缓存未启用")，success 也可能为 True(code=1)
        # 只要返回 JSON 且 status 200 即可
        assert 'success' in data

@pytest.mark.asyncio
class TestAICall:
    """测试AI调用功能"""

    @patch('main.client')
    async def test_openai_call_success(self, mock_client):
        """测试OpenAI调用成功 (模拟异步)"""
        # 构造 Mock 响应结构
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "测试答案"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        # 模拟 create 方法返回 awaitable
        async def mock_create(*args, **kwargs):
            return mock_response
            
        mock_client.chat.completions.create.side_effect = mock_create

        with patch.object(Config, 'AI_PROVIDER', 'openai'):
            result = await call_ai_with_retry_async("测试提示", 0.7)
            assert result == "测试答案"

    @patch('main.genai.GenerativeModel')
    async def test_gemini_call_success(self, mock_model_class):
        """测试Gemini调用成功"""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock()]
        mock_response.candidates[0].content.parts[0].text = "测试答案"

        # main.py 中 gemini 调用使用了 loop.run_in_executor
        # 我们 mock model.generate_content (同步方法)
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        with patch.object(Config, 'AI_PROVIDER', 'gemini'):
            result = await call_ai_with_retry_async("测试提示", 0.7)
            assert result == "测试答案"

if __name__ == '__main__':
    pytest.main([__file__])
