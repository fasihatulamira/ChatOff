# ===== MAIN CHATBOT WINDOW =====
# Loads chat sessions from MySQL, supports Knowledge Base management,
# and provides a Home navigation menu for Help, Chat, and Info.

import customtkinter as ctk
import threading
import uuid
import re
from tkinter import messagebox
from chatbot import get_response
from auth import (
    save_message, clear_history,
    add_knowledge, get_all_knowledge, delete_knowledge,
    build_system_prompt, get_user_sessions, load_session_messages,
    update_session_title
)

# Set UI theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# ─────────────────────────────────────────────
#  KNOWLEDGE BASE MODAL WINDOW
# ─────────────────────────────────────────────
class KnowledgeBaseWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("📚 Knowledge Base")
        self.geometry("620x580")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("#0097A7", "#006064"))
        header.pack(fill="x")
        ctk.CTkLabel(header, text="📚  Knowledge Base", font=ctk.CTkFont(size=22, weight="bold"), text_color="white").pack(pady=(18, 4))
        ctk.CTkLabel(header, text="Entries are injected as context into every AI response", font=ctk.CTkFont(size=12), text_color="#B2EBF2").pack(pady=(0, 16))

        form = ctk.CTkFrame(self, corner_radius=12)
        form.pack(fill="x", padx=20, pady=(16, 8))
        ctk.CTkLabel(form, text="Title", font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", padx=16, pady=(12, 2))
        self.title_entry = ctk.CTkEntry(form, placeholder_text="e.g. FAQ", height=38, corner_radius=8)
        self.title_entry.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(form, text="Content", font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", padx=16, pady=(0, 2))
        self.content_box = ctk.CTkTextbox(form, height=80, corner_radius=8)
        self.content_box.pack(fill="x", padx=16, pady=(0, 8))
        self.form_error = ctk.CTkLabel(form, text="", text_color="#FF6B6B", font=ctk.CTkFont(size=12))
        self.form_error.pack()
        ctk.CTkButton(form, text="➕  Add to Knowledge Base", height=40, corner_radius=8, fg_color=("#0097A7", "#006064"), hover_color=("#00838F", "#004D40"), command=self._add_entry).pack(fill="x", padx=16, pady=(4, 14))

        list_header = ctk.CTkFrame(self, fg_color="transparent")
        list_header.pack(fill="x", padx=20, pady=(4, 0))
        ctk.CTkLabel(list_header, text="Saved Entries", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(list_header, text="Clear All", width=80, height=28, command=self._clear_all).pack(side="right")

        self.entries_frame = ctk.CTkScrollableFrame(self, corner_radius=10, height=160)
        self.entries_frame.pack(fill="both", expand=True, padx=20, pady=(6, 16))
        self._refresh_entries()

    def _add_entry(self):
        title, content = self.title_entry.get().strip(), self.content_box.get("1.0", "end").strip()
        ok, msg = add_knowledge(title, content)
        if ok:
            self.title_entry.delete(0, "end"); self.content_box.delete("1.0", "end"); self.form_error.configure(text="")
            self._refresh_entries()
        else: self.form_error.configure(text=f"⚠  {msg}")

    def _refresh_entries(self):
        for w in self.entries_frame.winfo_children(): w.destroy()
        entries = get_all_knowledge()
        if not entries:
            ctk.CTkLabel(self.entries_frame, text="No entries yet.", text_color="gray").pack(pady=20)
            return
        for e in entries:
            row = ctk.CTkFrame(self.entries_frame, corner_radius=8)
            row.pack(fill="x", pady=4)
            text_frame = ctk.CTkFrame(row, fg_color="transparent")
            text_frame.pack(side="left", fill="both", expand=True, padx=12, pady=8)
            ctk.CTkLabel(text_frame, text=e["title"], font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x")
            ctk.CTkLabel(text_frame, text=e["content"][:80], font=ctk.CTkFont(size=11), text_color="gray", anchor="w").pack(fill="x")
            ctk.CTkButton(row, text="🗑", width=36, height=36, command=lambda i=e["id"]: (delete_knowledge(i), self._refresh_entries())).pack(side="right", padx=8)

    def _clear_all(self):
        if messagebox.askyesno("Clear", "Delete ALL knowledge?"):
            from auth import clear_knowledge; clear_knowledge(); self._refresh_entries()


# ─────────────────────────────────────────────
#  RE-USABLE COMPONENT: SIDEBAR
# ─────────────────────────────────────────────
class NavigationSidebar(ctk.CTkFrame):
    def __init__(self, parent, controller, new_chat_cmd=None, load_session_cmd=None):
        super().__init__(parent, width=250, corner_radius=0)
        self.controller = controller
        self.new_chat_cmd = new_chat_cmd
        self.load_session_cmd = load_session_cmd

        self.grid_rowconfigure(3, weight=1)

        # Title
        ctk.CTkLabel(self, text="🤖 ChatOff AI", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Navigation
        ctk.CTkButton(self, text="🏠 Home", height=32, fg_color="gray30", 
                      command=lambda: controller.show_frame(HomeFrame)).grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        
        if new_chat_cmd:
            ctk.CTkButton(self, text="➕ New Chat", height=40, font=ctk.CTkFont(weight="bold"), 
                          fg_color=("#0097A7", "#006064"), command=new_chat_cmd).grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # Session Table (Scrollable)
        ctk.CTkLabel(self, text="Previous Chats", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").grid(row=3, column=0, padx=20, pady=(10, 5), sticky="sw")
        self.session_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.session_scroll.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 20))

        # Bottom Sidebar
        self.kb_btn = ctk.CTkButton(self, text="📚 Knowledge Base", height=32, command=self._open_kb)
        self.kb_btn.grid(row=5, column=0, padx=20, pady=5, sticky="ew")
        
        # Appearance Settings
        ctk.CTkLabel(self, text="Appearance:", font=ctk.CTkFont(size=12), anchor="w").grid(row=6, column=0, padx=20, pady=(6, 0), sticky="ew")
        self.appearance_menu = ctk.CTkOptionMenu(self, values=["Dark", "Light", "System"], command=ctk.set_appearance_mode)
        self.appearance_menu.grid(row=7, column=0, padx=20, pady=(2, 20), sticky="ew")
        self.appearance_menu.set("Dark")

        self.refresh_sessions()

    def refresh_sessions(self):
        for w in self.session_scroll.winfo_children(): w.destroy()
        sessions = get_user_sessions(self.controller.username)
        for s in sessions:
            btn = ctk.CTkButton(self.session_scroll, text=s["session_title"], anchor="w",
                                fg_color="transparent", 
                                text_color=("#333333", "#CCCCCC"),
                                hover_color=("gray85", "gray25"), height=35,
                                command=lambda sid=s["session_id"]: self._on_session_click(sid))
            btn.pack(fill="x", pady=2)

    def _on_session_click(self, session_id):
        if self.load_session_cmd:
            self.load_session_cmd(session_id)
        else:
            chat_frame = self.controller.frames[ChatFrame]
            self.controller.show_frame(ChatFrame)
            chat_frame.load_session(session_id)

    def _open_kb(self): KnowledgeBaseWindow(self)


# ─────────────────────────────────────────────
#  RE-USABLE FRAME: HOME (MAIN MENU)
# ─────────────────────────────────────────────
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

        self._make_menu_card(btn_container, "❓", "Help", "Get automated assistance\n& usage tips", 
                            lambda: controller.show_frame(HelpFrame)).grid(row=0, column=0, padx=20)
        
        self._make_menu_card(btn_container, "🤖", "Ask AI", "Chat with your local\noffline models", 
                            lambda: controller.show_frame(ChatFrame)).grid(row=0, column=1, padx=20)

        self._make_menu_card(btn_container, "ℹ️", "Info", "Learn more about the\napps capabilities", 
                            lambda: controller.show_frame(InfoFrame)).grid(row=0, column=2, padx=20)

        ctk.CTkButton(self, text="⇠ Logout", width=120, height=36, fg_color="transparent", border_width=1,
                      text_color=("#CC0000", "#FF6B6B"), border_color=("#CC0000", "#FF6B6B"),
                      command=controller._logout).grid(row=2, column=0, pady=40)

    def _make_menu_card(self, parent, icon, title, desc, command):
        card = ctk.CTkFrame(parent, width=280, height=320, corner_radius=20)
        card.grid_propagate(False)
        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=60)).pack(pady=(40, 10))
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=24, weight="bold")).pack(pady=5)
        ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=13), text_color="gray", justify="center").pack(pady=10)
        ctk.CTkButton(card, text="Open", width=180, height=40, font=ctk.CTkFont(weight="bold"), 
                      corner_radius=10, command=command).pack(side="bottom", pady=40)
        return card


