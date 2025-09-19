"""
框架插件系统基础模块

提供可扩展的框架支持架构，允许动态注册和发现新的框架支持。
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FrameworkType(Enum):
    """框架类型枚举"""
    WEB_FRAMEWORK = "web_framework"
    ASYNC_FRAMEWORK = "async_framework"
    NOTIFICATION_FRAMEWORK = "notification_framework"
    CUSTOM = "custom"


@dataclass
class FrameworkMetadata:
    """框架元数据"""
    name: str
    version_range: str
    framework_type: FrameworkType
    description: str
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    min_python_version: str = "3.7"
    homepage: str = ""
    documentation: str = ""
    installation_guide: str = ""
    
    def __post_init__(self):
        """后初始化验证"""
        if not self.name:
            raise ValueError("框架名称不能为空")
        if not self.version_range:
            raise ValueError("版本范围不能为空")


class FrameworkPlugin(ABC):
    """框架插件抽象基类"""
    
    def __init__(self, metadata: FrameworkMetadata):
        self.metadata = metadata
        self._is_available = None
        self._version_info = None
    
    @abstractmethod
    def is_installed(self) -> bool:
        """
        检查框架是否已安装
        
        Returns:
            bool: 框架是否已安装
        """
        pass
    
    @abstractmethod
    def get_version(self) -> Optional[str]:
        """
        获取已安装框架的版本
        
        Returns:
            Optional[str]: 框架版本，未安装时返回None
        """
        pass
    
    @abstractmethod
    def validate_dependencies(self) -> List[str]:
        """
        验证框架依赖
        
        Returns:
            List[str]: 缺失的依赖列表
        """
        pass
    
    @abstractmethod
    def create_monitor(self, config: Dict[str, Any]) -> Any:
        """
        创建框架特定的监控器
        
        Args:
            config (Dict[str, Any]): 监控器配置
            
        Returns:
            Any: 框架特定的监控器实例
        """
        pass
    
    def is_compatible(self, version: str) -> bool:
        """
        检查版本兼容性
        
        Args:
            version (str): 要检查的版本
            
        Returns:
            bool: 是否兼容
        """
        try:
            return self._check_version_compatibility(version, self.metadata.version_range)
        except Exception as e:
            logger.warning(f"版本兼容性检查失败 {self.metadata.name}: {e}")
            return False
    
    def _check_version_compatibility(self, version: str, version_range: str) -> bool:
        """
        检查版本兼容性的具体实现
        
        Args:
            version (str): 实际版本
            version_range (str): 支持的版本范围
            
        Returns:
            bool: 是否兼容
        """
        # 简单的版本比较实现
        # 实际项目中可以使用packaging.specifiers
        try:
            from packaging import version as pkg_version
            from packaging.specifiers import SpecifierSet
            
            spec = SpecifierSet(version_range)
            return pkg_version.parse(version) in spec
        except ImportError:
            # 如果packaging不可用，使用简单的字符串比较
            logger.debug("packaging库不可用，使用简单版本比较")
            return version >= version_range.replace(">=", "").strip()
    
    def get_installation_command(self) -> str:
        """
        获取安装命令
        
        Returns:
            str: pip安装命令
        """
        return f"pip install web-performance-monitor[{self.metadata.name}]"
    
    def get_status_info(self) -> Dict[str, Any]:
        """
        获取插件状态信息
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        return {
            'name': self.metadata.name,
            'type': self.metadata.framework_type.value,
            'installed': self.is_installed(),
            'version': self.get_version(),
            'compatible': self.is_compatible(self.get_version() or "0.0.0"),
            'missing_dependencies': self.validate_dependencies(),
            'installation_command': self.get_installation_command()
        }


