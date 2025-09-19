"""
环境变量控制机制模块

提供环境变量解析、验证和配置优先级处理功能。
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union, Callable, Type
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ConfigPriority(Enum):
    """配置优先级枚举"""
    ENVIRONMENT = 1  # 环境变量（最高优先级）
    CONFIG_FILE = 2  # 配置文件
    DEFAULT = 3      # 默认值（最低优先级）


@dataclass
class EnvVarDefinition:
    """环境变量定义"""
    name: str
    default_value: Any
    value_type: Type
    description: str
    validator: Optional[Callable[[Any], bool]] = None
    transformer: Optional[Callable[[str], Any]] = None
    required: bool = False
    choices: Optional[List[Any]] = None


class EnvironmentConfigManager:
    """环境变量配置管理器"""
    
    def __init__(self):
        self.env_var_definitions: Dict[str, EnvVarDefinition] = {}
        self.config_cache: Dict[str, Any] = {}
        self.validation_errors: List[str] = []
        
        # 注册默认的环境变量定义
        self._register_default_env_vars()
    
    def _register_default_env_vars(self):
        """注册默认的环境变量定义"""
        
        # 依赖管理相关环境变量
        self.register_env_var(EnvVarDefinition(
            name='WPM_SKIP_DEPENDENCY_CHECK',
            default_value=False,
            value_type=bool,
            description='跳过运行时依赖检查',
            transformer=self._str_to_bool
        ))
        
        self.register_env_var(EnvVarDefinition(
            name='WPM_STRICT_DEPENDENCIES',
            default_value=False,
            value_type=bool,
            description='严格依赖模式，缺少依赖时抛出异常',
            transformer=self._str_to_bool
        ))
        
        self.register_env_var(EnvVarDefinition(
            name='WPM_AUTO_INSTALL_DEPS',
            default_value=False,
            value_type=bool,
            description='自动安装缺失的依赖（仅开发环境）',
            transformer=self._str_to_bool
        ))
        
        self.register_env_var(EnvVarDefinition(
            name='WPM_PREFERRED_FRAMEWORKS',
            default_value=[],
            value_type=list,
            description='首选框架列表，逗号分隔',
            transformer=self._str_to_list,
            validator=self._validate_frameworks
        ))
        
        self.register_env_var(EnvVarDefinition(
            name='WPM_NOTIFICATION_CHANNELS',
            default_value=[],
            value_type=list,
            description='通知渠道列表，逗号分隔',
            transformer=self._str_to_list,
            validator=self._validate_notification_channels
        ))
        
        # 自动检测相关环境变量
        self.register_env_var(EnvVarDefinition(
            name='WPM_ENABLE_AUTO_DETECTION',
            default_value=True,
            value_type=bool,
            description='启用自动框架检测',
            transformer=self._str_to_bool
        ))
        
        self.register_env_var(EnvVarDefinition(
            name='WPM_AUTO_DETECTION_INTERVAL',
            default_value=300,
            value_type=int,
            description='自动检测间隔（秒）',
            transformer=int,
            validator=lambda x: x > 0
        ))
        
        self.register_env_var(EnvVarDefinition(
            name='WPM_ENABLE_FRAMEWORK_MONITORING',
            default_value=True,
            value_type=bool,
            description='启用框架变更监控',
            transformer=self._str_to_bool
        ))
        
        # 优雅降级相关环境变量
        self.register_env_var(EnvVarDefinition(
            name='WPM_ENABLE_GRACEFUL_DEGRADATION',
            default_value=True,
            value_type=bool,
            description='启用优雅降级',
            transformer=self._str_to_bool
        ))
        
        self.register_env_var(EnvVarDefinition(
            name='WPM_FALLBACK_TO_BASIC_MONITOR',
            default_value=True,
            value_type=bool,
            description='回退到基础监控器',
            transformer=self._str_to_bool
        ))
        
        self.register_env_var(EnvVarDefinition(
            name='WPM_SHOW_DEPENDENCY_WARNINGS',
            default_value=True,
            value_type=bool,
            description='显示依赖警告',
            transformer=self._str_to_bool
        ))
        
        # 安装建议相关环境变量
        self.register_env_var(EnvVarDefinition(
            name='WPM_SHOW_INSTALLATION_SUGGESTIONS',
            default_value=True,
            value_type=bool,
            description='显示安装建议',
            transformer=self._str_to_bool
        ))
        
        self.register_env_var(EnvVarDefinition(
            name='WPM_SUGGEST_OPTIMAL_INSTALLATION',
            default_value=True,
            value_type=bool,
            description='建议最优安装方案',
            transformer=self._str_to_bool
        ))
        
        self.register_env_var(EnvVarDefinition(
            name='WPM_INCLUDE_SIZE_ESTIMATES',
            default_value=True,
            value_type=bool,
            description='包含大小估算',
            transformer=self._str_to_bool
        ))
        
        # 日志和调试相关环境变量
        self.register_env_var(EnvVarDefinition(
            name='WPM_LOG_LEVEL',
            default_value='INFO',
            value_type=str,
            description='日志级别',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            validator=lambda x: x.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        ))
        
        self.register_env_var(EnvVarDefinition(
            name='WPM_DEBUG_MODE',
            default_value=False,
            value_type=bool,
            description='调试模式',
            transformer=self._str_to_bool
        ))
        
        # 性能相关环境变量
        self.register_env_var(EnvVarDefinition(
            name='WPM_CACHE_DURATION',
            default_value=300,
            value_type=int,
            description='缓存持续时间（秒）',
            transformer=int,
            validator=lambda x: x >= 0
        ))
        
        self.register_env_var(EnvVarDefinition(
            name='WPM_MAX_CACHE_SIZE',
            default_value=1000,
            value_type=int,
            description='最大缓存大小',
            transformer=int,
            validator=lambda x: x > 0
        ))
    
    def register_env_var(self, definition: EnvVarDefinition):
        """注册环境变量定义"""
        self.env_var_definitions[definition.name] = definition
        logger.debug(f"注册环境变量: {definition.name}")
    
    def get_env_value(self, var_name: str, use_cache: bool = True) -> Any:
        """
        获取环境变量值
        
        Args:
            var_name (str): 环境变量名称
            use_cache (bool): 是否使用缓存
            
        Returns:
            Any: 环境变量值
        """
        # 检查缓存
        if use_cache and var_name in self.config_cache:
            return self.config_cache[var_name]
        
        # 获取环境变量定义
        if var_name not in self.env_var_definitions:
            raise ValueError(f"未注册的环境变量: {var_name}")
        
        definition = self.env_var_definitions[var_name]
        
        # 获取原始值
        raw_value = os.getenv(var_name)
        
        if raw_value is None:
            # 使用默认值
            value = definition.default_value
        else:
            # 转换值
            try:
                if definition.transformer:
                    value = definition.transformer(raw_value)
                else:
                    value = raw_value
            except (ValueError, TypeError) as e:
                logger.error(f"环境变量 {var_name} 值转换失败: {e}")
                value = definition.default_value
        
        # 验证值
        if not self._validate_value(var_name, value, definition):
            logger.warning(f"环境变量 {var_name} 验证失败，使用默认值")
            value = definition.default_value
        
        # 缓存结果
        if use_cache:
            self.config_cache[var_name] = value
        
        return value
    
    def get_all_env_values(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        获取所有环境变量值
        
        Args:
            use_cache (bool): 是否使用缓存
            
        Returns:
            Dict[str, Any]: 所有环境变量值
        """
        result = {}
        
        for var_name in self.env_var_definitions:
            try:
                result[var_name] = self.get_env_value(var_name, use_cache)
            except Exception as e:
                logger.error(f"获取环境变量 {var_name} 失败: {e}")
                result[var_name] = self.env_var_definitions[var_name].default_value
        
        return result
    
    def validate_all_env_vars(self) -> bool:
        """
        验证所有环境变量
        
        Returns:
            bool: 是否所有环境变量都有效
        """
        self.validation_errors.clear()
        all_valid = True
        
        for var_name, definition in self.env_var_definitions.items():
            raw_value = os.getenv(var_name)
            
            # 检查必需的环境变量
            if definition.required and raw_value is None:
                self.validation_errors.append(f"必需的环境变量 {var_name} 未设置")
                all_valid = False
                continue
            
            if raw_value is not None:
                # 转换和验证值
                try:
                    if definition.transformer:
                        value = definition.transformer(raw_value)
                    else:
                        value = raw_value
                    
                    if not self._validate_value(var_name, value, definition):
                        all_valid = False
                        
                except (ValueError, TypeError) as e:
                    self.validation_errors.append(f"环境变量 {var_name} 值转换失败: {e}")
                    all_valid = False
        
        return all_valid
    
    def get_validation_errors(self) -> List[str]:
        """获取验证错误列表"""
        return self.validation_errors.copy()
    
    def clear_cache(self):
        """清除配置缓存"""
        self.config_cache.clear()
        logger.debug("环境变量缓存已清除")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要
        
        Returns:
            Dict[str, Any]: 配置摘要
        """
        summary = {
            'total_env_vars': len(self.env_var_definitions),
            'cached_values': len(self.config_cache),
            'validation_errors': len(self.validation_errors),
            'env_var_status': {}
        }
        
        for var_name, definition in self.env_var_definitions.items():
            raw_value = os.getenv(var_name)
            summary['env_var_status'][var_name] = {
                'set': raw_value is not None,
                'value': raw_value if raw_value is not None else definition.default_value,
                'using_default': raw_value is None,
                'type': definition.value_type.__name__,
                'description': definition.description
            }
        
        return summary
    
    def export_env_template(self, include_descriptions: bool = True) -> str:
        """
        导出环境变量模板
        
        Args:
            include_descriptions (bool): 是否包含描述
            
        Returns:
            str: 环境变量模板
        """
        lines = []
        
        if include_descriptions:
            lines.append("# Web Performance Monitor 环境变量配置")
            lines.append("# 复制此文件为 .env 并根据需要修改值")
            lines.append("")
        
        for var_name, definition in sorted(self.env_var_definitions.items()):
            if include_descriptions:
                lines.append(f"# {definition.description}")
                if definition.choices:
                    lines.append(f"# 可选值: {', '.join(map(str, definition.choices))}")
                lines.append(f"# 类型: {definition.value_type.__name__}")
                lines.append(f"# 默认值: {definition.default_value}")
                if definition.required:
                    lines.append("# 必需: 是")
            
            # 格式化默认值
            if isinstance(definition.default_value, bool):
                default_str = str(definition.default_value).lower()
            elif isinstance(definition.default_value, list):
                default_str = ','.join(map(str, definition.default_value))
            else:
                default_str = str(definition.default_value)
            
            lines.append(f"{var_name}={default_str}")
            
            if include_descriptions:
                lines.append("")
        
        return '\n'.join(lines)
    
    def _validate_value(self, var_name: str, value: Any, definition: EnvVarDefinition) -> bool:
        """验证环境变量值"""
        try:
            # 类型检查
            if not isinstance(value, definition.value_type):
                self.validation_errors.append(
                    f"环境变量 {var_name} 类型错误: 期望 {definition.value_type.__name__}, 得到 {type(value).__name__}"
                )
                return False
            
            # 选择检查
            if definition.choices and value not in definition.choices:
                self.validation_errors.append(
                    f"环境变量 {var_name} 值无效: {value}, 可选值: {definition.choices}"
                )
                return False
            
            # 自定义验证器
            if definition.validator and not definition.validator(value):
                self.validation_errors.append(f"环境变量 {var_name} 自定义验证失败: {value}")
                return False
            
            return True
            
        except Exception as e:
            self.validation_errors.append(f"环境变量 {var_name} 验证时出错: {e}")
            return False
    
    def _str_to_bool(self, value: str) -> bool:
        """字符串转布尔值"""
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    def _str_to_list(self, value: str) -> List[str]:
        """字符串转列表（逗号分隔）"""
        if not value.strip():
            return []
        return [item.strip() for item in value.split(',') if item.strip()]
    
    def _str_to_json(self, value: str) -> Any:
        """字符串转JSON"""
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}")
    
    def _validate_frameworks(self, frameworks: List[str]) -> bool:
        """验证框架列表"""
        supported_frameworks = ['flask', 'fastapi']
        for framework in frameworks:
            if framework not in supported_frameworks:
                return False
        return True
    
    def _validate_notification_channels(self, channels: List[str]) -> bool:
        """验证通知渠道列表"""
        supported_channels = ['mattermost', 'file', 'console']
        for channel in channels:
            if channel not in supported_channels:
                return False
        return True


# 全局环境配置管理器实例
_global_env_manager: Optional[EnvironmentConfigManager] = None


def get_env_manager() -> EnvironmentConfigManager:
    """获取全局环境配置管理器"""
    global _global_env_manager
    
    if _global_env_manager is None:
        _global_env_manager = EnvironmentConfigManager()
    
    return _global_env_manager


def get_env_config(var_name: str, use_cache: bool = True) -> Any:
    """获取环境变量配置（便捷函数）"""
    manager = get_env_manager()
    return manager.get_env_value(var_name, use_cache)


def validate_env_config() -> bool:
    """验证环境变量配置（便捷函数）"""
    manager = get_env_manager()
    return manager.validate_all_env_vars()


def get_env_config_summary() -> Dict[str, Any]:
    """获取环境变量配置摘要（便捷函数）"""
    manager = get_env_manager()
    return manager.get_config_summary()


def export_env_template(file_path: Optional[str] = None) -> str:
    """导出环境变量模板（便捷函数）"""
    manager = get_env_manager()
    template = manager.export_env_template()
    
    if file_path:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(template)
            logger.info(f"环境变量模板已导出到: {file_path}")
        except Exception as e:
            logger.error(f"导出环境变量模板失败: {e}")
    
    return template