"""
依赖管理相关的数据模型
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Set
from enum import Enum
from datetime import datetime


class DependencyType(Enum):
    """依赖类型枚举"""
    CORE = "core"
    FRAMEWORK = "framework"
    NOTIFICATION = "notification"
    ASYNC = "async"


class DependencyChangeType(Enum):
    """依赖变更类型枚举"""
    ADDED = "added"
    REMOVED = "removed"
    UPDATED = "updated"
    RESOLVED = "resolved"
    BROKEN = "broken"


@dataclass
class DependencyStatus:
    """依赖状态信息"""
    framework: str
    is_available: bool
    missing_packages: List[str] = field(default_factory=list)
    installed_version: Optional[str] = None
    required_version: str = ""
    installation_command: str = ""
    dependency_type: DependencyType = DependencyType.FRAMEWORK
    last_checked: Optional[datetime] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.installation_command and self.framework:
            self.installation_command = f"pip install web-performance-monitor[{self.framework}]"
        
        if self.last_checked is None:
            self.last_checked = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['dependency_type'] = self.dependency_type.value
        if self.last_checked:
            data['last_checked'] = self.last_checked.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DependencyStatus':
        """从字典创建实例"""
        if 'dependency_type' in data:
            data['dependency_type'] = DependencyType(data['dependency_type'])
        
        if 'last_checked' in data and isinstance(data['last_checked'], str):
            data['last_checked'] = datetime.fromisoformat(data['last_checked'])
        
        return cls(**data)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DependencyStatus':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def compare_with(self, other: 'DependencyStatus') -> Dict[str, Any]:
        """与另一个状态比较"""
        if self.framework != other.framework:
            raise ValueError("只能比较相同框架的状态")
        
        changes = {
            'framework': self.framework,
            'availability_changed': self.is_available != other.is_available,
            'version_changed': self.installed_version != other.installed_version,
            'missing_packages_changed': set(self.missing_packages) != set(other.missing_packages),
            'changes': []
        }
        
        if changes['availability_changed']:
            if self.is_available and not other.is_available:
                changes['changes'].append({
                    'type': DependencyChangeType.RESOLVED.value,
                    'description': f'{self.framework} 依赖已解决'
                })
            elif not self.is_available and other.is_available:
                changes['changes'].append({
                    'type': DependencyChangeType.BROKEN.value,
                    'description': f'{self.framework} 依赖已损坏'
                })
        
        if changes['version_changed']:
            changes['changes'].append({
                'type': DependencyChangeType.UPDATED.value,
                'description': f'{self.framework} 版本从 {other.installed_version} 更新到 {self.installed_version}'
            })
        
        if changes['missing_packages_changed']:
            current_missing = set(self.missing_packages)
            previous_missing = set(other.missing_packages)
            
            resolved_packages = previous_missing - current_missing
            new_missing_packages = current_missing - previous_missing
            
            for package in resolved_packages:
                changes['changes'].append({
                    'type': DependencyChangeType.RESOLVED.value,
                    'description': f'包 {package} 已安装'
                })
            
            for package in new_missing_packages:
                changes['changes'].append({
                    'type': DependencyChangeType.BROKEN.value,
                    'description': f'包 {package} 缺失'
                })
        
        return changes
    
    def is_outdated(self, max_age_hours: int = 24) -> bool:
        """检查状态是否过期"""
        if not self.last_checked:
            return True
        
        age = datetime.now() - self.last_checked
        return age.total_seconds() > max_age_hours * 3600
    
    def get_health_score(self) -> float:
        """获取健康评分 (0-1)"""
        if self.is_available:
            return 1.0
        
        if not self.missing_packages:
            return 0.8  # 框架存在但可能有其他问题
        
        # 根据缺失包的数量计算评分
        max_missing = 5  # 假设最多缺失5个包
        missing_count = len(self.missing_packages)
        return max(0.0, 1.0 - (missing_count / max_missing))


@dataclass
class EnvironmentReport:
    """环境依赖报告"""
    supported_frameworks: List[str] = field(default_factory=list)
    available_frameworks: List[str] = field(default_factory=list)
    dependency_statuses: Dict[str, DependencyStatus] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def add_recommendation(self, message: str):
        """添加建议"""
        if message not in self.recommendations:
            self.recommendations.append(message)
    
    def add_warning(self, message: str):
        """添加警告"""
        if message not in self.warnings:
            self.warnings.append(message)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取报告摘要"""
        return {
            'total_supported': len(self.supported_frameworks),
            'total_available': len(self.available_frameworks),
            'missing_frameworks': [
                fw for fw in self.supported_frameworks 
                if fw not in self.available_frameworks
            ],
            'has_warnings': len(self.warnings) > 0,
            'has_recommendations': len(self.recommendations) > 0,
            'overall_health': self.get_overall_health_score(),
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    def get_overall_health_score(self) -> float:
        """获取整体健康评分"""
        if not self.dependency_statuses:
            return 0.0
        
        total_score = sum(status.get_health_score() for status in self.dependency_statuses.values())
        return total_score / len(self.dependency_statuses)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = {
            'supported_frameworks': self.supported_frameworks,
            'available_frameworks': self.available_frameworks,
            'dependency_statuses': {
                name: status.to_dict() for name, status in self.dependency_statuses.items()
            },
            'recommendations': self.recommendations,
            'warnings': self.warnings,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnvironmentReport':
        """从字典创建实例"""
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        if 'dependency_statuses' in data:
            data['dependency_statuses'] = {
                name: DependencyStatus.from_dict(status_data)
                for name, status_data in data['dependency_statuses'].items()
            }
        
        return cls(**data)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'EnvironmentReport':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def compare_with(self, other: 'EnvironmentReport') -> Dict[str, Any]:
        """与另一个报告比较"""
        comparison = {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'previous_timestamp': other.timestamp.isoformat() if other.timestamp else None,
            'framework_changes': {
                'added': list(set(self.available_frameworks) - set(other.available_frameworks)),
                'removed': list(set(other.available_frameworks) - set(self.available_frameworks))
            },
            'dependency_changes': {},
            'health_score_change': self.get_overall_health_score() - other.get_overall_health_score()
        }
        
        # 比较依赖状态变更
        all_frameworks = set(self.dependency_statuses.keys()) | set(other.dependency_statuses.keys())
        
        for framework in all_frameworks:
            current_status = self.dependency_statuses.get(framework)
            previous_status = other.dependency_statuses.get(framework)
            
            if current_status and previous_status:
                changes = current_status.compare_with(previous_status)
                if changes['changes']:  # 只记录有变更的
                    comparison['dependency_changes'][framework] = changes
            elif current_status and not previous_status:
                comparison['dependency_changes'][framework] = {
                    'type': DependencyChangeType.ADDED.value,
                    'description': f'新增框架 {framework}'
                }
            elif not current_status and previous_status:
                comparison['dependency_changes'][framework] = {
                    'type': DependencyChangeType.REMOVED.value,
                    'description': f'移除框架 {framework}'
                }
        
        return comparison
    
    def filter_by_framework_type(self, framework_types: List[DependencyType]) -> 'EnvironmentReport':
        """按依赖类型过滤报告"""
        filtered_statuses = {
            name: status for name, status in self.dependency_statuses.items()
            if status.dependency_type in framework_types
        }
        
        return EnvironmentReport(
            supported_frameworks=self.supported_frameworks,
            available_frameworks=[
                fw for fw in self.available_frameworks
                if fw in filtered_statuses and filtered_statuses[fw].is_available
            ],
            dependency_statuses=filtered_statuses,
            recommendations=self.recommendations.copy(),
            warnings=self.warnings.copy(),
            timestamp=self.timestamp
        )


@dataclass
class DependencyConfig:
    """依赖配置"""
    skip_dependency_check: bool = False
    strict_dependencies: bool = False
    auto_install_deps: bool = False
    preferred_frameworks: List[str] = field(default_factory=list)
    notification_channels: List[str] = field(default_factory=list)
    
    @classmethod
    def from_env_vars(cls, env_dict: Dict[str, str]) -> 'DependencyConfig':
        """从环境变量创建配置"""
        return cls(
            skip_dependency_check=env_dict.get('WPM_SKIP_DEPENDENCY_CHECK', '').lower() == 'true',
            strict_dependencies=env_dict.get('WPM_STRICT_DEPENDENCIES', '').lower() == 'true',
            auto_install_deps=env_dict.get('WPM_AUTO_INSTALL_DEPS', '').lower() == 'true',
            preferred_frameworks=env_dict.get('WPM_PREFERRED_FRAMEWORKS', '').split(',') if env_dict.get('WPM_PREFERRED_FRAMEWORKS') else [],
            notification_channels=env_dict.get('WPM_NOTIFICATION_CHANNELS', '').split(',') if env_dict.get('WPM_NOTIFICATION_CHANNELS') else []
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DependencyConfig':
        """从字典创建实例"""
        return cls(**data)
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        # 验证首选框架
        supported_frameworks = ['flask', 'fastapi']
        for framework in self.preferred_frameworks:
            if framework not in supported_frameworks:
                errors.append(f"不支持的首选框架: {framework}")
        
        # 验证通知渠道
        supported_channels = ['mattermost', 'file', 'console']
        for channel in self.notification_channels:
            if channel not in supported_channels:
                errors.append(f"不支持的通知渠道: {channel}")
        
        return errors