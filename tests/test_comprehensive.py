import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from app import app, call_ai_with_retry, search
from utils import Cache, format_answer_for_ocs, extract_answer, parse_reading_comprehension
from validators import InputValidator
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


class TestEmptyQuestionType:
    """测试空问题类型场景"""

    @patch('app.call_ai_with_retry')
    def test_search_with_empty_type(self, mock_ai_call, client):
        """测试空问题类型的情况"""
        mock_ai_call.return_value = "<answer>测试答案</answer>"

        response = client.get('/api/search?title=你是谁&type=&options=')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 1
        assert 'answer' in data

        # 验证AI调用使用了正确的参数
        mock_ai_call.assert_called_once()
        args, kwargs = mock_ai_call.call_args
        prompt = args[0]
        assert '你是谁' in prompt
        assert '类型: 未指定' in prompt

    @patch('app.call_ai_with_retry')
    def test_search_with_auto_detect_type(self, mock_ai_call, client):
        """测试自动识别类型（前端发送空字符串）"""
        mock_ai_call.return_value = "<answer>正确</answer>"

        response = client.get('/api/search?title=1+1等于2吗&type=&options=')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 1

    def test_input_validation_empty_type(self):
        """测试输入验证允许空类型"""
        valid, error_msg = InputValidator.validate_type("")
        assert valid is True
        assert error_msg is None

    def test_input_validation_invalid_type(self):
        """测试输入验证拒绝无效类型"""
        valid, error_msg = InputValidator.validate_type("invalid_type")
        assert valid is False
        assert "不支持的题目类型" in error_msg


class TestQuestionTypeHandling:
    """测试不同问题类型的处理"""

    @patch('app.call_ai_with_retry')
    def test_judgement_type(self, mock_ai_call, client):
        """测试判断题类型"""
        mock_ai_call.return_value = "<answer>正确</answer>"

        response = client.get('/api/search?title=1+1等于2吗&type=judgement&options=')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 1
        assert data['answer'] == '正确'

    @patch('app.call_ai_with_retry')
    def test_single_choice_type(self, mock_ai_call, client):
        """测试单选题类型"""
        mock_ai_call.return_value = "<answer>A. 北京</answer>"

        response = client.get('/api/search?title=中国的首都是哪里&type=single&options=A. 北京\nB. 上海')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 1
        assert '北京' in data['answer']

    @patch('app.call_ai_with_retry')
    def test_multiple_choice_type(self, mock_ai_call, client):
        """测试多选题类型"""
        mock_ai_call.return_value = "<answer>A. 选项1#B. 选项2</answer>"

        response = client.get('/api/search?title=选择正确的选项&type=multiple&options=A. 选项1\nB. 选项2\nC. 选项3')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 1

    @patch('app.call_ai_with_retry')
    def test_completion_type(self, mock_ai_call, client):
        """测试填空题类型"""
        mock_ai_call.return_value = "<answer>人工智能</answer>"

        response = client.get('/api/search?title=AI的全称是______&type=completion&options=')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 1
        assert data['answer'] == '人工智能'


