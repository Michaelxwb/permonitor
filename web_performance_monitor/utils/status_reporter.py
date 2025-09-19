"""
状态报告生成器模块

提供详细的依赖检查报告功能，支持状态变更通知和日志记录。
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .dependency_manager import DependencyManager
from ..models.dependency_models import EnvironmentReport, DependencyStatus

logger = logging.getLogger(__name__)


class StatusReporter:
    """状态报告生成器"""
    
    def __init__(self):
        self.dependency_manager = DependencyManager()
    
    def generate_detailed_report(self) -> EnvironmentReport:
        """生成详细的依赖检查报告"""
        return self.dependency_manager.check_dependencies()
    
    def check_dependencies(self) -> EnvironmentReport:
        """执行完整的依赖检查并返回报告"""
        logger.info("开始生成依赖状态报告")
        
        report = self.generate_detailed_report()
        
        # 记录报告摘要
        summary = report.get_summary()
        logger.info(f"依赖检查完成: {summary['total_available']}/{summary['total_supported']} 框架可用")
        
        if summary['has_warnings']:
            logger.warning(f"发现 {len(report.warnings)} 个警告")
        
        if summary['has_recommendations']:
            logger.info(f"生成 {len(report.recommendations)} 个建议")
        
        return report