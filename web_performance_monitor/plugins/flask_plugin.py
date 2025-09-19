"""
Flask框架插件实现
"""

import logging
from typing import Dict, List, Optional, Any

from ..core.plugin_system import FrameworkPlugin, FrameworkMetadata, FrameworkType

logger = logging.getLogger(__name__)


class FlaskPlugin(FrameworkPlugin):
    """Flask框架插件"""
    
    def __init__(self):
        metadata = FrameworkMetadata(
            name="flask",
            version_range=">=2.0.0",
            framework_type=FrameworkType.WEB_FRAMEWORK,
            description="Flask web框架监控支持",
            dependencies=["flask"],
            optional_dependencies=[],
            min_python_version="3.7",
            homepage="https://flask.palletsprojects.com/",
            documentation="https://flask.palletsprojects.com/en/2.3.x/",
            installation_guide="pip install web-performance-monitor[flask]"
        )
        super().__init__(metadata)
    
    def is_installed(self) -> bool:
        """检查Flask是否已安装"""
        try:
            import flask
            return True
        except ImportError:
            return False
    
    def get_version(self) -> Optional[str]:
        """获取Flask版本"""
        try:
            import flask
            return flask.__version__
        except (ImportError, AttributeError):
            return None
    
    def validate_dependencies(self) -> List[str]:
        """验证Flask依赖"""
        missing_deps = []
        
        try:
            import flask
            # 检查版本兼容性
            version = flask.__version__
            if not self.is_compatible(version):
                missing_deps.append(f"flask>={self.metadata.version_range} (当前版本: {version})")
        except ImportError:
            missing_deps.append("flask")
        
        return missing_deps
    
    def create_monitor(self, config: Dict[str, Any]) -> Any:
        """创建Flask监控器"""
        try:
            from ..monitors.flask_monitor import FlaskMonitor
            return FlaskMonitor(config)
        except ImportError as e:
            logger.error(f"创建Flask监控器失败: {e}")
            raise ValueError(f"无法创建Flask监控器: {e}")
    
    def get_middleware_class(self):
        """获取Flask中间件类"""
        try:
            from ..monitors.flask_monitor import FlaskMiddleware
            return FlaskMiddleware
        except ImportError:
            return None
    
    def get_decorator_function(self):
        """获取Flask装饰器函数"""
        try:
            from ..monitors.flask_monitor import flask_performance_monitor
            return flask_performance_monitor
        except ImportError:
            return None
    
    def get_integration_examples(self) -> Dict[str, str]:
        """获取集成示例"""
        return {
            "middleware": """
from flask import Flask
from web_performance_monitor import create_web_monitor

app = Flask(__name__)
monitor = create_web_monitor('flask')

# 使用中间件
app.wsgi_app = monitor.get_middleware()(app.wsgi_app)

@app.route('/')
def hello():
    return 'Hello, World!'
""",
            "decorator": """
from flask import Flask
from web_performance_monitor import create_web_monitor

app = Flask(__name__)
monitor = create_web_monitor('flask')

@app.route('/')
@monitor.monitor_endpoint()
def hello():
    return 'Hello, World!'
""",
            "manual": """
from flask import Flask
from web_performance_monitor import create_web_monitor

app = Flask(__name__)
monitor = create_web_monitor('flask')

@app.route('/')
def hello():
    with monitor.track_request():
        # 你的业务逻辑
        return 'Hello, World!'
"""
        }
    
    def get_configuration_options(self) -> Dict[str, Any]:
        """获取配置选项"""
        return {
            "auto_instrument": {
                "type": "boolean",
                "default": True,
                "description": "是否自动监控所有路由"
            },
            "track_templates": {
                "type": "boolean", 
                "default": True,
                "description": "是否跟踪模板渲染时间"
            },
            "track_database": {
                "type": "boolean",
                "default": True,
                "description": "是否跟踪数据库查询"
            },
            "exclude_paths": {
                "type": "list",
                "default": ["/health", "/metrics"],
                "description": "排除监控的路径列表"
            },
            "sample_rate": {
                "type": "float",
                "default": 1.0,
                "description": "采样率 (0.0-1.0)"
            }
        }
    
    def validate_configuration(self, config: Dict[str, Any]) -> List[str]:
        """验证配置"""
        errors = []
        
        if "sample_rate" in config:
            sample_rate = config["sample_rate"]
            if not isinstance(sample_rate, (int, float)) or not 0.0 <= sample_rate <= 1.0:
                errors.append("sample_rate必须是0.0到1.0之间的数字")
        
        if "exclude_paths" in config:
            exclude_paths = config["exclude_paths"]
            if not isinstance(exclude_paths, list):
                errors.append("exclude_paths必须是列表类型")
            elif not all(isinstance(path, str) for path in exclude_paths):
                errors.append("exclude_paths中的所有项目必须是字符串")
        
        return errors