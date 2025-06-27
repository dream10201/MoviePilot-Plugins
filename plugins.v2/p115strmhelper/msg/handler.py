# --- START OF FILE qbittorrenthelper/handler.py ---

from typing import List, Dict

from app.log import logger
from .framework.registry import command_registry, view_registry
from .framework.callbacks import Action
from .framework.handler import BaseActionHandler
from .schemas import Session
from .utils import Utils

command_registry.clear()


class ActionHandler(BaseActionHandler):
    """
    动作处理器。
    处理用户的动作请求，并执行相应的业务逻辑。
    """

    @command_registry.command(name='go_to', code='gt')
    def handle_go_to(self, session: Session, action: Action):
        """
        处理跳转到指定视图的操作
        :param session: 会话对象
        :param action: 回调动作
        :return:
        """
        if action.view:
            if view_registry.get_by_name(action.view):
                session.go_to(action.view)
            else:
                raise ValueError(f"未知视图 '{action.view}'，跳转失败。")

    @command_registry.command(name='go_back', code='gb')
    def handle_go_back(self, session: Session, action: Action):
        """
        处理返回操作
        :param session: 会话对象
        :param action: 回调动作
        """
        if action.view:
            if view_registry.get_by_name(action.view):
                session.go_back(action.view)
            else:
                logger.warning(f"未知视图 '{action.view}'，尝试返回失败。")
                raise ValueError(f"未知视图 '{action.view}'，返回失败。")

    @command_registry.command(name='page_next', code='pn')
    def handle_page_next(self, session: Session, action: Action):
        """
        处理下一页操作
        :param session: 会话对象
        :param action: 回调动作
        """
        session.page_next()

    @command_registry.command(name='page_prev', code='pp')
    def handle_page_prev(self, session: Session, action: Action):
        """
        处理上一页操作
        :param session: 会话对象
        :param action: 回调动作
        """
        session.page_prev()

    @command_registry.command(name='select_downloader', code='sd')
    def handle_select_downloader(self, session: Session, action: Action) -> List[Dict] | None:
        try:
            if action.value is None:
                raise ValueError("value 不能为空。")
            item_index = int(action.value)
            all_names = Utils.get_all_qb_downloader_name()
            if 0 <= item_index < len(all_names):
                session.business.downloader_name = all_names[item_index]
                session.go_to('downloader_menu')
            else:
                raise IndexError("索引超出范围。")
        except (ValueError, IndexError, TypeError) as e:
            logger.error(f"处理 select_downloader 失败: value={action.value}, error={e}")
            session.go_to('start')
            return [{'type': 'error_message', 'text': '选择下载器时发生错误，请重试。'}]
        return None

    @command_registry.command(name='close', code='cl')
    def handle_closed(self, session: Session, action: Action):
        session.business.current_view = 'close'
