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
from rag import process_pdf, get_all_sources, delete_source, clear_rag, query_rag, add_manual_entry, get_source_content, save_unanswered_question

# Set UI theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# ─────────────────────────────────────────────
#  MANUAL ENTRY WINDOW
# ─────────────────────────────────────────────
class ManualEntryWindow(ctk.CTkToplevel):
    def __init__(self, parent, on_success_callback):
        super().__init__(parent)
        self.title("Create Knowledge Entry")
        self.geometry("700x600")
        self.grab_set()
        self.on_success_callback = on_success_callback
        
        # Center the window
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (700 // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (600 // 2)
            self.geometry(f"+{x}+{y}")
        except:
            pass
            
        title_label = ctk.CTkLabel(self, text="Create Knowledge Entry", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack(pady=(30, 20), padx=40, anchor="w")
        
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=40, pady=(0, 20))
        
        # Entry Title
        ctk.CTkLabel(main_frame, text="ENTRY TITLE", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(anchor="w", pady=(0, 5))
        self.title_entry = ctk.CTkEntry(main_frame, placeholder_text="e.g., How to configure API environment variables", height=40)
        self.title_entry.pack(fill="x", pady=(0, 20))
        
        # User Question
        ctk.CTkLabel(main_frame, text="USER QUESTION", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(anchor="w", pady=(0, 5))
        self.question_entry = ctk.CTkEntry(main_frame, placeholder_text="State the question exactly as a user might ask it...", height=40)
        self.question_entry.pack(fill="x", pady=(0, 20))
        
        # Detailed Answer
        ctk.CTkLabel(main_frame, text="DETAILED ANSWER", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(anchor="w", pady=(0, 5))
        self.answer_box = ctk.CTkTextbox(main_frame, height=200, font=ctk.CTkFont(size=14))
        self.answer_box.pack(fill="x", pady=(0, 20))
        self.answer_box.insert("1.0", "Provide a clear, concise, and accurate answer...")
        self.answer_box.bind("<FocusIn>", self._clear_placeholder)
        
        # Button frame
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        self.status_label = ctk.CTkLabel(btn_frame, text="", text_color="gray")
        self.status_label.pack(side="left")
        
        publish_btn = ctk.CTkButton(btn_frame, text="Publish", height=40, width=120, font=ctk.CTkFont(weight="bold"), fg_color=("#0D47A1", "#1565C0"), command=self._save_entry)
        publish_btn.pack(side="right", padx=(10, 0))
        
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", height=40, width=120, fg_color="transparent", border_width=1, command=self.destroy)
        cancel_btn.pack(side="right")
        
    def _clear_placeholder(self, event):
        if self.answer_box.get("1.0", "end-1c") == "Provide a clear, concise, and accurate answer...":
            self.answer_box.delete("1.0", "end")
            
    def _save_entry(self):
        title = self.title_entry.get().strip()
        question = self.question_entry.get().strip()
        answer = self.answer_box.get("1.0", "end-1c").strip()
        
        if not title or not question or not answer or answer == "Provide a clear, concise, and accurate answer...":
            self.status_label.configure(text="Please fill in all fields.", text_color="#FF6B6B")
            return
            
        self.status_label.configure(text="Generating Embeddings & Saving...", text_color="gray")
        self.update_idletasks()
        
        def task():
            ok, msg = add_manual_entry(title, question, answer)
            self.after(0, lambda: self._on_save_complete(ok, msg))
            
        threading.Thread(target=task, daemon=True).start()
        
    def _on_save_complete(self, ok, msg):
        if ok:
            self.on_success_callback()
            self.destroy()
        else:
            self.status_label.configure(text=msg, text_color="#FF6B6B")


# ─────────────────────────────────────────────
#  VIEW SOURCE WINDOW
# ─────────────────────────────────────────────
class ViewSourceWindow(ctk.CTkToplevel):
    def __init__(self, parent, source_name, content):
        super().__init__(parent)
        self.title(f"Viewing: {source_name}")
        self.geometry("800x600")
        self.grab_set()
        
        # Center the window
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (800 // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (600 // 2)
            self.geometry(f"+{x}+{y}")
        except:
            pass
            
        title_label = ctk.CTkLabel(self, text=f"📄 {source_name}", font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=(20, 10), padx=20, anchor="w")
        
        self.textbox = ctk.CTkTextbox(self, font=ctk.CTkFont(size=14))
        self.textbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.textbox.insert("1.0", content)
        self.textbox.configure(state="disabled")
        
        close_btn = ctk.CTkButton(self, text="Close", height=36, width=120, command=self.destroy)
        close_btn.pack(pady=(0, 20))


# ─────────────────────────────────────────────
#  UNANSWERED QUESTIONS WINDOW
# ─────────────────────────────────────────────
class UnansweredQuestionsWindow(ctk.CTkToplevel):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.title("Unanswered Questions")
        self.geometry("800x600")
        self.grab_set()
        self.controller = controller
        
        # Center the window
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (800 // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (600 // 2)
            self.geometry(f"+{x}+{y}")
        except:
            pass
            
        title_label = ctk.CTkLabel(self, text="❓ Unanswered Questions", font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=(20, 10), padx=20, anchor="w")
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self._refresh()

    def _refresh(self):
        for w in self.scroll.winfo_children(): w.destroy()
        from rag import get_unanswered_questions, delete_unanswered_question
        questions = get_unanswered_questions()
        
        if not questions:
            ctk.CTkLabel(self.scroll, text="No unanswered questions. Great job!", text_color="gray").pack(pady=40)
            return
            
        for q in questions:
            row = ctk.CTkFrame(self.scroll, corner_radius=8, fg_color=("gray85", "gray15"))
            row.pack(fill="x", pady=5)
            
            lbl = ctk.CTkLabel(row, text=q["question"], font=ctk.CTkFont(size=14), wraplength=500, justify="left")
            lbl.pack(side="left", padx=15, pady=10, fill="x", expand=True)
            
            date_lbl = ctk.CTkLabel(row, text=q.get("date", ""), font=ctk.CTkFont(size=11), text_color="gray")
            date_lbl.pack(side="left", padx=10)
            
            def answer_cmd(q_text=q["question"], q_id=q["id"]):
                def on_success():
                    delete_unanswered_question(q_id)
                    self._refresh()
                    # Also refresh the admin's documents table behind this
                    if hasattr(self.controller, 'frames') and AdminFrame in self.controller.frames:
                        self.controller.frames[AdminFrame]._refresh_entries()
                win = ManualEntryWindow(self, on_success)
                win.question_entry.insert(0, q_text)
                win.title_entry.insert(0, f"Answer to: {q_text[:30]}")

            ans_btn = ctk.CTkButton(row, text="Answer", width=80, command=answer_cmd)
            ans_btn.pack(side="right", padx=10)


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
        self.upload_zone = ctk.CTkFrame(self, corner_radius=15, border_width=2, border_color=("gray70", "gray30"), fg_color=("gray90", "gray10"))
        self.upload_zone.pack(fill="x", padx=60, pady=(10, 30), ipady=20)
        
        icon_label = ctk.CTkLabel(self.upload_zone, text="📄", font=ctk.CTkFont(size=40))
        icon_label.pack(pady=(20, 5))
        
        main_text = ctk.CTkLabel(self.upload_zone, text="Click to browse and upload PDF", font=ctk.CTkFont(size=18, weight="bold"))
        main_text.pack(pady=5)
        
        sub_text = ctk.CTkLabel(self.upload_zone, text="Maximum file size: 50MB", font=ctk.CTkFont(size=12), text_color="gray")
        sub_text.pack(pady=(0, 10))
        
        btn_frame = ctk.CTkFrame(self.upload_zone, fg_color="transparent")
        btn_frame.pack(pady=(10, 10))
        
        self.upload_btn = ctk.CTkButton(btn_frame, text="Browse PDF", font=ctk.CTkFont(weight="bold"), fg_color=("#0097A7", "#006064"), hover_color=("#00838F", "#004D40"), command=self._upload_pdf)
        self.upload_btn.pack(side="left", padx=10)
        
        self.manual_btn = ctk.CTkButton(btn_frame, text="Add Manually", font=ctk.CTkFont(weight="bold"), fg_color=("#1976D2", "#0D47A1"), hover_color=("#1565C0", "#002171"), command=self._open_manual)
        self.manual_btn.pack(side="left", padx=10)
        
        self.status_label = ctk.CTkLabel(self.upload_zone, text="", text_color="gray", font=ctk.CTkFont(size=12))
        self.status_label.pack()

        # Documents Table area
        table_container = ctk.CTkFrame(self, corner_radius=15, fg_color=("gray95", "gray15"))
        table_container.pack(fill="both", expand=True, padx=40, pady=(0, 30))
        
        table_header_top = ctk.CTkFrame(table_container, fg_color="transparent")
        table_header_top.pack(fill="x", padx=20, pady=(15, 10))
        self.doc_count_label = ctk.CTkLabel(table_header_top, text="Uploaded Documents (0)", font=ctk.CTkFont(size=16, weight="bold"))
        self.doc_count_label.pack(side="left")
        ctk.CTkButton(table_header_top, text="Clear All", width=80, height=28, fg_color=("gray80", "gray30"), hover_color=("gray70", "gray20"), text_color=("black", "white"), command=self._clear_all).pack(side="right")
        ctk.CTkButton(table_header_top, text="Unanswered Questions", width=140, height=28, fg_color=("#F57C00", "#E65100"), hover_color=("#EF6C00", "#BF360C"), command=self._open_unanswered).pack(side="right", padx=(0, 10))
        
        # Columns
        col_frame = ctk.CTkFrame(table_container, fg_color=("gray85", "gray20"), corner_radius=8)
        col_frame.pack(fill="x", padx=(10, 26), pady=(0, 10))
        col_frame.grid_columnconfigure(0, weight=1)
        col_frame.grid_columnconfigure(1, minsize=250, weight=0)
        col_frame.grid_columnconfigure(2, minsize=200, weight=0)
        col_frame.grid_columnconfigure(3, minsize=100, weight=0)
        
        ctk.CTkLabel(col_frame, text="FILE NAME", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").grid(row=0, column=0, sticky="w", padx=15, pady=8)
        ctk.CTkLabel(col_frame, text="SIZE", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").grid(row=0, column=1, sticky="w", padx=10, pady=8)
        ctk.CTkLabel(col_frame, text="UPLOAD DATE", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").grid(row=0, column=2, sticky="w", padx=10, pady=8)
        ctk.CTkLabel(col_frame, text="ACTIONS", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").grid(row=0, column=3, sticky="e", padx=15, pady=8)
        
        self.entries_frame = ctk.CTkScrollableFrame(table_container, fg_color="transparent")
        self.entries_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self._refresh_entries()
        
    def _open_unanswered(self):
        UnansweredQuestionsWindow(self, self.controller)
        
    def _open_manual(self):
        ManualEntryWindow(self, self._refresh_entries)

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
            bg_color = ("gray95", "gray15") if i % 2 == 0 else ("gray90", "gray12")
            row = ctk.CTkFrame(self.entries_frame, corner_radius=0, fg_color=bg_color)
            row.pack(fill="x")
            
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, minsize=250, weight=0)
            row.grid_columnconfigure(2, minsize=200, weight=0)
            row.grid_columnconfigure(3, minsize=100, weight=0)
            
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
            ctk.CTkButton(action_frame, text="👁", width=30, height=30, fg_color="transparent", hover_color=("gray80", "gray30"), text_color=("black", "white"), command=lambda s=src: self._view_single(s)).pack(side="left", padx=(0, 5))
            ctk.CTkButton(action_frame, text="🗑", width=30, height=30, fg_color="transparent", hover_color=("gray80", "gray30"), text_color=("black", "white"), command=lambda s=src: self._delete_single(s)).pack(side="left")

    def _view_single(self, src):
        content = get_source_content(src)
        if not content:
            content = "No content found for this entry."
        ViewSourceWindow(self, src, content)

    def _delete_single(self, src):
        if messagebox.askyesno("Delete", f"Are you sure you want to delete '{src}'?"):
            delete_source(src)
            self._refresh_entries()

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

        self._make_menu_card(btn_container, "🤖", "Chat & Help", "Chat with AI and\nget automated assistance", 
                            lambda: controller.show_frame(ChatFrame)).grid(row=0, column=0, padx=20)

        self._make_menu_card(btn_container, "💡", "Info", "Learn more about the\napps capabilities", 
                            lambda: controller.show_frame(InfoFrame)).grid(row=0, column=1, padx=20)

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
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)

        self.sidebar = NavigationSidebar(self, controller, 
                                         new_chat_cmd=self.start_new_chat,
                                         load_session_cmd=self.load_session)
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="nsew")

        self.chat_area = ctk.CTkTextbox(self, font=ctk.CTkFont(size=14), state="disabled")
        self.chat_area.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="nsew")

        # Quick options frame
        self.options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.options_frame.grid(row=1, column=1, padx=20, pady=(10, 0), sticky="ew")
        self._populate_options()

        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=2, column=1, padx=20, pady=20, sticky="ew")
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

    def _populate_options(self):
        for w in self.options_frame.winfo_children(): w.destroy()
        
        options = ["How to Start a Chat", "Privacy & Data", "Managing Knowledge Base", "What models are supported?"]
        
        row_idx, col_idx, max_cols = 0, 0, 2
        for opt in options:
            btn = ctk.CTkButton(self.options_frame, text=opt, height=36, corner_radius=18,
                                fg_color="transparent", border_width=1, border_color="#0097A7",
                                text_color=("#0097A7", "#4DD0E1"), hover_color=("#E0F7FA", "#004D40"),
                                command=lambda o=opt: self._send_option(o))
            btn.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="ew")
            self.options_frame.grid_columnconfigure(col_idx, weight=1)
            
            col_idx += 1
            if col_idx >= max_cols:
                col_idx = 0
                row_idx += 1

    def _send_option(self, text):
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self._send()

    def start_new_chat(self):
        self.current_session_id = str(uuid.uuid4())
        self.chat_area.configure(state="normal")
        self.chat_area.delete("1.0", "end")
        self.chat_area.insert("end", "✨ New chat session started.\n\n", "italic")
        self.chat_area.insert("end", "Bot: ", "bold")
        self.chat_area.insert("end", "Hi, may I help you? You can choose an option below or type your question.\n\n")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")
        self.options_frame.grid()

    def load_session(self, session_id):
        self.options_frame.grid_remove()
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
        
        self.options_frame.grid_remove()
        
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
        
        if sys is None:
            # Fallback logic
            save_unanswered_question(prompt)
            fallback_msg = "Sorry, no answer found yet. We'll update this soon."
            self.controller.after(0, lambda: (
                self.chat_area.configure(state="normal"),
                self.chat_area.insert("end", "Bot: ", "bold"),
                self.chat_area.insert("end", fallback_msg + "\n\n"),
                self.chat_area.see("end"),
                self.chat_area.configure(state="disabled"),
                self.send_btn.configure(state="normal"),
                self.stop_btn.configure(state="disabled")
            ))
            save_message(self.controller.username, self.current_session_id, prompt, fallback_msg)
            self.controller.after(0, lambda: self.sidebar.refresh_sessions())
            if is_first_msg:
                threading.Thread(target=self._generate_catchy_title, args=(prompt,), daemon=True).start()
            return
            
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
            for F in (HomeFrame, ChatFrame, InfoFrame):
                frame = F(self.container, self)
                self.frames[F] = frame
                frame.grid(row=0, column=0, sticky="nsew")
            self.show_frame(HomeFrame)

    def show_frame(self, frame_class):
        frame = self.frames[frame_class]
        if hasattr(frame, "sidebar"):
            frame.sidebar.refresh_sessions()
            
        if frame_class == ChatFrame and getattr(frame, "current_session_id", None) is None:
            frame.start_new_chat()
            
        frame.tkraise()

    def _logout(self):
        from login import LoginWindow
        self.destroy(); LoginWindow().mainloop()
