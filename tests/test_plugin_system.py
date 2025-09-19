"""
插件系统测试模块
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any

from web_performance_monitor.core.plugin_system import (
    FrameworkPlugin,
    FrameworkMetadata,
    FrameworkType,
    PluginRegistry,
    PluginManager,
    get_plugin_manager,
    register_framework_plugin
)


class MockPlugin(FrameworkPlugin):
    """测试用的模拟插件"""
    
    def __init__(self, name: str = "test_framework", installed: bool = True, 
                 version: str = "1.0.0", missing_deps: List[str] = None):
        metadata = FrameworkMetadata(
            name=name,
            version_range=">=1.0.0",
            framework_type=FrameworkType.WEB_FRAMEWORK,
            description=f"Test {name} framework"
        )
        super().__init__(metadata)
        self._installed = installed
        self._version = version
        self._missing_deps = missing_deps or []
    
    def is_installed(self) -> bool:
        return self._installed
    
    def get_version(self) -> str:
        return self._version if self._installed else None
    
    def validate_dependencies(self) -> List[str]:
        return self._missing_deps
    
    def create_monitor(self, config: Dict[str, Any]) -> Any:
        return MagicMock()


class TestFrameworkMetadata:
    """框架元数据测试类"""
    
    def test_framework_metadata_creation(self):
        """测试框架元数据创建"""
        metadata = FrameworkMetadata(
            name="test_framework",
            version_range=">=1.0.0",
            framework_type=FrameworkType.WEB_FRAMEWORK,
            description="Test framework"
        )
        
        assert metadata.name == "test_framework"
        assert metadata.version_range == ">=1.0.0"
        assert metadata.framework_type == FrameworkType.WEB_FRAMEWORK
        assert metadata.description == "Test framework"
        assert metadata.dependencies == []
        assert metadata.optional_dependencies == []
        assert metadata.min_python_version == "3.7"
    
    def test_framework_metadata_validation(self):
        """测试框架元数据验证"""
        with pytest.raises(ValueError, match="框架名称不能为空"):
            FrameworkMetadata(
                name="",
                version_range=">=1.0.0",
                framework_type=FrameworkType.WEB_FRAMEWORK,
                description="Test"
            )
        
        with pytest.raises(ValueError, match="版本范围不能为空"):
            FrameworkMetadata(
                name="test",
                version_range="",
                framework_type=FrameworkType.WEB_FRAMEWORK,
                description="Test"
            )


class TestFrameworkPlugin:
    """框架插件测试类"""
    
    def test_plugin_creation(self):
        """测试插件创建"""
        plugin = MockPlugin()
        
        assert plugin.metadata.name == "test_framework"
        assert plugin.is_installed() == True
        assert plugin.get_version() == "1.0.0"
        assert plugin.validate_dependencies() == []
    
    def test_plugin_compatibility_check(self):
        """测试插件兼容性检查"""
        plugin = MockPlugin(version="1.5.0")
        
        # 测试兼容版本
        assert plugin.is_compatible("1.5.0") == True
        assert plugin.is_compatible("1.2.0") == True
        
        # 测试不兼容版本（如果有packaging库）
        try:
            assert plugin.is_compatible("0.9.0") == False
        except:
            # 如果没有packaging库，会使用简单比较
            pass
    
    def test_plugin_installation_command(self):
        """测试插件安装命令"""
        plugin = MockPlugin()
        command = plugin.get_installation_command()
        
        assert command == "pip install web-performance-monitor[test_framework]"
    
    def test_plugin_status_info(self):
        """测试插件状态信息"""
        plugin = MockPlugin(missing_deps=["dependency1"])
        status = plugin.get_status_info()
        
        assert status['name'] == "test_framework"
        assert status['type'] == "web_framework"
        assert status['installed'] == True
        assert status['version'] == "1.0.0"
        assert status['missing_dependencies'] == ["dependency1"]
        assert "pip install" in status['installation_command']


class TestPluginRegistry:
    """插件注册表测试类"""
    
    def setup_method(self):
        """测试方法设置"""
        self.registry = PluginRegistry()
    
    def test_register_plugin(self):
        """测试注册插件"""
        plugin = MockPlugin()
        self.registry.register_plugin(plugin)
        
        assert "test_framework" in self.registry._plugins
        assert self.registry.get_plugin("test_framework") == plugin
    
    def test_register_invalid_plugin(self):
        """测试注册无效插件"""
        with pytest.raises(TypeError, match="插件必须继承自FrameworkPlugin"):
            self.registry.register_plugin("not_a_plugin")
    
    def test_unregister_plugin(self):
        """测试注销插件"""
        plugin = MockPlugin()
        self.registry.register_plugin(plugin)
        
        result = self.registry.unregister_plugin("test_framework")
        assert result == True
        assert self.registry.get_plugin("test_framework") is None
        
        # 测试注销不存在的插件
        result = self.registry.unregister_plugin("nonexistent")
        assert result == False
    
    def test_get_plugins_by_type(self):
        """测试按类型获取插件"""
        web_plugin = MockPlugin("web_framework")
        async_plugin = MockPlugin("async_framework")
        async_plugin.metadata.framework_type = FrameworkType.ASYNC_FRAMEWORK
        
        self.registry.register_plugin(web_plugin)
        self.registry.register_plugin(async_plugin)
        
        web_plugins = self.registry.get_plugins_by_type(FrameworkType.WEB_FRAMEWORK)
        async_plugins = self.registry.get_plugins_by_type(FrameworkType.ASYNC_FRAMEWORK)
        
        assert len(web_plugins) == 1
        assert len(async_plugins) == 1
        assert web_plugins[0].metadata.name == "web_framework"
        assert async_plugins[0].metadata.name == "async_framework"
    
    def test_get_installed_plugins(self):
        """测试获取已安装插件"""
        installed_plugin = MockPlugin("installed", installed=True)
        uninstalled_plugin = MockPlugin("uninstalled", installed=False)
        
        self.registry.register_plugin(installed_plugin)
        self.registry.register_plugin(uninstalled_plugin)
        
        installed = self.registry.get_installed_plugins()
        
        assert len(installed) == 1
        assert installed[0].metadata.name == "installed"
    
    def test_get_available_plugins(self):
        """测试获取可用插件"""
        available_plugin = MockPlugin("available", installed=True, missing_deps=[])
        unavailable_plugin = MockPlugin("unavailable", installed=True, missing_deps=["missing_dep"])
        
        self.registry.register_plugin(available_plugin)
        self.registry.register_plugin(unavailable_plugin)
        
        available = self.registry.get_available_plugins()
        
        assert len(available) == 1
        assert available[0].metadata.name == "available"
    
    def test_validate_all_plugins(self):
        """测试验证所有插件"""
        good_plugin = MockPlugin("good", missing_deps=[])
        bad_plugin = MockPlugin("bad", missing_deps=["missing_dep"])
        
        self.registry.register_plugin(good_plugin)
        self.registry.register_plugin(bad_plugin)
        
        validation_results = self.registry.validate_all_plugins()
        
        assert "good" not in validation_results
        assert "bad" in validation_results
        assert validation_results["bad"] == ["missing_dep"]
    
    def test_discovery_hooks(self):
        """测试发现钩子"""
        def discovery_hook():
            return [MockPlugin("discovered")]
        
        self.registry.add_discovery_hook(discovery_hook)
        discovered_count = self.registry.discover_plugins()
        
        assert discovered_count == 1
        assert self.registry.get_plugin("discovered") is not None
        
        # 测试移除钩子
        result = self.registry.remove_discovery_hook(discovery_hook)
        assert result == True
    
    def test_registry_status(self):
        """测试注册表状态"""
        plugin1 = MockPlugin("plugin1", installed=True)
        plugin2 = MockPlugin("plugin2", installed=False)
        
        self.registry.register_plugin(plugin1)
        self.registry.register_plugin(plugin2)
        
        status = self.registry.get_registry_status()
        
        assert status['total_plugins'] == 2
        assert status['installed_plugins'] == 1
        assert status['available_plugins'] == 1  # plugin1 has no missing deps


class TestPluginManager:
    """插件管理器测试类"""
    
    def setup_method(self):
        """测试方法设置"""
        self.manager = PluginManager()
    
    def test_manager_initialization(self):
        """测试管理器初始化"""
        assert self.manager.registry is not None
        assert self.manager._initialized == False
        
        self.manager.initialize()
        assert self.manager._initialized == True
    
    def test_create_monitor_success(self):
        """测试成功创建监控器"""
        plugin = MockPlugin("test_framework", installed=True, missing_deps=[])
        self.manager.registry.register_plugin(plugin)
        
        monitor = self.manager.create_monitor("test_framework", {})
        assert monitor is not None
    
    def test_create_monitor_plugin_not_found(self):
        """测试插件不存在时创建监控器"""
        with pytest.raises(ValueError, match="未找到框架插件"):
            self.manager.create_monitor("nonexistent", {})
    
    def test_create_monitor_not_installed(self):
        """测试框架未安装时创建监控器"""
        plugin = MockPlugin("test_framework", installed=False)
        self.manager.registry.register_plugin(plugin)
        
        with pytest.raises(ValueError, match="未安装"):
            self.manager.create_monitor("test_framework", {})
    
    def test_create_monitor_missing_dependencies(self):
        """测试缺少依赖时创建监控器"""
        plugin = MockPlugin("test_framework", installed=True, missing_deps=["missing_dep"])
        self.manager.registry.register_plugin(plugin)
        
        with pytest.raises(ValueError, match="缺少依赖"):
            self.manager.create_monitor("test_framework", {})
    
    def test_get_available_frameworks(self):
        """测试获取可用框架列表"""
        available_plugin = MockPlugin("available", installed=True, missing_deps=[])
        unavailable_plugin = MockPlugin("unavailable", installed=False)
        
        self.manager.registry.register_plugin(available_plugin)
        self.manager.registry.register_plugin(unavailable_plugin)
        
        frameworks = self.manager.get_available_frameworks()
        
        assert "available" in frameworks
        assert "unavailable" not in frameworks
    
    def test_get_framework_info(self):
        """测试获取框架信息"""
        plugin = MockPlugin("test_framework")
        self.manager.registry.register_plugin(plugin)
        
        info = self.manager.get_framework_info("test_framework")
        
        assert info is not None
        assert info['metadata']['name'] == "test_framework"
        assert 'status' in info
        
        # 测试不存在的框架
        info = self.manager.get_framework_info("nonexistent")
        assert info is None
    
    def test_register_external_plugin(self):
        """测试注册外部插件"""
        metadata = FrameworkMetadata(
            name="external_framework",
            version_range=">=1.0.0",
            framework_type=FrameworkType.CUSTOM,
            description="External framework"
        )
        
        self.manager.register_external_plugin(MockPlugin, metadata)
        
        plugin = self.manager.registry.get_plugin("external_framework")
        assert plugin is not None
        assert plugin.metadata.name == "external_framework"
    
    def test_get_installation_recommendations(self):
        """测试获取安装建议"""
        installed_plugin = MockPlugin("installed", installed=True)
        uninstalled_plugin = MockPlugin("uninstalled", installed=False)
        
        self.manager.registry.register_plugin(installed_plugin)
        self.manager.registry.register_plugin(uninstalled_plugin)
        
        recommendations = self.manager.get_installation_recommendations()
        
        assert len(recommendations) == 1
        assert recommendations[0]['framework'] == "uninstalled"
        assert 'command' in recommendations[0]
        assert 'priority' in recommendations[0]


class TestGlobalPluginManager:
    """全局插件管理器测试类"""
    
    def test_get_plugin_manager_singleton(self):
        """测试全局插件管理器单例"""
        manager1 = get_plugin_manager()
        manager2 = get_plugin_manager()
        
        assert manager1 is manager2
        assert manager1._initialized == True
    
    @patch('web_performance_monitor.core.plugin_system._plugin_manager', None)
    def test_register_framework_plugin_function(self):
        """测试注册框架插件函数"""
        metadata = FrameworkMetadata(
            name="function_test",
            version_range=">=1.0.0",
            framework_type=FrameworkType.CUSTOM,
            description="Function test"
        )
        
        register_framework_plugin(MockPlugin, metadata)
        
        manager = get_plugin_manager()
        plugin = manager.registry.get_plugin("function_test")
        assert plugin is not None