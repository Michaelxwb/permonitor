"""
Mattermost通知器

通过Mattermost发送性能告警通知
"""
import io
import logging
import time
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse

from .base import BaseNotifier
from ..exceptions import NotificationError
from ..formatters import NotificationFormatter

if TYPE_CHECKING:
    from ..models import PerformanceMetrics

try:
    from mattermostdriver import Driver
    MATTERMOST_AVAILABLE = True
except ImportError:
    MATTERMOST_AVAILABLE = False
    Driver = None


class MattermostNotifier(BaseNotifier):
    """Mattermost通知器

    发送HTML报告到Mattermost指定频道
    """

    def __init__(self, server_url: str, token: str, channel_id: str,
                 max_retries: int = 3):
        """初始化Mattermost通知器

        Args:
            server_url: Mattermost服务器URL
            token: 访问令牌
            channel_id: 频道ID
            max_retries: 最大重试次数
        """
        if not MATTERMOST_AVAILABLE:
            raise NotificationError(
                "mattermostdriver包未安装，请运行: pip install mattermostdriver")

        self.server_url = server_url.rstrip('/')
        self.token = token
        self.channel_id = channel_id
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)

        # 初始化Mattermost驱动
        self._driver: Optional[Driver] = None
        self._authenticated = False

    def _get_driver(self) -> Driver:
        """获取Mattermost驱动实例

        Returns:
            Driver: Mattermost驱动实例

        Raises:
            NotificationError: 连接失败时抛出
        """
        if self._driver is None or not self._authenticated:
            try:
                # 解析URL以获取正确的配置
                parsed_url = urlparse(self.server_url)

                # 确保URL格式正确
                if not parsed_url.scheme:
                    # 如果没有scheme，默认使用https
                    full_url = f"https://{self.server_url}"
                    parsed_url = urlparse(full_url)
                else:
                    full_url = self.server_url

                # 提取主机名和端口
                hostname = parsed_url.hostname or parsed_url.netloc.split(':')[0]
                port = parsed_url.port
                scheme = parsed_url.scheme or 'https'

                # 如果没有指定端口，使用默认端口
                if port is None:
                    port = 443 if scheme == 'https' else 80

                self.logger.debug(
                    f"Mattermost连接配置: scheme={scheme}, hostname={hostname}, port={port}")

                self._driver = Driver({
                    'url': hostname,
                    'token': self.token,
                    'scheme': scheme,
                    'port': port,
                    'verify': True,
                    'timeout': 30
                })

                # 登录
                self._driver.login()
                self._authenticated = True

                self.logger.debug("Mattermost连接成功")

            except Exception as e:
                self.logger.error(f"Mattermost连接失败: {e}")
                raise NotificationError(f"Mattermost连接失败: {e}")

        return self._driver

    def send_notification(self, metrics: 'PerformanceMetrics',
                          html_report: str) -> bool:
        """发送HTML报告到Mattermost指定频道

        - 将HTML报告作为附件发送
        - 包含描述性消息：接口名称、请求URL、请求参数、响应时间和告警时间
        - 实施最多3次重试机制
        - 发送失败时记录错误日志但不影响应用运行

        Args:
            metrics: 性能指标数据
            html_report: HTML格式的性能报告

        Returns:
            bool: 发送是否成功
        """
        return self._retry_send(metrics, html_report)

    def _retry_send(self, metrics: 'PerformanceMetrics', html_report: str) -> bool:
        """重试发送机制

        Args:
            metrics: 性能指标数据
            html_report: HTML报告

        Returns:
            bool: 发送是否成功
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    # 重试前等待
                    wait_time = min(2 ** attempt, 10)  # 指数退避，最大10秒
                    self.logger.info(
                        f"Mattermost发送重试 {attempt}/{self.max_retries}，等待 {wait_time}秒")
                    time.sleep(wait_time)

                success = self._send_to_mattermost(metrics, html_report)

                if success:
                    if attempt > 0:
                        self.logger.info(f"Mattermost发送成功（重试 {attempt} 次后）")
                    else:
                        self.logger.info("Mattermost发送成功")
                    return True

            except Exception as e:
                last_error = e
                self.logger.warning(f"Mattermost发送尝试 {attempt + 1} 失败: {e}")

        # 所有重试都失败
        self.logger.error(
            f"Mattermost发送最终失败，已重试 {self.max_retries} 次: {last_error}")
        return False

    def _send_to_mattermost(self, metrics: 'PerformanceMetrics',
                            html_report: str) -> bool:
        """发送到Mattermost

        Args:
            metrics: 性能指标数据
            html_report: HTML报告

        Returns:
            bool: 发送是否成功
        """
        try:
            driver = self._get_driver()
            # 格式化消息
            message = NotificationFormatter.format_mattermost_message(metrics)
            file_data = io.BytesIO(html_report.encode("utf-8"))
            # 生成文件名
            filename = NotificationFormatter.generate_filename(metrics, "html")

            # 上传文件
            file_info = driver.files.upload_file(
                channel_id=self.channel_id,
                files={'files': (filename, file_data, 'text/html')}
            )

            if not file_info or 'file_infos' not in file_info:
                raise NotificationError("文件上传失败")

            file_id = file_info['file_infos'][0]['id']

            # 发送消息并附加文件
            post_data = {
                'channel_id': self.channel_id,
                'message': message,
                'file_ids': [file_id]
            }

            result = driver.posts.create_post(post_data)

            if result and 'id' in result:
                self.logger.debug(f"Mattermost消息发送成功，消息ID: {result['id']}")
                return True
            else:
                raise NotificationError("消息发送失败")

        except Exception as e:
            self.logger.error(f"Mattermost发送失败: {e}")
            return False

    def validate_config(self) -> bool:
        """验证Mattermost配置

        Returns:
            bool: 配置是否有效
        """
        try:
            # 检查必需的配置
            if not self.server_url:
                self.logger.error("Mattermost服务器URL未配置")
                return False

            if not self.token:
                self.logger.error("Mattermost访问令牌未配置")
                return False

            if not self.channel_id:
                self.logger.error("Mattermost频道ID未配置")
                return False

            # 尝试连接和认证
            try:
                driver = self._get_driver()

                # 验证频道是否存在
                channel_info = driver.channels.get_channel(self.channel_id)
                if not channel_info:
                    self.logger.error(f"频道不存在或无权访问: {self.channel_id}")
                    return False

                self.logger.info(
                    f"Mattermost配置验证成功，频道: {channel_info.get('display_name', self.channel_id)}")
                return True

            except Exception as e:
                self.logger.error(f"Mattermost连接验证失败: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Mattermost配置验证异常: {e}")
            return False

    def test_connection(self) -> dict:
        """测试Mattermost连接

        Returns:
            dict: 测试结果信息
        """
        try:
            driver = self._get_driver()

            # 获取用户信息
            user_info = driver.users.get_user('me')

            # 获取频道信息
            channel_info = driver.channels.get_channel(self.channel_id)

            # 获取服务器信息
            server_info = driver.system.ping()

            return {
                'success': True,
                'server_url': self.server_url,
                'user': {
                    'id': user_info.get('id'),
                    'username': user_info.get('username'),
                    'email': user_info.get('email')
                },
                'channel': {
                    'id': channel_info.get('id'),
                    'name': channel_info.get('name'),
                    'display_name': channel_info.get('display_name'),
                    'type': channel_info.get('type')
                },
                'server_status': server_info
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'server_url': self.server_url
            }

    def send_test_message(self) -> bool:
        """发送测试消息

        Returns:
            bool: 发送是否成功
        """
        try:
            driver = self._get_driver()

            test_message = """#### 🧪 性能监控测试消息

