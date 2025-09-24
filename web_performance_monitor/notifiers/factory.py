"""
通知器工厂模块

负责根据配置创建和管理通知器实例
"""

import logging
from typing import List, Dict, Type, Any

from .base import BaseNotifier
from .local_file import LocalFileNotifier
from .mattermost import MattermostNotifier
from ..config import Config
from ..exceptions import ConfigurationError, NotificationError


class NotificationFactory:
    """通知器工厂

    根据配置创建通知器实例，支持扩展新的通知器类型
    """

    def __init__(self, config: Config):
        """初始化通知器工厂

        Args:
            config: 配置实例
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 注册内置通知器类型
        self._notifier_registry: Dict[str, Type[BaseNotifier]] = {
            'local_file': LocalFileNotifier,
            'mattermost': MattermostNotifier
        }

    def create_notifiers(self) -> List[BaseNotifier]:
        """根据配置创建通知器列表，支持同时启用多种通知方式

        Returns:
            List[BaseNotifier]: 启用的通知器列表
        """
        notifiers = []

        try:
            # 创建本地文件通知器
            if self.config.enable_local_file:
                try:
                    local_notifier = self._create_local_file_notifier()
                    if local_notifier:
                        notifiers.append(local_notifier)
                        self.logger.info("本地文件通知器创建成功")
                except Exception as e:
                    self.logger.error(f"创建本地文件通知器失败: {e}")

            # 创建Mattermost通知器
            if self.config.enable_mattermost:
                try:
                    mattermost_notifier = self._create_mattermost_notifier()
                    if mattermost_notifier:
                        notifiers.append(mattermost_notifier)
                        self.logger.info("Mattermost通知器创建成功")
                except Exception as e:
                    self.logger.error(f"创建Mattermost通知器失败: {e}")

            if not notifiers:
                self.logger.warning("未创建任何通知器，将使用默认本地文件通知器")
                # 创建默认的本地文件通知器
                default_notifier = LocalFileNotifier()
                notifiers.append(default_notifier)

            self.logger.info(f"通知器工厂创建了 {len(notifiers)} 个通知器")
            return notifiers

        except Exception as e:
            self.logger.error(f"创建通知器失败: {e}")
            raise NotificationError(f"创建通知器失败: {e}")

    def _create_local_file_notifier(self) -> LocalFileNotifier:
        """创建本地文件通知器

        Returns:
            LocalFileNotifier: 本地文件通知器实例
        """
        return LocalFileNotifier(
            output_dir=self.config.local_output_dir
        )

    def _create_mattermost_notifier(self) -> MattermostNotifier:
        """创建Mattermost通知器

        Returns:
            MattermostNotifier: Mattermost通知器实例

        Raises:
            ConfigurationError: 配置无效时抛出
        """
        # 验证必需的配置
        if not self.config.mattermost_server_url:
            raise ConfigurationError("Mattermost服务器URL未配置")

        if not self.config.mattermost_token:
            raise ConfigurationError("Mattermost访问令牌未配置")

        if not self.config.mattermost_channel_id:
            raise ConfigurationError("Mattermost频道ID未配置")

        return MattermostNotifier(
            server_url=self.config.mattermost_server_url,
            token=self.config.mattermost_token,
            channel_id=self.config.mattermost_channel_id,
            max_retries=self.config.mattermost_max_retries
        )

    def register_notifier_type(self, notifier_type: str,
                               notifier_class: Type[BaseNotifier]) -> None:
        """注册新的通知器类型，支持扩展

        Args:
            notifier_type: 通知器类型名称
            notifier_class: 通知器类

        Raises:
            ValueError: 通知器类型无效时抛出
        """
        if not issubclass(notifier_class, BaseNotifier):
            raise ValueError(f"通知器类必须继承自BaseNotifier: {notifier_class}")

        self._notifier_registry[notifier_type] = notifier_class
        self.logger.info(
            f"注册通知器类型: {notifier_type} -> {notifier_class.__name__}")

    def get_registered_types(self) -> List[str]:
        """获取已注册的通知器类型列表

        Returns:
            List[str]: 通知器类型名称列表
        """
        return list(self._notifier_registry.keys())

    def create_notifier_by_type(self, notifier_type: str, **kwargs) -> BaseNotifier:
        """根据类型创建通知器实例

        Args:
            notifier_type: 通知器类型
            **kwargs: 通知器构造参数

        Returns:
            BaseNotifier: 通知器实例

        Raises:
            ValueError: 通知器类型未注册时抛出
            NotificationError: 创建失败时抛出
        """
        if notifier_type not in self._notifier_registry:
            raise ValueError(f"未注册的通知器类型: {notifier_type}")

        try:
            notifier_class = self._notifier_registry[notifier_type]
            notifier = notifier_class(**kwargs)

            # 验证配置
            if hasattr(notifier, 'validate_config'):
                if not notifier.validate_config():
                    raise NotificationError(f"通知器配置验证失败: {notifier_type}")

            self.logger.info(f"创建通知器成功: {notifier_type}")
            return notifier

        except Exception as e:
            self.logger.error(f"创建通知器失败: {notifier_type} - {e}")
            raise NotificationError(f"创建通知器失败: {notifier_type} - {e}")

    def create_custom_notifiers(self, notifier_configs: List[Dict[str, Any]]) -> List[
        BaseNotifier]:
        """根据自定义配置创建通知器列表

        Args:
            notifier_configs: 通知器配置列表，每个配置包含type和参数

        Returns:
            List[BaseNotifier]: 创建的通知器列表

        Example:
            notifier_configs = [
                {
                    'type': 'local_file',
                    'output_dir': '/custom/path'
                },
                {
                    'type': 'mattermost',
                    'server_url': 'https://mm.example.com',
                    'token': 'token',
                    'channel_id': 'channel'
                }
            ]
        """
        notifiers = []

        for config in notifier_configs:
            try:
                notifier_type = config.pop('type')
                notifier = self.create_notifier_by_type(notifier_type, **config)
                notifiers.append(notifier)

            except Exception as e:
                self.logger.error(f"创建自定义通知器失败: {config} - {e}")

        return notifiers

    def validate_all_configs(self) -> Dict[str, bool]:
        """验证所有启用的通知器配置

        Returns:
            Dict[str, bool]: 各通知器的配置验证结果
        """
        results = {}

        # 验证本地文件通知器配置
        if self.config.enable_local_file:
            try:
                notifier = self._create_local_file_notifier()
                results['local_file'] = notifier.validate_config() if hasattr(notifier,
                                                                              'validate_config') else True
            except Exception as e:
                self.logger.error(f"本地文件通知器配置验证失败: {e}")
                results['local_file'] = False

        # 验证Mattermost通知器配置
        if self.config.enable_mattermost:
            try:
                notifier = self._create_mattermost_notifier()
                results['mattermost'] = notifier.validate_config() if hasattr(notifier,
                                                                              'validate_config') else True
            except Exception as e:
                self.logger.error(f"Mattermost通知器配置验证失败: {e}")
                results['mattermost'] = False

        return results
