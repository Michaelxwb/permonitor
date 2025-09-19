"""
依赖管理器测试模块
"""

import pytest
from unittest.mock import patch, MagicMock
import os

from web_performance_monitor.utils.dependency_manager import DependencyManager
from web_performance_monitor.models.dependency_models import DependencyConfig, DependencyStatus, DependencyType


class TestDependencyManager:
    """依赖管理器测试类"""
    
    def setup_method(self):
        """测试方法设置"""
        self.config = DependencyConfig()
        self.manager = DependencyManager(self.config)
    
    def test_init_with_config(self):
        """测试使用配置初始化"""
        config = DependencyConfig(skip_dependency_check=True)
        manager = DependencyManager(config)
        assert manager.config.skip_dependency_check is True
    
    @patch.dict(os.environ, {'WPM_SKIP_DEPENDENCY_CHECK': 'true'})
    def test_init_from_env_vars(self):
        """测试从环境变量初始化"""
        manager = DependencyManager()
        assert manager.config.skip_dependency_check is True
    
    def test_get_supported_frameworks(self):
        """测试获取支持的框架列表"""
        frameworks = self.manager.get_supported_frameworks()
        assert 'flask' in frameworks
        assert 'fastapi' in frameworks
        assert isinstance(frameworks, list)
    
    @patch.object(DependencyManager, 'framework_detector')
    def test_check_framework_dependencies_available(self, mock_detector):
        """测试检查可用框架的依赖状态"""
        mock_detector.is_framework_available.return_value = True
        mock_detector.get_framework_version.return_value = '2.1.0'
        
        status = self.manager.check_framework_dependencies('flask')
        
        assert status.framework == 'flask'
        assert status.is_available is True
        assert status.installed_version == '2.1.0'
        assert status.dependency_type == DependencyType.FRAMEWORK
    
    @patch.object(DependencyManager, 'framework_detector')
    def test_check_framework_dependencies_unavailable(self, mock_detector):
        """测试检查不可用框架的依赖状态"""
        mock_detector.is_framework_available.return_value = False
        mock_detector.get_framework_version.return_value = None
        
        status = self.manager.check_framework_dependencies('flask')
        
        assert status.framework == 'flask'
        assert status.is_available is False
        assert 'flask' in status.missing_packages
        assert status.installation_command == "pip install web-performance-monitor[flask]"
    
    def test_check_framework_dependencies_unsupported(self):
        """测试检查不支持的框架"""
        status = self.manager.check_framework_dependencies('django')
        
        assert status.framework == 'django'
        assert status.is_available is False
        assert 'django' in status.missing_packages
    
    @patch.object(DependencyManager, 'framework_detector')
    def test_check_framework_dependencies_fastapi_with_async_deps(self, mock_detector):
        """测试检查FastAPI及其异步依赖"""
        mock_detector.is_framework_available.return_value = True
        mock_detector.get_framework_version.return_value = '0.100.0'
        mock_detector.check_fastapi_async_dependencies.return_value = {
            'uvicorn': True,
            'aiofiles': False,  # 缺失aiofiles
            'aiohttp': True
        }
        
        status = self.manager.check_framework_dependencies('fastapi')
        
        assert status.framework == 'fastapi'
        assert status.is_available is False  # 因为缺少aiofiles
        assert 'aiofiles' in status.missing_packages
    
    def test_get_installation_guide_flask(self):
        """测试获取Flask安装指导"""
        guide = self.manager.get_installation_guide('flask')
        
        assert 'Flask' in guide
        assert 'pip install web-performance-monitor[flask]' in guide
        assert 'Flask >= 2.0.0' in guide
    
    def test_get_installation_guide_fastapi(self):
        """测试获取FastAPI安装指导"""
        guide = self.manager.get_installation_guide('fastapi')
        
        assert 'FastAPI' in guide
        assert 'pip install web-performance-monitor[fastapi]' in guide
        assert 'uvicorn' in guide
        assert 'aiofiles' in guide
        assert 'aiohttp' in guide
    
    def test_get_installation_guide_unsupported(self):
        """测试获取不支持框架的安装指导"""
        guide = self.manager.get_installation_guide('django')
        assert '不支持的框架' in guide
    
    @patch.object(DependencyManager, 'check_framework_dependencies')
    def test_validate_environment_all_available(self, mock_check):
        """测试验证所有框架都可用的环境"""
        mock_status = DependencyStatus(
            framework='test',
            is_available=True,
            dependency_type=DependencyType.FRAMEWORK
        )
        mock_check.return_value = mock_status
        
        report = self.manager.validate_environment()
        
        assert len(report.available_frameworks) == len(self.manager.supported_frameworks)
        assert len(report.recommendations) > 0  # 应该有"所有框架都已安装"的建议
    
    @patch.object(DependencyManager, 'check_framework_dependencies')
    def test_validate_environment_none_available(self, mock_check):
        """测试验证没有框架可用的环境"""
        mock_status = DependencyStatus(
            framework='test',
            is_available=False,
            missing_packages=['test'],
            dependency_type=DependencyType.FRAMEWORK
        )
        mock_check.return_value = mock_status
        
        report = self.manager.validate_environment()
        
        assert len(report.available_frameworks) == 0
        assert len(report.recommendations) > 0
        # 应该建议安装所有框架
        assert any('pip install web-performance-monitor[all]' in rec for rec in report.recommendations)
    
    @patch.object(DependencyManager, 'check_framework_dependencies')
    def test_validate_environment_partial_available(self, mock_check):
        """测试验证部分框架可用的环境"""
        def mock_check_side_effect(framework):
            if framework == 'flask':
                return DependencyStatus(
                    framework='flask',
                    is_available=True,
                    dependency_type=DependencyType.FRAMEWORK
                )
            else:
                return DependencyStatus(
                    framework=framework,
                    is_available=False,
                    missing_packages=[framework],
                    dependency_type=DependencyType.FRAMEWORK
                )
        
        mock_check.side_effect = mock_check_side_effect
        
        report = self.manager.validate_environment()
        
        assert 'flask' in report.available_frameworks
        assert len(report.available_frameworks) == 1
        assert len(report.recommendations) > 0
    
    @patch('web_performance_monitor.utils.dependency_manager.__import__')
    def test_check_notification_dependencies_available(self, mock_import):
        """测试检查通知依赖可用的情况"""
        mock_import.return_value = MagicMock()  # 模拟成功导入
        
        report = self.manager.validate_environment()
        
        # 不应该有通知相关的警告
        notification_warnings = [w for w in report.warnings if 'mattermost' in w.lower()]
        assert len(notification_warnings) == 0
    
    @patch('web_performance_monitor.utils.dependency_manager.__import__')
    def test_check_notification_dependencies_missing(self, mock_import):
        """测试检查通知依赖缺失的情况"""
        mock_import.side_effect = ImportError("No module named 'mattermostdriver'")
        
        report = self.manager.validate_environment()
        
        # 应该有通知相关的警告
        notification_warnings = [w for w in report.warnings if 'mattermost' in w.lower()]
        assert len(notification_warnings) > 0
    
    @patch.object(DependencyManager, 'validate_environment')
    def test_get_dependency_summary(self, mock_validate):
        """测试获取依赖状态摘要"""
        from web_performance_monitor.models.dependency_models import EnvironmentReport
        
        mock_report = EnvironmentReport(
            supported_frameworks=['flask', 'fastapi'],
            available_frameworks=['flask'],
            warnings=['test warning'],
            recommendations=['test recommendation']
        )
        mock_validate.return_value = mock_report
        
        summary = self.manager.get_dependency_summary()
        
        assert summary['supported_frameworks'] == ['flask', 'fastapi']
        assert summary['available_frameworks'] == ['flask']
        assert summary['missing_frameworks'] == ['fastapi']
        assert summary['warnings_count'] == 1
        assert summary['recommendations_count'] == 1
        assert summary['overall_status'] == 'partial'
    
    def test_check_dependencies_skip_check(self):
        """测试跳过依赖检查的情况"""
        self.manager.config.skip_dependency_check = True
        
        report = self.manager.check_dependencies()
        
        assert len(report.recommendations) > 0
        assert any('跳过' in rec for rec in report.recommendations)
    
    @patch.object(DependencyManager, 'validate_environment')
    def test_check_dependencies_normal(self, mock_validate):
        """测试正常的依赖检查"""
        from web_performance_monitor.models.dependency_models import EnvironmentReport
        
        mock_report = EnvironmentReport()
        mock_validate.return_value = mock_report
        
        result = self.manager.check_dependencies()
        
        assert result == mock_report
        mock_validate.assert_called_once()
    
    @patch.object(DependencyManager, 'framework_detector')
    def test_suggest_optimal_installation_detected_framework(self, mock_detector):
        """测试检测到框架时的最优安装建议"""
        mock_detector.detect_framework_from_environment.return_value = 'flask'
        
        suggestion = self.manager.suggest_optimal_installation()
        
        assert 'flask' in suggestion
        assert 'pip install web-performance-monitor[flask]' in suggestion
    
    @patch.object(DependencyManager, 'framework_detector')
    def test_suggest_optimal_installation_multiple_frameworks(self, mock_detector):
        """测试检测到多个框架时的最优安装建议"""
        mock_detector.detect_framework_from_environment.return_value = None
        mock_detector.detect_installed_frameworks.return_value = ['flask', 'fastapi']
        
        suggestion = self.manager.suggest_optimal_installation()
        
        assert 'flask,fastapi' in suggestion or 'fastapi,flask' in suggestion
    
    @patch.object(DependencyManager, 'framework_detector')
    def test_suggest_optimal_installation_no_frameworks(self, mock_detector):
        """测试未检测到框架时的最优安装建议"""
        mock_detector.detect_framework_from_environment.return_value = None
        mock_detector.detect_installed_frameworks.return_value = []
        
        suggestion = self.manager.suggest_optimal_installation()
        
        assert 'pip install web-performance-monitor[all]' in suggestion