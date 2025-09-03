import pytest
import json
from unittest.mock import Mock, patch
from app import app, call_ai_with_retry
from utils import Cache, format_answer_for_ocs, extract_answer
from config import Config

@pytest.fixture
def client():
    """测试客户端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_cache():
    """模拟缓存"""
    return Mock(spec=Cache)

class TestUtils:
    """测试工具函数"""

    def test_format_answer_for_ocs(self):
        """测试答案格式化"""
        result = format_answer_for_ocs("测试问题", "测试答案")
        expected = {
            'code': 1,
            'question': '测试问题',
            'answer': '测试答案'
        }
        assert result == expected

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

    def test_cache_operations(self, mock_cache):
        """测试缓存操作"""
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None

        # 测试缓存未命中
        result = mock_cache.get("问题", "single", "选项")
        assert result is None

        # 测试缓存设置
        mock_cache.set("问题", "答案", "single", "选项")
        mock_cache.set.assert_called_once_with("问题", "答案", "single", "选项")

class TestAPI:
    """测试API端点"""

    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert 'version' in data

    def test_search_endpoint_missing_title(self, client):
        """测试搜索端点缺少标题"""
        response = client.get('/api/search')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 0
        assert '未提供问题内容' in data['msg']

    @patch('app.call_ai_with_retry')
    def test_search_endpoint_success(self, mock_ai_call, client):
        """测试搜索端点成功情况"""
        mock_ai_call.return_value = "<answer>北京</answer>"

        response = client.get('/api/search?title=中国的首都是哪里&type=single&options=A.北京')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 1
        assert data['answer'] == '北京'

    def test_cache_clear_endpoint(self, client):
        """测试缓存清除端点"""
        response = client.post('/api/cache/clear')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

class TestAICall:
    """测试AI调用功能"""

    @patch('app.client.chat.completions.create')
    def test_openai_call_success(self, mock_create):
        """测试OpenAI调用成功"""
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "测试答案"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_create.return_value = mock_response

        with patch.object(Config, 'AI_PROVIDER', 'openai'):
            result = call_ai_with_retry("测试提示", 0.7)
            assert result == "测试答案"

    @patch('app.genai.GenerativeModel')
    def test_gemini_call_success(self, mock_model_class):
        """测试Gemini调用成功"""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock()]
        mock_response.candidates[0].content.parts[0].text = "测试答案"

        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        with patch.object(Config, 'AI_PROVIDER', 'gemini'):
            result = call_ai_with_retry("测试提示", 0.7)
            assert result == "测试答案"

if __name__ == '__main__':
    pytest.main([__file__])