这是一条来自Web性能监控工具的测试消息。

**测试时间**: {timestamp}
**配置状态**: ✅ 正常
**通知功能**: ✅ 工作正常

如果您收到此消息，说明Mattermost通知配置正确。
""".format(timestamp=time.strftime('%Y-%m-%d %H:%M:%S'))

            post_data = {
                'channel_id': self.channel_id,
                'message': test_message
            }

            result = driver.posts.create_post(post_data)

            if result and 'id' in result:
                self.logger.info("Mattermost测试消息发送成功")
                return True
            else:
                self.logger.error("Mattermost测试消息发送失败")
                return False

        except Exception as e:
            self.logger.error(f"Mattermost测试消息发送异常: {e}")
            return False

    def disconnect(self) -> None:
        """断开Mattermost连接"""
        try:
            if self._driver and self._authenticated:
                self._driver.logout()
                self._authenticated = False
                self.logger.debug("Mattermost连接已断开")
        except Exception as e:
            self.logger.warning(f"断开Mattermost连接时出错: {e}")

    def __str__(self) -> str:
        """字符串表示"""
        return f"MattermostNotifier(server='{self.server_url}', channel='{self.channel_id}')"

    def __del__(self):
        """析构函数，确保连接被正确关闭"""
        try:
            self.disconnect()
        except:
            pass
