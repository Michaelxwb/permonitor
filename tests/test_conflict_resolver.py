"""
依赖冲突检测和解决测试模块
"""

import pytest
from unittest.mock import patch, MagicMock

from web_performance_monitor.core.conflict_resolver import (
    DependencyInfo,
    ConflictInfo,
    ConflictType,
    ConflictSeverity,
    VersionSpecParser,
    ConflictDetector,
    ConflictResolver
)


class TestDependencyInfo:
    """依赖信息测试类"""
    
    def test_dependency_info_creation(self):
        """测试依赖信息创建"""
        dep = DependencyInfo(
            name="flask",
            version="2.0.0",
            version_spec=">=2.0.0",
            required_by=["web_app"],
            optional=False
        )
        
        assert dep.name == "flask"
        assert dep.version == "2.0.0"
        assert dep.version_spec == ">=2.0.0"
        assert dep.required_by == ["web_app"]
        assert dep.optional == False
    
    def test_dependency_info_validation(self):
        """测试依赖信息验证"""
        with pytest.raises(ValueError, match="依赖名称不能为空"):
            DependencyInfo(name="")


class TestConflictInfo:
    """冲突信息测试类"""
    
    def test_conflict_info_creation(self):
        """测试冲突信息创建"""
        conflict = ConflictInfo(
            conflict_type=ConflictType.VERSION_MISMATCH,
            severity=ConflictSeverity.MEDIUM,
            description="版本冲突",
            affected_packages=["flask"],
            conflicting_requirements={"app1": ">=2.0.0", "app2": ">=1.0.0,<2.0.0"}
        )
        
        assert conflict.conflict_type == ConflictType.VERSION_MISMATCH
        assert conflict.severity == ConflictSeverity.MEDIUM
        assert conflict.description == "版本冲突"
        assert conflict.affected_packages == ["flask"]
        assert len(conflict.conflicting_requirements) == 2
    
    def test_conflict_info_validation(self):
        """测试冲突信息验证"""
        with pytest.raises(ValueError, match="冲突描述不能为空"):
            ConflictInfo(
                conflict_type=ConflictType.VERSION_MISMATCH,
                severity=ConflictSeverity.MEDIUM,
                description=""
            )


