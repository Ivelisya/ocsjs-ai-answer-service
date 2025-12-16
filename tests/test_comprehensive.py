import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from main import app, call_ai_with_retry_async
from utils import extract_answer, parse_reading_comprehension
from validators import InputValidator
from config import Config
import asyncio

@pytest.fixture
def client():
    """测试客户端"""
    app.state.testing = True
    # 取消速率限制以便测试
    with patch.object(Config, 'ENABLE_RATE_LIMIT', False):
        with TestClient(app) as client:
            yield client

@pytest.fixture
def mock_cache():
    """模拟缓存"""
    with patch('main.cache') as mock:
        yield mock

class TestEmptyQuestionType:
    """测试空问题类型场景"""

    @patch('main.call_ai_with_retry_async')
    def test_search_with_empty_type(self, mock_ai_call, client):
        """测试空问题类型的情况"""
        # 模拟异步返回
        async def mock_return(*args, **kwargs):
            return "<answer>测试答案</answer>"
        mock_ai_call.side_effect = mock_return

        response = client.get('/api/search', params={'title': '你是谁', 'type': '', 'options': ''})
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 1
        assert 'answer' in data
        
        mock_ai_call.assert_called_once()
    
    @patch('main.call_ai_with_retry_async')
    def test_search_with_auto_detect_type(self, mock_ai_call, client):
        """测试自动识别类型（前端发送空字符串）"""
        async def mock_return(*args, **kwargs):
            return "<answer>正确</answer>"
        mock_ai_call.side_effect = mock_return

        response = client.get('/api/search', params={'title': '1+1等于2吗', 'type': '', 'options': ''})
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 1

class TestQuestionTypeHandling:
    """测试不同问题类型的处理"""

    @patch('main.call_ai_with_retry_async')
    def test_judgement_type(self, mock_ai_call, client):
        """测试判断题类型"""
        async def mock_return(*args, **kwargs):
            return "<answer>正确</answer>"
        mock_ai_call.side_effect = mock_return

        response = client.get('/api/search', params={'title': '1+1等于2吗', 'type': 'judgement', 'options': ''})
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 1
        assert data['answer'] == '正确'

    @patch('main.call_ai_with_retry_async')
    def test_single_choice_type(self, mock_ai_call, client):
        """测试单选题类型"""
        async def mock_return(*args, **kwargs):
            return "<answer>A. 北京</answer>"
        mock_ai_call.side_effect = mock_return

        response = client.get('/api/search', params={'title': '中国的首都是哪里', 'type': 'single', 'options': 'A. 北京\nB. 上海'})
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 1
        assert '北京' in data['answer']

    @patch('main.call_ai_with_retry_async')
    def test_multiple_choice_type(self, mock_ai_call, client):
        """测试多选题类型"""
        async def mock_return(*args, **kwargs):
            return "<answer>A. 选项1#B. 选项2</answer>"
        mock_ai_call.side_effect = mock_return

        response = client.get('/api/search', params={
            'title': '选择正确的选项',
            'type': 'multiple',
            'options': 'A. 选项1\nB. 选项2\nC. 选项3'
        })
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 1

class TestFrontendIntegration:
    """测试前端集成场景"""

    @patch('main.call_ai_with_retry_async')
    def test_frontend_form_submission_empty_type(self, mock_ai_call, client):
        """测试前端表单提交空类型（自动识别）"""
        async def mock_return(*args, **kwargs):
            return "<answer>我是AI助手</answer>"
        mock_ai_call.side_effect = mock_return

        # FastAPI TestClient data 参数发送 form-urlencoded
        response = client.post('/api/search', data={
            'title': '你是谁',
            'type': '',
            'options': '',
            'context': ''
        })
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 1

    @patch('main.call_ai_with_retry_async')
    def test_frontend_form_with_options(self, mock_ai_call, client):
        """测试前端表单带选项的提交"""
        async def mock_return(*args, **kwargs):
            return "<answer>A. 选项1</answer>"
        mock_ai_call.side_effect = mock_return

        response = client.post('/api/search', data={
            'title': '选择正确的答案',
            'type': 'single',
            'options': 'A. 选项1\nB. 选项2\nC. 选项3',
            'context': '这是一个测试题目'
        })
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 1

