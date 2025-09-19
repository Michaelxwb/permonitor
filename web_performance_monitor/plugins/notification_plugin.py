"""
通知框架插件实现
"""

import logging
from typing import Dict, List, Optional, Any

from ..core.plugin_system import FrameworkPlugin, FrameworkMetadata, FrameworkType

logger = logging.getLogger(__name__)


class NotificationPlugin(FrameworkPlugin):
    """通知框架插件"""
    
    def __init__(self):
        metadata = FrameworkMetadata(
            name="notifications",
            version_range=">=7.0.0",
            framework_type=FrameworkType.NOTIFICATION_FRAMEWORK,
            description="Mattermost通知支持",
            dependencies=["mattermostdriver"],
            optional_dependencies=[],
            min_python_version="3.7",
            homepage="https://github.com/Vaelor/python-mattermost-driver",
            documentation="https://vaelor.github.io/python-mattermost-driver/",
            installation_guide="pip install web-performance-monitor[notifications]"
        )
        super().__init__(metadata)
    
    def is_installed(self) -> bool:
        """检查通知依赖是否已安装"""
        try:
            import mattermostdriver
            return True
        except ImportError:
            return False
    
    def get_version(self) -> Optional[str]:
        """获取mattermostdriver版本"""
        try:
            import mattermostdriver
            return mattermostdriver.__version__
        except (ImportError, AttributeError):
            return None
    
    def validate_dependencies(self) -> List[str]:
        """验证通知依赖"""
        missing_deps = []
        
        try:
            import mattermostdriver
            # 检查版本兼容性
            version = mattermostdriver.__version__
            if not self.is_compatible(version):
                missing_deps.append(f"mattermostdriver>={self.metadata.version_range} (当前版本: {version})")
        except ImportError:
            missing_deps.append("mattermostdriver")
        
        return missing_deps
    
    def create_monitor(self, config: Dict[str, Any]) -> Any:
        """创建通知监控器"""
        try:
            from ..notifications.mattermost_notifier import MattermostNotifier
            return MattermostNotifier(config)
        except ImportError as e:
            logger.error(f"创建通知监控器失败: {e}")
            raise ValueError(f"无法创建通知监控器: {e}")
    
    def get_notifier_class(self):
        """获取通知器类"""
        try:
            from ..notifications.mattermost_notifier import MattermostNotifier
            return MattermostNotifier
        except ImportError:
            return None
    
    def get_integration_examples(self) -> Dict[str, str]:
        """获取集成示例"""
        return {
            "basic_setup": """
from web_performance_monitor import create_web_monitor

# 配置通知
config = {
    'notifications': {
        'mattermost': {
            'url': 'https://your-mattermost-server.com',
            'token': 'your-bot-token',
            'channel': 'monitoring-alerts'
        }
    }
}

monitor = create_web_monitor('flask', config)
""",
            "custom_alerts": """
from web_performance_monitor.notifications import MattermostNotifier

notifier = MattermostNotifier({
    'url': 'https://your-mattermost-server.com',
    'token': 'your-bot-token',
    'channel': 'alerts'
})

# 发送自定义警报
notifier.send_alert(
    title="性能警报",
    message="响应时间超过阈值",
    severity="warning",
    metrics={'response_time': 2.5}
)
""",
            "threshold_monitoring": """
from web_performance_monitor import create_web_monitor

config = {
    'thresholds': {
        'response_time': 1.0,  # 1秒
        'error_rate': 0.05     # 5%
    },
    'notifications': {
        'mattermost': {
            'url': 'https://your-mattermost-server.com',
            'token': 'your-bot-token',
            'channel': 'performance-alerts',
            'alert_on_threshold': True
        }
    }
}

monitor = create_web_monitor('fastapi', config)
"""
        }
    
    def get_configuration_options(self) -> Dict[str, Any]:
        """获取配置选项"""
        return {
            "url": {
                "type": "string",
                "required": True,
                "description": "Mattermost服务器URL"
            },
            "token": {
                "type": "string",
                "required": True,
                "description": "Bot访问令牌"
            },
            "channel": {
                "type": "string",
                "default": "monitoring",
                "description": "发送通知的频道"
            },
            "username": {
                "type": "string",
                "default": "Performance Monitor",
                "description": "Bot显示名称"
            },
            "icon_url": {
                "type": "string",
                "default": "",
                "description": "Bot头像URL"
            },
            "alert_on_threshold": {
                "type": "boolean",
                "default": True,
                "description": "是否在超过阈值时发送警报"
            },
            "alert_on_error": {
                "type": "boolean",
                "default": True,
                "description": "是否在发生错误时发送警报"
            },
            "batch_notifications": {
                "type": "boolean",
                "default": False,
                "description": "是否批量发送通知"
            },
            "batch_interval": {
                "type": "integer",
                "default": 300,
                "description": "批量发送间隔（秒）"
            },
            "rate_limit": {
                "type": "integer",
                "default": 10,
                "description": "每分钟最大通知数量"
            },
            "timeout": {
                "type": "float",
                "default": 10.0,
                "description": "请求超时时间（秒）"
            }
        }
    
    def validate_configuration(self, config: Dict[str, Any]) -> List[str]:
        """验证配置"""
        errors = []
        
        # 检查必需字段
        required_fields = ["url", "token"]
        for field in required_fields:
            if field not in config or not config[field]:
                errors.append(f"缺少必需的配置项: {field}")
        
        # 验证URL格式
        if "url" in config:
            url = config["url"]
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                errors.append("url必须是有效的HTTP/HTTPS URL")
        
        # 验证数值类型
        numeric_fields = {
            "batch_interval": (int, lambda x: x > 0, "必须是正整数"),
            "rate_limit": (int, lambda x: x > 0, "必须是正整数"),
            "timeout": ((int, float), lambda x: x > 0, "必须是正数")
        }
        
        for field, (expected_type, validator, error_msg) in numeric_fields.items():
            if field in config:
                value = config[field]
                if not isinstance(value, expected_type):
                    errors.append(f"{field}类型错误: {error_msg}")
                elif not validator(value):
                    errors.append(f"{field}值错误: {error_msg}")
        
        return errors
    
    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """测试连接"""
        try:
            from ..notifications.mattermost_notifier import MattermostNotifier
            
            notifier = MattermostNotifier(config)
            result = notifier.test_connection()
            
            return {
                "success": result,
                "message": "连接成功" if result else "连接失败",
                "timestamp": __import__("datetime").datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"连接测试失败: {e}",
                "timestamp": __import__("datetime").datetime.now().isoformat()
            }
    
    def get_supported_alert_types(self) -> List[str]:
        """获取支持的警报类型"""
        return [
            "threshold_exceeded",    # 阈值超出
            "error_occurred",       # 错误发生
            "performance_degraded", # 性能下降
            "system_status",        # 系统状态
            "custom_metric",        # 自定义指标
            "health_check"          # 健康检查
        ]
    
    def get_message_templates(self) -> Dict[str, str]:
        """获取消息模板"""
        return {
            "threshold_exceeded": """
🚨 **性能警报**

**服务**: {service_name}
**指标**: {metric_name}
**当前值**: {current_value}
**阈值**: {threshold}
**时间**: {timestamp}

请检查系统性能状况。
""",
            "error_occurred": """
❌ **错误警报**

**服务**: {service_name}
**错误类型**: {error_type}
**错误消息**: {error_message}
**时间**: {timestamp}

请立即检查系统状态。
""",
            "performance_degraded": """
⚠️ **性能下降警报**

**服务**: {service_name}
**影响指标**: {affected_metrics}
**下降幅度**: {degradation_percentage}%
**时间**: {timestamp}

建议检查系统负载和资源使用情况。
""",
            "system_status": """
ℹ️ **系统状态报告**

**服务**: {service_name}
**状态**: {status}
**详细信息**: {details}
**时间**: {timestamp}
""",
            "health_check": """
💚 **健康检查报告**

**服务**: {service_name}
**状态**: {health_status}
**检查项目**: {check_items}
**时间**: {timestamp}
"""
        }