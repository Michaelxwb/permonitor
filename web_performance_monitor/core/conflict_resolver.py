"""
依赖冲突检测和解决模块

提供版本兼容性检查、依赖冲突检测和解决建议功能。
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ConflictSeverity(Enum):
    """冲突严重程度"""
    LOW = "low"           # 轻微冲突，可能不影响功能
    MEDIUM = "medium"     # 中等冲突，可能影响部分功能
    HIGH = "high"         # 严重冲突，可能导致功能失效
    CRITICAL = "critical" # 致命冲突，必须解决


class ConflictType(Enum):
    """冲突类型"""
    VERSION_MISMATCH = "version_mismatch"       # 版本不匹配
    MISSING_DEPENDENCY = "missing_dependency"   # 缺失依赖
    CIRCULAR_DEPENDENCY = "circular_dependency" # 循环依赖
    INCOMPATIBLE_VERSIONS = "incompatible_versions" # 不兼容版本
    DUPLICATE_DEPENDENCY = "duplicate_dependency"   # 重复依赖


@dataclass
class DependencyInfo:
    """依赖信息"""
    name: str
    version: Optional[str] = None
    version_spec: str = ""
    required_by: List[str] = field(default_factory=list)
    optional: bool = False
    
    def __post_init__(self):
        if not self.name:
            raise ValueError("依赖名称不能为空")


@dataclass
class ConflictInfo:
    """冲突信息"""
    conflict_type: ConflictType
    severity: ConflictSeverity
    description: str
    affected_packages: List[str] = field(default_factory=list)
    conflicting_requirements: Dict[str, str] = field(default_factory=dict)
    resolution_suggestions: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.description:
            raise ValueError("冲突描述不能为空")


class VersionSpecParser:
    """版本规范解析器"""
    
    def __init__(self):
        # 版本比较操作符的正则表达式
        self.version_pattern = re.compile(
            r'^([><=!~]+)?\s*([0-9]+(?:\.[0-9]+)*(?:[-+][a-zA-Z0-9]+)*)\s*$'
        )
    
    def parse_version_spec(self, spec: str) -> List[Tuple[str, str]]:
        """
        解析版本规范
        
        Args:
            spec (str): 版本规范字符串，如 ">=1.0.0,<2.0.0"
            
        Returns:
            List[Tuple[str, str]]: (操作符, 版本) 的列表
        """
        if not spec:
            return []
        
        # 分割多个条件
        conditions = [cond.strip() for cond in spec.split(',')]
        parsed_conditions = []
        
        for condition in conditions:
            match = self.version_pattern.match(condition)
            if match:
                operator = match.group(1) or '=='
                version = match.group(2)
                parsed_conditions.append((operator, version))
            else:
                logger.warning(f"无法解析版本规范: {condition}")
        
        return parsed_conditions
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """
        比较两个版本
        
        Args:
            version1 (str): 版本1
            version2 (str): 版本2
            
        Returns:
            int: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """
        try:
            # 尝试使用packaging库进行精确比较
            from packaging import version
            v1 = version.parse(version1)
            v2 = version.parse(version2)
            
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            else:
                return 0
        except ImportError:
            # 如果没有packaging库，使用简单的字符串比较
            return self._simple_version_compare(version1, version2)
    
    def _simple_version_compare(self, version1: str, version2: str) -> int:
        """简单的版本比较实现"""
        def normalize_version(v):
            return [int(x) for x in v.split('.') if x.isdigit()]
        
        v1_parts = normalize_version(version1)
        v2_parts = normalize_version(version2)
        
        # 补齐长度
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        for i in range(max_len):
            if v1_parts[i] < v2_parts[i]:
                return -1
            elif v1_parts[i] > v2_parts[i]:
                return 1
        
        return 0
    
    def check_version_compatibility(self, version: str, spec: str) -> bool:
        """
        检查版本是否满足规范
        
        Args:
            version (str): 实际版本
            spec (str): 版本规范
            
        Returns:
            bool: 是否兼容
        """
        if not spec:
            return True
        
        conditions = self.parse_version_spec(spec)
        
        for operator, required_version in conditions:
            comparison = self.compare_versions(version, required_version)
            
            if operator == '==' and comparison != 0:
                return False
            elif operator == '!=' and comparison == 0:
                return False
            elif operator == '>' and comparison <= 0:
                return False
            elif operator == '>=' and comparison < 0:
                return False
            elif operator == '<' and comparison >= 0:
                return False
            elif operator == '<=' and comparison > 0:
                return False
            elif operator == '~=' and not self._compatible_release(version, required_version):
                return False
        
        return True
    
    def _compatible_release(self, version: str, base_version: str) -> bool:
        """检查兼容发布版本（~=操作符）"""
        try:
            v_parts = [int(x) for x in version.split('.') if x.isdigit()]
            b_parts = [int(x) for x in base_version.split('.') if x.isdigit()]
            
            if len(v_parts) < len(b_parts):
                return False
            
            # 检查前n-1位是否相等，最后一位是否>=
            for i in range(len(b_parts) - 1):
                if v_parts[i] != b_parts[i]:
                    return False
            
            return v_parts[len(b_parts) - 1] >= b_parts[-1]
        except (ValueError, IndexError):
            return False


class ConflictDetector:
    """冲突检测器"""
    
    def __init__(self):
        self.version_parser = VersionSpecParser()
        self._installed_packages = {}
        self._dependency_graph = {}
    
    def detect_conflicts(self, dependencies: List[DependencyInfo]) -> List[ConflictInfo]:
        """
        检测依赖冲突
        
        Args:
            dependencies (List[DependencyInfo]): 依赖列表
            
        Returns:
            List[ConflictInfo]: 检测到的冲突列表
        """
        conflicts = []
        
        # 更新已安装包信息
        self._update_installed_packages()
        
        # 构建依赖图
        self._build_dependency_graph(dependencies)
        
        # 检测各种类型的冲突
        conflicts.extend(self._detect_version_conflicts(dependencies))
        conflicts.extend(self._detect_missing_dependencies(dependencies))
        conflicts.extend(self._detect_circular_dependencies())
        conflicts.extend(self._detect_incompatible_versions(dependencies))
        
        return conflicts
    
    def _update_installed_packages(self):
        """更新已安装包信息"""
        try:
            import pkg_resources
            self._installed_packages = {
                pkg.project_name.lower(): pkg.version 
                for pkg in pkg_resources.working_set
            }
        except ImportError:
            logger.warning("pkg_resources不可用，无法获取已安装包信息")
            self._installed_packages = {}
    
    def _build_dependency_graph(self, dependencies: List[DependencyInfo]):
        """构建依赖图"""
        self._dependency_graph = {}
        
        for dep in dependencies:
            if dep.name not in self._dependency_graph:
                self._dependency_graph[dep.name] = {
                    'version_spec': dep.version_spec,
                    'required_by': dep.required_by.copy(),
                    'optional': dep.optional
                }
            else:
                # 合并依赖信息
                existing = self._dependency_graph[dep.name]
                existing['required_by'].extend(dep.required_by)
                existing['required_by'] = list(set(existing['required_by']))
                
                # 如果有一个是必需的，则整体为必需
                existing['optional'] = existing['optional'] and dep.optional
    
    def _detect_version_conflicts(self, dependencies: List[DependencyInfo]) -> List[ConflictInfo]:
        """检测版本冲突"""
        conflicts = []
        
        # 按包名分组
        package_requirements = {}
        for dep in dependencies:
            if dep.name not in package_requirements:
                package_requirements[dep.name] = []
            package_requirements[dep.name].append(dep)
        
        # 检查每个包的版本要求
        for package_name, deps in package_requirements.items():
            if len(deps) > 1:
                # 检查版本规范是否兼容
                version_specs = [dep.version_spec for dep in deps if dep.version_spec]
                if len(set(version_specs)) > 1:
                    # 有不同的版本要求
                    conflict = self._create_version_conflict(package_name, deps)
                    if conflict:
                        conflicts.append(conflict)
        
        return conflicts
    
    def _create_version_conflict(self, package_name: str, deps: List[DependencyInfo]) -> Optional[ConflictInfo]:
        """创建版本冲突信息"""
        conflicting_requirements = {}
        required_by = []
        
        for dep in deps:
            if dep.version_spec:
                for requirer in dep.required_by:
                    conflicting_requirements[requirer] = dep.version_spec
                required_by.extend(dep.required_by)
        
        if len(conflicting_requirements) > 1:
            description = f"包 {package_name} 有冲突的版本要求"
            
            # 尝试找到兼容的版本范围
            suggestions = self._generate_version_resolution_suggestions(package_name, deps)
            
            return ConflictInfo(
                conflict_type=ConflictType.VERSION_MISMATCH,
                severity=ConflictSeverity.MEDIUM,
                description=description,
                affected_packages=[package_name],
                conflicting_requirements=conflicting_requirements,
                resolution_suggestions=suggestions
            )
        
        return None
    
    def _detect_missing_dependencies(self, dependencies: List[DependencyInfo]) -> List[ConflictInfo]:
        """检测缺失依赖"""
        conflicts = []
        
        for dep in dependencies:
            if not dep.optional and dep.name.lower() not in self._installed_packages:
                conflict = ConflictInfo(
                    conflict_type=ConflictType.MISSING_DEPENDENCY,
                    severity=ConflictSeverity.HIGH,
                    description=f"缺失必需的依赖: {dep.name}",
                    affected_packages=[dep.name],
                    resolution_suggestions=[
                        f"安装缺失的依赖: pip install {dep.name}",
                        f"或安装完整版本: pip install web-performance-monitor[all]"
                    ]
                )
                conflicts.append(conflict)
        
        return conflicts
    
    def _detect_circular_dependencies(self) -> List[ConflictInfo]:
        """检测循环依赖"""
        conflicts = []
        visited = set()
        rec_stack = set()
        
        def has_cycle(node, path):
            if node in rec_stack:
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                return cycle
            
            if node in visited:
                return None
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            # 检查依赖关系（这里简化处理，实际需要更复杂的依赖解析）
            dependencies = self._dependency_graph.get(node, {}).get('required_by', [])
            for dep in dependencies:
                cycle = has_cycle(dep, path.copy())
                if cycle:
                    return cycle
            
            rec_stack.remove(node)
            path.pop()
            return None
        
        for package in self._dependency_graph:
            if package not in visited:
                cycle = has_cycle(package, [])
                if cycle:
                    conflict = ConflictInfo(
                        conflict_type=ConflictType.CIRCULAR_DEPENDENCY,
                        severity=ConflictSeverity.HIGH,
                        description=f"检测到循环依赖: {' -> '.join(cycle)}",
                        affected_packages=cycle,
                        resolution_suggestions=[
                            "检查依赖配置，移除循环引用",
                            "考虑重构代码以避免循环依赖"
                        ]
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def _detect_incompatible_versions(self, dependencies: List[DependencyInfo]) -> List[ConflictInfo]:
        """检测不兼容版本"""
        conflicts = []
        
        for dep in dependencies:
            installed_version = self._installed_packages.get(dep.name.lower())
            if installed_version and dep.version_spec:
                if not self.version_parser.check_version_compatibility(installed_version, dep.version_spec):
                    conflict = ConflictInfo(
                        conflict_type=ConflictType.INCOMPATIBLE_VERSIONS,
                        severity=ConflictSeverity.HIGH,
                        description=f"已安装的 {dep.name} 版本 {installed_version} 不满足要求 {dep.version_spec}",
                        affected_packages=[dep.name],
                        resolution_suggestions=[
                            f"升级到兼容版本: pip install '{dep.name}{dep.version_spec}'",
                            f"或降级到兼容版本（如果可能）"
                        ]
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def _generate_version_resolution_suggestions(self, package_name: str, deps: List[DependencyInfo]) -> List[str]:
        """生成版本解决建议"""
        suggestions = []
        
        # 收集所有版本要求
        version_specs = [dep.version_spec for dep in deps if dep.version_spec]
        
        if len(version_specs) > 1:
            suggestions.append(f"尝试找到满足所有要求的 {package_name} 版本")
            suggestions.append(f"检查是否可以更新依赖 {package_name} 的包")
            suggestions.append("考虑使用虚拟环境隔离不兼容的依赖")
        
        return suggestions


class ConflictResolver:
    """冲突解决器"""
    
    def __init__(self):
        self.detector = ConflictDetector()
    
    def analyze_and_resolve(self, dependencies: List[DependencyInfo]) -> Dict[str, Any]:
        """
        分析并提供解决方案
        
        Args:
            dependencies (List[DependencyInfo]): 依赖列表
            
        Returns:
            Dict[str, Any]: 分析结果和解决方案
        """
        # 检测冲突
        conflicts = self.detector.detect_conflicts(dependencies)
        
        # 按严重程度分类
        conflicts_by_severity = self._categorize_conflicts(conflicts)
        
        # 生成解决方案
        resolution_plan = self._generate_resolution_plan(conflicts)
        
        # 生成报告
        report = self._generate_conflict_report(conflicts, resolution_plan)
        
        return {
            'conflicts': conflicts,
            'conflicts_by_severity': conflicts_by_severity,
            'resolution_plan': resolution_plan,
            'report': report,
            'has_critical_conflicts': any(c.severity == ConflictSeverity.CRITICAL for c in conflicts),
            'total_conflicts': len(conflicts)
        }
    
    def _categorize_conflicts(self, conflicts: List[ConflictInfo]) -> Dict[str, List[ConflictInfo]]:
        """按严重程度分类冲突"""
        categorized = {severity.value: [] for severity in ConflictSeverity}
        
        for conflict in conflicts:
            categorized[conflict.severity.value].append(conflict)
        
        return categorized
    
    def _generate_resolution_plan(self, conflicts: List[ConflictInfo]) -> List[Dict[str, Any]]:
        """生成解决方案计划"""
        plan = []
        
        # 按优先级排序冲突（严重程度高的优先）
        sorted_conflicts = sorted(conflicts, key=lambda c: self._get_severity_priority(c.severity), reverse=True)
        
        for i, conflict in enumerate(sorted_conflicts, 1):
            step = {
                'step': i,
                'conflict_type': conflict.conflict_type.value,
                'severity': conflict.severity.value,
                'description': conflict.description,
                'affected_packages': conflict.affected_packages,
                'actions': conflict.resolution_suggestions,
                'estimated_time': self._estimate_resolution_time(conflict),
                'risk_level': self._assess_resolution_risk(conflict)
            }
            plan.append(step)
        
        return plan
    
    def _get_severity_priority(self, severity: ConflictSeverity) -> int:
        """获取严重程度优先级"""
        priority_map = {
            ConflictSeverity.CRITICAL: 4,
            ConflictSeverity.HIGH: 3,
            ConflictSeverity.MEDIUM: 2,
            ConflictSeverity.LOW: 1
        }
        return priority_map.get(severity, 0)
    
    def _estimate_resolution_time(self, conflict: ConflictInfo) -> str:
        """估算解决时间"""
        time_estimates = {
            ConflictType.MISSING_DEPENDENCY: "5-10分钟",
            ConflictType.VERSION_MISMATCH: "10-30分钟",
            ConflictType.INCOMPATIBLE_VERSIONS: "15-45分钟",
            ConflictType.CIRCULAR_DEPENDENCY: "30分钟-2小时",
            ConflictType.DUPLICATE_DEPENDENCY: "5-15分钟"
        }
        return time_estimates.get(conflict.conflict_type, "未知")
    
    def _assess_resolution_risk(self, conflict: ConflictInfo) -> str:
        """评估解决风险"""
        risk_levels = {
            ConflictType.MISSING_DEPENDENCY: "低",
            ConflictType.VERSION_MISMATCH: "中",
            ConflictType.INCOMPATIBLE_VERSIONS: "中",
            ConflictType.CIRCULAR_DEPENDENCY: "高",
            ConflictType.DUPLICATE_DEPENDENCY: "低"
        }
        return risk_levels.get(conflict.conflict_type, "未知")
    
    def _generate_conflict_report(self, conflicts: List[ConflictInfo], resolution_plan: List[Dict[str, Any]]) -> str:
        """生成冲突报告"""
        if not conflicts:
            return "✅ 未检测到依赖冲突"
        
        report = "🔍 依赖冲突分析报告\n\n"
        
        # 概述
        report += f"检测到 {len(conflicts)} 个依赖冲突:\n"
        
        severity_counts = {}
        for conflict in conflicts:
            severity = conflict.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        for severity, count in severity_counts.items():
            emoji = self._get_severity_emoji(severity)
            report += f"  {emoji} {severity.upper()}: {count} 个\n"
        
        report += "\n"
        
        # 详细冲突信息
        report += "📋 详细冲突信息:\n\n"
        for i, conflict in enumerate(conflicts, 1):
            emoji = self._get_severity_emoji(conflict.severity.value)
            report += f"{i}. {emoji} {conflict.description}\n"
            report += f"   类型: {conflict.conflict_type.value}\n"
            report += f"   影响包: {', '.join(conflict.affected_packages)}\n"
            
            if conflict.conflicting_requirements:
                report += "   冲突要求:\n"
                for requirer, requirement in conflict.conflicting_requirements.items():
                    report += f"     - {requirer}: {requirement}\n"
            
            report += "\n"
        
        # 解决方案
        if resolution_plan:
            report += "🛠️ 建议的解决方案:\n\n"
            for step in resolution_plan:
                report += f"步骤 {step['step']}: {step['description']}\n"
                report += f"  预估时间: {step['estimated_time']}\n"
                report += f"  风险等级: {step['risk_level']}\n"
                report += "  操作步骤:\n"
                for action in step['actions']:
                    report += f"    - {action}\n"
                report += "\n"
        
        return report
    
    def _get_severity_emoji(self, severity: str) -> str:
        """获取严重程度对应的emoji"""
        emoji_map = {
            'critical': '🚨',
            'high': '⚠️',
            'medium': '⚡',
            'low': 'ℹ️'
        }
        return emoji_map.get(severity, '❓')
    
    def get_quick_fix_suggestions(self, conflicts: List[ConflictInfo]) -> List[str]:
        """获取快速修复建议"""
        suggestions = []
        
        # 统计冲突类型
        conflict_types = [c.conflict_type for c in conflicts]
        
        if ConflictType.MISSING_DEPENDENCY in conflict_types:
            suggestions.append("运行 'pip install web-performance-monitor[all]' 安装所有依赖")
        
        if ConflictType.VERSION_MISMATCH in conflict_types:
            suggestions.append("使用虚拟环境隔离项目依赖")
            suggestions.append("更新到最新版本的依赖包")
        
        if ConflictType.INCOMPATIBLE_VERSIONS in conflict_types:
            suggestions.append("检查并更新requirements.txt中的版本约束")
        
        if ConflictType.CIRCULAR_DEPENDENCY in conflict_types:
            suggestions.append("重构代码以消除循环依赖")
        
        return suggestions