class TestVersionSpecParser:
    """版本规范解析器测试类"""
    
    def setup_method(self):
        """测试方法设置"""
        self.parser = VersionSpecParser()
    
    def test_parse_version_spec_single(self):
        """测试解析单个版本规范"""
        result = self.parser.parse_version_spec(">=1.0.0")
        
        assert len(result) == 1
        assert result[0] == (">=", "1.0.0")
    
    def test_parse_version_spec_multiple(self):
        """测试解析多个版本规范"""
        result = self.parser.parse_version_spec(">=1.0.0,<2.0.0")
        
        assert len(result) == 2
        assert (">=", "1.0.0") in result
        assert ("<", "2.0.0") in result
    
    def test_parse_version_spec_empty(self):
        """测试解析空版本规范"""
        result = self.parser.parse_version_spec("")
        
        assert result == []
    
    def test_parse_version_spec_invalid(self):
        """测试解析无效版本规范"""
        result = self.parser.parse_version_spec("invalid_spec")
        
        assert result == []
    
    @patch('web_performance_monitor.core.conflict_resolver.version')
    def test_compare_versions_with_packaging(self, mock_version_module):
        """测试使用packaging库比较版本"""
        mock_v1 = MagicMock()
        mock_v2 = MagicMock()
        mock_version_module.parse.side_effect = [mock_v1, mock_v2]
        
        # 测试v1 < v2
        mock_v1.__lt__ = MagicMock(return_value=True)
        mock_v1.__gt__ = MagicMock(return_value=False)
        result = self.parser.compare_versions("1.0.0", "2.0.0")
        assert result == -1
        
        # 测试v1 > v2
        mock_v1.__lt__ = MagicMock(return_value=False)
        mock_v1.__gt__ = MagicMock(return_value=True)
        result = self.parser.compare_versions("2.0.0", "1.0.0")
        assert result == 1
        
        # 测试v1 == v2
        mock_v1.__lt__ = MagicMock(return_value=False)
        mock_v1.__gt__ = MagicMock(return_value=False)
        result = self.parser.compare_versions("1.0.0", "1.0.0")
        assert result == 0
    
    def test_compare_versions_simple(self):
        """测试简单版本比较"""
        # 模拟没有packaging库的情况
        with patch('web_performance_monitor.core.conflict_resolver.version', side_effect=ImportError):
            result = self.parser.compare_versions("1.0.0", "2.0.0")
            assert result == -1
            
            result = self.parser.compare_versions("2.0.0", "1.0.0")
            assert result == 1
            
            result = self.parser.compare_versions("1.0.0", "1.0.0")
            assert result == 0
    
    def test_check_version_compatibility(self):
        """测试版本兼容性检查"""
        # 测试等于
        assert self.parser.check_version_compatibility("1.0.0", "==1.0.0") == True
        assert self.parser.check_version_compatibility("1.0.1", "==1.0.0") == False
        
        # 测试大于等于
        assert self.parser.check_version_compatibility("1.0.0", ">=1.0.0") == True
        assert self.parser.check_version_compatibility("1.0.1", ">=1.0.0") == True
        assert self.parser.check_version_compatibility("0.9.0", ">=1.0.0") == False
        
        # 测试小于
        assert self.parser.check_version_compatibility("0.9.0", "<1.0.0") == True
        assert self.parser.check_version_compatibility("1.0.0", "<1.0.0") == False
        
        # 测试空规范
        assert self.parser.check_version_compatibility("1.0.0", "") == True
    
    def test_compatible_release(self):
        """测试兼容发布版本检查"""
        # 测试兼容发布
        assert self.parser._compatible_release("1.4.2", "1.4.0") == True
        assert self.parser._compatible_release("1.4.0", "1.4.0") == True
        assert self.parser._compatible_release("1.3.9", "1.4.0") == False
        assert self.parser._compatible_release("1.5.0", "1.4.0") == False


class TestConflictDetector:
    """冲突检测器测试类"""
    
    def setup_method(self):
        """测试方法设置"""
        self.detector = ConflictDetector()
    
    @patch('web_performance_monitor.core.conflict_resolver.pkg_resources')
    def test_update_installed_packages(self, mock_pkg_resources):
        """测试更新已安装包信息"""
        mock_pkg = MagicMock()
        mock_pkg.project_name = "Flask"
        mock_pkg.version = "2.0.0"
        mock_pkg_resources.working_set = [mock_pkg]
        
        self.detector._update_installed_packages()
        
        assert "flask" in self.detector._installed_packages
        assert self.detector._installed_packages["flask"] == "2.0.0"
    
    def test_build_dependency_graph(self):
        """测试构建依赖图"""
        deps = [
            DependencyInfo("flask", version_spec=">=2.0.0", required_by=["app1"]),
            DependencyInfo("flask", version_spec=">=1.0.0", required_by=["app2"]),
            DependencyInfo("requests", version_spec=">=2.25.0", required_by=["app1"])
        ]
        
        self.detector._build_dependency_graph(deps)
        
        assert "flask" in self.detector._dependency_graph
        assert "requests" in self.detector._dependency_graph
        
        flask_info = self.detector._dependency_graph["flask"]
        assert "app1" in flask_info["required_by"]
        assert "app2" in flask_info["required_by"]
    
    def test_detect_version_conflicts(self):
        """测试检测版本冲突"""
        deps = [
            DependencyInfo("flask", version_spec=">=2.0.0", required_by=["app1"]),
            DependencyInfo("flask", version_spec=">=1.0.0,<2.0.0", required_by=["app2"])
        ]
        
        conflicts = self.detector._detect_version_conflicts(deps)
        
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.VERSION_MISMATCH
        assert "flask" in conflicts[0].affected_packages
    
    def test_detect_missing_dependencies(self):
        """测试检测缺失依赖"""
        deps = [
            DependencyInfo("nonexistent_package", required_by=["app1"], optional=False)
        ]
        
        self.detector._installed_packages = {}  # 模拟没有安装任何包
        
        conflicts = self.detector._detect_missing_dependencies(deps)
        
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.MISSING_DEPENDENCY
        assert conflicts[0].severity == ConflictSeverity.HIGH
    
    def test_detect_incompatible_versions(self):
        """测试检测不兼容版本"""
        deps = [
            DependencyInfo("flask", version_spec=">=3.0.0", required_by=["app1"])
        ]
        
        self.detector._installed_packages = {"flask": "2.0.0"}
        
        conflicts = self.detector._detect_incompatible_versions(deps)
        
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.INCOMPATIBLE_VERSIONS
        assert conflicts[0].severity == ConflictSeverity.HIGH
    
    def test_detect_conflicts_integration(self):
        """测试冲突检测集成"""
        deps = [
            DependencyInfo("flask", version_spec=">=2.0.0", required_by=["app1"]),
            DependencyInfo("missing_package", required_by=["app1"], optional=False)
        ]
        
        self.detector._installed_packages = {"flask": "1.0.0"}  # 版本不兼容
        
        conflicts = self.detector.detect_conflicts(deps)
        
        # 应该检测到缺失依赖和版本不兼容
        conflict_types = [c.conflict_type for c in conflicts]
        assert ConflictType.MISSING_DEPENDENCY in conflict_types
        assert ConflictType.INCOMPATIBLE_VERSIONS in conflict_types


