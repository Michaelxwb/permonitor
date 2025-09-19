"""
Data models.

This module contains all data model definitions.
"""

from .models import PerformanceMetrics, AlertRecord, CacheEntry

# 依赖管理相关模型
try:
    from .dependency_models import DependencyStatus, EnvironmentReport, DependencyConfig, DependencyType
    _dependency_models_available = True
except ImportError:
    DependencyStatus = None
    EnvironmentReport = None
    DependencyConfig = None
    DependencyType = None
    _dependency_models_available = False

__all__ = [
    'PerformanceMetrics',
    'AlertRecord', 
    'CacheEntry'
]

# 只有在依赖模型可用时才添加到__all__
if _dependency_models_available:
    __all__.extend([
        'DependencyStatus',
        'EnvironmentReport', 
        'DependencyConfig',
        'DependencyType'
    ])