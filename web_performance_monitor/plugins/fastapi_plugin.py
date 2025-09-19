"""
FastAPI框架插件实现
"""

import logging
from typing import Dict, List, Optional, Any

from ..core.plugin_system import FrameworkPlugin, FrameworkMetadata, FrameworkType

logger = logging.getLogger(__name__)


class FastAPIPlugin(FrameworkPlugin):
    """FastAPI框架插件"""
    
    def __init__(self):
        metadata = FrameworkMetadata(
            name="fastapi",
            version_range=">=0.100.0",
            framework_type=FrameworkType.ASYNC_FRAMEWORK,
            description="FastAPI异步web框架监控支持",
            dependencies=["fastapi", "uvicorn", "aiofiles", "aiohttp"],
            optional_dependencies=["starlette"],
            min_python_version="3.7",
            homepage="https://fastapi.tiangolo.com/",
            documentation="https://fastapi.tiangolo.com/",
            installation_guide="pip install web-performance-monitor[fastapi]"
        )
        super().__init__(metadata)
    
    def is_installed(self) -> bool:
        """检查FastAPI是否已安装"""
        try:
            import fastapi
            return True
        except ImportError:
            return False
    
    def get_version(self) -> Optional[str]:
        """获取FastAPI版本"""
        try:
            import fastapi
            return fastapi.__version__
        except (ImportError, AttributeError):
            return None
    
    def validate_dependencies(self) -> List[str]:
        """验证FastAPI依赖"""
        missing_deps = []
        
        # 检查核心依赖
        core_deps = {
            "fastapi": "FastAPI核心库",
            "uvicorn": "ASGI服务器",
            "aiofiles": "异步文件操作",
            "aiohttp": "异步HTTP客户端"
        }
        
        for dep, description in core_deps.items():
            try:
                __import__(dep)
            except ImportError:
                missing_deps.append(f"{dep} ({description})")
        
        # 检查FastAPI版本兼容性
        try:
            import fastapi
            version = fastapi.__version__
            if not self.is_compatible(version):
                missing_deps.append(f"fastapi>={self.metadata.version_range} (当前版本: {version})")
        except ImportError:
            pass  # 已在上面检查过
        
        return missing_deps
    
    def create_monitor(self, config: Dict[str, Any]) -> Any:
        """创建FastAPI监控器"""
        try:
            from ..monitors.fastapi_monitor import FastAPIMonitor
            return FastAPIMonitor(config)
        except ImportError as e:
            logger.error(f"创建FastAPI监控器失败: {e}")
            raise ValueError(f"无法创建FastAPI监控器: {e}")
    
    def get_middleware_class(self):
        """获取FastAPI中间件类"""
        try:
            from ..monitors.fastapi_monitor import FastAPIMiddleware
            return FastAPIMiddleware
        except ImportError:
            return None
    
    def get_decorator_function(self):
        """获取FastAPI装饰器函数"""
        try:
            from ..monitors.fastapi_monitor import fastapi_performance_monitor
            return fastapi_performance_monitor
        except ImportError:
            return None
    
    def get_integration_examples(self) -> Dict[str, str]:
        """获取集成示例"""
        return {
            "middleware": """
from fastapi import FastAPI
from web_performance_monitor import create_web_monitor

app = FastAPI()
monitor = create_web_monitor('fastapi')

# 添加中间件
app.add_middleware(monitor.get_middleware())

@app.get("/")
async def read_root():
    return {"Hello": "World"}
""",
            "decorator": """
from fastapi import FastAPI
from web_performance_monitor import create_web_monitor

app = FastAPI()
monitor = create_web_monitor('fastapi')

@app.get("/")
@monitor.monitor_endpoint()
async def read_root():
    return {"Hello": "World"}
""",
            "manual": """
from fastapi import FastAPI
from web_performance_monitor import create_web_monitor

app = FastAPI()
monitor = create_web_monitor('fastapi')

@app.get("/")
async def read_root():
    async with monitor.track_request():
        # 你的业务逻辑
        return {"Hello": "World"}
""",
            "dependency_injection": """
from fastapi import FastAPI, Depends
from web_performance_monitor import create_web_monitor

app = FastAPI()
monitor = create_web_monitor('fastapi')

def get_monitor():
    return monitor

@app.get("/")
async def read_root(monitor = Depends(get_monitor)):
    with monitor.track_operation("custom_operation"):
        # 你的业务逻辑
        return {"Hello": "World"}
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
            "track_background_tasks": {
                "type": "boolean",
                "default": True,
                "description": "是否跟踪后台任务"
            },
            "track_websockets": {
                "type": "boolean",
                "default": False,
                "description": "是否跟踪WebSocket连接"
            },
            "track_startup_shutdown": {
                "type": "boolean",
                "default": True,
                "description": "是否跟踪启动和关闭事件"
            },
            "exclude_paths": {
                "type": "list",
                "default": ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"],
                "description": "排除监控的路径列表"
            },
            "sample_rate": {
                "type": "float",
                "default": 1.0,
                "description": "采样率 (0.0-1.0)"
            },
            "async_context_timeout": {
                "type": "float",
                "default": 30.0,
                "description": "异步上下文超时时间（秒）"
            }
        }
    
    def validate_configuration(self, config: Dict[str, Any]) -> List[str]:
        """验证配置"""
        errors = []
        
        if "sample_rate" in config:
            sample_rate = config["sample_rate"]
            if not isinstance(sample_rate, (int, float)) or not 0.0 <= sample_rate <= 1.0:
                errors.append("sample_rate必须是0.0到1.0之间的数字")
        
        if "async_context_timeout" in config:
            timeout = config["async_context_timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                errors.append("async_context_timeout必须是正数")
        
        if "exclude_paths" in config:
            exclude_paths = config["exclude_paths"]
            if not isinstance(exclude_paths, list):
                errors.append("exclude_paths必须是列表类型")
            elif not all(isinstance(path, str) for path in exclude_paths):
                errors.append("exclude_paths中的所有项目必须是字符串")
        
        return errors
    
    def get_performance_tips(self) -> List[str]:
        """获取性能优化建议"""
        return [
            "使用异步数据库驱动（如asyncpg、aiomysql）以获得最佳性能",
            "合理设置uvicorn的worker数量，通常为CPU核心数的2倍",
            "使用连接池来管理数据库连接",
            "对于CPU密集型任务，考虑使用后台任务或任务队列",
            "启用HTTP/2支持以提高并发性能",
            "使用适当的缓存策略减少重复计算",
            "监控内存使用，避免内存泄漏"
        ]
    
    def get_troubleshooting_guide(self) -> Dict[str, str]:
        """获取故障排除指南"""
        return {
            "import_error": """
如果遇到导入错误：
1. 确保安装了所有必需的依赖：pip install web-performance-monitor[fastapi]
2. 检查Python版本是否>=3.7
3. 验证虚拟环境是否正确激活
""",
            "async_issues": """
如果遇到异步相关问题：
1. 确保所有数据库操作使用异步驱动
2. 在异步函数中使用await关键字
3. 避免在异步上下文中使用同步阻塞操作
""",
            "performance_issues": """
如果遇到性能问题：
1. 检查是否有同步阻塞操作
2. 监控数据库连接池使用情况
3. 使用性能分析工具识别瓶颈
4. 考虑启用请求采样以减少监控开销
""",
            "middleware_conflicts": """
如果中间件冲突：
1. 检查中间件添加顺序
2. 确保监控中间件在其他中间件之前添加
3. 避免重复添加相同的中间件
"""
        }