class TestConflictResolver:
    """冲突解决器测试类"""
    
    def setup_method(self):
        """测试方法设置"""
        self.resolver = ConflictResolver()
    
    def test_categorize_conflicts(self):
        """测试冲突分类"""
        conflicts = [
            ConflictInfo(ConflictType.VERSION_MISMATCH, ConflictSeverity.HIGH, "高严重度冲突"),
            ConflictInfo(ConflictType.MISSING_DEPENDENCY, ConflictSeverity.MEDIUM, "中等严重度冲突"),
            ConflictInfo(ConflictType.INCOMPATIBLE_VERSIONS, ConflictSeverity.LOW, "低严重度冲突")
        ]
        
        categorized = self.resolver._categorize_conflicts(conflicts)
        
        assert len(categorized["high"]) == 1
        assert len(categorized["medium"]) == 1
        assert len(categorized["low"]) == 1
        assert len(categorized["critical"]) == 0
    
    def test_generate_resolution_plan(self):
        """测试生成解决方案计划"""
        conflicts = [
            ConflictInfo(ConflictType.MISSING_DEPENDENCY, ConflictSeverity.HIGH, "缺失依赖", 
                        resolution_suggestions=["安装依赖"]),
            ConflictInfo(ConflictType.VERSION_MISMATCH, ConflictSeverity.MEDIUM, "版本冲突",
                        resolution_suggestions=["更新版本"])
        ]
        
        plan = self.resolver._generate_resolution_plan(conflicts)
        
        assert len(plan) == 2
        # 高严重度的应该排在前面
        assert plan[0]["severity"] == "high"
        assert plan[1]["severity"] == "medium"
        
        # 检查计划结构
        for step in plan:
            assert "step" in step
            assert "conflict_type" in step
            assert "actions" in step
            assert "estimated_time" in step
            assert "risk_level" in step
    
    def test_get_severity_priority(self):
        """测试获取严重程度优先级"""
        assert self.resolver._get_severity_priority(ConflictSeverity.CRITICAL) == 4
        assert self.resolver._get_severity_priority(ConflictSeverity.HIGH) == 3
        assert self.resolver._get_severity_priority(ConflictSeverity.MEDIUM) == 2
        assert self.resolver._get_severity_priority(ConflictSeverity.LOW) == 1
    
    def test_estimate_resolution_time(self):
        """测试估算解决时间"""
        conflict = ConflictInfo(ConflictType.MISSING_DEPENDENCY, ConflictSeverity.HIGH, "测试")
        time_estimate = self.resolver._estimate_resolution_time(conflict)
        
        assert "分钟" in time_estimate
    
    def test_assess_resolution_risk(self):
        """测试评估解决风险"""
        conflict = ConflictInfo(ConflictType.CIRCULAR_DEPENDENCY, ConflictSeverity.HIGH, "测试")
        risk_level = self.resolver._assess_resolution_risk(conflict)
        
        assert risk_level == "高"
    
    def test_analyze_and_resolve_no_conflicts(self):
        """测试分析无冲突的情况"""
        deps = [
            DependencyInfo("flask", version_spec=">=2.0.0", required_by=["app1"])
        ]
        
        # 模拟没有冲突
        with patch.object(self.resolver.detector, 'detect_conflicts', return_value=[]):
            result = self.resolver.analyze_and_resolve(deps)
            
            assert result["total_conflicts"] == 0
            assert result["has_critical_conflicts"] == False
            assert "✅ 未检测到依赖冲突" in result["report"]
    
    def test_analyze_and_resolve_with_conflicts(self):
        """测试分析有冲突的情况"""
        deps = [
            DependencyInfo("flask", version_spec=">=2.0.0", required_by=["app1"])
        ]
        
        conflicts = [
            ConflictInfo(ConflictType.MISSING_DEPENDENCY, ConflictSeverity.HIGH, "缺失依赖",
                        affected_packages=["flask"], resolution_suggestions=["安装依赖"])
        ]
        
        with patch.object(self.resolver.detector, 'detect_conflicts', return_value=conflicts):
            result = self.resolver.analyze_and_resolve(deps)
            
            assert result["total_conflicts"] == 1
            assert result["has_critical_conflicts"] == False
            assert len(result["resolution_plan"]) == 1
            assert "依赖冲突分析报告" in result["report"]
    
    def test_generate_conflict_report_no_conflicts(self):
        """测试生成无冲突报告"""
        report = self.resolver._generate_conflict_report([], [])
        
        assert "✅ 未检测到依赖冲突" in report
    
    def test_generate_conflict_report_with_conflicts(self):
        """测试生成有冲突的报告"""
        conflicts = [
            ConflictInfo(ConflictType.MISSING_DEPENDENCY, ConflictSeverity.HIGH, "缺失依赖",
                        affected_packages=["flask"])
        ]
        
        resolution_plan = [
            {
                "step": 1,
                "description": "解决缺失依赖",
                "estimated_time": "5-10分钟",
                "risk_level": "低",
                "actions": ["安装依赖"]
            }
        ]
        
        report = self.resolver._generate_conflict_report(conflicts, resolution_plan)
        
        assert "依赖冲突分析报告" in report
        assert "检测到 1 个依赖冲突" in report
        assert "HIGH: 1 个" in report
        assert "详细冲突信息" in report
        assert "建议的解决方案" in report
    
    def test_get_severity_emoji(self):
        """测试获取严重程度emoji"""
        assert self.resolver._get_severity_emoji("critical") == "🚨"
        assert self.resolver._get_severity_emoji("high") == "⚠️"
        assert self.resolver._get_severity_emoji("medium") == "⚡"
        assert self.resolver._get_severity_emoji("low") == "ℹ️"
        assert self.resolver._get_severity_emoji("unknown") == "❓"
    
    def test_get_quick_fix_suggestions(self):
        """测试获取快速修复建议"""
        conflicts = [
            ConflictInfo(ConflictType.MISSING_DEPENDENCY, ConflictSeverity.HIGH, "缺失依赖"),
            ConflictInfo(ConflictType.VERSION_MISMATCH, ConflictSeverity.MEDIUM, "版本冲突")
        ]
        
        suggestions = self.resolver.get_quick_fix_suggestions(conflicts)
        
        assert any("pip install web-performance-monitor[all]" in s for s in suggestions)
        assert any("虚拟环境" in s for s in suggestions)