class TestErrorHandling:
    """测试错误处理场景"""

    def test_search_without_title(self, client):
        """测试没有提供标题的情况"""
        # FastAPI 会将 query params 自动解析
        response = client.get('/api/search')
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert '未提供问题内容' in data['msg']

    @patch('main.call_ai_with_retry_async')
    def test_ai_call_failure(self, mock_ai_call, client):
        """测试AI调用失败的情况"""
        mock_ai_call.side_effect = Exception("AI服务不可用")

        response = client.get('/api/search', params={'title': '测试问题', 'type': 'single'})
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert '服务内部错误' in data['msg']

class TestCacheIntegration:
    """测试缓存集成"""

    @patch('main.cache')
    @patch('main.call_ai_with_retry_async')
    def test_cache_hit(self, mock_ai_call, mock_cache, client):
        """测试缓存命中的情况"""
        mock_cache.get.return_value = {"code": 1, "answer": "缓存的答案", "question": "测试问题"}
        
        with patch.object(Config, 'ENABLE_CACHE', True):
             response = client.get('/api/search', params={'title': '测试问题', 'type': 'single'})
             assert response.status_code == 200
             data = response.json()
             assert data['code'] == 1
             assert data['answer'] == '缓存的答案'
             mock_ai_call.assert_not_called()

    @patch('main.cache')
    @patch('main.call_ai_with_retry_async')
    def test_cache_miss(self, mock_ai_call, mock_cache, client):
        """测试缓存未命中的情况"""
        mock_cache.get.return_value = None
        
        async def mock_return(*args, **kwargs):
            return "<answer>新的答案</answer>"
        mock_ai_call.side_effect = mock_return

        with patch.object(Config, 'ENABLE_CACHE', True):
            response = client.get('/api/search', params={'title': '测试问题', 'type': 'single'})
            assert response.status_code == 200
            data = response.json()
            assert data['code'] == 1
            assert data['answer'] == '新的答案'
            
            # 缓存 set 是 background task

class TestExternalDatabase:
    """测试外部题库功能"""

    @patch('main.get_external_db')
    @patch('main.call_ai_with_retry_async')
    def test_external_db_hit(self, mock_ai_call, mock_get_external_db, client):
        """测试外部题库命中的情况"""
        mock_external_db = Mock()
        # 防止 fall-through 导致 crash
        async def mock_return(*args, **kwargs):
             return "<answer>AI fallback answer</answer>"
        mock_ai_call.side_effect = mock_return
        
        # 使用 AsyncMock 模拟异步方法
        mock_external_db.query_all_databases = AsyncMock(return_value=(True, "测试问题", "测试答案"))
        mock_external_db._is_not_found_answer.return_value = False
        mock_get_external_db.return_value = mock_external_db

        with patch.object(Config, 'ENABLE_EXTERNAL_DATABASE', True):
            response = client.get('/api/search', params={'title': '测试问题', 'type': 'single'})
            assert response.status_code == 200
            data = response.json()
            assert data['code'] == 1
            assert data['answer'] == '测试答案'
            mock_ai_call.assert_not_called()

class TestRateLimiting:
    """测试速率限制功能"""

    @patch('main.rate_limiter')
    def test_rate_limit_exceeded(self, mock_rate_limiter, client):
        """测试超出速率限制的情况"""
        mock_rate_limiter.is_allowed.return_value = (False, "请求过于频繁")
        
        with patch.object(Config, 'ENABLE_RATE_LIMIT', True):
            response = client.get('/api/search', params={'title': '测试问题', 'type': 'single'})
            assert response.status_code == 429
            data = response.json()
            assert data['code'] == 0
            assert '请求过于频繁' in data['msg']

class TestInputValidation:
    """测试输入验证"""

    def test_validate_question_too_long(self, client):
        """测试问题内容过长的情况"""
        with patch.object(Config, 'ENABLE_INPUT_VALIDATION', True):
            long_question = "测试问题" * 2000 # 8000 chars > 5000 max
            response = client.post('/api/search', data={
                'title': long_question,
                'type': 'single'
            })
            assert response.status_code == 200
            data = response.json()
            assert data['code'] == 0
            assert '超过最大长度限制' in data['msg']

if __name__ == '__main__':
    pytest.main([__file__])
