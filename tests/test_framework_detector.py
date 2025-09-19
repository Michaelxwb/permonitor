"""
框架检测器测试模块
"""

import pytest
from unittest.mock import patch, MagicMock
import importlib
import sys

from web_performance_monitor.utils.framework_detector import FrameworkDetector


class TestFrameworkDetector:
    """框架检测器测试类"""
    
    def test_detect_installed_frameworks_empty(self):
        """测试在没有安装框架时的检测结果"""
        with patch.object(FrameworkDetector, 'is_framework_available', return_value=False):
            result = FrameworkDetector.detect_installed_frameworks()
            assert result == []
    
    def test_detect_installed_frameworks_with_flask(self):
        """测试检测到Flask时的结果"""
        def mock_is_available(framework):
            return framework == 'flask'
        
        with patch.object(FrameworkDetector, 'is_framework_available', side_effect=mock_is_available):
            result = FrameworkDetector.detect_installed_frameworks()
            assert 'flask' in result
            assert 'fastapi' not in result
    
    def test_detect_installed_frameworks_with_fastapi(self):
        """测试检测到FastAPI时的结果"""
        def mock_is_available(framework):
            return framework == 'fastapi'
        
        with patch.object(FrameworkDetector, 'is_framework_available', side_effect=mock_is_available):
            result = FrameworkDetector.detect_installed_frameworks()
            assert 'fastapi' in result
            assert 'flask' not in result
    
    def test_detect_installed_frameworks_with_both(self):
        """测试同时检测到Flask和FastAPI时的结果"""
        with patch.object(FrameworkDetector, 'is_framework_available', return_value=True):
            result = FrameworkDetector.detect_installed_frameworks()
            assert 'flask' in result
            assert 'fastapi' in result
    
    def test_is_framework_available_unsupported(self):
        """测试不支持的框架"""
        result = FrameworkDetector.is_framework_available('django')
        assert result is False
    
    @patch('importlib.import_module')
    def test_is_framework_available_import_error(self, mock_import):
        """测试模块导入错误的情况"""
        mock_import.side_effect = ImportError("No module named 'flask'")
        
        result = FrameworkDetector.is_framework_available('flask')
        assert result is False
    
    @patch('importlib.import_module')
    @patch.object(FrameworkDetector, 'get_framework_version')
    def test_is_framework_available_version_check(self, mock_get_version, mock_import):
        """测试版本检查逻辑"""
        mock_import.return_value = MagicMock()
        mock_get_version.return_value = '2.1.0'
        
        result = FrameworkDetector.is_framework_available('flask')
        assert result is True
        
        # 测试版本过低的情况
        mock_get_version.return_value = '1.9.0'
        result = FrameworkDetector.is_framework_available('flask')
        assert result is False
    
    @patch('importlib.import_module')
    def test_get_framework_version_success(self, mock_import):
        """测试成功获取框架版本"""
        mock_module = MagicMock()
        mock_module.__version__ = '2.1.0'
        mock_import.return_value = mock_module
        
        result = FrameworkDetector.get_framework_version('flask')
        assert result == '2.1.0'
    
    @patch('importlib.import_module')
    def test_get_framework_version_no_version_attr(self, mock_import):
        """测试模块没有版本属性的情况"""
        mock_module = MagicMock()
        del mock_module.__version__
        mock_import.return_value = mock_module
        
        result = FrameworkDetector.get_framework_version('flask')
        assert result is None
    
    @patch('importlib.import_module')
    def test_get_framework_version_import_error(self, mock_import):
        """测试导入错误的情况"""
        mock_import.side_effect = ImportError("No module named 'flask'")
        
        result = FrameworkDetector.get_framework_version('flask')
        assert result is None
    
    def test_get_framework_version_unsupported(self):
        """测试不支持的框架"""
        result = FrameworkDetector.get_framework_version('django')
        assert result is None
    
    @patch('importlib.import_module')
    def test_check_fastapi_async_dependencies_all_available(self, mock_import):
        """测试所有FastAPI异步依赖都可用的情况"""
        mock_module = MagicMock()
        mock_module.__version__ = '25.0.0'  # 高于最低要求的版本
        mock_import.return_value = mock_module
        
        result = FrameworkDetector.check_fastapi_async_dependencies()
        
        assert 'uvicorn' in result
        assert 'aiofiles' in result
        assert 'aiohttp' in result
        assert all(result.values())  # 所有依赖都应该可用
    
    @patch('importlib.import_module')
    def test_check_fastapi_async_dependencies_missing(self, mock_import):
        """测试FastAPI异步依赖缺失的情况"""
        mock_import.side_effect = ImportError("No module found")
        
        result = FrameworkDetector.check_fastapi_async_dependencies()
        
        assert 'uvicorn' in result
        assert 'aiofiles' in result
        assert 'aiohttp' in result
        assert not any(result.values())  # 所有依赖都应该不可用
    
    def test_suggest_installation_flask(self):
        """测试Flask安装建议"""
        result = FrameworkDetector.suggest_installation(['flask'])
        assert result['flask'] == "pip install web-performance-monitor[flask]"
    
    def test_suggest_installation_fastapi(self):
        """测试FastAPI安装建议"""
        result = FrameworkDetector.suggest_installation(['fastapi'])
        assert result['fastapi'] == "pip install web-performance-monitor[fastapi]"
    
    def test_suggest_installation_multiple(self):
        """测试多个框架的安装建议"""
        result = FrameworkDetector.suggest_installation(['flask', 'fastapi'])
        assert result['flask'] == "pip install web-performance-monitor[flask]"
        assert result['fastapi'] == "pip install web-performance-monitor[fastapi]"
    
    @patch.object(FrameworkDetector, 'is_framework_available')
    @patch.object(FrameworkDetector, 'get_framework_version')
    @patch.object(FrameworkDetector, 'check_fastapi_async_dependencies')
    def test_get_framework_status_report(self, mock_async_deps, mock_get_version, mock_is_available):
        """测试框架状态报告生成"""
        mock_is_available.return_value = True
        mock_get_version.return_value = '2.1.0'
        mock_async_deps.return_value = {'uvicorn': True, 'aiofiles': True, 'aiohttp': True}
        
        result = FrameworkDetector.get_framework_status_report()
        
        assert 'flask' in result
        assert 'fastapi' in result
        
        # 检查Flask状态
        flask_status = result['flask']
        assert flask_status['available'] is True
        assert flask_status['version'] == '2.1.0'
        assert flask_status['min_version'] == '2.0.0'
        
        # 检查FastAPI状态（应该包含异步依赖信息）
        fastapi_status = result['fastapi']
        assert fastapi_status['available'] is True
        assert 'async_dependencies' in fastapi_status
    
    @patch.object(FrameworkDetector, 'detect_installed_frameworks')
    def test_detect_framework_from_environment_empty(self, mock_detect):
        """测试环境中没有框架时的自动检测"""
        mock_detect.return_value = []
        
        result = FrameworkDetector.detect_framework_from_environment()
        assert result is None
    
    @patch.object(FrameworkDetector, 'detect_installed_frameworks')
    def test_detect_framework_from_environment_single(self, mock_detect):
        """测试环境中只有一个框架时的自动检测"""
        mock_detect.return_value = ['flask']
        
        result = FrameworkDetector.detect_framework_from_environment()
        assert result == 'flask'
    
    @patch.object(FrameworkDetector, 'detect_installed_frameworks')
    def test_detect_framework_from_environment_multiple_with_fastapi(self, mock_detect):
        """测试环境中有多个框架且包含FastAPI时的自动检测"""
        mock_detect.return_value = ['flask', 'fastapi']
        
        result = FrameworkDetector.detect_framework_from_environment()
        assert result == 'fastapi'  # 应该优先选择FastAPI
    
    @patch.object(FrameworkDetector, 'detect_installed_frameworks')
    def test_detect_framework_from_environment_multiple_no_fastapi(self, mock_detect):
        """测试环境中有多个框架但不包含FastAPI时的自动检测"""
        mock_detect.return_value = ['flask']
        
        result = FrameworkDetector.detect_framework_from_environment()
        assert result == 'flask'  # 应该返回第一个检测到的框架