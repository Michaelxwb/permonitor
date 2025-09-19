"""
运行时依赖检查器测试模块
"""

import pytest
import warnings
from unittest.mock import patch, MagicMock
import os

from web_performance_monitor.core.dependency_checker import RuntimeDependencyChecker
from web_performance_monitor.exceptions.exceptions import MissingDependencyError, DependencyError


class TestRuntimeDependencyChecker:
    """运行时依赖检查器测试类"""
    
    def setup_method(self):
        """测试方法设置"""
        self.checker = RuntimeDependencyChecker()
    
    def test_init_default(self):
        """测试默认初始化"""
        checker = RuntimeDependencyChecker()
        assert checker.strict_mode is False  # 默认非严格模式
        assert hasattr(checker, 'config')
        assert hasattr(checker, 'framework_detector')
    
    def test_init_with_strict_mode(self):
        """测试使用严格模式初始化"""
        checker = RuntimeDependencyChecker(strict_mode=True)
        assert checker.strict_mode is True
    
    @patch.dict(os.environ, {'WPM_STRICT_DEPENDENCIES': 'true'})
    def test_init_strict_mode_from_env(self):
        """测试从环境变量设置严格模式"""
        checker = RuntimeDependencyChecker()
        assert checker.strict_mode is True
    
    @patch.dict(os.environ, {'WPM_SKIP_DEPENDENCY_CHECK': 'true'})
    def test_should_skip_check_true(self):
        """测试跳过依赖检查"""
        checker = RuntimeDependencyChecker()
        assert checker.should_skip_check() is True
    
    @patch.dict(os.environ, {'WPM_SKIP_DEPENDENCY_CHECK': 'false'})
    def test_should_skip_check_false(self):
        """测试不跳过依赖检查"""
        checker = RuntimeDependencyChecker()
        assert checker.should_skip_check() is False
    
    @patch.object(RuntimeDependencyChecker, 'should_skip_check')
    def test_check_and_warn_skip_check(self, mock_skip):
        """测试跳过检查时的行为"""
        mock_skip.return_value = True
        
        result = self.checker.check_and_warn('flask')
        assert result is True
    
    @patch.object(RuntimeDependencyChecker, 'framework_detector')
    @patch.object(RuntimeDependencyChecker, 'get_missing_dependencies')
    def test_check_and_warn_success(self, mock_missing_deps, mock_detector):
        """测试依赖检查成功的情况"""
        mock_detector.is_framework_available.return_value = True
        mock_missing_deps.return_value = []
        
        result = self.checker.check_and_warn('flask')
        assert result is True
    
    @patch.object(RuntimeDependencyChecker, 'framework_detector')
    @patch.object(RuntimeDependencyChecker, 'get_missing_dependencies')
    def test_check_and_warn_missing_deps_non_strict(self, mock_missing_deps, mock_detector):
        """测试非严格模式下缺少依赖的情况"""
        mock_detector.is_framework_available.return_value = False
        mock_missing_deps.return_value = ['flask']
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = self.checker.check_and_warn('flask')
            
            assert result is False
            assert len(w) > 0
            assert "Missing flask dependencies" in str(w[0].message)
    
    @patch.object(RuntimeDependencyChecker, 'framework_detector')
    @patch.object(RuntimeDependencyChecker, 'get_missing_dependencies')
    def test_check_and_warn_missing_deps_strict(self, mock_missing_deps, mock_detector):
        """测试严格模式下缺少依赖的情况"""
        self.checker.strict_mode = True
        mock_detector.is_framework_available.return_value = False
        mock_missing_deps.return_value = ['flask']
        
        with pytest.raises(MissingDependencyError) as exc_info:
            self.checker.check_and_warn('flask')
        
        assert exc_info.value.framework == 'flask'
        assert 'flask' in exc_info.value.missing_packages
    
    def test_check_and_warn_cache(self):
        """测试检查结果缓存"""
        with patch.object(self.checker.framework_detector, 'is_framework_available', return_value=True) as mock_check:
            with patch.object(self.checker, 'get_missing_dependencies', return_value=[]):
                # 第一次调用
                result1 = self.checker.check_and_warn('flask')
                # 第二次调用
                result2 = self.checker.check_and_warn('flask')
                
                assert result1 is True
                assert result2 is True
                # 应该只调用一次实际检查
                assert mock_check.call_count == 1
    
    @patch.object(RuntimeDependencyChecker, 'framework_detector')
    def test_get_missing_dependencies_framework_unavailable(self, mock_detector):
        """测试框架不可用时获取缺失依赖"""
        mock_detector.is_framework_available.return_value = False
        
        missing = self.checker.get_missing_dependencies('flask')
        assert 'flask' in missing
    
    @patch.object(RuntimeDependencyChecker, 'framework_detector')
    def test_get_missing_dependencies_fastapi_partial(self, mock_detector):
        """测试FastAPI部分依赖缺失的情况"""
        mock_detector.is_framework_available.return_value = True
        mock_detector.check_fastapi_async_dependencies.return_value = {
            'uvicorn': True,
            'aiofiles': False,
            'aiohttp': True
        }
        
        missing = self.checker.get_missing_dependencies('fastapi')
        assert 'aiofiles' in missing
        assert 'uvicorn' not in missing
        assert 'aiohttp' not in missing
    
    def test_validate_framework_usage_success(self):
        """测试框架使用验证成功"""
        with patch.object(self.checker, 'check_and_warn', return_value=True):
            result = self.checker.validate_framework_usage('flask', 'middleware')
            assert result is True
    
    def test_validate_framework_usage_failure_non_strict(self):
        """测试非严格模式下框架使用验证失败"""
        with patch.object(self.checker, 'check_and_warn', side_effect=Exception("Test error")):
            result = self.checker.validate_framework_usage('flask', 'middleware')
            assert result is False
    
    def test_validate_framework_usage_failure_strict(self):
        """测试严格模式下框架使用验证失败"""
        self.checker.strict_mode = True
        
        with patch.object(self.checker, 'check_and_warn', side_effect=Exception("Test error")):
            with pytest.raises(DependencyError):
                self.checker.validate_framework_usage('flask', 'middleware')
    
    def test_validate_framework_usage_missing_dependency_strict(self):
        """测试严格模式下缺少依赖的框架使用验证"""
        self.checker.strict_mode = True
        
        with patch.object(self.checker, 'check_and_warn', side_effect=MissingDependencyError('flask', ['flask'])):
            with pytest.raises(MissingDependencyError):
                self.checker.validate_framework_usage('flask', 'middleware')
    
    @patch('web_performance_monitor.core.dependency_checker.__import__')
    def test_check_notification_dependencies_available(self, mock_import):
        """测试通知依赖可用的情况"""
        mock_import.return_value = MagicMock()
        
        result = self.checker.check_notification_dependencies('mattermost')
        assert result is True
    
    @patch('web_performance_monitor.core.dependency_checker.__import__')
    def test_check_notification_dependencies_missing_non_strict(self, mock_import):
        """测试非严格模式下通知依赖缺失"""
        mock_import.side_effect = ImportError("No module named 'mattermostdriver'")
        
        result = self.checker.check_notification_dependencies('mattermost')
        assert result is False
    
    @patch('web_performance_monitor.core.dependency_checker.__import__')
    def test_check_notification_dependencies_missing_strict(self, mock_import):
        """测试严格模式下通知依赖缺失"""
        self.checker.strict_mode = True
        mock_import.side_effect = ImportError("No module named 'mattermostdriver'")
        
        with pytest.raises(MissingDependencyError) as exc_info:
            self.checker.check_notification_dependencies('mattermost')
        
        assert exc_info.value.framework == 'mattermost'
        assert 'mattermostdriver' in exc_info.value.missing_packages
    
    def test_check_notification_dependencies_unsupported(self):
        """测试不支持的通知类型"""
        result = self.checker.check_notification_dependencies('unsupported')
        assert result is False
    
    @patch.object(RuntimeDependencyChecker, 'should_skip_check')
    def test_check_notification_dependencies_skip_check(self, mock_skip):
        """测试跳过通知依赖检查"""
        mock_skip.return_value = True
        
        result = self.checker.check_notification_dependencies('mattermost')
        assert result is True
    
    @patch.object(RuntimeDependencyChecker, 'framework_detector')
    @patch.object(RuntimeDependencyChecker, 'get_missing_dependencies')
    @patch.object(RuntimeDependencyChecker, 'check_notification_dependencies')
    def test_get_environment_status(self, mock_notification, mock_missing_deps, mock_detector):
        """测试获取环境状态"""
        mock_detector.is_framework_available.return_value = True
        mock_detector.get_framework_version.return_value = '2.1.0'
        mock_missing_deps.return_value = []
        mock_notification.return_value = True
        
        status = self.checker.get_environment_status()
        
        assert 'skip_check' in status
        assert 'strict_mode' in status
        assert 'frameworks' in status
        assert 'notifications' in status
        assert 'config' in status
        
        # 检查框架状态
        assert 'flask' in status['frameworks']
        assert 'fastapi' in status['frameworks']
        
        # 检查通知状态
        assert 'mattermost' in status['notifications']
    
    def test_clear_cache(self):
        """测试清除缓存"""
        # 先添加一些缓存
        self.checker._check_cache['test'] = True
        
        self.checker.clear_cache()
        assert len(self.checker._check_cache) == 0
    
    @patch.object(RuntimeDependencyChecker, 'check_and_warn')
    def test_precheck_all_dependencies_success(self, mock_check):
        """测试预检查所有依赖成功"""
        mock_check.return_value = True
        
        results = self.checker.precheck_all_dependencies()
        
        assert 'flask' in results
        assert 'fastapi' in results
        assert all(results.values())  # 所有结果都应该为True
    
    @patch.object(RuntimeDependencyChecker, 'check_and_warn')
    def test_precheck_all_dependencies_with_failures(self, mock_check):
        """测试预检查所有依赖有失败的情况"""
        def mock_check_side_effect(framework):
            if framework == 'flask':
                raise MissingDependencyError('flask', ['flask'])
            return True
        
        mock_check.side_effect = mock_check_side_effect
        
        results = self.checker.precheck_all_dependencies()
        
        assert results['flask'] is False
        assert results['fastapi'] is True