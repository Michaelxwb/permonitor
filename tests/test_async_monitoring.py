"""
异步监控测试

测试异步装饰器功能和FastAPI中间件集成
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from web_performance_monitor import UnifiedConfig, FastAPIMonitor
from web_performance_monitor.core.base import AsyncFunctionExecutionContext
from web_performance_monitor.notifications.manager import AsyncNotificationManager
from web_performance_monitor.models.models import PerformanceMetrics
from datetime import datetime


class TestAsyncMonitoring:
    """异步监控测试"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        return UnifiedConfig(
            threshold_seconds=0.1,  # 低阈值便于测试
            enable_local_file=True,
            enable_mattermost=False
        )
    
    @pytest.fixture
    def fastapi_monitor(self, config):
        """FastAPI监控器实例"""
        return FastAPIMonitor(config)
    
    @pytest.mark.asyncio
    async def test_async_decorator_with_async_function(self, fastapi_monitor):
        """测试异步装饰器与异步函数"""
        @fastapi_monitor.create_decorator()
        async def async_test_func():
            await asyncio.sleep(0.01)
            return "async_result"
        
        result = await async_test_func()
        assert result == "async_result"
    
    def test_async_decorator_with_sync_function(self, fastapi_monitor):
        """测试异步装饰器与同步函数"""
        @fastapi_monitor.create_decorator()
        def sync_test_func():
            return "sync_result"
        
        result = sync_test_func()
        assert result == "sync_result"
    
    @pytest.mark.asyncio
    async def test_async_function_execution_context(self):
        """测试异步函数执行上下文"""
        async def test_func(x, y=10):
            await asyncio.sleep(0.01)
            return x + y
        
        context = AsyncFunctionExecutionContext(test_func, (5,), {'y': 15})
        result = await context.execute_async()
        assert result == 20
        
        # 测试请求信息提取
        request_info = context.get_request_info()
        assert 'test_func' in request_info['endpoint']
        assert request_info['request_method'] == 'FUNCTION'
    
    @pytest.mark.asyncio
    async def test_async_monitoring_execution(self, fastapi_monitor):
        """测试异步监控执行流程"""
        async def test_operation():
            await asyncio.sleep(0.02)
            return "monitored_result"
        
        context = AsyncFunctionExecutionContext(test_operation, (), {})
        
        # Mock analyzer
        fastapi_monitor.analyzer = Mock()
        fastapi_monitor.analyzer.start_profiling_async = AsyncMock(return_value=Mock())
        fastapi_monitor.analyzer.get_execution_time_async = AsyncMock(return_value=0.02)
        fastapi_monitor.analyzer.stop_profiling_async = AsyncMock(return_value="<html>report</html>")
        
        result = await fastapi_monitor._monitor_execution_async(context)
        assert result == "monitored_result"
        
        # 验证analyzer方法被调用
        fastapi_monitor.analyzer.start_profiling_async.assert_called_once()
        fastapi_monitor.analyzer.stop_profiling_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_alert_processing(self, fastapi_monitor):
        """测试异步告警处理"""
        # Mock alert manager
        fastapi_monitor.alert_manager = Mock()
        fastapi_monitor.alert_manager.process_alert_async = AsyncMock(return_value=Mock())
        
        # Mock context
        context = Mock()
        context.get_request_info.return_value = {
            'endpoint': '/test',
            'request_url': 'http://localhost/test',
            'request_params': {},
            'request_method': 'GET'
        }
        
        await fastapi_monitor._process_alert_async(context, 2.0, "<html>report</html>")
        
        # 验证告警处理被调用
        fastapi_monitor.alert_manager.process_alert_async.assert_called_once()
        
        # 验证传递的metrics参数
        call_args = fastapi_monitor.alert_manager.process_alert_async.call_args
        metrics = call_args[0][0]
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.execution_time == 2.0
        assert metrics.endpoint == '/test'


