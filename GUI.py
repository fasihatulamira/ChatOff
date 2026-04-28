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
    get_user_sessions, load_session_messages,
    update_session_title
)
import os
from rag import process_pdf, get_all_sources, delete_source, clear_rag, query_rag

# Set UI theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# ─────────────────────────────────────────────
#  ADMIN DASHBOARD FRAME
# ─────────────────────────────────────────────
class AdminFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

        # Header (Logout & Appearance)
        header = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        header.pack(fill="x", pady=(10, 0), padx=20)
        
        logout_btn = ctk.CTkButton(header, text="Logout", width=80, fg_color="#D32F2F", hover_color="#B71C1C", command=self.controller._logout)
        logout_btn.pack(side="right", padx=(10, 0))
        
        self.appearance_menu = ctk.CTkOptionMenu(header, values=["Dark", "Light", "System"], command=ctk.set_appearance_mode, width=100)
        self.appearance_menu.pack(side="right")
        self.appearance_menu.set("Dark")
        
        # Title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=40, pady=(10, 20))
        ctk.CTkLabel(title_frame, text="Knowledge Base Management", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Upload and manage PDF documents to power the AI responses.", font=ctk.CTkFont(size=14), text_color="gray").pack(anchor="w")

        # Upload Zone (Large dashed-like area)
        self.upload_zone = ctk.CTkFrame(self, corner_radius=15, border_width=2, border_color="gray30", fg_color="gray10")
        self.upload_zone.pack(fill="x", padx=60, pady=(10, 30), ipady=20)
        
        icon_label = ctk.CTkLabel(self.upload_zone, text="📄", font=ctk.CTkFont(size=40))
        icon_label.pack(pady=(20, 5))
        
        main_text = ctk.CTkLabel(self.upload_zone, text="Click to browse and upload PDF", font=ctk.CTkFont(size=18, weight="bold"))
        main_text.pack(pady=5)
        
        sub_text = ctk.CTkLabel(self.upload_zone, text="Maximum file size: 50MB", font=ctk.CTkFont(size=12), text_color="gray")
        sub_text.pack(pady=(0, 10))
        
        self.upload_btn = ctk.CTkButton(self.upload_zone, text="Browse Files", font=ctk.CTkFont(weight="bold"), fg_color=("#0097A7", "#006064"), hover_color=("#00838F", "#004D40"), command=self._upload_pdf)
        self.upload_btn.pack(pady=(10, 10))
        
        self.status_label = ctk.CTkLabel(self.upload_zone, text="", text_color="gray", font=ctk.CTkFont(size=12))
        self.status_label.pack()

        # Documents Table area
        table_container = ctk.CTkFrame(self, corner_radius=15, fg_color="gray15")
        table_container.pack(fill="both", expand=True, padx=40, pady=(0, 30))
        
        table_header_top = ctk.CTkFrame(table_container, fg_color="transparent")
        table_header_top.pack(fill="x", padx=20, pady=(15, 10))
        self.doc_count_label = ctk.CTkLabel(table_header_top, text="Uploaded Documents (0)", font=ctk.CTkFont(size=16, weight="bold"))
        self.doc_count_label.pack(side="left")
        ctk.CTkButton(table_header_top, text="Clear All", width=80, height=28, fg_color="gray30", hover_color="gray20", command=self._clear_all).pack(side="right")
        
        # Columns
        col_frame = ctk.CTkFrame(table_container, fg_color="gray20", corner_radius=8)
        col_frame.pack(fill="x", padx=20, pady=(0, 10))
        col_frame.grid_columnconfigure(0, weight=4)
        col_frame.grid_columnconfigure(1, weight=1)
        col_frame.grid_columnconfigure(2, weight=2)
        col_frame.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(col_frame, text="FILE NAME", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").grid(row=0, column=0, sticky="w", padx=15, pady=8)
        ctk.CTkLabel(col_frame, text="SIZE", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").grid(row=0, column=1, sticky="w", padx=10, pady=8)
        ctk.CTkLabel(col_frame, text="UPLOAD DATE", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").grid(row=0, column=2, sticky="w", padx=10, pady=8)
        ctk.CTkLabel(col_frame, text="ACTIONS", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").grid(row=0, column=3, sticky="e", padx=15, pady=8)
        
        self.entries_frame = ctk.CTkScrollableFrame(table_container, fg_color="transparent")
        self.entries_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self._refresh_entries()

    def _upload_pdf(self):
        file_path = ctk.filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not file_path: return
        
        self.upload_btn.configure(state="disabled")
        self.status_label.configure(text=f"Reading & Embedding: {os.path.basename(file_path)}...")
        
        def task():
            def progress(current, total):
                self.controller.after(0, lambda: self.status_label.configure(text=f"Embedding chunk {current}/{total}..."))
                
            ok, msg = process_pdf(file_path, progress_callback=progress)
            self.controller.after(0, lambda: self._upload_complete(ok, msg))
            
        threading.Thread(target=task, daemon=True).start()
        
    def _upload_complete(self, ok, msg):
        self.upload_btn.configure(state="normal")
        color = "#4CAF50" if ok else "#FF6B6B"
        self.status_label.configure(text=msg, text_color=color)
        if ok:
            self._refresh_entries()

    def _refresh_entries(self):
        for w in self.entries_frame.winfo_children(): w.destroy()
        sources_info = get_all_sources()
        self.doc_count_label.configure(text=f"Uploaded Documents ({len(sources_info)})")
        
        if not sources_info:
            ctk.CTkLabel(self.entries_frame, text="No documents found.", text_color="gray").pack(pady=40)
            return
            
        for i, (src, meta) in enumerate(sources_info):
            bg_color = "gray15" if i % 2 == 0 else "gray12"
            row = ctk.CTkFrame(self.entries_frame, corner_radius=0, fg_color=bg_color)
            row.pack(fill="x")
            
            row.grid_columnconfigure(0, weight=4)
            row.grid_columnconfigure(1, weight=1)
            row.grid_columnconfigure(2, weight=2)
            row.grid_columnconfigure(3, weight=1)
            
            # File name with icon
            name_frame = ctk.CTkFrame(row, fg_color="transparent")
            name_frame.grid(row=0, column=0, sticky="w", padx=15, pady=12)
            ctk.CTkLabel(name_frame, text="📄", text_color="#EF5350").pack(side="left", padx=(0, 10))
            ctk.CTkLabel(name_frame, text=src, font=ctk.CTkFont(size=13)).pack(side="left")
            
            # Size
            ctk.CTkLabel(row, text=meta.get("size", "Unknown"), font=ctk.CTkFont(size=12), text_color="gray").grid(row=0, column=1, sticky="w", padx=10)
            
            # Date
            ctk.CTkLabel(row, text=meta.get("date", "Unknown"), font=ctk.CTkFont(size=12), text_color="gray").grid(row=0, column=2, sticky="w", padx=10)
            
            # Actions
            action_frame = ctk.CTkFrame(row, fg_color="transparent")
            action_frame.grid(row=0, column=3, sticky="e", padx=15)
            ctk.CTkButton(action_frame, text="🗑", width=30, height=30, fg_color="transparent", hover_color="gray30", command=lambda s=src: (delete_source(s), self._refresh_entries())).pack(side="right")

    def _clear_all(self):
        if messagebox.askyesno("Clear", "Delete ALL uploaded PDFs?"):
            clear_rag()
            self._refresh_entries()


# ─────────────────────────────────────────────
#  RE-USABLE COMPONENT: SIDEBAR
# ─────────────────────────────────────────────
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
                      command=lambda: controller.show_frame(HomeFrame)).grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        
        if new_chat_cmd:
            ctk.CTkButton(self, text="➕ New Chat", height=40, font=ctk.CTkFont(weight="bold"), 
                          fg_color=("#0097A7", "#006064"), command=new_chat_cmd).grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # Session Table (Scrollable)
        ctk.CTkLabel(self, text="Previous Chats", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").grid(row=3, column=0, padx=20, pady=(10, 5), sticky="sw")
        self.session_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.session_scroll.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 20))


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

        self.chat_scroll = ctk.CTkScrollableFrame(content, fg_color="transparent")
        self.chat_scroll.pack(fill="both", expand=True, padx=20, pady=20)

        self.options_frame = None
        self._show_initial_help()

    def _add_bubble(self, sender, text, is_system=True):
        bg_color = ("gray85", "gray20") if is_system else ("#0097A7", "#006064")
        text_color = ("black", "white") if is_system else "white"
        
        bubble_frame = ctk.CTkFrame(self.chat_scroll, fg_color=bg_color, corner_radius=15)
        
        anchor = "w" if is_system else "e"
        padx = (10, 100) if is_system else (100, 10)
        
        bubble_frame.pack(anchor=anchor, padx=padx, pady=8)

        lbl = ctk.CTkLabel(bubble_frame, text=f"{sender}:\n{text}", font=ctk.CTkFont(size=14), justify="left", text_color=text_color)
        lbl.pack(padx=15, pady=10)

        self.after(50, lambda: self.chat_scroll._parent_canvas.yview_moveto(1.0))
        return bubble_frame

    def _show_options(self):
        if self.options_frame:
            self.options_frame.destroy()
            
        self.options_frame = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        self.options_frame.pack(anchor="w", padx=(10, 100), pady=(0, 10))

        options = ["How to Start a Chat", "Privacy & Data"]
        for opt in options:
            btn = ctk.CTkButton(self.options_frame, text=opt, height=34, corner_radius=17,
                                fg_color="transparent", border_width=1, border_color="#0097A7",
                                text_color=("#0097A7", "#4DD0E1"), hover_color=("#E0F7FA", "#004D40"),
                                command=lambda o=opt: self._handle_help_req(o))
            btn.pack(anchor="w", pady=4)
        
        self.after(50, lambda: self.chat_scroll._parent_canvas.yview_moveto(1.0))

    def _show_initial_help(self):
        self._add_bubble("System", "Hello! How can I assist you today? Please choose an option below:", is_system=True)
        self._show_options()

    def _handle_help_req(self, topic):
        if self.options_frame:
            self.options_frame.destroy()
            self.options_frame = None

        self._add_bubble("You", topic, is_system=False)
        responses = {
            "How to Start a Chat": "Go to 'Ask AI' from the dashboard. Click 'New Chat' to start or select an old one from the sidebar.",
            "Managing Knowledge Base": "In 'Ask AI', click 'Knowledge Base'. Add titles and content to provide the AI with custom local data.",
            "Privacy & Data": "ChatOff runs entirely on your local machine. No data is sent to the internet. Your chats are stored in your MySQL db.",
        }
        self.after(300, lambda: self._add_bubble("System", responses.get(topic, "I don't have info on that yet."), is_system=True))
        self.after(800, self._show_options)


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
        self.stop_btn = ctk.CTkButton(self.input_frame, text="Stop", width=100, height=42, 
                                      command=self._stop_generation, state="disabled", 
                                      fg_color="#d9534f", hover_color="#c9302c")
        self.stop_btn.grid(row=0, column=2, padx=(10, 0))
        self.stop_generation_flag = False

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
            self.chat_area.insert("end", "You: ", "bold")
            self.chat_area.insert("end", f"{m['prompt_text']}\n\n")
            self.chat_area.insert("end", "Bot: ", "bold")
            self.chat_area.insert("end", f"{m['response_text']}\n\n")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    def _stop_generation(self):
        self.stop_generation_flag = True

    def _send(self):
        msg = self.entry.get().strip()
        if not msg: return
        
        is_first_msg = (self.current_session_id is None)
        if is_first_msg: self.current_session_id = str(uuid.uuid4())
        
        self.entry.delete(0, "end")
        self._append_chat("You", msg)
        
        self.send_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.stop_generation_flag = False
        threading.Thread(target=self._process_ai, args=(msg, is_first_msg), daemon=True).start()

    def _process_ai(self, prompt, is_first_msg):
        model = "llama3"
        sys = query_rag(prompt)
        collected = []
        try:
            self.controller.after(0, lambda: (self.chat_area.configure(state="normal"), self.chat_area.insert("end", "Bot: ", "bold")))
            for chunk in get_response(prompt, model, sys):
                if self.stop_generation_flag:
                    break
                collected.append(chunk)
                self.controller.after(0, lambda c=chunk: (self.chat_area.configure(state="normal"), self.chat_area.insert("end", c), self.chat_area.see("end"), self.chat_area.configure(state="disabled")))
            
            full = "".join(collected)
            save_message(self.controller.username, self.current_session_id, prompt, full)
            self.controller.after(0, lambda: (self.chat_area.configure(state="normal"), self.chat_area.insert("end", "\n\n"), self.chat_area.configure(state="disabled")))
            self.controller.after(0, lambda: self.sidebar.refresh_sessions())

            # If it's the first message, generate a catchy title in the background
            if is_first_msg:
                threading.Thread(target=self._generate_catchy_title, args=(prompt,), daemon=True).start()

        except Exception as e:
            self.controller.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.controller.after(0, lambda: self.send_btn.configure(state="normal"))
            self.controller.after(0, lambda: self.stop_btn.configure(state="disabled"))

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
        # Ensure we start on a new line if there is already content
        if self.chat_area.get("1.0", "end-1c").strip():
            self.chat_area.insert("end", "\n")
        self.chat_area.insert("end", f"{sender}: ", "bold")
        self.chat_area.insert("end", f"{message}\n\n")
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
        self.after(10, lambda: self.state("zoomed"))  # Maximize after window draws

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        if self.username == "admin":
            frame = AdminFrame(self.container, self)
            self.frames[AdminFrame] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            self.show_frame(AdminFrame)
        else:
            for F in (HomeFrame, ChatFrame, HelpFrame, InfoFrame):
                frame = F(self.container, self)
                self.frames[F] = frame
                frame.grid(row=0, column=0, sticky="nsew")
            self.show_frame(HomeFrame)

    def show_frame(self, frame_class):
        if hasattr(self.frames[frame_class], "sidebar"):
            self.frames[frame_class].sidebar.refresh_sessions()
        self.frames[frame_class].tkraise()

    def _logout(self):
        from login import LoginWindow
        self.destroy(); LoginWindow().mainloop()
