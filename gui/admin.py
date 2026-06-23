"""Admin dashboard frame."""
import os
import re
import datetime
import threading
import customtkinter as ctk
from tkinter import messagebox

from auth import get_main_topics, get_sub_topics
from rag import (
    process_pdf, get_all_sources, delete_source, clear_rag,
    get_source_content, get_embed_model_warning,
)
from gui.processing import ProcessingWindow
from gui.dialogs import ManualEntryWindow, ViewSourceWindow, UnansweredQuestionsWindow
from gui.admin_embedded import EmbeddedAIBuilderFrame, EmbeddedManageTopicsFrame
from gui.scroll_utils import setup_smooth_scroll

DOCUMENT_SORT_OPTIONS = (
    ("Newest first", "date_desc"),
    ("Oldest first", "date_asc"),
    ("Name A-Z", "name_asc"),
    ("Name Z-A", "name_desc"),
    ("Largest first", "size_desc"),
    ("Smallest first", "size_asc"),
    ("PDFs first", "type_pdf"),
    ("Manual entries first", "type_manual"),
)

class AdminFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.doc_sort_mode = "date_desc"

        # Left Sidebar
        self.admin_sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("#0F0F12", "#09090B"))
        self.admin_sidebar.pack(side="left", fill="y")
        self.admin_sidebar.pack_propagate(False)

        # Purple left accent strip
        accent_strip = ctk.CTkFrame(self.admin_sidebar, width=4, corner_radius=0, fg_color="#8E24AA")
        accent_strip.pack(side="left", fill="y")

        # Sidebar content frame
        sidebar_content = ctk.CTkFrame(self.admin_sidebar, fg_color="transparent")
        sidebar_content.pack(side="left", fill="both", expand=True, padx=15, pady=20)

        # Branding titles
        logo_lbl = ctk.CTkLabel(
            sidebar_content, 
            text="AI Command", 
            font=ctk.CTkFont(size=24, weight="bold"), 
            text_color="#B388FF"
        )
        logo_lbl.pack(anchor="w", pady=(10, 0))

        sublogo_lbl = ctk.CTkLabel(
            sidebar_content, 
            text="Power User Console", 
            font=ctk.CTkFont(size=12, weight="bold"), 
            text_color="#FF8A65"
        )
        sublogo_lbl.pack(anchor="w", pady=(0, 30))

        # Helper to create menu buttons
        def create_menu_btn(parent, icon, text, is_active=False):
            fg = "transparent"
            border_w = 1 if is_active else 0
            border_c = "#B388FF" if is_active else None
            text_c = "white" if is_active else "#A1A1AA"
            hover_c = ("gray85", "#1E1E24")
            
            btn = ctk.CTkButton(
                parent,
                text=f"{icon}  {text}",
                font=ctk.CTkFont(size=14, weight="bold" if is_active else "normal"),
                anchor="w",
                height=40,
                corner_radius=8,
                fg_color=fg,
                border_width=border_w,
                border_color=border_c,
                text_color=text_c,
                hover_color=hover_c,
                command=lambda t=text: self.show_view(t)
            )
            return btn

        # Menu Buttons (In the exact layout requested)
        btn_manage = create_menu_btn(sidebar_content, "⚙️", "Dashboard", is_active=True)
        btn_manage.pack(fill="x", pady=6)

        btn_builder = create_menu_btn(sidebar_content, "✨", "Topic Builder", is_active=False)
        btn_builder.pack(fill="x", pady=6)

        btn_topic = create_menu_btn(sidebar_content, "📋", "Manage Topic", is_active=False)
        btn_topic.pack(fill="x", pady=6)

        btn_library = create_menu_btn(sidebar_content, "📂", "Library", is_active=False)
        btn_library.pack(fill="x", pady=6)

        self.menu_buttons = {
            "Dashboard": btn_manage,
            "Topic Builder": btn_builder,
            "Manage Topic": btn_topic,
            "Library": btn_library
        }

        # Bottom sidebar container (for theme and logout)
        bottom_sidebar_container = ctk.CTkFrame(sidebar_content, fg_color="transparent")
        bottom_sidebar_container.pack(side="bottom", fill="x", pady=(0, 10))

        appearance_lbl = ctk.CTkLabel(
            bottom_sidebar_container, 
            text="Appearance:", 
            font=ctk.CTkFont(size=11, weight="bold"), 
            text_color="#71717A"
        )
        appearance_lbl.pack(anchor="w", pady=(10, 2))

        self.appearance_menu = ctk.CTkOptionMenu(
            bottom_sidebar_container, 
            values=["Dark", "Light", "System"], 
            command=ctk.set_appearance_mode, 
            height=36,
            fg_color=("#374151", "#1E1E24"),
            button_color=("#4B5563", "#27272A"),
            button_hover_color=("#6B7280", "#3F3F46")
        )
        self.appearance_menu.pack(fill="x", pady=(0, 15))
        self.appearance_menu.set("Dark")

        preview_btn = ctk.CTkButton(
            bottom_sidebar_container,
            text="👁  Preview User Chat",
            height=38,
            font=ctk.CTkFont(weight="bold", size=13),
            fg_color=("#1565C0", "#0D47A1"),
            hover_color=("#1976D2", "#1565C0"),
            command=self.controller.enter_admin_user_preview,
        )
        preview_btn.pack(fill="x", pady=(0, 10))

        logout_btn = ctk.CTkButton(
            bottom_sidebar_container, 
            text="⇠  Logout", 
            height=38, 
            font=ctk.CTkFont(weight="bold", size=13),
            fg_color=("#D32F2F", "#B71C1C"), 
            hover_color=("#FF1744", "#C62828"), 
            command=self.controller._logout
        )
        logout_btn.pack(fill="x", pady=(0, 10))

        # Main Container Frame
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(side="right", fill="both", expand=True)

        # Title & Buttons Header Section inside self.main_container (with beautiful top padding)
        title_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        title_frame.pack(fill="x", padx=40, pady=(25, 20))
        self.title_frame = title_frame
        
        # Centered Container for Title, Subtitle and Buttons
        title_center_container = ctk.CTkFrame(title_frame, fg_color="transparent")
        title_center_container.pack(anchor="center")
        
        title_lbl = ctk.CTkLabel(
            title_center_container, 
            text="Knowledge Base Management", 
            font=ctk.CTkFont(size=30, weight="bold"), 
            text_color=("gray20", "white"),
            justify="center"
        )
        title_lbl.pack(anchor="center")
        
        subtitle_lbl = ctk.CTkLabel(
            title_center_container, 
            text="Upload and manage PDF documents to power the AI responses.", 
            font=ctk.CTkFont(size=13), 
            text_color=("#4B5563", "#A1A1AA"),
            justify="center"
        )
        subtitle_lbl.pack(anchor="center", pady=(4, 15))
        
        # Centered Inline Buttons
        title_right = ctk.CTkFrame(title_center_container, fg_color="transparent")
        title_right.pack(anchor="center", pady=(0, 5))
        
        self.upload_btn = ctk.CTkButton(
            title_right, 
            text="📥 Upload PDF", 
            font=ctk.CTkFont(weight="bold", size=13), 
            height=38, 
            fg_color=("#0097A7", "#006064"), 
            hover_color=("#00838F", "#004D40"), 
            command=self._upload_pdf
        )
        self.upload_btn.pack(side="left", padx=8)
        
        self.manual_btn = ctk.CTkButton(
            title_right, 
            text="➕ Add Manually", 
            font=ctk.CTkFont(weight="bold", size=13), 
            height=38, 
            fg_color=("#1976D2", "#0D47A1"), 
            hover_color=("#1565C0", "#002171"), 
            command=self._open_manual
        )
        self.manual_btn.pack(side="left", padx=8)
        
        self.builder_btn = ctk.CTkButton(
            title_right, 
            text="✨ Topic Builder", 
            font=ctk.CTkFont(weight="bold", size=13), 
            height=38, 
            fg_color=("#8E24AA", "#6A1B9A"), 
            hover_color=("#7B1FA2", "#4A148C"), 
            command=lambda: self.show_view("Topic Builder")
        )
        self.builder_btn.pack(side="left", padx=8)
        
        self.manage_topics_btn = ctk.CTkButton(
            title_right, 
            text="🖧 Manage Topics", 
            font=ctk.CTkFont(weight="bold", size=13), 
            height=38, 
            fg_color=("#F57C00", "#E65100"), 
            hover_color=("#EF6C00", "#BF360C"), 
            command=lambda: self.show_view("Manage Topic")
        )
        self.manage_topics_btn.pack(side="left", padx=8)
        
        # Keep status_label defined but not packed to prevent crash on configuration
        self.status_label = ctk.CTkLabel(self.main_container, text="", text_color="gray", font=ctk.CTkFont(size=12))

        # Insights Panel container inside self.main_container
        self.insights_panel = ctk.CTkFrame(self.main_container, fg_color="transparent")

        # Documents Table area inside self.main_container
        table_container = ctk.CTkFrame(self.main_container, corner_radius=15, fg_color=("gray95", "gray15"))
        table_container.pack(fill="both", expand=True, padx=40, pady=(0, 30))
        self.table_container = table_container
        
        table_header_top = ctk.CTkFrame(table_container, fg_color="transparent")
        table_header_top.pack(fill="x", padx=20, pady=(15, 10))
        
        self.doc_count_label = ctk.CTkLabel(table_header_top, text="Uploaded Documents (0)", font=ctk.CTkFont(size=18, weight="bold"), text_color=("gray20", "white"))
        self.doc_count_label.pack(side="left")

        sort_labels = [label for label, _ in DOCUMENT_SORT_OPTIONS]
        self._sort_label_to_mode = {label: mode for label, mode in DOCUMENT_SORT_OPTIONS}
        self._sort_mode_to_label = {mode: label for label, mode in DOCUMENT_SORT_OPTIONS}

        sort_controls = ctk.CTkFrame(table_header_top, fg_color="transparent")
        sort_controls.pack(side="left", padx=(20, 0))

        ctk.CTkLabel(
            sort_controls,
            text="Sort by:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#4B5563", "#A1A1AA"),
        ).pack(side="left", padx=(0, 8))

        self.doc_sort_menu = ctk.CTkOptionMenu(
            sort_controls,
            values=sort_labels,
            width=170,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=("#E5E7EB", "#27272A"),
            button_color=("#D1D5DB", "#3F3F46"),
            button_hover_color=("#9CA3AF", "#52525B"),
            command=self._on_sort_change,
        )
        self.doc_sort_menu.set(self._sort_mode_to_label["date_desc"])
        self.doc_sort_menu.pack(side="left")
        
        self.clear_all_btn = ctk.CTkButton(
            table_header_top, 
            text="🗑 Clear All", 
            width=90, 
            height=32, 
            font=ctk.CTkFont(size=12, weight="bold"), 
            fg_color=("#374151", "#27272A"), 
            hover_color=("#4B5563", "#3F3F46"), 
            text_color="#D1D5DB", 
            command=self._clear_all
        )
        self.clear_all_btn.pack(side="right")
        
        self.unanswered_btn = ctk.CTkButton(
            table_header_top, 
            text="⚠ Unanswered Questions", 
            width=170, 
            height=32, 
            font=ctk.CTkFont(size=12, weight="bold"), 
            fg_color=("#FFCCBC", "#FF8A65"), 
            hover_color=("#FFAB91", "#FF7043"), 
            text_color="#1E1E1E", 
            command=self._open_unanswered
        )
        self.unanswered_btn.pack(side="right", padx=(0, 10))
        
        
        self.col_frame = ctk.CTkFrame(table_container, fg_color=("gray85", "gray20"), corner_radius=8)
        self.col_frame.pack(fill="x", padx=(15, 37), pady=(0, 10))
        self.col_frame.grid_columnconfigure(0, weight=1)
        self.col_frame.grid_columnconfigure(1, minsize=200, weight=0)
        self.col_frame.grid_columnconfigure(2, minsize=200, weight=0)
        self.col_frame.grid_columnconfigure(3, minsize=120, weight=0)
        
        ctk.CTkLabel(self.col_frame, text="🖧 FILE NAME", font=ctk.CTkFont(size=10, weight="bold"), text_color=("#4B5563", "#A1A1AA")).grid(row=0, column=0, sticky="w", padx=15, pady=6)
        ctk.CTkLabel(self.col_frame, text="SIZE", font=ctk.CTkFont(size=10, weight="bold"), text_color=("#4B5563", "#A1A1AA")).grid(row=0, column=1, sticky="w", padx=10, pady=6)
        ctk.CTkLabel(self.col_frame, text="UPLOAD DATE", font=ctk.CTkFont(size=10, weight="bold"), text_color=("#4B5563", "#A1A1AA")).grid(row=0, column=2, sticky="w", padx=10, pady=6)
        ctk.CTkLabel(self.col_frame, text="ACTIONS", font=ctk.CTkFont(size=10, weight="bold"), text_color=("#4B5563", "#A1A1AA")).grid(row=0, column=3, sticky="e", padx=15, pady=6)
        
        self.entries_frame = ctk.CTkScrollableFrame(table_container, fg_color="transparent")
        self.entries_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        setup_smooth_scroll(
            self.entries_frame,
            hover_widgets=(table_container, self.col_frame),
        )
        self.entries_frame.bind("<Configure>", lambda event: self._align_header_action())
        
        self.show_view("Dashboard")

    def show_view(self, name):
        # Update active highlight styling on all buttons
        for btn_name, btn in self.menu_buttons.items():
            is_active = (btn_name == name)
            btn.configure(
                border_width=1 if is_active else 0,
                border_color="#B388FF",
                text_color="white" if is_active else "#A1A1AA",
                font=ctk.CTkFont(size=14, weight="bold" if is_active else "normal")
            )
            
        # Hide all components
        self.title_frame.pack_forget()
        self.table_container.pack_forget()
        self.status_label.pack_forget()
        
        if hasattr(self, 'ai_builder_view'):
            self.ai_builder_view.pack_forget()
        if hasattr(self, 'manage_topics_view'):
            self.manage_topics_view.pack_forget()
        if hasattr(self, 'insights_panel'):
            self.insights_panel.pack_forget()
            
        # Route to active view
        if name == "Dashboard":
            self.title_frame.pack(fill="x", padx=40, pady=(25, 20))
            self._refresh_insights_panel()
            self.insights_panel.pack(fill="x", padx=40, pady=(0, 10))
            self.table_container.pack(fill="both", expand=True, padx=40, pady=(0, 30))
            self.status_label.pack(pady=5)
            self._refresh_entries()
            
        elif name == "Library":
            # Library displays ONLY the documents table (hiding the header title frame)
            self.table_container.pack(fill="both", expand=True, padx=40, pady=(30, 30))
            self._refresh_entries()
            
        elif name == "Topic Builder":
            if not hasattr(self, 'ai_builder_view'):
                self.ai_builder_view = EmbeddedAIBuilderFrame(self.main_container, self)
            self.ai_builder_view.pack(fill="both", expand=True, padx=40, pady=30)
            self.ai_builder_view._reset_view()
            
        elif name == "Manage Topic":
            if not hasattr(self, 'manage_topics_view'):
                self.manage_topics_view = EmbeddedManageTopicsFrame(self.main_container, self.controller, self)
            self.manage_topics_view.pack(fill="both", expand=True, padx=40, pady=30)
            self.manage_topics_view._refresh()

    def _open_unanswered(self):
        UnansweredQuestionsWindow(self, self.controller)
        
    def _open_manual(self):
        ManualEntryWindow(self, self._refresh_entries)
        
    def _open_topic_builder(self):
        self.show_view("Topic Builder")

    def _open_manage_topics(self):
        self.show_view("Manage Topic")

    def _upload_pdf(self):
        file_path = ctk.filedialog.askopenfilename(parent=self, filetypes=[("PDF Files", "*.pdf")])
        if not file_path: return
        
        if hasattr(self, 'upload_btn') and self.upload_btn:
            self.upload_btn.configure(state="disabled")
        self.status_label.configure(text=f"Reading & Embedding: {os.path.basename(file_path)}...", text_color="gray")
        
        def on_cancel():
            if hasattr(self, 'upload_btn') and self.upload_btn:
                self.upload_btn.configure(state="normal")
            self.status_label.configure(text="Upload cancelled by user.", text_color="orange")
            self.processing_win = None
            
        self.processing_win = ProcessingWindow(
            self, 
            title="Uploading PDF", 
            message=f"Processing {os.path.basename(file_path)}", 
            show_progress=True,
            on_cancel=on_cancel
        )
        
        def task():
            current_win = self.processing_win
            def progress(current, total):
                if current_win is None or current_win.is_cancelled:
                    return False
                self.controller.after(0, lambda: current_win.update_progress(current, total) if (current_win and not current_win.is_cancelled) else None)
                return True
                
            ok, msg = process_pdf(file_path, progress_callback=progress)
            
            # If the user cancelled during processing, discard results immediately without running callbacks
            if current_win is None or current_win.is_cancelled:
                return
                
            self.controller.after(0, lambda: self._upload_complete(ok, msg))
            
        threading.Thread(target=task, daemon=True).start()
        
    def _upload_complete(self, ok, msg):
        if hasattr(self, 'processing_win') and self.processing_win:
            self.processing_win.finish()
            self.processing_win = None
            
        if hasattr(self, 'upload_btn') and self.upload_btn:
            self.upload_btn.configure(state="normal")
            
        if ok:
            self.status_label.configure(text=msg, text_color="#4CAF50")
            self._refresh_entries()
            success_msg = "Document successfully processed into the Knowledge Base!"
            embed_warn = get_embed_model_warning()
            if embed_warn:
                success_msg += f"\n\nNote: {embed_warn}"
            messagebox.showinfo("Success", success_msg)
        else:
            self.status_label.configure(text=msg, text_color="#FF6B6B")
            messagebox.showerror("Error", msg)

    def _on_sort_change(self, selected_label: str):
        self.doc_sort_mode = self._sort_label_to_mode.get(selected_label, "date_desc")
        self._refresh_entries()

    def _parse_document_added_at(self, meta: dict) -> datetime.datetime:
        added_at = meta.get("added_at")
        if added_at:
            try:
                return datetime.datetime.fromisoformat(added_at)
            except ValueError:
                pass
        date_str = meta.get("date", "")
        try:
            return datetime.datetime.strptime(date_str, "%b %d, %Y")
        except ValueError:
            return datetime.datetime.min

    def _parse_document_size_mb(self, meta: dict, src: str) -> float:
        if src.startswith("Manual:"):
            return -1.0
        size = meta.get("size", "")
        match = re.search(r"([\d.]+)", size)
        if not match:
            return 0.0
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0

    def _sort_sources(self, sources_info: list[tuple[str, dict]]) -> list[tuple[str, dict]]:
        mode = self.doc_sort_mode

        if mode == "date_desc":
            return sorted(
                sources_info,
                key=lambda item: (self._parse_document_added_at(item[1]), item[0].lower()),
                reverse=True,
            )
        if mode == "date_asc":
            return sorted(
                sources_info,
                key=lambda item: (self._parse_document_added_at(item[1]), item[0].lower()),
            )
        if mode == "name_asc":
            return sorted(sources_info, key=lambda item: item[0].lower())
        if mode == "name_desc":
            return sorted(sources_info, key=lambda item: item[0].lower(), reverse=True)
        if mode == "size_desc":
            return sorted(
                sources_info,
                key=lambda item: (self._parse_document_size_mb(item[1], item[0]), item[0].lower()),
                reverse=True,
            )
        if mode == "size_asc":
            return sorted(
                sources_info,
                key=lambda item: (self._parse_document_size_mb(item[1], item[0]), item[0].lower()),
            )
        if mode == "type_pdf":
            return sorted(sources_info, key=lambda item: (item[0].startswith("Manual:"), item[0].lower()))
        if mode == "type_manual":
            return sorted(sources_info, key=lambda item: (not item[0].startswith("Manual:"), item[0].lower()))
        return sources_info

    def _refresh_entries(self):
        for w in self.entries_frame.winfo_children(): w.destroy()
        sources_info = self._sort_sources(get_all_sources())
        self.doc_count_label.configure(text=f"Uploaded Documents ({len(sources_info)})")
        
        if not sources_info:
            ctk.CTkLabel(self.entries_frame, text="No documents found.", text_color="gray").pack(pady=40)
            return
            
        for i, (src, meta) in enumerate(sources_info):
            row = ctk.CTkFrame(
                self.entries_frame, 
                corner_radius=10, 
                border_width=1, 
                border_color=("gray80", "#232329"), 
                fg_color=("gray95", "#16161a")
            )
            row.pack(fill="x", pady=6, padx=5)
            
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, minsize=200, weight=0)
            row.grid_columnconfigure(2, minsize=200, weight=0)
            row.grid_columnconfigure(3, minsize=120, weight=0)
            
            name_frame = ctk.CTkFrame(row, fg_color="transparent")
            name_frame.grid(row=0, column=0, sticky="w", padx=15, pady=10)
            
            is_manual = src.startswith("Manual:")
            
            if is_manual:
                icon_frame = ctk.CTkFrame(name_frame, width=36, height=36, corner_radius=8, fg_color=("#E0F2F1", "#102624"))
                icon_frame.pack_propagate(False)
                icon_frame.pack(side="left", padx=(0, 12))
                ctk.CTkLabel(icon_frame, text="📝", font=ctk.CTkFont(size=16)).pack(expand=True)
                
                badge_text = "MANUAL ENTRY"
            else:
                icon_frame = ctk.CTkFrame(name_frame, width=36, height=36, corner_radius=8, fg_color=("#FFEBEE", "#2E1618"))
                icon_frame.pack_propagate(False)
                icon_frame.pack(side="left", padx=(0, 12))
                ctk.CTkLabel(icon_frame, text="📄", font=ctk.CTkFont(size=16)).pack(expand=True)
                
                if "complex" in src.lower():
                    badge_text = "OCR ACTIVE"
                else:
                    badge_text = "VECTOR OPTIMIZED"
            
            text_container = ctk.CTkFrame(name_frame, fg_color="transparent")
            text_container.pack(side="left", fill="both")
            
            name_lbl = ctk.CTkLabel(text_container, text=src, font=ctk.CTkFont(size=13, weight="bold"), text_color=("black", "white"))
            name_lbl.pack(anchor="w")
            
            badge_frame = ctk.CTkFrame(text_container, corner_radius=4, fg_color=("gray90", "#212124"), border_width=1, border_color=("gray80", "#2D2D30"))
            badge_frame.pack(anchor="w", pady=(2, 0))
            badge_lbl = ctk.CTkLabel(badge_frame, text=badge_text, font=ctk.CTkFont(size=8, weight="bold"), text_color=("#555555", "#A1A1AA"))
            badge_lbl.pack(padx=6, pady=1)
            
            size_val = "Manual Entry" if is_manual else meta.get("size", "Unknown")
            ctk.CTkLabel(row, text=size_val, font=ctk.CTkFont(size=12, weight="bold"), text_color=("gray30", "#A1A1AA")).grid(row=0, column=1, sticky="w", padx=10)
            
            ctk.CTkLabel(row, text=meta.get("date", "Unknown"), font=ctk.CTkFont(size=12), text_color=("gray40", "#71717A")).grid(row=0, column=2, sticky="w", padx=10)
            
            action_frame = ctk.CTkFrame(row, fg_color="transparent")
            action_frame.grid(row=0, column=3, sticky="e", padx=15)
            
            view_btn = ctk.CTkButton(
                action_frame, 
                text="👁", 
                width=32, 
                height=32, 
                corner_radius=16, 
                fg_color="transparent", 
                hover_color=("gray85", "#27272A"), 
                text_color=("gray30", "#A1A1AA"), 
                font=ctk.CTkFont(size=15), 
                command=lambda s=src: self._view_single(s)
            )
            view_btn.pack(side="left", padx=(0, 6))
            
            delete_btn = ctk.CTkButton(
                action_frame, 
                text="🗑", 
                width=32, 
                height=32, 
                corner_radius=16, 
                fg_color="transparent", 
                hover_color=("#FFEBEE", "#3C1F22"), 
                text_color=("#D32F2F", "#EF5350"), 
                font=ctk.CTkFont(size=15), 
                command=lambda s=src: self._delete_single(s)
            )
            delete_btn.pack(side="left")
            
        self.after(50, self._align_header_action)
        self.after(150, self._align_header_action)

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

    def _align_header_action(self, event=None):
        children = self.entries_frame.winfo_children()
        row_card = None
        for child in children:
            if isinstance(child, ctk.CTkFrame):
                row_card = child
                break
        if row_card:
            self._align_header(row_card)

    def _align_header(self, row):
        row.update_idletasks()
        row_width = row.winfo_width()
        table_container = self.entries_frame.master
        container_width = table_container.winfo_width()
        
        if row_width > 1 and container_width > 1:
            scale = 1.0
            if hasattr(self.col_frame, "_get_widget_scaling"):
                scale = self.col_frame._get_widget_scaling()
            elif hasattr(self.col_frame, "_scaling_coefficient"):
                scale = self.col_frame._scaling_coefficient
            # col_frame has left padding of 15 (virtual), which scales to 15 * scale physical pixels.
            # Calculate physical right padding: container_width - left_pad_physical - row_width
            right_pad_physical = container_width - (15 * scale) - row_width
            right_pad_virtual = int(right_pad_physical / scale)
            
            # Bound the calculated value to a sane range to prevent layout collapse
            if 10 <= right_pad_virtual <= 100:
                current_padx = self.col_frame.pack_info().get("padx", (15, 37))
                if isinstance(current_padx, (tuple, list)):
                    current_right = int(current_padx[1])
                else:
                    current_right = int(current_padx)
                
                if current_right != right_pad_virtual:
                    self.col_frame.pack_configure(padx=(15, right_pad_virtual))

    def _refresh_insights_panel(self):
        for w in self.insights_panel.winfo_children():
            w.destroy()
            
        from rag import get_all_sources, get_unanswered_questions
        sources = get_all_sources()
        unanswered = get_unanswered_questions()
        topics = get_main_topics()
        
        subtopics_count = 0
        for t in topics:
            subtopics_count += len(get_sub_topics(t['id']))
            
        self.insights_panel.grid_columnconfigure((0, 1, 2), weight=1, uniform="equal")
        
        doc_card = ctk.CTkFrame(self.insights_panel, corner_radius=12, fg_color=("#E8F5E9", "#1B5E20"))
        doc_card.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(doc_card, text="📁", font=ctk.CTkFont(size=40)).pack(pady=(15, 5))
        ctk.CTkLabel(doc_card, text="Total Documents", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#2E7D32", "#A5D6A7")).pack()
        ctk.CTkLabel(doc_card, text=str(len(sources)), font=ctk.CTkFont(size=24, weight="bold"), text_color=("#1B5E20", "white")).pack(pady=(5, 15))
        
        topic_card = ctk.CTkFrame(self.insights_panel, corner_radius=12, fg_color=("#E3F2FD", "#0D47A1"))
        topic_card.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(topic_card, text="📋", font=ctk.CTkFont(size=40)).pack(pady=(15, 5))
        ctk.CTkLabel(topic_card, text="Topics (Sub-topics)", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#1565C0", "#90CAF9")).pack()
        ctk.CTkLabel(topic_card, text=f"{len(topics)} ({subtopics_count})", font=ctk.CTkFont(size=24, weight="bold"), text_color=("#0D47A1", "white")).pack(pady=(5, 15))
        
        unans_card = ctk.CTkFrame(self.insights_panel, corner_radius=12, fg_color=("#FBE9E7", "#BF360C"))
        unans_card.grid(row=0, column=2, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(unans_card, text="❓", font=ctk.CTkFont(size=40)).pack(pady=(15, 5))
        ctk.CTkLabel(unans_card, text="Unanswered Questions", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#D84315", "#FFAB91")).pack()
        ctk.CTkLabel(unans_card, text=str(len(unanswered)), font=ctk.CTkFont(size=24, weight="bold"), text_color=("#BF360C", "white")).pack(pady=(5, 15))

        embed_warn = get_embed_model_warning()
        if embed_warn:
            warn_frame = ctk.CTkFrame(self.insights_panel, corner_radius=8, fg_color=("#FFF3E0", "#4E342E"))
            warn_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="ew")
            ctk.CTkLabel(
                warn_frame,
                text=f"⚠ {embed_warn}",
                font=ctk.CTkFont(size=12),
                text_color=("#E65100", "#FFCC80"),
                wraplength=900,
                justify="left",
            ).pack(padx=15, pady=10, anchor="w")

