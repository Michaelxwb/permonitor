"""
优化验证测试

验证异步处理机制优化、内存管理改进和错误处理增强
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from web_performance_monitor import UnifiedConfig
from web_performance_monitor.alerts.manager import AsyncAlertManager
from web_performance_monitor.utils.cache import CacheManager
from web_performance_monitor.models.models import PerformanceMetrics
from web_performance_monitor.utils.async_retry import AsyncRetryHandler
from web_performance_monitor.exceptions.async_error_handler import AsyncErrorHandler


class TestAsyncProcessingOptimization:
    """异步处理机制优化测试"""

    @pytest.fixture
    def config(self):
        """测试配置"""
        return UnifiedConfig(
            threshold_seconds=0.1,
            fastapi_max_concurrent_alerts=5,
            alert_max_retries=2,
            fastapi_async_timeout=5.0
        )

    @pytest.fixture
    def async_alert_manager(self, config):
        """异步告警管理器实例"""
        return AsyncAlertManager(config)

    @pytest.mark.asyncio
    async def test_cancellation_handling(self, async_alert_manager):
        """测试取消处理"""
        # Mock should_alert to return True
        async_alert_manager.should_alert = Mock(return_value=True)
        
        # Mock retry mechanism to simulate cancellation
        async def cancelled_operation(*args, **kwargs):
            raise asyncio.CancelledError("Operation cancelled")
        
        with patch('web_performance_monitor.utils.async_retry.AsyncRetryHandler.retry_async_operation', 
                   side_effect=cancelled_operation):
            metrics = PerformanceMetrics(
                endpoint="/test",
                request_url="http://localhost/test",
                request_params={},
                execution_time=2.0,
                timestamp=datetime.now(),
                request_method="GET",
                status_code=200
            )
            
            result = await async_alert_manager.process_alert_async(metrics, "<html>report</html>")
            assert result is None
            
            # 验证统计信息
            stats = async_alert_manager.get_alert_stats()
            assert stats['cancelled'] == 1

    @pytest.mark.asyncio
    async def test_timeout_handling(self, async_alert_manager):
        """测试超时处理"""
        # Mock should_alert to return True
        async_alert_manager.should_alert = Mock(return_value=True)
        
        # Mock safe_execute_with_timeout to simulate timeout
        async def timeout_operation(*args, **kwargs):
            raise asyncio.TimeoutError("Operation timeout")
        
        with patch('web_performance_monitor.exceptions.async_error_handler.AsyncErrorHandler.safe_execute_with_timeout', 
                   side_effect=timeout_operation):
            metrics = PerformanceMetrics(
                endpoint="/test",
                request_url="http://localhost/test",
                request_params={},
                execution_time=2.0,
                timestamp=datetime.now(),
                request_method="GET",
                status_code=200
            )
            
            result = await async_alert_manager.process_alert_async(metrics, "<html>report</html>")
            assert result is None
            
            # 验证统计信息
            stats = async_alert_manager.get_alert_stats()
            assert stats['timed_out'] >= 1


class TestMemoryManagementImprovement:
    """内存管理策略改进测试"""

    @pytest.fixture
    def cache_manager(self):
        """缓存管理器实例（小容量便于测试）"""
        return CacheManager(max_entries=10)

    def test_lru_cache_strategy(self, cache_manager):
        """测试LRU缓存策略"""
        # 添加一些条目
        for i in range(10):
            cache_manager.mark_alerted(f"key_{i}", f"data_{i}")
        
        # 访问前几个条目以改变访问顺序
        for i in range(3):
            cache_manager.is_recently_alerted(f"key_{i}")
        
        # 添加更多条目以触发清理
        for i in range(10, 15):
            cache_manager.mark_alerted(f"key_{i}", f"data_{i}")
        
        # 验证LRU策略：最早访问但未重新访问的条目应该被清理
        # key_3, key_4, key_5 应该被清理（最早添加且未重新访问）
        # key_0, key_1, key_2 应该保留（因为被重新访问过）
        assert cache_manager.is_recently_alerted("key_0") == True
        assert cache_manager.is_recently_alerted("key_1") == True
        assert cache_manager.is_recently_alerted("key_2") == True

    def test_memory_limit_enforcement(self, cache_manager):
        """测试内存限制执行"""
        # 添加超过限制的条目
        for i in range(15):
            cache_manager.mark_alerted(f"key_{i}", f"data_{i}")
        
        # 验证条目数量不超过限制
        assert len(cache_manager) <= 10


class TestErrorHandlingEnhancement:
    """错误处理能力增强测试"""

    @pytest.mark.asyncio
    async def test_retry_with_timeout(self):
        """测试带超时的重试机制"""
        call_count = 0
        
        async def slow_operation():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(2)  # 比超时时间长
            return "success"
        
        # 测试超时情况
        try:
            result = await AsyncRetryHandler.retry_async_operation(
                slow_operation, 
                max_retries=2, 
                delay=0.01,
                timeout=0.1  # 100ms超时
            )
            assert result is None
        except asyncio.TimeoutError:
            # 重试机制会重新抛出超时异常
            pass
        assert call_count >= 1  # 至少调用一次

    @pytest.mark.asyncio
    async def test_safe_execute_with_timeout(self):
        """测试带超时的安全执行"""
        async def slow_function():
            await asyncio.sleep(2)
            return "result"
        
        # 测试超时情况
        try:
            result = await AsyncErrorHandler.safe_execute_with_timeout(
                slow_function, 
                timeout=0.1  # 100ms超时
            )
            assert result is None
        except asyncio.TimeoutError:
            # safe_execute_with_timeout会重新抛出超时异常
            pass

    @pytest.mark.asyncio
    async def test_safe_execute_async_with_cancellation(self):
        """测试带取消的安全异步执行"""
        async def cancelled_function():
            raise asyncio.CancelledError("Operation cancelled")
        
        result = await AsyncErrorHandler.safe_execute_async(cancelled_function)
        assert result is None


class TestIntegrationScenarios:
    """集成场景测试"""

    @pytest.fixture
    def config(self):
        """测试配置"""
        return UnifiedConfig(
            threshold_seconds=0.1,
            fastapi_max_concurrent_alerts=3,
            alert_max_retries=1,
            fastapi_async_timeout=2.0,
            enable_local_file=True,
            enable_mattermost=False
        )

    @pytest.fixture
    def async_alert_manager(self, config):
        """异步告警管理器实例"""
        return AsyncAlertManager(config)

    @pytest.mark.asyncio
    async def test_concurrent_alert_processing_with_limits(self, async_alert_manager):
        """测试并发告警处理与限制"""
        # Mock should_alert to return True for some alerts
        async_alert_manager.should_alert = Mock(return_value=True)
        
        # Mock notification manager
        async_alert_manager.notification_manager = Mock()
        async_alert_manager.notification_manager.send_notifications_async = AsyncMock(return_value=True)
        
        # 创建多个性能指标
        metrics_list = []
        for i in range(10):
            metrics = PerformanceMetrics(
                endpoint=f"/test_{i}",
                request_url=f"http://localhost/test_{i}",
                request_params={},
                execution_time=2.0,
                timestamp=datetime.now(),
                request_method="GET",
                status_code=200
            )
            metrics_list.append(metrics)
        
        # 并发处理所有告警
        tasks = [
            async_alert_manager.process_alert_async(metrics, "<html>report</html>")
            for metrics in metrics_list
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 验证结果
        success_count = sum(1 for result in results if result is not None)
        assert success_count >= 5  # 至少处理了一半
        
        # 验证统计信息
        stats = async_alert_manager.get_alert_stats()
        assert stats['total_processed'] >= 5
        assert stats['successful'] >= 5

    @pytest.mark.asyncio
    async def test_error_recovery_in_alert_processing(self, async_alert_manager):
        """测试告警处理中的错误恢复"""
        # Mock should_alert to return True
        async_alert_manager.should_alert = Mock(return_value=True)
        
        # Mock notification manager to fail first time then succeed
        call_count = 0
        async def flaky_notification(metrics, html_report):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary failure")
            return True
        
        async_alert_manager.notification_manager = Mock()
        async_alert_manager.notification_manager.send_notifications_async = AsyncMock(side_effect=flaky_notification)
        
        metrics = PerformanceMetrics(
            endpoint="/test",
            request_url="http://localhost/test",
            request_params={},
            execution_time=2.0,
            timestamp=datetime.now(),
            request_method="GET",
            status_code=200
        )
        
        result = await async_alert_manager.process_alert_async(metrics, "<html>report</html>")
        
        # 验证重试后成功
        assert result is not None
        assert call_count == 2  # 调用了两次，第一次失败，第二次成功
        
        # 验证统计信息
        stats = async_alert_manager.get_alert_stats()
        assert stats['successful'] == 1
        assert stats['retried'] == 1