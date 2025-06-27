# --- START OF FILE qbittorrenthelper/framework/schemas.py ---

import time
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TypeVar

from app.schemas.types import MessageChannel


@dataclass
class BaseMessage:
    """
    消息模型的通用基类。
    """
    # 消息类型
    channel: Optional[MessageChannel] = None
    # 来源名
    source: Optional[str] = None
    # 用户 ID
    userid: Optional[int] = None
    # 用户名
    username: Optional[str] = None
    # 原始消息 ID
    original_message_id: Optional[int] = None
    # 原始聊天 ID
    original_chat_id: Optional[int] = None


@dataclass
class BaseBusiness:
    """
    业务模型的通用基类。
    """
    # 当前视图名称，用于标识当前业务逻辑的状态
    current_view: str = "start"
    # 当前页码
    page: int = 0
    # 总页数
    total_pages: int = 0
    # 附加数据，可以存储任何额外的信息
    extra_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BaseSession:
    """
    Session 模型的通用基类。
    """
    # 会话 ID，用于唯一标识每个用户在每个聊天中的会话
    session_id: str
    # 插件 ID，用于标识当前会话所属的插件
    plugin_id: str

    # 会话的最后活动时间戳
    last_active: float = field(default_factory=time.time, init=False)

    # 业务逻辑处理对象，包含当前视图、页码等信息
    business: BaseBusiness = field(default_factory=BaseBusiness)
    # 消息上下文，包含频道、来源、用户等信息
    message: BaseMessage = field(default_factory=BaseMessage)

    # 历史记录，用于保存视图切换前的状态
    history: Dict[str, message] = field(default_factory=dict)

    def update_message_context(self, event_data: Dict[str, Any]):
        """
        更新消息上下文信息。
        :param event_data: 字典，包含事件数据，必须包含 'channel', 'source', 'userid' 或 'user' 字段。
        """
        self.message.channel = event_data.get("channel")
        self.message.source = event_data.get("source")
        self.message.userid = event_data.get("userid") or event_data.get("user")
        self.message.username = event_data.get("username") or event_data.get("user")
        self.message.original_message_id = event_data.get("original_message_id")
        self.message.original_chat_id = event_data.get("original_chat_id")
        self.message.original_message_text = event_data.get("text")
        self.update_activity()

    def update_activity(self):
        """
        更新会话的最后活动时间戳。
        """
        self.last_active = time.time()

    def go_to(self, view: str):
        """
        切换到指定的视图，并保存当前状态到历史记录。
        :param view: 要切换到的视图名称。
        """
        self.history[self.business.current_view] = deepcopy(self.business)
        self.business.current_view = view
        self.business.page = 0
        self.business.total_pages = 0

    def go_back(self, view: str):
        """
        返回到历史记录
        :param view: 要返回的视图名称。
        """
        previous_state = self.history.get(view)
        if previous_state:
            # 恢复 business 对象的状态
            for key, value in previous_state.items():
                if hasattr(self.business, key):
                    setattr(self.business, key, value)

        else:
            # 如果历史记录中没有，则回到起始页
            self.go_to("start")

    def page_next(self):
        """
        翻到下一页。
        """
        if self.business.total_pages > 0 and self.business.page < self.business.total_pages - 1:
            self.business.page += 1

    def page_prev(self):
        """
        翻到上一页。
        """
        if self.business.page > 0:
            self.business.page -= 1


TSession = TypeVar('TSession', bound=BaseSession)