# ─────────────────────────────────────────────
#  RE-USABLE FRAME: HELP (AUTOMATED)
# ─────────────────────────────────────────────
class HelpFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

        self.sidebar = NavigationSidebar(self, controller)
        self.sidebar.pack(side="left", fill="y")

        content = ctk.CTkFrame(self, corner_radius=20)
        content.pack(side="right", fill="both", expand=True, padx=40, pady=40)

        self.help_box = ctk.CTkTextbox(content, font=ctk.CTkFont(size=15), state="disabled")
        self.help_box.pack(fill="both", expand=True, padx=20, pady=20)

        self.btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=20, pady=(0, 20))

        self._show_initial_help()

    def _show_initial_help(self):
        self._append_help("System", "Hello! How can I assist you today? Please choose an option below:")
        options = ["How to Start a Chat", "Managing Knowledge Base", "Privacy & Data"]
        for opt in options:
            ctk.CTkButton(self.btn_frame, text=opt, height=36, corner_radius=8,
                          command=lambda o=opt: self._handle_help_req(o)).pack(side="left", padx=5)

    def _append_help(self, sender, msg):
        self.help_box.configure(state="normal")
        self.help_box.insert("end", f"\n【{sender}】: {msg}\n")
        self.help_box.see("end")
        self.help_box.configure(state="disabled")

    def _handle_help_req(self, topic):
        self._append_help("You", topic)
        responses = {
            "How to Start a Chat": "Go to 'Ask AI' from the dashboard. Click 'New Chat' to start or select an old one from the sidebar.",
            "Managing Knowledge Base": "In 'Ask AI', click 'Knowledge Base'. Add titles and content to provide the AI with custom local data.",
            "Privacy & Data": "ChatOff runs entirely on your local machine. No data is sent to the internet. Your chats are stored in your MySQL db.",
        }
        self._append_help("System", responses.get(topic, "I don't have info on that yet."))


