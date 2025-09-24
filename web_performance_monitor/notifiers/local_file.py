"""
本地文件通知器

将性能报告保存到本地文件系统
"""

import os
import logging
from typing import TYPE_CHECKING
from ..exceptions import NotificationError
from ..formatters import NotificationFormatter
from .base import BaseNotifier

if TYPE_CHECKING:
    from ..models import PerformanceMetrics


class LocalFileNotifier(BaseNotifier):
    """本地文件通知器
    
    将HTML报告保存到配置目录（默认/tmp）
    """
    
    def __init__(self, output_dir: str = "/tmp"):
        """初始化本地文件通知器
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        
        # 确保输出目录存在
        self._ensure_output_dir()
    
    def _ensure_output_dir(self) -> None:
        """确保输出目录存在"""
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir, exist_ok=True)
                self.logger.info(f"创建输出目录: {self.output_dir}")
            
            # 检查目录是否可写
            if not os.access(self.output_dir, os.W_OK):
                raise NotificationError(f"输出目录不可写: {self.output_dir}")
                
        except OSError as e:
            raise NotificationError(f"创建输出目录失败: {self.output_dir} - {e}")
    
    def send_notification(self, metrics: 'PerformanceMetrics', html_report: str) -> bool:
        """保存HTML报告到配置目录（默认/tmp）
        
        - 生成包含时间戳和接口名的唯一文件名避免冲突
        - 在日志中打印文件路径和请求摘要信息
        - 存储失败时记录错误日志但不影响应用运行
        
        Args:
            metrics: 性能指标数据
            html_report: HTML格式的性能报告
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 检查HTML报告是否有效
            if html_report is None:
                self.logger.warning("HTML报告为None，跳过本地文件通知")
                return False
                
            # 生成唯一文件名
            filename = NotificationFormatter.generate_filename(metrics, "html")
            file_path = os.path.join(self.output_dir, filename)
            
            # 写入HTML报告
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_report)
            
            # 记录成功信息
            summary_message = NotificationFormatter.format_log_message(metrics, file_path)
            self.logger.info(summary_message)
            
            # 记录详细的请求摘要信息
            self.logger.info(
                f"性能报告详情: "
                f"URL={metrics.request_url} "
                f"参数={len(metrics.request_params)}个 "
                f"方法={metrics.request_method} "
                f"状态码={metrics.status_code} "
                f"文件大小={len(html_report)}字节"
            )
            
            return True
            
        except OSError as e:
            error_msg = f"保存性能报告失败: {e}"
            self.logger.error(error_msg)
            return False
            
        except Exception as e:
            error_msg = f"本地文件通知器异常: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False
    
    def validate_config(self) -> bool:
        """验证本地文件通知器配置
        
        Returns:
            bool: 配置是否有效
        """
        try:
            # 检查输出目录是否存在且可写
            if not os.path.exists(self.output_dir):
                try:
                    os.makedirs(self.output_dir, exist_ok=True)
                except OSError:
                    self.logger.error(f"无法创建输出目录: {self.output_dir}")
                    return False
            
            if not os.path.isdir(self.output_dir):
                self.logger.error(f"输出路径不是目录: {self.output_dir}")
                return False
            
            if not os.access(self.output_dir, os.W_OK):
                self.logger.error(f"输出目录不可写: {self.output_dir}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"验证本地文件配置失败: {e}")
            return False
    
    def get_output_dir(self) -> str:
        """获取输出目录路径
        
        Returns:
            str: 输出目录路径
        """
        return self.output_dir
    
    def set_output_dir(self, output_dir: str) -> None:
        """设置输出目录路径
        
        Args:
            output_dir: 新的输出目录路径
            
        Raises:
            NotificationError: 目录无效时抛出
        """
        self.output_dir = output_dir
        self._ensure_output_dir()
        self.logger.info(f"输出目录已更新: {output_dir}")
    
    def cleanup_old_files(self, days: int = 30) -> int:
        """清理旧的性能报告文件
        
        Args:
            days: 保留天数，超过此天数的文件将被删除
            
        Returns:
            int: 删除的文件数量
        """
        try:
            import time
            from datetime import datetime, timedelta
            
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            deleted_count = 0
            
            if not os.path.exists(self.output_dir):
                return 0
            
            for filename in os.listdir(self.output_dir):
                if not filename.startswith('performance_alert_'):
                    continue
                
                file_path = os.path.join(self.output_dir, filename)
                
                try:
                    # 检查文件修改时间
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                        self.logger.debug(f"删除旧文件: {filename}")
                        
                except OSError as e:
                    self.logger.warning(f"删除文件失败: {filename} - {e}")
            
            if deleted_count > 0:
                self.logger.info(f"清理了 {deleted_count} 个超过 {days} 天的旧文件")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"清理旧文件失败: {e}")
            return 0
    
    def get_recent_files(self, hours: int = 24) -> list:
        """获取最近的性能报告文件列表
        
        Args:
            hours: 时间范围（小时）
            
        Returns:
            list: 文件信息列表，包含文件名、路径、修改时间等
        """
        try:
            import time
            from datetime import datetime
            
            if not os.path.exists(self.output_dir):
                return []
            
            cutoff_time = time.time() - (hours * 60 * 60)
            recent_files = []
            
            for filename in os.listdir(self.output_dir):
                if not filename.startswith('performance_alert_'):
                    continue
                
                file_path = os.path.join(self.output_dir, filename)
                
                try:
                    stat = os.stat(file_path)
                    if stat.st_mtime >= cutoff_time:
                        recent_files.append({
                            'filename': filename,
                            'path': file_path,
                            'size': stat.st_size,
                            'modified_time': datetime.fromtimestamp(stat.st_mtime),
                            'age_hours': (time.time() - stat.st_mtime) / 3600
                        })
                        
                except OSError as e:
                    self.logger.warning(f"获取文件信息失败: {filename} - {e}")
            
            # 按修改时间排序（最新的在前）
            recent_files.sort(key=lambda x: x['modified_time'], reverse=True)
            
            return recent_files
            
        except Exception as e:
            self.logger.error(f"获取最近文件失败: {e}")
            return []
    
    def get_disk_usage(self) -> dict:
        """获取输出目录的磁盘使用情况
        
        Returns:
            dict: 磁盘使用信息
        """
        try:
            if not os.path.exists(self.output_dir):
                return {'error': '输出目录不存在'}
            
            # 获取目录大小
            total_size = 0
            file_count = 0
            
            for filename in os.listdir(self.output_dir):
                if filename.startswith('performance_alert_'):
                    file_path = os.path.join(self.output_dir, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                    except OSError:
                        pass
            
            # 获取磁盘空间信息
            statvfs = os.statvfs(self.output_dir)
            free_space = statvfs.f_frsize * statvfs.f_bavail
            total_space = statvfs.f_frsize * statvfs.f_blocks
            
            return {
                'output_dir': self.output_dir,
                'report_files_count': file_count,
                'report_files_size': total_size,
                'report_files_size_mb': total_size / (1024 * 1024),
                'disk_free_space': free_space,
                'disk_total_space': total_space,
                'disk_usage_percent': ((total_space - free_space) / total_space) * 100
            }
            
        except Exception as e:
            self.logger.error(f"获取磁盘使用情况失败: {e}")
            return {'error': str(e)}
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"LocalFileNotifier(output_dir='{self.output_dir}')"