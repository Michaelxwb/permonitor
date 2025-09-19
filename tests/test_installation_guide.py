"""
安装指导生成器测试模块
"""

import pytest
from unittest.mock import patch, MagicMock
import platform

from web_performance_monitor.utils.installation_guide import InstallationGuide, InstallationRecommendation
from web_performance_monitor.models.dependency_models import DependencyStatus


class TestInstallationGuide:
    """安装指导生成器测试类"""
    
    def setup_method(self):
        """测试方法设置"""
        self.guide = InstallationGuide()
    
    def test_generate_installation_command_single_framework(self):
        """测试生成单个框架的安装命令"""
        command = self.guide.generate_installation_command(['flask'])
        assert command == "pip install web-performance-monitor[flask]"
    
    def test_generate_installation_command_multiple_frameworks(self):
        """测试生成多个框架的安装命令"""
        command = self.guide.generate_installation_command(['flask', 'fastapi'])
        assert 'flask,fastapi' in command or 'fastapi,flask' in command
        assert 'web-performance-monitor[' in command
    
    def test_generate_installation_command_with_notifications(self):
        """测试包含通知的安装命令"""
        command = self.guide.generate_installation_command(['flask'], include_notifications=True)
        assert 'flask,notifications' in command or 'notifications,flask' in command
    
    def test_generate_installation_command_all_extras(self):
        """测试生成包含所有extras的安装命令"""
        command = self.guide.generate_installation_command(['flask', 'fastapi'], include_notifications=True)
        assert command == "pip install web-performance-monitor[all]"
    
    def test_generate_installation_command_empty_frameworks(self):
        """测试空框架列表的安装命令"""
        command = self.guide.generate_installation_command([])
        assert command == "pip install web-performance-monitor"
    
    @patch.object(InstallationGuide, 'dependency_manager')
    def test_generate_framework_specific_guide_flask(self, mock_manager):
        """测试生成Flask特定的安装指导"""
        # 模拟依赖状态
        mock_status = DependencyStatus(
            framework='flask',
            is_available=True,
            installed_version='2.1.0',
            required_version='2.0.0'
        )
        mock_manager.check_framework_dependencies.return_value = mock_status
        
        guide = self.guide.generate_framework_specific_guide('flask')
        
        assert guide['framework'] == 'flask'
        assert guide['current_status']['available'] is True
        assert guide['current_status']['installed_version'] == '2.1.0'
        assert 'installation' in guide
        assert 'compatibility' in guide
        assert 'next_steps' in guide
    
    @patch.object(InstallationGuide, 'dependency_manager')
    @patch.object(InstallationGuide, 'framework_detector')
    def test_generate_framework_specific_guide_fastapi(self, mock_detector, mock_manager):
        """测试生成FastAPI特定的安装指导"""
        # 模拟依赖状态
        mock_status = DependencyStatus(
            framework='fastapi',
            is_available=False,
            missing_packages=['uvicorn']
        )
        mock_manager.check_framework_dependencies.return_value = mock_status
        
        # 模拟异步依赖检查
        mock_detector.check_fastapi_async_dependencies.return_value = {
            'uvicorn': False,
            'aiofiles': True,
            'aiohttp': True
        }
        
        guide = self.guide.generate_framework_specific_guide('fastapi')
        
        assert guide['framework'] == 'fastapi'
        assert guide['current_status']['available'] is False
        assert 'uvicorn' in guide['current_status']['missing_packages']
        assert 'async_dependencies' in guide
        assert guide['async_dependencies']['missing'] == ['uvicorn']
    
    def test_generate_framework_specific_guide_unsupported(self):
        """测试不支持的框架"""
        guide = self.guide.generate_framework_specific_guide('django')
        
        assert 'error' in guide
        assert '不支持的框架' in guide['error']
        assert 'supported_frameworks' in guide
    
    @patch.object(InstallationGuide, 'framework_detector')
    def test_generate_multi_framework_recommendations(self, mock_detector):
        """测试生成多框架安装建议"""
        mock_detector.detect_installed_frameworks.return_value = ['flask']
        
        recommendations = self.guide.generate_multi_framework_recommendations(['flask', 'fastapi'])
        
        assert len(recommendations) > 0
        assert isinstance(recommendations[0], InstallationRecommendation)
        
        # 检查是否有安装所有框架的建议
        all_framework_rec = next((r for r in recommendations if 'flask' in r.description and 'fastapi' in r.description), None)
        assert all_framework_rec is not None
        
        # 检查是否有渐进式安装建议（基于已安装的flask）
        progressive_rec = next((r for r in recommendations if '缺失的框架' in r.description), None)
        assert progressive_rec is not None
    
    @patch.object(InstallationGuide, 'framework_detector')
    def test_generate_multi_framework_recommendations_no_installed(self, mock_detector):
        """测试没有已安装框架时的多框架建议"""
        mock_detector.detect_installed_frameworks.return_value = []
        
        recommendations = self.guide.generate_multi_framework_recommendations(['flask', 'fastapi'])
        
        assert len(recommendations) > 0
        
        # 应该有逐个安装的建议
        flask_rec = next((r for r in recommendations if r.description.startswith('仅安装 flask')), None)
        fastapi_rec = next((r for r in recommendations if r.description.startswith('仅安装 fastapi')), None)
        
        assert flask_rec is not None
        assert fastapi_rec is not None
    
    @patch.object(InstallationGuide, 'framework_detector')
    @patch.object(InstallationGuide, 'dependency_manager')
    def test_generate_environment_specific_guide_detected_framework(self, mock_manager, mock_detector):
        """测试检测到框架时的环境特定指导"""
        # 模拟检测到Flask但依赖不完整
        mock_detector.detect_framework_from_environment.return_value = 'flask'
        mock_detector.detect_installed_frameworks.return_value = []
        
        mock_status = DependencyStatus(
            framework='flask',
            is_available=False,
            missing_packages=['flask']
        )
        mock_manager.check_framework_dependencies.return_value = mock_status
        
        guide = self.guide.generate_environment_specific_guide()
        
        assert 'environment' in guide
        assert 'detected_usage' in guide
        assert guide['detected_usage'] == 'flask'
        assert 'recommendations' in guide
        
        # 应该有立即安装的高优先级建议
        immediate_rec = next((r for r in guide['recommendations'] if r['type'] == 'immediate'), None)
        assert immediate_rec is not None
        assert immediate_rec['priority'] == 'high'
    
    @patch.object(InstallationGuide, 'framework_detector')
    @patch.object(InstallationGuide, 'dependency_manager')
    def test_generate_environment_specific_guide_installed_incomplete(self, mock_manager, mock_detector):
        """测试已安装框架但依赖不完整时的指导"""
        mock_detector.detect_framework_from_environment.return_value = None
        mock_detector.detect_installed_frameworks.return_value = ['flask']
        
        mock_status = DependencyStatus(
            framework='flask',
            is_available=False,
            missing_packages=['some_dependency']
        )
        mock_manager.check_framework_dependencies.return_value = mock_status
        
        guide = self.guide.generate_environment_specific_guide()
        
        assert guide['detected_frameworks'] == ['flask']
        
        # 应该有维护类型的建议
        maintenance_rec = next((r for r in guide['recommendations'] if r['type'] == 'maintenance'), None)
        assert maintenance_rec is not None
        assert maintenance_rec['priority'] == 'medium'
    
    @patch.object(InstallationGuide, 'framework_detector')
    def test_generate_environment_specific_guide_no_frameworks(self, mock_detector):
        """测试没有检测到框架时的指导"""
        mock_detector.detect_framework_from_environment.return_value = None
        mock_detector.detect_installed_frameworks.return_value = []
        
        guide = self.guide.generate_environment_specific_guide()
        
        assert len(guide['recommendations']) >= 3  # Flask, FastAPI, all
        
        # 检查探索性建议
        exploration_recs = [r for r in guide['recommendations'] if r['type'] == 'exploration']
        assert len(exploration_recs) >= 2
        
        # 检查综合性建议
        comprehensive_rec = next((r for r in guide['recommendations'] if r['type'] == 'comprehensive'), None)
        assert comprehensive_rec is not None
    
    def test_generate_troubleshooting_guide_basic(self):
        """测试基础故障排除指导"""
        error_info = {}
        
        guide = self.guide.generate_troubleshooting_guide(error_info)
        
        assert 'common_issues' in guide
        assert 'specific_solutions' in guide
        assert 'verification_steps' in guide
        
        # 检查常见问题
        assert len(guide['common_issues']) >= 3
        
        # 检查验证步骤
        assert len(guide['verification_steps']) >= 4
        
        # 验证步骤应该包含Python版本检查
        python_check = next((step for step in guide['verification_steps'] if 'python --version' in step), None)
        assert python_check is not None
    
    def test_generate_troubleshooting_guide_with_missing_packages(self):
        """测试包含缺失包信息的故障排除指导"""
        error_info = {
            'missing_packages': ['flask', 'uvicorn']
        }
        
        guide = self.guide.generate_troubleshooting_guide(error_info)
        
        assert len(guide['specific_solutions']) >= 2
        
        # 检查Flask特定解决方案
        flask_solution = next((s for s in guide['specific_solutions'] if s['package'] == 'flask'), None)
        assert flask_solution is not None
        assert 'web-performance-monitor[flask]' in flask_solution['command']
        
        # 检查uvicorn特定解决方案
        uvicorn_solution = next((s for s in guide['specific_solutions'] if s['package'] == 'uvicorn'), None)
        assert uvicorn_solution is not None
        assert 'web-performance-monitor[fastapi]' in uvicorn_solution['command']
    
    def test_get_framework_description(self):
        """测试获取框架描述"""
        flask_desc = self.guide._get_framework_description('flask')
        assert 'Flask' in flask_desc
        assert '轻量级' in flask_desc
        
        fastapi_desc = self.guide._get_framework_description('fastapi')
        assert 'FastAPI' in fastapi_desc
        assert '异步' in fastapi_desc
        
        unknown_desc = self.guide._get_framework_description('unknown')
        assert 'unknown' in unknown_desc
    
    def test_generate_next_steps_available(self):
        """测试依赖可用时的下一步建议"""
        status = DependencyStatus(
            framework='flask',
            is_available=True
        )
        
        steps = self.guide._generate_next_steps('flask', status)
        
        assert len(steps) >= 3
        assert any('✅' in step for step in steps)
        assert any('依赖已完整安装' in step for step in steps)
    
    def test_generate_next_steps_unavailable(self):
        """测试依赖不可用时的下一步建议"""
        status = DependencyStatus(
            framework='flask',
            is_available=False,
            missing_packages=['flask'],
            installation_command='pip install web-performance-monitor[flask]'
        )
        
        steps = self.guide._generate_next_steps('flask', status)
        
        assert len(steps) >= 3
        assert any('📦' in step for step in steps)
        assert any('pip install' in step for step in steps)
        assert any('缺失的包' in step for step in steps)
    
    def test_estimate_total_size(self):
        """测试估算总安装大小"""
        # 测试单个包
        size = self.guide._estimate_total_size(['flask'])
        assert 'MB' in size
        
        # 测试多个包
        size = self.guide._estimate_total_size(['flask', 'fastapi'])
        assert 'MB' in size
        assert '-' in size  # 应该是范围
        
        # 测试未知包
        size = self.guide._estimate_total_size(['unknown'])
        assert size == "0 MB"
    
    def test_generate_environment_next_steps_high_priority(self):
        """测试高优先级建议的下一步"""
        recommendations = [
            {'priority': 'high', 'command': 'pip install flask'}
        ]
        
        steps = self.guide._generate_environment_next_steps(recommendations)
        
        assert len(steps) >= 3
        assert any('🚨' in step for step in steps)
        assert any('pip install flask' in step for step in steps)
    
    def test_generate_environment_next_steps_no_high_priority(self):
        """测试没有高优先级建议的下一步"""
        recommendations = [
            {'priority': 'medium', 'command': 'pip install flask'}
        ]
        
        steps = self.guide._generate_environment_next_steps(recommendations)
        
        assert len(steps) >= 3
        assert any('📋' in step for step in steps)
        assert any('最小安装' in step for step in steps)
    
    def test_generate_environment_next_steps_empty(self):
        """测试空建议列表的下一步"""
        steps = self.guide._generate_environment_next_steps([])
        
        assert len(steps) == 1
        assert 'check_dependencies()' in steps[0]


class TestInstallationRecommendation:
    """安装建议数据类测试"""
    
    def test_installation_recommendation_creation(self):
        """测试创建安装建议"""
        rec = InstallationRecommendation(
            command="pip install flask",
            description="Install Flask",
            priority=1,
            reason="Flask is needed",
            estimated_size="5 MB",
            compatibility_notes="Requires Python 3.7+"
        )
        
        assert rec.command == "pip install flask"
        assert rec.description == "Install Flask"
        assert rec.priority == 1
        assert rec.reason == "Flask is needed"
        assert rec.estimated_size == "5 MB"
        assert rec.compatibility_notes == "Requires Python 3.7+"
    
    def test_installation_recommendation_optional_fields(self):
        """测试可选字段的安装建议"""
        rec = InstallationRecommendation(
            command="pip install flask",
            description="Install Flask",
            priority=1,
            reason="Flask is needed"
        )
        
        assert rec.estimated_size is None
        assert rec.compatibility_notes is None