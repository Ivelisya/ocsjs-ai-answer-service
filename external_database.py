# -*- coding: utf-8 -*-
"""
外部题库查询模块
"""
import json
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode

import aiohttp


logger = logging.getLogger("ai_answer_service")


class ExternalDatabase:
    """外部题库查询器"""
    
    def __init__(self, databases_config: List[Dict]):
        """
        初始化外部题库配置
        
        Args:
            databases_config: 题库配置列表
        """
        self.databases = databases_config
        self.timeout = aiohttp.ClientTimeout(total=10)  # 10秒超时
    
    def _is_not_found_answer(self, answer: str) -> bool:
        """
        判断答案是否表示"未找到"
        
        Args:
            answer: 答案字符串
            
        Returns:
            是否表示未找到
        """
        if not answer:
            return True
            
        # 转换为小写进行匹配
        answer_lower = answer.lower().strip()
        
        # 常见的"未找到"表达
        not_found_patterns = [
            "非常抱歉",
            "题目搜索不到",
            "未找到",
            "没有找到",
            "搜索不到",
            "抱歉",
            "sorry",
            "not found",
            "no answer",
            "无法找到",
            "查询失败",
            "暂无答案"
        ]
        
        return any(pattern in answer_lower for pattern in not_found_patterns)
    
    async def query_all_databases(self, title: str, options: str = "", question_type: str = "") -> Tuple[bool, Optional[str], Optional[str]]:
        """
        查询所有配置的外部题库
        
        Args:
            title: 题目标题
            options: 选项
            question_type: 题目类型
            
        Returns:
            (是否找到答案, 题目, 答案)
        """
        for db_config in self.databases:
            try:
                found, question, answer = await self._query_single_database(
                    db_config, title, options, question_type
                )
                if found and answer:
                    # 检查答案是否表示"未找到"
                    if self._is_not_found_answer(answer):
                        logger.info(f"外部题库 '{db_config['name']}' 返回未找到答案，继续查询其他题库")
                        continue
                    else:
                        logger.info(f"从外部题库 '{db_config['name']}' 找到有效答案")
                        return True, question, answer
            except Exception as e:
                logger.warning(f"查询外部题库 '{db_config['name']}' 失败: {e}")
                continue
        
        logger.info("所有外部题库均未找到有效答案")
        return False, None, None
    
    async def _query_single_database(self, db_config: Dict, title: str, options: str, question_type: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        查询单个外部题库
        
        Args:
            db_config: 题库配置
            title: 题目标题
            options: 选项
            question_type: 题目类型
            
        Returns:
            (是否找到答案, 题目, 答案)
        """
        try:
            # 准备请求数据
            data = self._prepare_request_data(db_config.get("data", {}), title, options, question_type)
            headers = db_config.get("headers", {})
            method = db_config.get("method", "get").lower()
            url = db_config["url"]
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                if method == "get":
                    # GET请求将数据作为查询参数
                    if data:
                        url += "?" + urlencode(data)
                    async with session.get(url, headers=headers) as response:
                        response_text = await response.text()
                elif method == "post":
                    # POST请求
                    content_type = db_config.get("contentType", "json")
                    if content_type == "json":
                        headers["Content-Type"] = "application/json"
                        async with session.post(url, headers=headers, json=data) as response:
                            response_text = await response.text()
                    else:
                        # form数据
                        headers["Content-Type"] = "application/x-www-form-urlencoded"
                        async with session.post(url, headers=headers, data=data) as response:
                            response_text = await response.text()
                else:
                    logger.warning(f"不支持的HTTP方法: {method}")
                    return False, None, None
                
                # 解析响应
                return self._parse_response(db_config, response_text)
                
        except asyncio.TimeoutError:
            logger.warning(f"查询 {db_config['name']} 超时")
            return False, None, None
        except Exception as e:
            logger.warning(f"查询 {db_config['name']} 出错: {e}")
            return False, None, None
    
    def _prepare_request_data(self, data_template: Dict, title: str, options: str, question_type: str) -> Dict:
        """
        准备请求数据，替换模板变量
        
        Args:
            data_template: 数据模板
            title: 题目标题
            options: 选项
            question_type: 题目类型
            
        Returns:
            处理后的请求数据
        """
        data = {}
        for key, value in data_template.items():
            if isinstance(value, str):
                # 替换模板变量
                value = value.replace("${title}", title)
                value = value.replace("${options}", options)
                value = value.replace("${type}", question_type)
                data[key] = value
            else:
                data[key] = value
        return data
    
    def _parse_response(self, db_config: Dict, response_text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        解析响应数据
        
        Args:
            db_config: 题库配置
            response_text: 响应文本
            
        Returns:
            (是否找到答案, 题目, 答案)
        """
        try:
            # 尝试解析JSON
            response_data = json.loads(response_text)
            
            # 执行处理函数（简化版本，仅支持基本的逻辑）
            handler = db_config.get("handler", "")
            
            if "言溪题库" in db_config.get("name", ""):
                # 言溪题库逻辑: res.code === 0 ? [res.data.answer, undefined] : [res.data.question, res.data.answer]
                if response_data.get("code") == 0:
                    answer = response_data.get("data", {}).get("answer")
                    if answer:
                        return True, None, answer
                else:
                    question = response_data.get("data", {}).get("question")
                    answer = response_data.get("data", {}).get("answer")
                    if answer:
                        return True, question, answer
            
            elif "网课小工具题库" in db_config.get("name", "") or "GO题" in db_config.get("name", ""):
                # GO题库逻辑: res.code === 1 ? [undefined, res.data] : [res.msg, undefined]
                if response_data.get("code") == 1:
                    answer = response_data.get("data")
                    if answer:
                        return True, None, answer
                else:
                    # 返回错误信息，但不算找到答案
                    return False, response_data.get("msg"), None
            
            # 通用逻辑：尝试从常见字段提取答案
            answer = (response_data.get("answer") or 
                     response_data.get("data", {}).get("answer") if isinstance(response_data.get("data"), dict) else response_data.get("data"))
            
            if answer:
                question = (response_data.get("question") or 
                           response_data.get("data", {}).get("question") if isinstance(response_data.get("data"), dict) else None)
                return True, question, answer
            
            return False, None, None
            
        except json.JSONDecodeError:
            logger.warning(f"无法解析 {db_config['name']} 的响应为JSON")
            return False, None, None
        except Exception as e:
            logger.warning(f"解析 {db_config['name']} 响应时出错: {e}")
            return False, None, None


def get_default_databases() -> List[Dict]:
    """获取默认的外部题库配置"""
    import os
    
    # 尝试从配置文件读取
    config_file = "external_databases.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if config.get("enabled", True):
                    # 只返回启用的数据库
                    return [db for db in config.get("databases", []) if db.get("enabled", True)]
                else:
                    return []
        except Exception as e:
            logger.warning(f"读取外部题库配置文件失败: {e}")
    
    # 默认配置
    return [
        {
            "name": "言溪题库",
            "homepage": "https://tk.enncy.cn/",
            "url": "https://tk.enncy.cn/query",
            "method": "get",
            "type": "GM_xmlhttpRequest",
            "contentType": "json",
            "data": {
                "token": "03549ac40976408bae38e0841317f047",
                "title": "${title}",
                "options": "${options}",
                "type": "${type}"
            },
            "handler": "return (res)=>res.code === 0 ? [res.data.answer, undefined] : [res.data.question,res.data.answer]"
        },
        {
            "name": "网课小工具题库（GO题）",
            "homepage": "https://cx.icodef.com/",
            "url": "https://cx.icodef.com/wyn-nb?v=4",
            "method": "post",
            "type": "GM_xmlhttpRequest",
            "data": {
                "question": "${title}"
            },
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": ""
            },
            "handler": "return  (res)=> res.code === 1 ? [undefined,res.data] : [res.msg,undefined]"
        }
    ]
