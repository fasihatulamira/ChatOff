"""Home dashboard and info screens."""
import customtkinter as ctk


def _open_chat(controller):
    from gui.chat import ChatFrame
    controller.show_frame(ChatFrame)


class HomeFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, height=120, corner_radius=0, fg_color=("#1565C0", "#0D1B2A"))
        header.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(header, text="💬  ChatOff Dashboard", font=ctk.CTkFont(size=32, weight="bold"), text_color="white").pack(pady=(30, 2))
        ctk.CTkLabel(header, text=f"Welcome back, {controller.user_name}!", font=ctk.CTkFont(size=14), text_color="#90CAF9").pack(pady=(0, 20))

        btn_container = ctk.CTkFrame(self, fg_color="transparent")
        btn_container.grid(row=1, column=0, pady=40)

        self._make_menu_card(btn_container, "🤖", "Chat & Help", "Chat with AI and\nget automated assistance", 
                            lambda: _open_chat(controller)).grid(row=0, column=0, padx=20)

        self._make_menu_card(btn_container, "💡", "Info", "Learn more about the\napps capabilities", 
                            lambda: controller.show_frame(InfoFrame)).grid(row=0, column=1, padx=20)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, pady=40)

        if controller.is_admin and controller.admin_preview_mode:
            ctk.CTkButton(
                footer, text="⇠ Back to Admin Console", width=200, height=36,
                fg_color=("#1565C0", "#0D47A1"), hover_color=("#1976D2", "#1565C0"),
                command=controller.back_to_admin_console,
            ).pack(side="left", padx=8)

        ctk.CTkButton(
            footer, text="⇠ Logout", width=120, height=36, fg_color="transparent", border_width=1,
            text_color=("#CC0000", "#FF6B6B"), border_color=("#CC0000", "#FF6B6B"),
            command=controller._logout,
        ).pack(side="left", padx=8)

    def _make_menu_card(self, parent, icon, title, desc, command):
        card = ctk.CTkFrame(parent, width=280, height=320, corner_radius=20)
        card.grid_propagate(False)
        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=60)).pack(pady=(40, 10))
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=24, weight="bold")).pack(pady=5)
        ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=13), text_color="gray", justify="center").pack(pady=10)
        ctk.CTkButton(card, text="Open", width=180, height=40, font=ctk.CTkFont(weight="bold"), 
                      corner_radius=10, command=command).pack(side="bottom", pady=40)
        return card



class InfoFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        
        container = ctk.CTkFrame(self, corner_radius=20)
        container.pack(fill="both", expand=True, padx=100, pady=100)
        
        ctk.CTkLabel(container, text="ℹ️  Application Information", font=ctk.CTkFont(size=32, weight="bold")).pack(pady=40)
        info_text = (
            "ChatOff is designed for secure, offline AI assistance.\n\n"
            "• Powered by local Ollama models (llama3.2:3b)\n"
            "• Zero data leakage—everything stays on your PC\n"
            "• AI-powered catchy session titles\n"
            "• Custom Knowledge Base support\n\n"
            "Version 2.2.0 (Offline Edition)"
        )
        ctk.CTkLabel(container, text=info_text, font=ctk.CTkFont(size=16), justify="center").pack(pady=20)
        ctk.CTkButton(container, text="← Back to Home", command=lambda: controller.show_frame(HomeFrame)).pack(pady=40)
