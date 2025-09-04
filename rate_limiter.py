# -*- coding: utf-8 -*-
"""
速率限制模块
"""
import time
import threading
from collections import defaultdict, deque
from typing import Dict, Optional


class RateLimiter:
    """基于内存的速率限制器"""
    
    def __init__(self, max_requests: int = 100, time_window: int = 3600):
        """
        初始化速率限制器

        Args:
            max_requests: 时间窗口内的最大请求数
            time_window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.RLock()

        # 添加统计信息
        self.total_requests = 0
        self.blocked_requests = 0
    
    def is_allowed(self, identifier: str) -> tuple[bool, Optional[str]]:
        """
        检查请求是否被允许

        Args:
            identifier: 唯一标识符（如IP地址）

        Returns:
            (是否允许, 错误信息)
        """
        current_time = time.time()

        with self._lock:
            # 清理过期记录
            request_queue = self.requests[identifier]
            while request_queue and request_queue[0] < current_time - self.time_window:
                request_queue.popleft()

            # 更新统计信息
            self.total_requests += 1

            # 检查是否超过限制
            if len(request_queue) >= self.max_requests:
                self.blocked_requests += 1
                return False, f"请求频率过高，请稍后再试。限制：{self.max_requests}次/{self.time_window}秒"

            # 记录新请求
            request_queue.append(current_time)
            return True, None
    
    def get_remaining_requests(self, identifier: str) -> int:
        """获取剩余请求次数"""
        current_time = time.time()
        
        with self._lock:
            request_queue = self.requests[identifier]
            # 清理过期记录
            while request_queue and request_queue[0] < current_time - self.time_window:
                request_queue.popleft()
            
            return max(0, self.max_requests - len(request_queue))
    
    def get_stats(self) -> Dict[str, int]:
        """获取速率限制器的统计信息"""
        with self._lock:
            return {
                "total_requests": self.total_requests,
                "blocked_requests": self.blocked_requests,
                "active_identifiers": len(self.requests),
                "max_requests": self.max_requests,
                "time_window": self.time_window,
            }
