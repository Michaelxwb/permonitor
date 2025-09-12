"""
告警管理模块

负责告警逻辑、阈值检查和通知发送
"""

import logging
from typing import List, Dict, Any, Optional
from .config import Config
from .models import PerformanceMetrics, AlertRecord
from .cache import CacheManager
from .notifiers.factory import NotificationFactory
from .notifiers.base import BaseNotifier
from .exceptions import NotificationError
from .utils import safe_execute
from .formatters import NotificationFormatter


class AlertManager:
    """告警管理器
    
    负责告警逻辑判断、重复告警防护和通知发送
    """
    
    def __init__(self, config: Config):
        """初始化告警管理器
        
        Args:
            config: 配置实例
        """
        self.config = config
        self.cache_manager = CacheManager()
        self.notification_factory = NotificationFactory(config)
        self.logger = logging.getLogger(__name__)
        
        # 创建通知器列表
        self.notifiers = self.notification_factory.create_notifiers()
        
        self.logger.info(f"告警管理器初始化完成，启用 {len(self.notifiers)} 个通知器")
    
    def should_alert(self, metrics: PerformanceMetrics) -> bool:
        """判断是否应该发送告警
        
        检查：
        1. 响应时间是否超过配置阈值（默认1秒）
        2. 同一接口在时间窗口内（默认10天）是否已告警
        
        Args:
            metrics: 性能指标数据
            
        Returns:
            bool: 是否应该发送告警
        """
        try:
            # 1. 检查响应时间是否超过阈值
            if not metrics.is_slow(self.config.threshold_seconds):
                self.logger.debug(
                    f"响应时间未超过阈值: {metrics.execution_time:.2f}s <= {self.config.threshold_seconds}s"
                )
                return False
            
            # 2. 检查是否重复告警
            cache_key = self.cache_manager.generate_metrics_key(metrics)
            
            if self.cache_manager.is_recently_alerted(cache_key, self.config.alert_window_days):
                self.logger.info(
                    f"跳过重复告警: {metrics.endpoint} "
                    f"(窗口期: {self.config.alert_window_days}天)"
                )
                return False
            
            self.logger.info(
                f"触发告警条件: {metrics.endpoint} "
                f"响应时间={metrics.execution_time:.2f}s > 阈值={self.config.threshold_seconds}s"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"告警判断失败: {e}")
            return False
    
    def send_alert(self, metrics: PerformanceMetrics, html_report: str) -> AlertRecord:
        """发送告警通知，支持同时启用多种通知方式
        
        Args:
            metrics: 性能指标数据
            html_report: HTML格式的性能报告
            
        Returns:
            AlertRecord: 告警记录
        """
        notification_status = {}
        
        try:
            # 标记已告警，防止重复
            cache_key = self.cache_manager.generate_metrics_key(metrics)
            self.cache_manager.mark_alerted(cache_key, {
                'endpoint': metrics.endpoint,
                'execution_time': metrics.execution_time,
                'timestamp': metrics.timestamp.isoformat()
            })
            
            # 发送到所有启用的通知器
            for notifier in self.notifiers:
                notifier_name = notifier.__class__.__name__
                success = self._safe_send_notification(notifier, metrics, html_report)
                notification_status[notifier_name] = success
                
                if success:
                    self.logger.info(f"告警通知发送成功: {notifier_name}")
                else:
                    self.logger.warning(f"告警通知发送失败: {notifier_name}")
            
            # 创建告警记录
            alert_record = AlertRecord(
                endpoint=metrics.endpoint,
                request_url=metrics.request_url,
                request_params=metrics.request_params,
                alert_time=metrics.timestamp,
                execution_time=metrics.execution_time,
                notification_status=notification_status
            )
            
            # 记录告警摘要
            successful_notifiers = [name for name, success in notification_status.items() if success]
            failed_notifiers = [name for name, success in notification_status.items() if not success]
            
            self.logger.info(
                f"告警处理完成: {metrics.format_summary()} "
                f"成功={len(successful_notifiers)} 失败={len(failed_notifiers)}"
            )
            
            if failed_notifiers:
                self.logger.warning(f"部分通知器发送失败: {failed_notifiers}")
            
            return alert_record
            
        except Exception as e:
            self.logger.error(f"发送告警失败: {e}")
            # 即使发送失败也要返回记录
            return AlertRecord(
                endpoint=metrics.endpoint,
                request_url=metrics.request_url,
                request_params=metrics.request_params,
                alert_time=metrics.timestamp,
                execution_time=metrics.execution_time,
                notification_status={'error': str(e)}
            )
    
    def _safe_send_notification(self, notifier: BaseNotifier, metrics: PerformanceMetrics, html_report: str) -> bool:
        """安全发送通知，确保通知失败不影响应用正常运行
        
        Args:
            notifier: 通知器实例
            metrics: 性能指标数据
            html_report: HTML报告
            
        Returns:
            bool: 发送是否成功
        """
        def _send():
            return notifier.send_notification(metrics, html_report)
        
        try:
            result = safe_execute(_send)
            return result is True
        except Exception as e:
            self.logger.error(f"通知发送异常: {notifier.__class__.__name__} - {e}")
            return False
    
    def process_metrics(self, metrics: PerformanceMetrics, html_report: str) -> Optional[AlertRecord]:
        """处理性能指标，判断是否告警并发送通知
        
        Args:
            metrics: 性能指标数据
            html_report: HTML报告
            
        Returns:
            Optional[AlertRecord]: 告警记录，未触发告警时返回None
        """
        try:
            if self.should_alert(metrics):
                return self.send_alert(metrics, html_report)
            else:
                return None
        except Exception as e:
            self.logger.error(f"处理性能指标失败: {e}")
            return None
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """获取告警统计信息
        
        Returns:
            Dict[str, Any]: 告警统计信息
        """
        try:
            cache_stats = self.cache_manager.get_cache_stats()
            recent_alerts = self.cache_manager.get_recent_alerts(24)  # 最近24小时
            
            return {
                'cache_stats': cache_stats,
                'recent_alerts_count': len(recent_alerts),
                'recent_alerts': recent_alerts[:10],  # 最近10条
                'enabled_notifiers': [notifier.__class__.__name__ for notifier in self.notifiers],
                'config': {
                    'threshold_seconds': self.config.threshold_seconds,
                    'alert_window_days': self.config.alert_window_days
                }
            }
        except Exception as e:
            self.logger.error(f"获取告警统计失败: {e}")
            return {'error': str(e)}
    
    def cleanup_old_alerts(self) -> int:
        """清理过期的告警记录
        
        Returns:
            int: 清理的记录数量
        """
        try:
            return self.cache_manager.cleanup_expired_entries(self.config.alert_window_days)
        except Exception as e:
            self.logger.error(f"清理过期告警失败: {e}")
            return 0
    
    def force_alert(self, metrics: PerformanceMetrics, html_report: str) -> AlertRecord:
        """强制发送告警（忽略重复检查）
        
        Args:
            metrics: 性能指标数据
            html_report: HTML报告
            
        Returns:
            AlertRecord: 告警记录
        """
        self.logger.info(f"强制发送告警: {metrics.endpoint}")
        return self.send_alert(metrics, html_report)
    
    def test_notifiers(self) -> Dict[str, bool]:
        """测试所有通知器的连通性
        
        Returns:
            Dict[str, bool]: 各通知器的测试结果
        """
        from datetime import datetime
        
        # 创建测试数据
        test_metrics = PerformanceMetrics(
            endpoint="/test",
            request_url="http://localhost/test",
            request_params={"test": True},
            execution_time=2.0,
            timestamp=datetime.now(),
            request_method="GET",
            status_code=200
        )
        
        test_html = "<html><body><h1>测试报告</h1><p>这是一个测试性能报告</p></body></html>"
        
        results = {}
        for notifier in self.notifiers:
            notifier_name = notifier.__class__.__name__
            try:
                # 检查配置有效性
                if hasattr(notifier, 'validate_config'):
                    if not notifier.validate_config():
                        results[notifier_name] = False
                        continue
                
                # 发送测试通知
                success = self._safe_send_notification(notifier, test_metrics, test_html)
                results[notifier_name] = success
                
            except Exception as e:
                self.logger.error(f"测试通知器失败: {notifier_name} - {e}")
                results[notifier_name] = False
        
        return results
    
    def reload_config(self, new_config: Config) -> None:
        """重新加载配置
        
        Args:
            new_config: 新的配置实例
        """
        try:
            self.config = new_config
            
            # 重新创建通知器
            self.notification_factory = NotificationFactory(new_config)
            self.notifiers = self.notification_factory.create_notifiers()
            
            self.logger.info(f"配置重新加载完成，启用 {len(self.notifiers)} 个通知器")
            
        except Exception as e:
            self.logger.error(f"重新加载配置失败: {e}")
            raise NotificationError(f"重新加载配置失败: {e}")