class TestFrontendIntegration:
    """测试前端集成场景"""

    def test_frontend_form_submission_empty_type(self, client):
        """测试前端表单提交空类型（自动识别）"""
        # 模拟前端发送的请求
        response = client.post('/api/search', data={
            'title': '你是谁',
            'type': '',  # 前端自动识别选项
            'options': '',
            'context': ''
        })
        # 即使AI调用失败，也应该返回适当的错误响应
        assert response.status_code == 200
        data = json.loads(response.data)
        # 应该返回错误而不是崩溃
        assert 'code' in data

    def test_frontend_form_with_options(self, client):
        """测试前端表单带选项的提交"""
        response = client.post('/api/search', data={
            'title': '选择正确的答案',
            'type': 'single',
            'options': 'A. 选项1\nB. 选项2\nC. 选项3',
            'context': '这是一个测试题目'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'code' in data


class TestErrorHandling:
    """测试错误处理场景"""

    def test_search_without_title(self, client):
        """测试没有提供标题的情况"""
        response = client.get('/api/search')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 0
        assert '未提供问题内容' in data['msg']

    def test_search_with_empty_title(self, client):
        """测试空标题的情况"""
        response = client.get('/api/search?title=&type=single')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 0
        assert '未提供问题内容' in data['msg']

    @patch('app.call_ai_with_retry')
    def test_ai_call_failure(self, mock_ai_call, client):
        """测试AI调用失败的情况"""
        mock_ai_call.side_effect = Exception("AI服务不可用")

        response = client.get('/api/search?title=测试问题&type=single')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 0
        assert '服务内部错误' in data['msg']

    @patch('app.call_ai_with_retry')
    def test_ai_returns_empty_answer(self, mock_ai_call, client):
        """测试AI返回空答案的情况"""
        mock_ai_call.return_value = "<answer></answer>"

        response = client.get('/api/search?title=测试问题&type=single')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 0
        assert 'AI 返回的答案为空' in data['msg']


class TestCacheIntegration:
    """测试缓存集成"""

    @patch('app.cache')
    @patch('app.call_ai_with_retry')
    def test_cache_hit(self, mock_ai_call, mock_cache, client):
        """测试缓存命中的情况"""
        mock_cache.get.return_value = "缓存的答案"

        response = client.get('/api/search?title=测试问题&type=single')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 1
        assert data['answer'] == '缓存的答案'

        # AI不应该被调用
        mock_ai_call.assert_not_called()

    @patch('app.cache')
    @patch('app.call_ai_with_retry')
    def test_cache_miss(self, mock_ai_call, mock_cache, client):
        """测试缓存未命中的情况"""
        mock_cache.get.return_value = None
        mock_ai_call.return_value = "<answer>新的答案</answer>"

        response = client.get('/api/search?title=测试问题&type=single')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 1
        assert data['answer'] == '新的答案'

        # 缓存不应该被设置（根据用户要求）
        mock_cache.set.assert_not_called()


class TestReadingComprehension:
    """测试阅读理解题处理"""

    def test_parse_reading_comprehension(self):
        """测试阅读理解题解析"""
        text = """Reading Comprehension (10 points)
这是一个阅读理解题目。

(1) 问题内容是什么？
A. 选项1
B. 选项2
C. 选项3"""

        context, question, options = parse_reading_comprehension(text)
        assert context == "这是一个阅读理解题目。"
        assert "问题内容是什么" in question
        assert "A. 选项1" in options

    @patch('app.call_ai_with_retry')
    def test_reading_comprehension_detection(self, mock_ai_call, client):
        """测试阅读理解题自动检测"""
        mock_ai_call.return_value = "<answer>A. 选项1</answer>"

        question_text = "Reading Comprehension: 这是一个阅读理解题目。(1) 问题内容是什么？A. 选项1 B. 选项2"
        response = client.get(f'/api/search?title={question_text}&type=single')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 1


class TestExternalDatabase:
    """测试外部题库功能"""

    @patch('app.get_external_db')
    @patch('app.call_ai_with_retry')
    def test_external_db_hit(self, mock_ai_call, mock_get_external_db, client):
        """测试外部题库命中的情况"""
        mock_external_db = Mock()
        async def mock_query(*args, **kwargs):
            return (True, "测试问题", "测试答案")
        mock_external_db.query_all_databases = mock_query
        mock_external_db._is_not_found_answer.return_value = False  # "测试答案"不是未找到答案
        mock_get_external_db.return_value = mock_external_db

        response = client.get('/api/search?title=测试问题&type=single')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 1
        assert data['answer'] == '测试答案'

        # AI不应该被调用
        mock_ai_call.assert_not_called()

    @patch('app.get_external_db')
    @patch('app.call_ai_with_retry')
    def test_external_db_miss(self, mock_ai_call, mock_get_external_db, client):
        """测试外部题库未命中的情况"""
        mock_external_db = Mock()
        async def mock_query(*args, **kwargs):
            return (False, None, None)
        mock_external_db.query_all_databases = mock_query
        mock_external_db._is_not_found_answer.return_value = False
        mock_get_external_db.return_value = mock_external_db
        mock_ai_call.return_value = "<answer>AI答案</answer>"

        response = client.get('/api/search?title=测试问题&type=single')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 1
        assert data['answer'] == 'AI答案'

    @patch('app.Config.ENABLE_EXTERNAL_DATABASE', False)
    @patch('app.call_ai_with_retry')
    def test_external_db_disabled_uses_ai(self, mock_ai_call, client):
        """测试外部题库未启用时直接使用AI的情况"""
        mock_ai_call.return_value = "<answer>AI答案</answer>"

        response = client.get('/api/search?title=测试问题&type=single')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 1
        assert data['answer'] == 'AI答案'

        # AI应该被调用
        mock_ai_call.assert_called_once()

    @patch('app.get_external_db')
    @patch('app.call_ai_with_retry')
    def test_external_db_returns_not_found_message(self, mock_ai_call, mock_get_external_db, client):
        """测试外部题库返回'未找到'消息时应该使用AI的情况"""
        mock_external_db = Mock()
        async def mock_query(*args, **kwargs):
            # 返回"未找到"消息
            return (True, "测试问题", "非常抱歉，题目搜索不到。")
        mock_external_db.query_all_databases = mock_query
        mock_external_db._is_not_found_answer.return_value = True  # "非常抱歉，题目搜索不到。"是未找到答案
        mock_get_external_db.return_value = mock_external_db
        mock_ai_call.return_value = "<answer>AI答案</answer>"

        response = client.get('/api/search?title=测试问题&type=single')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 1
        assert data['answer'] == 'AI答案'

        # AI应该被调用，因为外部题库返回的是"未找到"消息
        mock_ai_call.assert_called_once()


class TestRateLimiting:
    """测试速率限制功能"""

    @patch('app.Config.ENABLE_RATE_LIMIT', True)
    @patch('app.rate_limiter')
    def test_rate_limit_exceeded(self, mock_rate_limiter, client):
        """测试超出速率限制的情况"""
        mock_rate_limiter.is_allowed.return_value = (False, "请求过于频繁，请稍后再试")

        response = client.get('/api/search?title=测试问题&type=single')
        assert response.status_code == 429
        data = json.loads(response.data)
        assert data['code'] == 0
        assert '请求过于频繁' in data['msg']


class TestInputValidation:
    """测试输入验证"""

    def test_validate_question_too_long(self, client):
        """测试问题内容过长的情况"""
        long_question = "测试问题" * 1000  # 创建超长问题
        response = client.get(f'/api/search?title={long_question}&type=single')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 0
        assert '超过最大长度限制' in data['msg']

    def test_validate_options_malicious(self, client):
        """测试选项包含恶意内容的情况"""
        malicious_options = "A. 正常选项<script>alert('xss')</script>"
        response = client.get(f'/api/search?title=测试问题&type=single&options={malicious_options}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 0
        assert '包含不当内容' in data['msg']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
