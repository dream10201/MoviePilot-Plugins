# --- START OF FILE qbittorrenthelper/__init__.py ---
from copy import deepcopy
from dataclasses import dataclass, asdict
from time import sleep
from typing import Any, List, Dict, Tuple, Optional

from app.core.event import eventmanager, Event
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType, MessageChannel

from .framework.callbacks import decode_action, Action
from .framework.manager import BaseSessionManager
from .framework.schemas import TSession
from .schemas import Session
from .handler import ActionHandler
from .views import ViewRenderer


# 实例化一个该插件专用的 SessionManager
session_manager = BaseSessionManager(session_class=Session)


@dataclass
class Config:
    enabled: bool = True
    session_timeout: int = 10
    session_timeout_minutes: int = 10
    allowed_channels: Optional[List[MessageChannel]] = None
    allowed_sources: Optional[List[str]] = None
    allowed_users: Optional[List[int]] = None


class QBittorrentHelper(_PluginBase):
    plugin_name = "qBittorrent助手"
    plugin_desc = "支持在Telegram、Slack等平台中，使用命令(按钮)查看并控制 qbittorrent 下载器。"
    plugin_icon = "Synomail_A.png"
    plugin_version = "1.0"
    plugin_author = "Aqr-K"
    author_url = "https://github.com/Aqr-K"
    plugin_config_prefix = "qbittorrenthelper_"
    plugin_order = 29
    auth_level = 1

    def __init__(self, config: dict = None):
        """
        初始化 qBittorrentHelper 插件。
        """
        super().__init__()
        self.config = Config(**(config or {}))

        # 实例化处理器和渲染器
        self.action_handler = ActionHandler()
        self.view_renderer = ViewRenderer()
        # 初始化时设置超时
        session_manager.set_timeout(self.config.session_timeout)

    def init_plugin(self, config: dict = None):
        """
        初始化插件配置。
        """
        if config:
            self.config = Config(**(config or {}))
            session_manager.set_timeout(self.config.session_timeout_minutes)
            self.update_config(asdict(self.config))
        logger.info(f"插件 {self.plugin_name} 已加载，会话超时设置为 {self.config.session_timeout_minutes} 分钟。")

    def get_state(self):
        return self.config.enabled

    def get_service(self) -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        default_data = asdict(Config())
        UserItems = []
        MessageChannelItems = [{'title': channel.value, 'value': channel.name} for channel in MessageChannel]
        # 返回您原有的表单结构
        return [], default_data

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        pass

    def get_command(self) -> List[Dict[str, Any]]:
        return [{
            "cmd": f"/{self.__class__.__name__.lower()}_start",
            "event": EventType.PluginAction,
            "desc": "启动下载器选择菜单",
            "category": "下载器管理",
            "data": {
                "action": f"{self.__class__.__name__.lower()}_start"
            }
        }]

    @eventmanager.register(EventType.PluginAction)
    def command_action(self, event: Event):
        """
        处理初始化的 start 命令。
        """
        event_data = event.event_data
        if not event_data or event_data.get("action") != f"{self._plugin_id.lower()}_start":
            return
        if not self.config.enabled:
            logger.warning(f"插件 {self.plugin_name} 已禁用，无法处理命令。")
            return

        try:
            session = session_manager.get_or_create(event_data, plugin_id=self._plugin_id)
            if not self._check_permissions(session):
                return
            # 直接进入开始视图
            session.go_to("start")
            self._render_and_send(session)
        except Exception as e:
            logger.error(f"处理 start 命令失败: {e}", exc_info=True)

    @eventmanager.register(EventType.MessageAction)
    def message_action(self, event: Event):
        """
        处理按钮点击回调，这是重构的核心。
        """
        event_data = event.event_data
        callback_text = event_data.get("text", "")

        # 1. 解码 Action
        session_id, action = decode_action(callback_text=callback_text)
        if not session_id or not action:
            # 如果解码失败或不属于本插件，则忽略
            return

        # 2. 获取会话
        session = session_manager.get(session_id)
        if not session:
            # Todo: 需要优化
            context = {
                "channel": event_data.get("channel"),
                "source": event_data.get("source"),
                "userid": event_data.get("userid") or event_data.get("user"),
                "original_message_id": event_data.get("original_message_id"),
                "original_chat_id": event_data.get("original_chat_id")
            }
            self.post_message(**context, title="⚠️ 会话已过期",
                              text=f"操作已超时。\n请重新发起 `/{self._plugin_id.lower()}_start` 命令。")
            return

        # 3. 更新会话上下文并检查权限
        session.update_message_context(event_data)
        if not self._check_permissions(session):
            return

        # 4. 委托给 ActionHandler 处理业务逻辑
        immediate_messages = self.action_handler.process(session, action)
        if immediate_messages:
            for msg in immediate_messages:
                self.__send_message(session, text=msg.get('text'), title="错误")
                return

        # 5. 渲染新视图并发送
        self._render_and_send(session)

    @eventmanager.register(EventType.CommandExcute)
    def not_signup_command_action(self, event: Event):
        """
        处理非注册命令的执行。
        """
        event_data = event.event_data
        cmd = event_data.get("cmd", "")
        if not event_data or not cmd.startswith(f"/{self._plugin_id.lower()}"):
            return

        parts = cmd.split()
        # 如果没有足够的部分，直接返回，这应该是初始化
        if len(parts) < 2:
            return
        if not parts or parts[0] != "/" + self._plugin_id.lower():
            return

        try:
            # 获取会话 ID 和 Action
            session = session_manager.get_or_create(event_data, plugin_id=self._plugin_id)
            action = Action(command=parts[1], value=parts[2] if len(parts) > 2 else None)
            if not self._check_permissions(session):
                return
            session.business.current_view = action.command
            immediate_messages = self.action_handler.process(session, action)
            if immediate_messages:
                for msg in immediate_messages:
                    self.__send_message(session, text=msg.get('text'), title="错误")
                    return

            # 如果有原消息，则删除后，发送一条新的消息，让用户重新进入回调消息视窗
            if session.message.original_message_id and session.message.original_chat_id:
                self.__delete_message(session)
                # 移除 session 中的相关id
                session.message.original_message_id = None
                session.message.original_chat_id = None

            # 渲染并发送新的视图
            self._render_and_send(session)

        except Exception as e:
            logger.error(f"处理非注册命令失败: {e}", exc_info=True)

    @property
    def _plugin_id(self) -> str:
        """
        获取插件的唯一标识符。
        """
        return self.__class__.__name__

    def _check_permissions(self, session: TSession) -> bool:
        """
        检查用户和来源是否有权限使用此插件。
        """
        message = session.message
        if self.config.allowed_users and message.userid not in self.config.allowed_users:
            self.__send_message(session, title="🚫 权限不足", text="您无权使用此功能。")
            return False
        if self.config.allowed_channels and message.channel not in self.config.allowed_channels:
            self.__send_message(session, title="🚫 类型受限", text="此消息渠道无权使用该功能。")
            return False
        if self.config.allowed_sources and message.source not in self.config.allowed_sources:
            self.__send_message(session, title="🚫 来源受限", text="此消息来源无权使用该功能。")
            return False
        return True

    def _render_and_send(self, session: TSession):
        """
        根据 Session 的当前状态，渲染视图并发送/编辑消息。
        """
        # 1. 委托给 ViewRenderer 生成界面数据
        render_data = self.view_renderer.render(session)

        # 2. 发送或编辑消息
        self.__send_message(session, render_data=render_data)

        # 3. 处理会话结束逻辑
        if session.business.current_view == 'close':
            # 深复制session留作删除消息使用
            copy_session = deepcopy(session)
            session_manager.end(session.session_id)
            # 等待一段时间让用户看到“已关闭”的消息
            sleep(10)
            self.__delete_message(copy_session)

    @staticmethod
    def __get_message_context(session: TSession) -> dict:
        """
        从会话中提取用于发送消息的上下文。
        """
        return asdict(session.message)

    def __send_message(self, session: TSession, render_data: Optional[dict] = None, **kwargs):
        """
        统一的消息发送接口。
        """
        context = self.__get_message_context(session)
        if render_data:
            context.update(render_data)
        context.update(kwargs)
        # 将 user key改名成 userid，规避传入值只是user
        userid = context.get('user')
        if userid:
            context['userid'] = userid
            # 删除多余的 user 键
            del context['user']
        self.post_message(**context)

    def __delete_message(self, session: Session):
        """
        删除会话中的原始消息。
        """
        # Todo: 实现删除消息的逻辑
        pass
