"""Main application window controller."""
import threading

import customtkinter as ctk

from auth import is_admin_user
from chatbot import warm_ollama_models
from gui.admin import AdminFrame
from gui.home import HomeFrame, InfoFrame
from gui.chat import ChatFrame

class OfflineChatbot(ctk.CTk):
    def __init__(self, user_name: str = "User", username: str = ""):
        super().__init__()
        self.user_name, self.username = user_name, username or user_name.lower().replace(" ", "")
        self.is_admin = is_admin_user(self.username)
        self.admin_preview_mode = False
        self.title("ChatOff AI 🤖")
        self.logged_out = False

        win_w, win_h = 1100, 800
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{win_w}x{win_h}+{(sw-win_w)//2}+{(sh-win_h)//2}")
        self.minsize(900, 700)
        self.after(10, lambda: self.state("zoomed"))  # Maximize after window draws
        threading.Thread(target=warm_ollama_models, daemon=True).start()

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        if self.is_admin:
            frame = AdminFrame(self.container, self)
            self.frames[AdminFrame] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            self.show_frame(AdminFrame)
        else:
            self._ensure_user_frames()
            self.show_frame(HomeFrame)

    def _ensure_user_frames(self):
        for F in (HomeFrame, ChatFrame, InfoFrame):
            if F not in self.frames:
                frame = F(self.container, self)
                self.frames[F] = frame
                frame.grid(row=0, column=0, sticky="nsew")

    def enter_admin_user_preview(self):
        if not self.is_admin:
            return
        self.admin_preview_mode = True
        self._ensure_user_frames()
        self.show_frame(HomeFrame)

    def back_to_admin_console(self):
        if not self.is_admin:
            return
        self.admin_preview_mode = False
        if AdminFrame not in self.frames:
            frame = AdminFrame(self.container, self)
            self.frames[AdminFrame] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        self.show_frame(AdminFrame)

    def show_frame(self, frame_class):
        frame = self.frames[frame_class]
        if hasattr(frame, "sidebar"):
            frame.sidebar.refresh_sessions()
            
        if frame_class == ChatFrame and getattr(frame, "current_session_id", None) is None:
            frame.start_new_chat()
            
        frame.tkraise()

    def _logout(self):
        self.logged_out = True
        self.destroy()
