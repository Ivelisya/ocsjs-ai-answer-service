# AI题库服务API文档

## 概述

AI题库服务是一个基于大型语言模型（LLM）的问题解答服务，支持 **OpenAI API** 和 **Google Gemini API**。它专为[OCS (Online Course Script)](https://github.com/ocsjs/ocsjs)设计，可以通过AI自动回答题目。此服务实现了与OCS AnswererWrapper兼容的API接口，方便用户将AI能力整合到OCS题库搜索中。

## AI提供商配置

本服务支持通过环境变量配置使用不同的AI提供商。主要的配置项在 `.env` 文件中设置：

*   `AI_PROVIDER`: 指定使用的AI提供商。
    *   设置为 `"openai"` (默认) 来使用 OpenAI API。
    *   设置为 `"gemini"` 来使用 Google Gemini API。
*   **OpenAI 配置** (当 `AI_PROVIDER="openai"` 时):
    *   `OPENAI_API_KEY`: 你的OpenAI API密钥。
    *   `OPENAI_MODEL`: 使用的OpenAI模型 (例如, `gpt-3.5-turbo`, `gpt-4`).
    *   `OPENAI_API_BASE`: (可选) OpenAI API的基础URL。
*   **Gemini 配置** (当 `AI_PROVIDER="gemini"` 时):
    *   `GEMINI_API_KEY`: 你的Google Gemini API密钥。
    *   `GEMINI_MODEL`: 使用的Gemini模型 (例如, `gemini-pro`).

请参考项目根目录下的 `.env.example` 文件获取详细的配置示例。

## 接口详情

### 搜索接口

**URL**: `/api/search`

**方法**: `GET` 或 `POST`

**参数**:

| 参数名   | 类型   | 必填 | 说明                                                     |
|---------|--------|------|----------------------------------------------------------|
| title   | string | 是   | 题目内容                                                 |
| type    | string | 否   | 题目类型 (single-单选, multiple-多选, judgement-判断, completion-填空) |
| options | string | 否   | 选项内容，通常是A、B、C、D选项的文本                       |

**成功响应**:

```json
{
  "code": 1,
  "question": "问题内容",
  "answer": "AI生成的答案"
}
```

**失败响应**:

```json
{
  "code": 0,
  "msg": "错误信息"
}
```

### 健康检查接口

**URL**: `/api/health`

**方法**: `GET`

**响应**:

```json
{
  "status": "ok",
  "message": "AI题库服务运行正常",
  "version": "1.1.0",
  "cache_enabled": true,
  "ai_provider": "openai",
  "model": "gpt-3.5-turbo"
}
```
*注意: `ai_provider` 和 `model` 字段会根据您的配置动态显示。*

### 缓存清理接口

**URL**: `/api/cache/clear`

**方法**: `POST`

**响应**:

```json
{
  "success": true,
  "message": "缓存已清除"
}
```

### 统计信息接口

**URL**: `/api/stats`

**方法**: `GET`

**响应**:

```json
{
  "version": "1.1.0",
  "uptime": 1621234567.89,
  "ai_provider": "openai",
  "model": "gpt-3.5-turbo",
  "cache_enabled": true,
  "cache_size": 123,
  "qa_records_count": 50
}
```
*注意: `ai_provider` 和 `model` 字段会根据您的配置动态显示。*

## OCS配置示例

在OCS的自定义题库配置中添加如下配置：

```json
[
  {
    "name": "AI智能题库",
    "homepage": "https://github.com/yourusername/ai-answer-service",
    "url": "http://localhost:5000/api/search",
    "method": "get",
    "contentType": "json",
    "data": {
      "title": "${title}",
      "type": "${type}",
      "options": "${options}"
    },
    "handler": "return (res)=> res.code === 1 ? [res.question, res.answer] : [res.msg, undefined]"
  }
]
```

## 安全设置

如果你想增加安全性，可以在`.env`文件中设置访问令牌：

```
ACCESS_TOKEN=your_secret_token_here
```

设置后，所有API请求都需要包含此令牌，可以通过以下两种方式之一传递：

1. HTTP头部: `X-Access-Token: your_secret_token_here`
2. URL参数: `?token=your_secret_token_here`

## 注意事项

1.  **多选题答案格式**: 对于多选题，OCS期望的答案格式是用`#`分隔的选项内容，例如`中国#世界#地球`。本服务已提示AI模型按此格式返回，并在后端进行了相应的处理以尽可能确保格式正确。

2.  **API请求限制与费用**: 无论是使用OpenAI还是Gemini，请注意各自API的使用限制和可能的费用。确保您的账户有足够的额度或已正确配置付费。

3.  **网络连接**: 确保部署此服务的服务器能够访问所选AI提供商的API端点（例如 `api.openai.com` 或 `generativelanguage.googleapis.com`）。某些地区可能需要代理服务。

4.  **题库域名**: 根据OCS文档说明，需要将题库配置中`homepage`以及`url`所涉及到的域名，在脚本头部元信息`@connect`中新增，否则无法请求到数据。

5.  **模型选择**: 不同的模型在性能、成本和能力上有所不同。请根据您的需求选择合适的模型，并在 `.env` 文件中配置。