# ─────────────────────────────────────────────
#  RE-USABLE FRAME: INFO
# ─────────────────────────────────────────────
class InfoFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        
        container = ctk.CTkFrame(self, corner_radius=20)
        container.pack(fill="both", expand=True, padx=100, pady=100)
        
        ctk.CTkLabel(container, text="ℹ️  Application Information", font=ctk.CTkFont(size=32, weight="bold")).pack(pady=40)
        info_text = (
            "ChatOff is designed for secure, offline AI assistance.\n\n"
            "• Powered by Llama3 local model\n"
            "• Zero data leakage—everything stays on your PC\n"
            "• AI-powered catchy session titles\n"
            "• Custom Knowledge Base support\n\n"
            "Version 2.1.0 (Llama3 Edition)"
        )
        ctk.CTkLabel(container, text=info_text, font=ctk.CTkFont(size=16), justify="center").pack(pady=20)
        ctk.CTkButton(container, text="← Back to Home", command=lambda: controller.show_frame(HomeFrame)).pack(pady=40)


# ─────────────────────────────────────────────
#  RE-USABLE FRAME: CHAT (ASK AI)
# ─────────────────────────────────────────────
class ChatFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.current_session_id = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = NavigationSidebar(self, controller, 
                                         new_chat_cmd=self.start_new_chat,
                                         load_session_cmd=self.load_session)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")

        self.chat_area = ctk.CTkTextbox(self, font=ctk.CTkFont(size=14), state="disabled")
        self.chat_area.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="nsew")

        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=1, column=1, padx=20, pady=20, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        self.entry = ctk.CTkEntry(self.input_frame, placeholder_text="Type a message...", height=42)
        self.entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.entry.bind("<Return>", lambda e: self._send())
        self.send_btn = ctk.CTkButton(self.input_frame, text="Send", width=100, height=42, command=self._send)
        self.send_btn.grid(row=0, column=1)

    def start_new_chat(self):
        self.current_session_id = str(uuid.uuid4())
        self.chat_area.configure(state="normal")
        self.chat_area.delete("1.0", "end")
        self.chat_area.insert("end", "✨ New chat session started.\n\n", "italic")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    def load_session(self, session_id):
        self.current_session_id = session_id
        messages = load_session_messages(self.controller.username, session_id)
        self.chat_area.configure(state="normal")
        self.chat_area.delete("1.0", "end")
        for m in messages:
            lbl = "You" if m["sender"] == "user" else "Bot"
            self.chat_area.insert("end", f"{lbl}: ", "bold")
            self.chat_area.insert("end", f"{m['message']}\n\n")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    def _send(self):
        msg = self.entry.get().strip()
        if not msg: return
        
        is_first_msg = (self.current_session_id is None)
        if is_first_msg: self.current_session_id = str(uuid.uuid4())
        
        self.entry.delete(0, "end")
        self._append_chat("You", msg)
        save_message(self.controller.username, self.current_session_id, "user", msg, "llama3")
        
        self.send_btn.configure(state="disabled")
        threading.Thread(target=self._process_ai, args=(msg, is_first_msg), daemon=True).start()

    def _process_ai(self, prompt, is_first_msg):
        model, sys = "llama3", build_system_prompt()
        collected = []
        try:
            self.controller.after(0, lambda: (self.chat_area.configure(state="normal"), self.chat_area.insert("end", "Bot: ", "bold")))
            for chunk in get_response(prompt, model, sys):
                collected.append(chunk)
                self.controller.after(0, lambda c=chunk: (self.chat_area.configure(state="normal"), self.chat_area.insert("end", c), self.chat_area.see("end"), self.chat_area.configure(state="disabled")))
            
            full = "".join(collected)
            save_message(self.controller.username, self.current_session_id, "bot", full, model)
            self.controller.after(0, lambda: self.sidebar.refresh_sessions())

            # If it's the first message, generate a catchy title in the background
            if is_first_msg:
                threading.Thread(target=self._generate_catchy_title, args=(prompt,), daemon=True).start()

        except Exception as e:
            self.controller.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.controller.after(0, lambda: self.send_btn.configure(state="normal"))

    def _generate_catchy_title(self, prompt):
        """Asks the AI to create a short catchy title for the conversation."""
        title_prompt = f"Summarize the following topic into a catchy 3-word title for a sidebar. Reply ONLY with the title: {prompt}"
        try:
            # We use a short request to get just the title
            gen = get_response(title_prompt, "llama3", system_prompt="You are a helpful assistant that provides short, catchy titles.")
            title = "".join(list(gen)).strip()
            # Clean up quotes if AI adds them
            title = re.sub(r'["\']', '', title)
            # Cap it at 30 chars just in case
            title = title[:30]
            
            update_session_title(self.current_session_id, title)
            self.controller.after(0, lambda: self.sidebar.refresh_sessions())
        except:
            pass

    def _append_chat(self, sender, message):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", f"{sender}: {message}\n\n")
        self.chat_area.configure(state="disabled")
        self.chat_area.see("end")


# ─────────────────────────────────────────────
#  MODIFIED MAIN CLASS (CONTROLLER)
# ─────────────────────────────────────────────
class OfflineChatbot(ctk.CTk):
    def __init__(self, user_name: str = "User", username: str = ""):
        super().__init__()
        self.user_name, self.username = user_name, username or user_name.lower().replace(" ", "")
        self.title("ChatOff AI 🤖")

        win_w, win_h = 1100, 800
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{win_w}x{win_h}+{(sw-win_w)//2}+{(sh-win_h)//2}")
        self.minsize(900, 700)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (HomeFrame, ChatFrame, HelpFrame, InfoFrame):
            frame = F(self.container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.show_frame(HomeFrame)

    def show_frame(self, frame_class):
        if hasattr(self.frames[frame_class], "sidebar"):
            self.frames[frame_class].sidebar.refresh_sessions()
        self.frames[frame_class].tkraise()

    def _logout(self):
        from login import LoginWindow
        self.destroy(); LoginWindow().mainloop()
