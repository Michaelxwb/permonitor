"""
优雅降级机制模块

处理依赖缺失情况，提供有限功能而不是完全失败。
"""

import logging
import warnings
from typing import List, Dict, Optional, Callable, Any
from functools import wraps

from ..exceptions.exceptions import MissingDependencyError, DependencyError
from ..utils.framework_detector import FrameworkDetector

logger = logging.getLogger(__name__)


class GracefulDegradation:
    """优雅降级处理器"""
    
    # 功能可用性缓存
    _feature_availability_cache: Dict[str, bool] = {}
    
    @staticmethod
    def handle_missing_framework(framework: str, fallback_action: str = "warn") -> bool:
        """
        处理缺失框架的情况
        
        Args:
            framework (str): 缺失的框架名称
            fallback_action (str): 回退动作 ("warn", "error", "silent")
            
        Returns:
            bool: 是否可以继续执行（在降级模式下）
        """
        message = f"框架 {framework} 不可用，某些功能将被禁用"
        installation_guide = f"安装 {framework} 支持: pip install web-performance-monitor[{framework}]"
        
        if fallback_action == "error":
            logger.error(f"{message}。{installation_guide}")
            return False
        elif fallback_action == "warn":
            logger.warning(f"{message}。{installation_guide}")
            warnings.warn(
                f"Framework {framework} is not available. Some features will be disabled. "
                f"Install with: pip install web-performance-monitor[{framework}]",
                UserWarning,
                stacklevel=3
            )
        elif fallback_action == "silent":
            logger.debug(f"{message}。{installation_guide}")
        
        return True
    
    @staticmethod
    def provide_limited_functionality(available_features: List[str]) -> Dict[str, Any]:
        """
        在依赖不完整时提供有限功能
        
        Args:
            available_features (List[str]): 可用功能列表
            
        Returns:
            Dict[str, Any]: 功能状态和建议
        """
        all_features = [
            "flask_middleware",
            "flask_decorator", 
            "fastapi_middleware",
            "async_monitoring",
            "mattermost_notifications",
            "file_notifications",
            "performance_analysis"
        ]
        
        unavailable_features = [f for f in all_features if f not in available_features]
        
        status = {
            "available_features": available_features,
            "unavailable_features": unavailable_features,
            "functionality_level": len(available_features) / len(all_features),
            "recommendations": []
        }
        
        # 生成功能建议
        if "flask_middleware" not in available_features or "flask_decorator" not in available_features:
            status["recommendations"].append(
                "安装Flask支持以启用Flask中间件和装饰器: pip install web-performance-monitor[flask]"
            )
        
        if "fastapi_middleware" not in available_features or "async_monitoring" not in available_features:
            status["recommendations"].append(
                "安装FastAPI支持以启用异步监控: pip install web-performance-monitor[fastapi]"
            )
        
        if "mattermost_notifications" not in available_features:
            status["recommendations"].append(
                "安装通知支持以启用Mattermost通知: pip install web-performance-monitor[notifications]"
            )
        
        return status
    
    @staticmethod
    def handle_missing_notification_deps() -> Dict[str, bool]:
        """
        处理通知依赖缺失，自动禁用对应通知渠道
        
        Returns:
            Dict[str, bool]: 通知渠道可用性状态
        """
        notification_status = {
            "mattermost": False,
            "file": True,  # 文件通知总是可用
            "console": True  # 控制台通知总是可用
        }
        
        # 检查Mattermost依赖
        try:
            import mattermostdriver
            notification_status["mattermost"] = True
            logger.debug("Mattermost通知可用")
        except ImportError:
            logger.info("Mattermost依赖不可用，已禁用Mattermost通知。安装命令: pip install web-performance-monitor[notifications]")
        
        return notification_status
    
    @staticmethod
    def check_feature_availability(feature_name: str) -> bool:
        """
        检查特定功能的可用性
        
        Args:
            feature_name (str): 功能名称
            
        Returns:
            bool: 功能是否可用
        """
        # 使用缓存避免重复检查
        if feature_name in GracefulDegradation._feature_availability_cache:
            return GracefulDegradation._feature_availability_cache[feature_name]
        
        detector = FrameworkDetector()
        available = False
        
        if feature_name in ["flask_middleware", "flask_decorator"]:
            available = detector.is_framework_available("flask")
        elif feature_name in ["fastapi_middleware", "async_monitoring"]:
            available = detector.is_framework_available("fastapi")
            if available and feature_name == "async_monitoring":
                # 检查异步依赖
                async_deps = detector.check_fastapi_async_dependencies()
                available = all(async_deps.values())
        elif feature_name == "mattermost_notifications":
            try:
                import mattermostdriver
                available = True
            except ImportError:
                available = False
        elif feature_name in ["file_notifications", "console_notifications", "performance_analysis"]:
            available = True  # 这些功能总是可用
        
        # 缓存结果
        GracefulDegradation._feature_availability_cache[feature_name] = available
        return available
    
    @staticmethod
    def clear_feature_cache():
        """清除功能可用性缓存"""
        GracefulDegradation._feature_availability_cache.clear()
    
    @staticmethod
    def get_degraded_config(original_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取降级后的配置
        
        Args:
            original_config (Dict[str, Any]): 原始配置
            
        Returns:
            Dict[str, Any]: 降级后的配置
        """
        degraded_config = original_config.copy()
        
        # 检查并禁用不可用的通知渠道
        notification_status = GracefulDegradation.handle_missing_notification_deps()
        
        if "notifications" in degraded_config:
            available_notifications = []
            for notification in degraded_config["notifications"]:
                if isinstance(notification, dict):
                    notification_type = notification.get("type", "").lower()
                elif isinstance(notification, str):
                    notification_type = notification.lower()
                else:
                    continue
                
                if notification_type in notification_status and notification_status[notification_type]:
                    available_notifications.append(notification)
                else:
                    logger.info(f"禁用不可用的通知类型: {notification_type}")
            
            degraded_config["notifications"] = available_notifications
        
        return degraded_config


def require_framework(framework: str, fallback_action: str = "warn"):
    """
    装饰器：要求特定框架可用
    
    Args:
        framework (str): 需要的框架名称
        fallback_action (str): 回退动作
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            detector = FrameworkDetector()
            
            if not detector.is_framework_available(framework):
                can_continue = GracefulDegradation.handle_missing_framework(framework, fallback_action)
                
                if not can_continue:
                    raise MissingDependencyError(framework, [framework])
                
                # 在降级模式下，返回一个空的结果或默认值
                logger.info(f"在降级模式下执行 {func.__name__}")
                return None
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_feature(feature_name: str, fallback_value: Any = None):
    """
    装饰器：要求特定功能可用
    
    Args:
        feature_name (str): 功能名称
        fallback_value (Any): 功能不可用时的回退值
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not GracefulDegradation.check_feature_availability(feature_name):
                logger.warning(f"功能 {feature_name} 不可用，返回回退值")
                return fallback_value
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


class FeatureGate:
    """功能门控，用于控制功能的可用性"""
    
    def __init__(self):
        self.detector = FrameworkDetector()
        self._gates: Dict[str, bool] = {}
    
    def is_enabled(self, feature_name: str) -> bool:
        """
        检查功能是否启用
        
        Args:
            feature_name (str): 功能名称
            
        Returns:
            bool: 功能是否启用
        """
        if feature_name in self._gates:
            return self._gates[feature_name]
        
        return GracefulDegradation.check_feature_availability(feature_name)
    
    def enable_feature(self, feature_name: str):
        """强制启用功能"""
        self._gates[feature_name] = True
    
    def disable_feature(self, feature_name: str):
        """强制禁用功能"""
        self._gates[feature_name] = False
    
    def reset_feature(self, feature_name: str):
        """重置功能状态（使用自动检测）"""
        if feature_name in self._gates:
            del self._gates[feature_name]
    
    def get_available_features(self) -> List[str]:
        """获取所有可用功能列表"""
        all_features = [
            "flask_middleware",
            "flask_decorator", 
            "fastapi_middleware",
            "async_monitoring",
            "mattermost_notifications",
            "file_notifications",
            "performance_analysis"
        ]
        
        return [feature for feature in all_features if self.is_enabled(feature)]
    
    def get_feature_report(self) -> Dict[str, Any]:
        """获取功能可用性报告"""
        all_features = [
            "flask_middleware",
            "flask_decorator", 
            "fastapi_middleware", 
            "async_monitoring",
            "mattermost_notifications",
            "file_notifications",
            "performance_analysis"
        ]
        
        report = {
            "available_features": [],
            "unavailable_features": [],
            "feature_details": {}
        }
        
        for feature in all_features:
            is_available = self.is_enabled(feature)
            
            if is_available:
                report["available_features"].append(feature)
            else:
                report["unavailable_features"].append(feature)
            
            report["feature_details"][feature] = {
                "available": is_available,
                "reason": self._get_unavailability_reason(feature) if not is_available else None
            }
        
        return report
    
    def _get_unavailability_reason(self, feature_name: str) -> str:
        """获取功能不可用的原因"""
        if feature_name in ["flask_middleware", "flask_decorator"]:
            return "Flask framework not installed"
        elif feature_name in ["fastapi_middleware", "async_monitoring"]:
            if not self.detector.is_framework_available("fastapi"):
                return "FastAPI framework not installed"
            else:
                async_deps = self.detector.check_fastapi_async_dependencies()
                missing = [dep for dep, available in async_deps.items() if not available]
                if missing:
                    return f"Missing async dependencies: {', '.join(missing)}"
        elif feature_name == "mattermost_notifications":
            return "mattermostdriver package not installed"
        
        return "Unknown reason"