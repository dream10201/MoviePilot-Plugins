# --- START OF FILE qbittorrenthelper/schemas.py ---

from dataclasses import dataclass, field
from typing import Optional

from .framework.schemas import BaseSession, BaseBusiness


@dataclass
class Business(BaseBusiness):
    """
    本插件专属的业务模型。
    """
    downloader_name: Optional[str] = None


@dataclass
class Session(BaseSession):
    """
    组装成本插件专属的 Session。
    """
    business: Business = field(default_factory=Business)

    def go_back(self, view: str):
        """
        回到指定的视图状态（插件专属的健壮实现）。
        """
        history_business = self.history.get(view)

        # 如果成功获取到历史状态，则直接恢复
        if history_business:
            self.business = history_business
            # 不直接弹出，规避ide中可能的误报
            self.history.pop(view, None)
            if view == "start":
                self.history.clear()
        # 如果没有获取到（即历史不存在），则安全地回退到顶层 start 视图
        else:
            self.go_to("start")