class PluginRegistry:
    """插件注册表"""
    
    def __init__(self):
        self._plugins: Dict[str, FrameworkPlugin] = {}
        self._plugin_types: Dict[FrameworkType, List[str]] = {
            framework_type: [] for framework_type in FrameworkType
        }
        self._discovery_hooks: List[Callable[[], List[FrameworkPlugin]]] = []
    
    def register_plugin(self, plugin: FrameworkPlugin) -> None:
        """
        注册框架插件
        
        Args:
            plugin (FrameworkPlugin): 要注册的插件
        """
        if not isinstance(plugin, FrameworkPlugin):
            raise TypeError("插件必须继承自FrameworkPlugin")
        
        plugin_name = plugin.metadata.name
        
        if plugin_name in self._plugins:
            logger.warning(f"插件 {plugin_name} 已存在，将被覆盖")
        
        self._plugins[plugin_name] = plugin
        
        # 更新类型索引
        framework_type = plugin.metadata.framework_type
        if plugin_name not in self._plugin_types[framework_type]:
            self._plugin_types[framework_type].append(plugin_name)
        
        logger.info(f"已注册框架插件: {plugin_name}")
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """
        注销框架插件
        
        Args:
            plugin_name (str): 插件名称
            
        Returns:
            bool: 是否成功注销
        """
        if plugin_name not in self._plugins:
            return False
        
        plugin = self._plugins[plugin_name]
        framework_type = plugin.metadata.framework_type
        
        # 从类型索引中移除
        if plugin_name in self._plugin_types[framework_type]:
            self._plugin_types[framework_type].remove(plugin_name)
        
        # 从主注册表中移除
        del self._plugins[plugin_name]
        
        logger.info(f"已注销框架插件: {plugin_name}")
        return True
    
    def get_plugin(self, plugin_name: str) -> Optional[FrameworkPlugin]:
        """
        获取指定插件
        
        Args:
            plugin_name (str): 插件名称
            
        Returns:
            Optional[FrameworkPlugin]: 插件实例，不存在时返回None
        """
        return self._plugins.get(plugin_name)
    
    def get_plugins_by_type(self, framework_type: FrameworkType) -> List[FrameworkPlugin]:
        """
        按类型获取插件列表
        
        Args:
            framework_type (FrameworkType): 框架类型
            
        Returns:
            List[FrameworkPlugin]: 插件列表
        """
        plugin_names = self._plugin_types.get(framework_type, [])
        return [self._plugins[name] for name in plugin_names if name in self._plugins]
    
    def get_all_plugins(self) -> Dict[str, FrameworkPlugin]:
        """
        获取所有已注册的插件
        
        Returns:
            Dict[str, FrameworkPlugin]: 所有插件的字典
        """
        return self._plugins.copy()
    
    def get_installed_plugins(self) -> List[FrameworkPlugin]:
        """
        获取已安装的插件列表
        
        Returns:
            List[FrameworkPlugin]: 已安装的插件列表
        """
        return [plugin for plugin in self._plugins.values() if plugin.is_installed()]
    
    def get_available_plugins(self) -> List[FrameworkPlugin]:
        """
        获取可用的插件列表（已安装且依赖完整）
        
        Returns:
            List[FrameworkPlugin]: 可用的插件列表
        """
        available = []
        for plugin in self._plugins.values():
            if plugin.is_installed() and not plugin.validate_dependencies():
                available.append(plugin)
        return available
    
    def discover_plugins(self) -> int:
        """
        发现并注册新插件
        
        Returns:
            int: 发现的新插件数量
        """
        discovered_count = 0
        
        for discovery_hook in self._discovery_hooks:
            try:
                new_plugins = discovery_hook()
                for plugin in new_plugins:
                    if plugin.metadata.name not in self._plugins:
                        self.register_plugin(plugin)
                        discovered_count += 1
            except Exception as e:
                logger.error(f"插件发现钩子执行失败: {e}")
        
        return discovered_count
    
    def add_discovery_hook(self, hook: Callable[[], List[FrameworkPlugin]]) -> None:
        """
        添加插件发现钩子
        
        Args:
            hook (Callable): 发现钩子函数，应返回插件列表
        """
        if hook not in self._discovery_hooks:
            self._discovery_hooks.append(hook)
    
    def remove_discovery_hook(self, hook: Callable[[], List[FrameworkPlugin]]) -> bool:
        """
        移除插件发现钩子
        
        Args:
            hook (Callable): 要移除的钩子函数
            
        Returns:
            bool: 是否成功移除
        """
        try:
            self._discovery_hooks.remove(hook)
            return True
        except ValueError:
            return False
    
    def validate_all_plugins(self) -> Dict[str, List[str]]:
        """
        验证所有插件的依赖
        
        Returns:
            Dict[str, List[str]]: 插件名称到缺失依赖的映射
        """
        validation_results = {}
        
        for plugin_name, plugin in self._plugins.items():
            try:
                missing_deps = plugin.validate_dependencies()
                if missing_deps:
                    validation_results[plugin_name] = missing_deps
            except Exception as e:
                logger.error(f"验证插件 {plugin_name} 时出错: {e}")
                validation_results[plugin_name] = [f"验证失败: {e}"]
        
        return validation_results
    
    def get_registry_status(self) -> Dict[str, Any]:
        """
        获取注册表状态
        
        Returns:
            Dict[str, Any]: 注册表状态信息
        """
        total_plugins = len(self._plugins)
        installed_plugins = len(self.get_installed_plugins())
        available_plugins = len(self.get_available_plugins())
        
        type_counts = {}
        for framework_type, plugin_names in self._plugin_types.items():
            type_counts[framework_type.value] = len(plugin_names)
        
        return {
            'total_plugins': total_plugins,
            'installed_plugins': installed_plugins,
            'available_plugins': available_plugins,
            'plugins_by_type': type_counts,
            'discovery_hooks': len(self._discovery_hooks)
        }


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.registry = PluginRegistry()
        self._initialized = False
    
    def initialize(self) -> None:
        """初始化插件管理器"""
        if self._initialized:
            return
        
        # 注册内置插件
        self._register_builtin_plugins()
        
        # 发现外部插件
        self.registry.discover_plugins()
        
        self._initialized = True
        logger.info("插件管理器初始化完成")
    
    def _register_builtin_plugins(self) -> None:
        """注册内置插件"""
        try:
            # 注册Flask插件
            from ..plugins.flask_plugin import FlaskPlugin
            flask_plugin = FlaskPlugin()
            self.registry.register_plugin(flask_plugin)
        except ImportError as e:
            logger.debug(f"Flask插件注册失败: {e}")
        
        try:
            # 注册FastAPI插件
            from ..plugins.fastapi_plugin import FastAPIPlugin
            fastapi_plugin = FastAPIPlugin()
            self.registry.register_plugin(fastapi_plugin)
        except ImportError as e:
            logger.debug(f"FastAPI插件注册失败: {e}")
        
        try:
            # 注册通知插件
            from ..plugins.notification_plugin import NotificationPlugin
            notification_plugin = NotificationPlugin()
            self.registry.register_plugin(notification_plugin)
        except ImportError as e:
            logger.debug(f"通知插件注册失败: {e}")
        
        logger.info("内置插件注册完成")
    
    def create_monitor(self, framework_name: str, config: Dict[str, Any]) -> Any:
        """
        创建指定框架的监控器
        
        Args:
            framework_name (str): 框架名称
            config (Dict[str, Any]): 配置
            
        Returns:
            Any: 监控器实例
            
        Raises:
            ValueError: 框架不存在或不可用
        """
        plugin = self.registry.get_plugin(framework_name)
        if not plugin:
            raise ValueError(f"未找到框架插件: {framework_name}")
        
        if not plugin.is_installed():
            raise ValueError(f"框架 {framework_name} 未安装")
        
        missing_deps = plugin.validate_dependencies()
        if missing_deps:
            raise ValueError(f"框架 {framework_name} 缺少依赖: {', '.join(missing_deps)}")
        
        return plugin.create_monitor(config)
    
    def get_available_frameworks(self) -> List[str]:
        """
        获取可用框架列表
        
        Returns:
            List[str]: 可用框架名称列表
        """
        return [plugin.metadata.name for plugin in self.registry.get_available_plugins()]
    
    def get_framework_info(self, framework_name: str) -> Optional[Dict[str, Any]]:
        """
        获取框架信息
        
        Args:
            framework_name (str): 框架名称
            
        Returns:
            Optional[Dict[str, Any]]: 框架信息，不存在时返回None
        """
        plugin = self.registry.get_plugin(framework_name)
        if not plugin:
            return None
        
        return {
            'metadata': {
                'name': plugin.metadata.name,
                'version_range': plugin.metadata.version_range,
                'type': plugin.metadata.framework_type.value,
                'description': plugin.metadata.description,
                'dependencies': plugin.metadata.dependencies,
                'optional_dependencies': plugin.metadata.optional_dependencies,
                'min_python_version': plugin.metadata.min_python_version,
                'homepage': plugin.metadata.homepage,
                'documentation': plugin.metadata.documentation,
                'installation_guide': plugin.metadata.installation_guide
            },
            'status': plugin.get_status_info()
        }
    
    def register_external_plugin(self, plugin_class: Type[FrameworkPlugin], 
                                metadata: FrameworkMetadata) -> None:
        """
        注册外部插件
        
        Args:
            plugin_class (Type[FrameworkPlugin]): 插件类
            metadata (FrameworkMetadata): 插件元数据
        """
        plugin_instance = plugin_class(metadata)
        self.registry.register_plugin(plugin_instance)
    
    def get_installation_recommendations(self) -> List[Dict[str, Any]]:
        """
        获取安装建议
        
        Returns:
            List[Dict[str, Any]]: 安装建议列表
        """
        recommendations = []
        
        for plugin in self.registry.get_all_plugins().values():
            if not plugin.is_installed():
                recommendations.append({
                    'framework': plugin.metadata.name,
                    'type': plugin.metadata.framework_type.value,
                    'description': plugin.metadata.description,
                    'command': plugin.get_installation_command(),
                    'priority': self._calculate_recommendation_priority(plugin)
                })
        
        # 按优先级排序
        recommendations.sort(key=lambda x: x['priority'], reverse=True)
        return recommendations
    
    def _calculate_recommendation_priority(self, plugin: FrameworkPlugin) -> int:
        """
        计算推荐优先级
        
        Args:
            plugin (FrameworkPlugin): 插件实例
            
        Returns:
            int: 优先级分数
        """
        priority = 0
        
        # Web框架优先级更高
        if plugin.metadata.framework_type == FrameworkType.WEB_FRAMEWORK:
            priority += 10
        elif plugin.metadata.framework_type == FrameworkType.ASYNC_FRAMEWORK:
            priority += 8
        elif plugin.metadata.framework_type == FrameworkType.NOTIFICATION_FRAMEWORK:
            priority += 5
        
        # 依赖较少的优先级更高
        priority -= len(plugin.metadata.dependencies)
        
        return priority


# 全局插件管理器实例
_plugin_manager = None


def get_plugin_manager() -> PluginManager:
    """
    获取全局插件管理器实例
    
    Returns:
        PluginManager: 插件管理器实例
    """
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
        _plugin_manager.initialize()
    return _plugin_manager


def register_framework_plugin(plugin_class: Type[FrameworkPlugin], 
                             metadata: FrameworkMetadata) -> None:
    """
    注册框架插件的便捷函数
    
    Args:
        plugin_class (Type[FrameworkPlugin]): 插件类
        metadata (FrameworkMetadata): 插件元数据
    """
    manager = get_plugin_manager()
    manager.register_external_plugin(plugin_class, metadata)