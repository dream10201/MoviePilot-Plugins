# --- START OF FILE qbittorrenthelper/utils.py ---

from typing import List, Optional, Tuple, Any

from app.helper.downloader import DownloaderHelper


class Utils:
    """
    辅助类，提供一些通用的工具方法。
    """

    @staticmethod
    def format_size(size: float, precision: int = 2) -> str:
        """
        字节数转换
        """
        if not isinstance(size, (int, float)) or size < 0:
            return "N/A"
        suffixes = ["B", "KB", "MB", "GB", "TB"]
        suffix_index = 0
        while size >= 1024 and suffix_index < 4:
            suffix_index += 1
            size /= 1024.0
        return f"{size:.{precision}f} {suffixes[suffix_index]}"

    @staticmethod
    def to_emoji_number(n: int) -> str:
        """
        将一个整数转换为对应的带圈数字 Emoji 字符串 (例如 ①, ②, ⑩)。
        """
        if not isinstance(n, int):
            return "❓"
        if n == 10:
            return "⑩"
        emoji_map = {
            '0': '⓪', '1': '①', '2': '②', '3': '③', '4': '④',
            '5': '⑤', '6': '⑥', '7': '⑦', '8': '⑧', '9': '⑨'
        }
        return "".join(emoji_map.get(digit, digit) for digit in str(n))

    @staticmethod
    def get_downloader_instance(downloader_name: str, type_filter: str = "qbittorrent") \
            -> Tuple[Optional[Any], Optional[str]]:
        """
        获取指定下载器的实例
        """
        if not downloader_name:
            return None, "下载器名称不能为空。"
        services = DownloaderHelper().get_services(type_filter=type_filter)
        service_info = services.get(downloader_name)
        if not service_info or not hasattr(service_info, 'instance'):
            return None, f"下载器 `{downloader_name}` 不存在、未启用或未正确初始化。"
        return service_info.instance, None

    @staticmethod
    def get_running_qb_downloader_name(type_filter: str = "qbittorrent") -> List[str]:
        """
        获取所有正在运行的指定类型的下载器名称
        """
        running_services = DownloaderHelper().get_services(type_filter=type_filter)
        return [name for name, service in running_services.items() if hasattr(service, 'instance')]

    @staticmethod
    def get_all_qb_downloader_name(include_disabled: bool = True, conf_type: str = "qbittorrent") -> List[str]:
        """
        获取所有已配置的指定类型的下载器名称
        """
        all_configs = DownloaderHelper().get_configs(include_disabled=include_disabled)
        names = {name for name, conf in all_configs.items() if hasattr(conf, 'type') and conf.type == conf_type}
        return sorted(list(names))
