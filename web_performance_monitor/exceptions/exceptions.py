"""
异常定义模块

定义性能监控工具的异常层次结构
"""


class PerformanceMonitorError(Exception):
    """性能监控工具基础异常类"""
    pass


class ConfigurationError(PerformanceMonitorError):
    """配置相关错误"""
    pass


class NotificationError(PerformanceMonitorError):
    """通知发送相关错误"""
    pass


class ProfilingError(PerformanceMonitorError):
    """性能分析相关错误"""
    pass


class CacheError(PerformanceMonitorError):
    """缓存操作相关错误"""
    pass


class DependencyError(PerformanceMonitorError):
    """依赖相关错误的基类"""
    
    def __init__(self, message: str, framework: str = None, suggestions: list = None):
        """
        初始化依赖错误
        
        Args:
            message (str): 错误消息
            framework (str, optional): 相关框架名称
            suggestions (list, optional): 解决建议列表
        """
        super().__init__(message)
        self.framework = framework
        self.suggestions = suggestions or []


class MissingDependencyError(DependencyError):
    """缺失依赖错误"""
    
    def __init__(self, framework: str, missing_packages: list, installation_command: str = None):
        """
        初始化缺失依赖错误
        
        Args:
            framework (str): 框架名称
            missing_packages (list): 缺失的包列表
            installation_command (str, optional): 安装命令建议
        """
        self.framework = framework
        self.missing_packages = missing_packages
        self.installation_command = installation_command or f"pip install web-performance-monitor[{framework}]"
        
        missing_str = ', '.join(missing_packages)
        message = f"Missing dependencies for {framework}: {missing_str}"
        
        suggestions = [
            f"Install missing dependencies: {self.installation_command}",
            f"Or install all dependencies: pip install web-performance-monitor[all]"
        ]
        
        super().__init__(message, framework, suggestions)
    
    def get_installation_guide(self) -> str:
        """
        获取详细的安装指导
        
        Returns:
            str: 安装指导文本
        """
        guide = f"缺少 {self.framework} 依赖: {', '.join(self.missing_packages)}\n\n"
        guide += "解决方案:\n"
        for i, suggestion in enumerate(self.suggestions, 1):
            guide += f"{i}. {suggestion}\n"
        
        return guide


class FrameworkNotSupportedError(DependencyError):
    """不支持的框架错误"""
    
    def __init__(self, framework: str, supported_frameworks: list = None):
        """
        初始化不支持框架错误
        
        Args:
            framework (str): 不支持的框架名称
            supported_frameworks (list, optional): 支持的框架列表
        """
        self.unsupported_framework = framework
        self.supported_frameworks = supported_frameworks or []
        
        message = f"Framework '{framework}' is not supported"
        
        suggestions = []
        if self.supported_frameworks:
            suggestions.append(f"Supported frameworks: {', '.join(self.supported_frameworks)}")
            suggestions.append("Consider using one of the supported frameworks")
        
        super().__init__(message, framework, suggestions)


class DependencyConflictError(DependencyError):
    """依赖冲突错误"""
    
    def __init__(self, conflicting_packages: dict, resolution_suggestions: list = None):
        """
        初始化依赖冲突错误
        
        Args:
            conflicting_packages (dict): 冲突的包及其版本信息
            resolution_suggestions (list, optional): 解决建议
        """
        self.conflicting_packages = conflicting_packages
        
        conflict_details = []
        for package, versions in conflicting_packages.items():
            if isinstance(versions, dict):
                required = versions.get('required', 'unknown')
                installed = versions.get('installed', 'unknown')
                conflict_details.append(f"{package} (required: {required}, installed: {installed})")
            else:
                conflict_details.append(f"{package}: {versions}")
        
        message = f"Dependency conflicts detected: {', '.join(conflict_details)}"
        
        suggestions = resolution_suggestions or [
            "Update conflicting packages to compatible versions",
            "Create a new virtual environment",
            "Check for package compatibility issues"
        ]
        
        super().__init__(message, None, suggestions)


class DependencyVersionError(DependencyError):
    """依赖版本错误"""
    
    def __init__(self, package: str, required_version: str, installed_version: str = None):
        """
        初始化依赖版本错误
        
        Args:
            package (str): 包名称
            required_version (str): 需要的版本
            installed_version (str, optional): 已安装的版本
        """
        self.package = package
        self.required_version = required_version
        self.installed_version = installed_version
        
        if installed_version:
            message = f"Package '{package}' version mismatch: required {required_version}, installed {installed_version}"
        else:
            message = f"Package '{package}' version {required_version} is required but not installed"
        
        suggestions = [
            f"Upgrade package: pip install '{package}>={required_version}'",
            f"Or reinstall with correct version: pip install '{package}=={required_version}'"
        ]
        
        super().__init__(message, package, suggestions)


class EnvironmentValidationError(DependencyError):
    """环境验证错误"""
    
    def __init__(self, validation_failures: list, environment_info: dict = None):
        """
        初始化环境验证错误
        
        Args:
            validation_failures (list): 验证失败的项目列表
            environment_info (dict, optional): 环境信息
        """
        self.validation_failures = validation_failures
        self.environment_info = environment_info or {}
        
        failures_str = '; '.join(validation_failures)
        message = f"Environment validation failed: {failures_str}"
        
        suggestions = [
            "Check your Python environment setup",
            "Verify all required packages are installed",
            "Consider recreating your virtual environment"
        ]
        
        super().__init__(message, None, suggestions)