"""
安装指导生成器模块

提供智能的安装建议和指导，支持多框架组合和个性化建议。
"""

import logging
import os
import platform
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

from .framework_detector import FrameworkDetector
from .dependency_manager import DependencyManager
from ..models.dependency_models import DependencyStatus, EnvironmentReport

logger = logging.getLogger(__name__)


@dataclass
class InstallationRecommendation:
    """安装建议"""
    command: str
    description: str
    priority: int  # 1=高优先级, 2=中优先级, 3=低优先级
    reason: str
    estimated_size: Optional[str] = None
    compatibility_notes: Optional[str] = None


class InstallationGuide:
    """安装指导生成器"""
    
    def __init__(self):
        self.framework_detector = FrameworkDetector()
        self.dependency_manager = DependencyManager()
        
        # 框架依赖大小估算（MB）
        self.package_sizes = {
            'flask': '2-5',
            'fastapi': '15-25', 
            'uvicorn': '8-12',
            'aiofiles': '1-2',
            'aiohttp': '5-8',
            'mattermostdriver': '3-6'
        }
        
        # 框架兼容性信息
        self.compatibility_info = {
            'flask': {
                'python_versions': '>=3.7',
                'notes': 'Flask 2.0+ 需要 Python 3.7 或更高版本'
            },
            'fastapi': {
                'python_versions': '>=3.7',
                'notes': 'FastAPI 需要 Python 3.7+ 和异步支持'
            }
        }
    
    def generate_installation_command(self, frameworks: List[str], include_notifications: bool = False) -> str:
        """
        生成特定框架的安装命令
        
        Args:
            frameworks (List[str]): 框架列表
            include_notifications (bool): 是否包含通知依赖
            
        Returns:
            str: 安装命令
        """
        if not frameworks:
            return "pip install web-performance-monitor"
        
        # 去重并排序
        unique_frameworks = sorted(set(frameworks))
        
        # 构建extras列表
        extras = unique_frameworks.copy()
        
        if include_notifications:
            extras.append('notifications')
        
        if len(extras) == 1:
            return f"pip install web-performance-monitor[{extras[0]}]"
        elif set(extras) >= {'flask', 'fastapi', 'notifications'}:
            return "pip install web-performance-monitor[all]"
        else:
            extras_str = ','.join(extras)
            return f"pip install web-performance-monitor[{extras_str}]"
    
    def generate_framework_specific_guide(self, framework: str) -> Dict[str, any]:
        """
        生成框架特定的安装指导
        
        Args:
            framework (str): 框架名称
            
        Returns:
            Dict[str, any]: 详细的安装指导
        """
        if framework not in self.framework_detector.SUPPORTED_FRAMEWORKS:
            return {
                'error': f'不支持的框架: {framework}',
                'supported_frameworks': list(self.framework_detector.SUPPORTED_FRAMEWORKS.keys())
            }
        
        # 检查当前状态
        status = self.dependency_manager.check_framework_dependencies(framework)
        
        guide = {
            'framework': framework,
            'current_status': {
                'available': status.is_available,
                'installed_version': status.installed_version,
                'required_version': status.required_version,
                'missing_packages': status.missing_packages
            },
            'installation': {
                'command': self.generate_installation_command([framework]),
                'estimated_size': self.package_sizes.get(framework, '未知'),
                'description': self._get_framework_description(framework)
            },
            'compatibility': self.compatibility_info.get(framework, {}),
            'next_steps': self._generate_next_steps(framework, status)
        }
        
        # 为FastAPI添加异步依赖信息
        if framework == 'fastapi':
            async_deps = self.framework_detector.check_fastapi_async_dependencies()
            guide['async_dependencies'] = {
                'status': async_deps,
                'missing': [dep for dep, available in async_deps.items() if not available],
                'notes': '异步功能需要所有异步依赖都可用'
            }
        
        return guide
    
    def generate_multi_framework_recommendations(self, target_frameworks: List[str]) -> List[InstallationRecommendation]:
        """
        生成多框架组合安装的建议
        
        Args:
            target_frameworks (List[str]): 目标框架列表
            
        Returns:
            List[InstallationRecommendation]: 安装建议列表
        """
        recommendations = []
        
        # 检测当前环境
        installed_frameworks = self.framework_detector.detect_installed_frameworks()
        
        # 选项1: 安装所有目标框架
        if len(target_frameworks) > 1:
            all_command = self.generate_installation_command(target_frameworks, include_notifications=True)
            total_size = self._estimate_total_size(target_frameworks + ['notifications'])
            
            recommendations.append(InstallationRecommendation(
                command=all_command,
                description=f"安装所有目标框架支持: {', '.join(target_frameworks)}",
                priority=1,
                reason="提供完整功能支持",
                estimated_size=total_size,
                compatibility_notes="推荐用于需要多框架支持的项目"
            ))
        
        # 选项2: 逐个安装框架
        for framework in target_frameworks:
            if framework not in installed_frameworks:
                command = self.generate_installation_command([framework])
                size = self.package_sizes.get(framework, '未知')
                
                recommendations.append(InstallationRecommendation(
                    command=command,
                    description=f"仅安装 {framework} 支持",
                    priority=2,
                    reason=f"最小化安装，仅支持 {framework}",
                    estimated_size=f"{size} MB",
                    compatibility_notes=self.compatibility_info.get(framework, {}).get('notes')
                ))
        
        # 选项3: 渐进式安装建议
        if installed_frameworks:
            missing_frameworks = [fw for fw in target_frameworks if fw not in installed_frameworks]
            if missing_frameworks:
                command = self.generate_installation_command(missing_frameworks)
                
                recommendations.append(InstallationRecommendation(
                    command=command,
                    description=f"添加缺失的框架支持: {', '.join(missing_frameworks)}",
                    priority=1,
                    reason=f"基于已安装的 {', '.join(installed_frameworks)} 扩展功能",
                    estimated_size=self._estimate_total_size(missing_frameworks)
                ))
        
        # 按优先级排序
        recommendations.sort(key=lambda x: x.priority)
        return recommendations
    
    def generate_environment_specific_guide(self) -> Dict[str, any]:
        """
        生成基于当前环境的个性化安装指导
        
        Returns:
            Dict[str, any]: 环境特定的安装指导
        """
        # 收集环境信息
        env_info = {
            'python_version': platform.python_version(),
            'platform': platform.system(),
            'architecture': platform.machine()
        }
        
        # 检测已安装框架
        installed_frameworks = self.framework_detector.detect_installed_frameworks()
        
        # 检测环境中可能的框架使用
        detected_framework = self.framework_detector.detect_framework_from_environment()
        
        # 生成建议
        recommendations = []
        
        if detected_framework:
            # 有明确检测到的框架
            status = self.dependency_manager.check_framework_dependencies(detected_framework)
            
            if not status.is_available:
                recommendations.append({
                    'type': 'immediate',
                    'priority': 'high',
                    'command': self.generate_installation_command([detected_framework]),
                    'reason': f'检测到 {detected_framework} 环境但依赖不完整',
                    'missing_packages': status.missing_packages
                })
        
        elif installed_frameworks:
            # 有已安装的框架但可能依赖不完整
            for framework in installed_frameworks:
                status = self.dependency_manager.check_framework_dependencies(framework)
                if not status.is_available and status.missing_packages:
                    recommendations.append({
                        'type': 'maintenance',
                        'priority': 'medium',
                        'command': self.generate_installation_command([framework]),
                        'reason': f'{framework} 依赖不完整',
                        'missing_packages': status.missing_packages
                    })
        
        else:
            # 没有检测到框架，提供通用建议
            recommendations.extend([
                {
                    'type': 'exploration',
                    'priority': 'low',
                    'command': 'pip install web-performance-monitor[flask]',
                    'reason': 'Flask 是最流行的 Python web 框架',
                    'use_case': '适合传统web应用和API'
                },
                {
                    'type': 'exploration', 
                    'priority': 'low',
                    'command': 'pip install web-performance-monitor[fastapi]',
                    'reason': 'FastAPI 提供现代异步web开发',
                    'use_case': '适合高性能API和微服务'
                },
                {
                    'type': 'comprehensive',
                    'priority': 'medium',
                    'command': 'pip install web-performance-monitor[all]',
                    'reason': '获得完整功能支持',
                    'use_case': '适合多框架项目或学习用途'
                }
            ])
        
        return {
            'environment': env_info,
            'detected_frameworks': installed_frameworks,
            'detected_usage': detected_framework,
            'recommendations': recommendations,
            'next_steps': self._generate_environment_next_steps(recommendations)
        }
    
    def generate_troubleshooting_guide(self, error_info: Dict[str, any]) -> Dict[str, any]:
        """
        生成故障排除指导
        
        Args:
            error_info (Dict[str, any]): 错误信息
            
        Returns:
            Dict[str, any]: 故障排除指导
        """
        troubleshooting = {
            'common_issues': [],
            'specific_solutions': [],
            'verification_steps': []
        }
        
        # 常见问题和解决方案
        common_issues = [
            {
                'issue': '导入错误 (ImportError)',
                'solutions': [
                    '确认已安装对应框架: pip list | grep flask',
                    '重新安装依赖: pip install --force-reinstall web-performance-monitor[flask]',
                    '检查虚拟环境是否正确激活'
                ]
            },
            {
                'issue': '版本不兼容',
                'solutions': [
                    '升级到兼容版本: pip install --upgrade flask>=2.0.0',
                    '检查依赖冲突: pip check',
                    '创建新的虚拟环境重新安装'
                ]
            },
            {
                'issue': 'FastAPI 异步功能不可用',
                'solutions': [
                    '安装完整的 FastAPI 支持: pip install web-performance-monitor[fastapi]',
                    '确认异步依赖: pip list | grep -E "(uvicorn|aiofiles|aiohttp)"',
                    '检查 Python 版本是否支持异步 (>=3.7)'
                ]
            }
        ]
        
        troubleshooting['common_issues'] = common_issues
        
        # 基于错误信息的特定解决方案
        if 'missing_packages' in error_info:
            missing = error_info['missing_packages']
            for package in missing:
                if package == 'flask':
                    troubleshooting['specific_solutions'].append({
                        'package': package,
                        'command': 'pip install web-performance-monitor[flask]',
                        'verification': 'python -c "import flask; print(flask.__version__)"'
                    })
                elif package in ['uvicorn', 'aiofiles', 'aiohttp']:
                    troubleshooting['specific_solutions'].append({
                        'package': package,
                        'command': 'pip install web-performance-monitor[fastapi]',
                        'verification': f'python -c "import {package}; print({package}.__version__)"'
                    })
        
        # 验证步骤
        troubleshooting['verification_steps'] = [
            '检查 Python 版本: python --version',
            '检查已安装包: pip list | grep web-performance-monitor',
            '验证框架导入: python -c "import web_performance_monitor; print(web_performance_monitor.get_supported_frameworks())"',
            '运行依赖检查: python -c "import web_performance_monitor; print(web_performance_monitor.check_dependencies())"'
        ]
        
        return troubleshooting
    
    def _get_framework_description(self, framework: str) -> str:
        """获取框架描述"""
        descriptions = {
            'flask': 'Flask 是一个轻量级的 Python web 框架，适合构建传统web应用和RESTful API',
            'fastapi': 'FastAPI 是一个现代、快速的web框架，专为构建API而设计，支持异步编程和自动API文档生成'
        }
        return descriptions.get(framework, f'{framework} web框架支持')
    
    def _generate_next_steps(self, framework: str, status: DependencyStatus) -> List[str]:
        """生成下一步操作建议"""
        if status.is_available:
            return [
                f'✅ {framework} 依赖已完整安装',
                f'可以开始使用 {framework} 监控功能',
                '查看文档了解具体使用方法'
            ]
        else:
            steps = [f'📦 安装 {framework} 依赖: {status.installation_command}']
            
            if status.missing_packages:
                steps.append(f'缺失的包: {", ".join(status.missing_packages)}')
            
            steps.extend([
                '安装完成后重新导入模块',
                '运行依赖检查确认安装成功'
            ])
            
            return steps
    
    def _estimate_total_size(self, packages: List[str]) -> str:
        """估算总安装大小"""
        total_min = 0
        total_max = 0
        
        for package in packages:
            if package in self.package_sizes:
                size_range = self.package_sizes[package]
                if '-' in size_range:
                    min_size, max_size = map(int, size_range.split('-'))
                    total_min += min_size
                    total_max += max_size
                else:
                    size = int(size_range)
                    total_min += size
                    total_max += size
        
        if total_min == total_max:
            return f"{total_min} MB"
        else:
            return f"{total_min}-{total_max} MB"
    
    def _generate_environment_next_steps(self, recommendations: List[Dict]) -> List[str]:
        """生成环境特定的下一步建议"""
        if not recommendations:
            return ['运行 web_performance_monitor.check_dependencies() 检查当前状态']
        
        high_priority = [r for r in recommendations if r.get('priority') == 'high']
        
        if high_priority:
            return [
                '🚨 立即执行高优先级建议',
                f"运行: {high_priority[0]['command']}",
                '完成后重新检查依赖状态'
            ]
        else:
            return [
                '📋 根据项目需求选择合适的安装选项',
                '💡 建议从最小安装开始，按需添加功能',
                '📚 查看文档了解各框架的特性和用途'
            ]