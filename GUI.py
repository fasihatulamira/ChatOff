"""Backward-compatible entry point: from GUI import OfflineChatbot"""
from gui.theme import apply_theme
from gui.app import OfflineChatbot
from gui.admin import AdminFrame
from gui.chat import ChatFrame
from gui.home import HomeFrame, InfoFrame

apply_theme()

__all__ = [
    "OfflineChatbot",
    "AdminFrame",
    "ChatFrame",
    "HomeFrame",
    "InfoFrame",
]