class TestAsyncNotificationManager:
    """异步通知管理器测试"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        return UnifiedConfig(
            enable_local_file=True,
            enable_mattermost=True,
            fastapi_max_concurrent_alerts=5
        )
    
    @pytest.fixture
    def notification_manager(self, config):
        """异步通知管理器实例"""
        return AsyncNotificationManager(config)
    
    @pytest.fixture
    def test_metrics(self):
        """测试性能指标"""
        return PerformanceMetrics(
            endpoint="/test",
            request_url="http://localhost/test",
            request_params={},
            execution_time=2.0,
            timestamp=datetime.now(),
            request_method="GET",
            status_code=200
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_notification_sending(self, notification_manager, test_metrics):
        """测试并发通知发送"""
        # Mock notifiers
        mock_notifier1 = Mock()
        mock_notifier1.send_notification_async = AsyncMock(return_value=True)
        mock_notifier1.__class__.__name__ = "MockNotifier1"
        
        mock_notifier2 = Mock()
        mock_notifier2.send_notification_async = AsyncMock(return_value=True)
        mock_notifier2.__class__.__name__ = "MockNotifier2"
        
        notification_manager.notifiers = [mock_notifier1, mock_notifier2]
        
        result = await notification_manager.send_notifications_async(test_metrics, "<html>report</html>")
        
        assert result == True
        mock_notifier1.send_notification_async.assert_called_once()
        mock_notifier2.send_notification_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_concurrent_notification_with_failures(self, notification_manager, test_metrics):
        """测试并发通知发送时的失败处理"""
        # Mock notifiers - 一个成功，一个失败
        mock_notifier1 = Mock()
        mock_notifier1.send_notification_async = AsyncMock(return_value=True)
        mock_notifier1.__class__.__name__ = "SuccessNotifier"
        
        mock_notifier2 = Mock()
        mock_notifier2.send_notification_async = AsyncMock(side_effect=Exception("Network error"))
        mock_notifier2.__class__.__name__ = "FailNotifier"
        
        notification_manager.notifiers = [mock_notifier1, mock_notifier2]
        
        result = await notification_manager.send_notifications_async(test_metrics, "<html>report</html>")
        
        # 至少一个成功，所以返回True
        assert result == True
        mock_notifier1.send_notification_async.assert_called_once()
        mock_notifier2.send_notification_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_semaphore_concurrency_control(self, config, test_metrics):
        """测试信号量并发控制"""
        config.fastapi_max_concurrent_alerts = 2
        notification_manager = AsyncNotificationManager(config)
        
        # 创建多个mock通知器
        notifiers = []
        for i in range(5):
            mock_notifier = Mock()
            mock_notifier.send_notification_async = AsyncMock(return_value=True)
            mock_notifier.__class__.__name__ = f"MockNotifier{i}"
            notifiers.append(mock_notifier)
        
        notification_manager.notifiers = notifiers
        
        # 记录并发执行的时间
        start_time = asyncio.get_event_loop().time()
        result = await notification_manager.send_notifications_async(test_metrics, "<html>report</html>")
        end_time = asyncio.get_event_loop().time()
        
        assert result == True
        # 验证所有通知器都被调用
        for notifier in notifiers:
            notifier.send_notification_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_empty_notifiers_list(self, notification_manager, test_metrics):
        """测试空通知器列表"""
        notification_manager.notifiers = []
        
        result = await notification_manager.send_notifications_async(test_metrics, "<html>report</html>")
        assert result == False


class TestAsyncRetryMechanism:
    """异步重试机制测试"""
    
    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """测试第一次尝试就成功"""
        from web_performance_monitor.async_retry import AsyncRetryHandler
        
        async def successful_operation():
            return "success"
        
        result = await AsyncRetryHandler.retry_async_operation(
            successful_operation, max_retries=3
        )
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """测试失败后重试成功"""
        from web_performance_monitor.async_retry import AsyncRetryHandler
        
        call_count = 0
        
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await AsyncRetryHandler.retry_async_operation(
            flaky_operation, max_retries=3, delay=0.01
        )
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_final_failure(self):
        """测试最终失败"""
        from web_performance_monitor.async_retry import AsyncRetryHandler
        
        async def always_failing_operation():
            raise Exception("Permanent failure")
        
        with pytest.raises(Exception, match="Permanent failure"):
            await AsyncRetryHandler.retry_async_operation(
                always_failing_operation, max_retries=2, delay=0.01
            )