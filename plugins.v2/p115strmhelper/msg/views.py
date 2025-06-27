# --- START OF FILE qbittorrenthelper/views.py ---

import math
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

from .framework.registry import view_registry
from .framework.callbacks import Action
from .framework.views import BaseViewRenderer
from .schemas import Session
from .utils import Utils
from ...schemas import ChannelCapabilityManager

view_registry.clear()


class ViewRenderer(BaseViewRenderer):
    """
    视图渲染器
    """

    @staticmethod
    def now_date() -> str:
        """
        返回当前时间的字符串表示。
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_navigation_buttons(self, session: Session,
                               go_back: Optional[str] = None, refresh: bool = False, close: bool = False) -> list:
        """
        获取导航按钮，包含返回、刷新和关闭按钮。
        """
        nav_buttons = []
        if go_back:
            nav_buttons.append(self._build_common_go_back_button(session, view=go_back))
        if refresh:
            nav_buttons.append(self._build_common_refresh_button(session))
        if close:
            nav_buttons.append(self._build_common_close_button(session))
        return nav_buttons

    @view_registry.view(name='start', code='st')
    def render_start(self, session: Session) -> Dict:
        """
        渲染开始视图，显示欢迎信息和下载器列表。
        """
        all_names = Utils.get_all_qb_downloader_name()
        title = "🔧 下载器列表"
        buttons, text_lines = [], ["请选择要操作的下载器：\n"]

        if not all_names:
            text = "当前没有可用的下载器。"
            buttons.append(self._build_common_close_button(session))
            return {"title": title, "text": text, "buttons": buttons}

        running_names = Utils.get_running_qb_downloader_name()

        # 获取频道能力
        supports_buttons = ChannelCapabilityManager.supports_buttons(session.message.channel)

        max_buttons_per_row = ChannelCapabilityManager.get_max_buttons_per_row(session.message.channel)
        max_total_button_rows = ChannelCapabilityManager.get_max_button_rows(session.message.channel)

        # --- 修改开始 ---

        # 决定本页要显示的下载器按钮行数
        if max_total_button_rows >= 4:
            downloader_button_rows = 2
        else:
            downloader_button_rows = 1

        # 计算正确的 page_size
        # 每页的项目数 = 期望的按钮行数 * 每行的按钮数
        page_size = downloader_button_rows * max_buttons_per_row

        # 计算总页数
        session.business.total_pages = math.ceil(len(all_names) / page_size)

        # 如果没有设置页码，则默认为第一页
        if session.business.page >= session.business.total_pages > 0:
            session.business.page = session.business.total_pages - 1

        start_index = session.business.page * page_size

        # 页面内容
        paged_items = all_names[start_index: start_index + page_size]

        button_row = []
        for i, name in enumerate(paged_items):
            original_index = all_names.index(name)
            icon = "🟢" if name in running_names else "🔴"
            text_lines.append(f"{Utils.to_emoji_number(start_index + i + 1)}. {icon} {name}")

            # 支持按钮时，生成按钮
            if supports_buttons:
                button_row.append(self._build_button(session, Utils.to_emoji_number(start_index + i + 1),
                                                     Action(command='select_downloader', value=original_index)))

                # 如果当前行已满，添加到按钮列表
                if len(button_row) == max_buttons_per_row:
                    buttons.append(button_row)
                    button_row = []

        if button_row:
            buttons.append(button_row)

        # 当前页码
        text_lines.append(f"\n页码: {session.business.page + 1} / {session.business.total_pages}")
        text_lines.append(f"\n数据刷新时间：{self.now_date()}")
        text = "\n".join(text_lines)

        # 添加分页行
        page_nav = []
        if session.business.page > 0:
            page_nav.append(self._build_button(session, "◀️ 上一页", Action(command='page_prev')))
        if session.business.page < session.business.total_pages - 1:
            page_nav.append(self._build_button(session, "▶️ 下一页", Action(command='page_next')))
        if page_nav:
            buttons.append(page_nav)

        # 添加关闭行
        buttons.append([self._build_common_close_button(session)])

        return {"title": title, "text": text, "buttons": buttons}

    @view_registry.view(name='downloader_menu', code='dm')
    def render_downloader_menu(self, session: Session) -> Dict:
        """
        渲染下载器菜单视图，显示当前选择的下载器状态和操作选项。
        """
        downloader_name = session.business.downloader_name
        title, buttons, text = f"菜单 - {downloader_name or '未知'}", [], ""
        if not downloader_name:
            text = "错误：未选择任何下载器。"
        else:
            instance, error_text = Utils.get_downloader_instance(downloader_name)
            if not instance:
                text = error_text or f"无法获取 `{downloader_name}` 的实例。"
            else:
                info = instance.downloader_info() if hasattr(instance, 'downloader_info') else None
                if info and isinstance(info, dict):
                    text = (
                        f"**{downloader_name}** 状态:\n"
                        f"⬇️ 下载: {Utils.format_size(info.get('download_speed'))}/s\n"
                        f"⬆️ 上传: {Utils.format_size(info.get('upload_speed'))}/s\n"
                        f"📥 已下载: {Utils.format_size(info.get('download_size'))}\n"
                        f"📤 已上传: {Utils.format_size(info.get('upload_size'))}")
                else:
                    text = f"已选择下载器：**{downloader_name}**\n无法获取详细信息。"
                menu_buttons = [self._build_button(session, "📈 任务", Action(command='go_to', view='tasks')),
                                self._build_button(session, "⚙️ 设置", Action(command='go_to', view='settings')),
                                self._build_button(session, "ℹ️ 版本", Action(command='go_to', view='version'))]
                buttons.append(menu_buttons)
        buttons.append(self.get_navigation_buttons(session, go_back='start', refresh=True, close=True))
        return {"title": title, "text": text, "buttons": buttons}

    @view_registry.view(name='close', code='cl')
    def render_closed(self, session: Session) -> Dict:
        return {"title": "✅ 操作完成", "text": "会话已关闭。", "buttons": []}

    @view_registry.view(name='tasks', code='ts')
    def render_tasks(self, session: Session) -> Dict:
        """
        渲染任务视图，显示下载器的任务列表。
        """
        downloader_name = session.business.downloader_name
        title, buttons, text = f"任务列表 - {downloader_name or '未知'}", [], ""
        if not downloader_name:
            text = "错误：未选择任何下载器。"
        else:
            instance, error_text = Utils.get_downloader_instance(downloader_name)
            if not instance:
                text = error_text or f"无法获取 `{downloader_name}` 的实例。"
            else:
                text = "功能正在开发中，敬请期待！"
        buttons.append(self.get_navigation_buttons(session, go_back='downloader_menu', refresh=True, close=True))
        return {"title": title, "text": text, "buttons": buttons}

    @view_registry.view(name='settings', code='stg')
    def render_settings(self, session: Session) -> Dict:
        """
        渲染设置视图，显示下载器的设置选项。
        """
        downloader_name = session.business.downloader_name
        title, buttons, text = f"设置 - {downloader_name or '未知'}", [], ""
        if not downloader_name:
            text = "错误：未选择任何下载器。"
        else:
            instance, error_text = Utils.get_downloader_instance(downloader_name)
            if not instance:
                text = error_text or f"无法获取 `{downloader_name}` 的实例。"
            else:
                text = "功能正在开发中，敬请期待！"
        buttons.append(self.get_navigation_buttons(session, go_back='downloader_menu', refresh=True, close=True))
        return {"title": title, "text": text, "buttons": buttons}

    @view_registry.view(name='version', code='ver')
    def render_version(self, session: Session) -> Dict:
        """
        渲染版本视图，显示下载器的版本信息。
        """
        downloader_name = session.business.downloader_name
        title, buttons, text = f"版本信息 - {downloader_name or '未知'}", [], ""
        if not downloader_name:
            text = "错误：未选择任何下载器。"
        else:
            instance, error_text = Utils.get_downloader_instance(downloader_name)
            if not instance:
                text = error_text or f"无法获取取 `{downloader_name}` 的实例。"
            else:
                # 检查是否有 qbc 实例
                if hasattr(instance, "qbc"):
                    app_version = instance.qbc.app_version()
                    web_api_version = instance.qbc.app_web_api_version()
                    text = (f"App 版本: {app_version} \n"
                            f"Web Api 版本: {web_api_version}")

                    text += f"\n\n数据刷新时间：{self.now_date()}"
                else:
                    text = f"**{downloader_name}** 版本信息不可用。"

        buttons.append(self.get_navigation_buttons(session, go_back='downloader_menu', refresh=False, close=True))
        return {"title": title, "text": text, "buttons": buttons}
