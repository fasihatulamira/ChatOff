"""Chat navigation sidebar with session history."""
import customtkinter as ctk

from auth import get_user_sessions
from gui.scroll_utils import setup_smooth_scroll

class NavigationSidebar(ctk.CTkFrame):
    def __init__(self, parent, controller, new_chat_cmd=None, load_session_cmd=None):
        super().__init__(parent, width=250, corner_radius=0)
        self.controller = controller
        self.new_chat_cmd = new_chat_cmd
        self.load_session_cmd = load_session_cmd

        self.grid_rowconfigure(4, weight=1)

        # Title
        ctk.CTkLabel(self, text="🤖 ChatOff AI", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Navigation

        ctk.CTkButton(self, text="🏠 Home", height=32, fg_color="gray30",
                      command=lambda: self._go_home()).grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        
        if new_chat_cmd:
            ctk.CTkButton(self, text="➕ New Chat", height=40, font=ctk.CTkFont(weight="bold"), 
                          fg_color=("#0097A7", "#006064"), command=new_chat_cmd).grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # Session Table (Scrollable)
        ctk.CTkLabel(self, text="Previous Chats", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").grid(row=3, column=0, padx=20, pady=(10, 5), sticky="sw")
        self.session_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.session_scroll.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 20))
        setup_smooth_scroll(self.session_scroll, hover_widgets=(self,))


        # Appearance Settings
        ctk.CTkLabel(self, text="Appearance:", font=ctk.CTkFont(size=12), anchor="w").grid(row=6, column=0, padx=20, pady=(6, 0), sticky="ew")
        self.appearance_menu = ctk.CTkOptionMenu(self, values=["Dark", "Light", "System"], command=ctk.set_appearance_mode)
        self.appearance_menu.grid(row=7, column=0, padx=20, pady=(2, 20), sticky="ew")
        self.appearance_menu.set("Dark")

        self.refresh_sessions()

    def refresh_sessions(self):
        for w in self.session_scroll.winfo_children(): w.destroy()
        sessions, db_err = get_user_sessions(self.controller.username)
        if db_err:
            ctk.CTkLabel(
                self.session_scroll,
                text=f"⚠ History unavailable:\n{db_err[:80]}",
                text_color="#FF6B6B",
                font=ctk.CTkFont(size=11),
                wraplength=200,
                justify="left",
            ).pack(pady=10, padx=5)
            return
        for s in sessions:
            btn = ctk.CTkButton(self.session_scroll, text=s["session_title"], anchor="w",
                                fg_color="transparent", 
                                text_color=("#333333", "#CCCCCC"),
                                hover_color=("gray85", "gray25"), height=35,
                                command=lambda sid=s["session_id"]: self._on_session_click(sid))
            btn.pack(fill="x", pady=2)

    def _go_home(self):
        from gui.home import HomeFrame

        self.controller.show_frame(HomeFrame)

    def _on_session_click(self, session_id):
        if self.load_session_cmd:
            self.load_session_cmd(session_id)
        else:
            from gui.chat import ChatFrame

            chat_frame = self.controller.frames[ChatFrame]
            self.controller.show_frame(ChatFrame)
            chat_frame.load_session(session_id)
