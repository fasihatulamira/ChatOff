"""Admin/user dialog windows."""
import threading
import customtkinter as ctk
from tkinter import messagebox

from gui.processing import ProcessingWindow
from gui.scroll_utils import setup_smooth_scroll
from rag import add_manual_entry

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
        except Exception:
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
        
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", height=40, width=120, fg_color="transparent", border_width=1, border_color=("#B0B0B0", "#52525B"), text_color=("#1A1A1E", "#E4E4E7"), hover_color=("#E5E7EB", "#27272A"), command=self.destroy)
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
        
        self.processing_win = ProcessingWindow(
            self, 
            title="Saving Entry", 
            message="Generating embeddings & saving..."
        )
        
        def task():
            ok, msg = add_manual_entry(title, question, answer)
            self.after(0, lambda: self._on_save_complete(ok, msg))
            
        threading.Thread(target=task, daemon=True).start()
        
    def _on_save_complete(self, ok, msg):
        if hasattr(self, 'processing_win') and self.processing_win:
            self.processing_win.finish()
            self.processing_win = None
            
        if ok:
            self.on_success_callback()
            messagebox.showinfo("Success", "Knowledge entry saved successfully!")
            self.destroy()
        else:
            self.status_label.configure(text=msg, text_color="#FF6B6B")
            messagebox.showerror("Error", msg)


class ViewSourceWindow(ctk.CTkToplevel):
    def __init__(self, parent, source_name, content):
        super().__init__(parent)
        self.title(f"Viewing: {source_name}")
        self.geometry("800x600")
        self.grab_set()

        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (800 // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (600 // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header,
            text=source_name,
            font=ctk.CTkFont(size=18, weight="bold"),
            wraplength=720,
            justify="left",
        ).pack(side="left", anchor="w")

        close_btn = ctk.CTkButton(header, text="Close", width=80, command=self.destroy)
        close_btn.pack(side="right")

        self.content_box = ctk.CTkTextbox(self, font=ctk.CTkFont(size=13), wrap="word")
        self.content_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.content_box.insert("1.0", content or "No content found for this entry.")
        self.content_box.configure(state="disabled")


class AnswerQuestionDialog(ctk.CTkToplevel):
    def __init__(self, parent, question_id, question_text, current_answer="", on_save=None):
        super().__init__(parent)
        self.title("Provide Answer")
        self.geometry("600x450")
        self.grab_set()
        self.on_save = on_save
        self.question_id = question_id
        
        # Center window
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (600 // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (450 // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass
            
        ctk.CTkLabel(self, text="📝 Answer Question", font=ctk.CTkFont(size=20, weight="bold"), text_color="#B388FF").pack(pady=(20, 10), padx=25, anchor="w")
        
        # Question Display
        q_frame = ctk.CTkFrame(self, fg_color=("gray90", "gray10"), corner_radius=8)
        q_frame.pack(fill="x", padx=25, pady=5)
        
        ctk.CTkLabel(q_frame, text="QUESTION:", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").pack(anchor="w", padx=15, pady=(8, 2))
        ctk.CTkLabel(q_frame, text=question_text, font=ctk.CTkFont(size=13, weight="bold"), wraplength=520, justify="left").pack(anchor="w", padx=15, pady=(0, 10))
        
        # Answer Box
        ctk.CTkLabel(self, text="YOUR ANSWER:", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").pack(anchor="w", padx=25, pady=(15, 2))
        self.answer_box = ctk.CTkTextbox(self, height=180, font=ctk.CTkFont(size=13))
        self.answer_box.pack(fill="both", expand=True, padx=25, pady=(0, 20))
        self.answer_box.insert("1.0", current_answer)
        
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=(0, 20))
        
        save_btn = ctk.CTkButton(
            btn_frame, 
            text="Save & Learn", 
            font=ctk.CTkFont(weight="bold"),
            height=36,
            fg_color=("#388E3C", "#2E7D32"), 
            hover_color=("#2E7D32", "#1B5E20"),
            command=self._save
        )
        save_btn.pack(side="right", padx=(10, 0))
        
        cancel_btn = ctk.CTkButton(
            btn_frame, 
            text="Cancel", 
            height=36,
            fg_color="transparent", 
            border_width=1, 
            border_color=("#B0B0B0", "#52525B"), 
            text_color=("#1A1A1E", "#E4E4E7"), 
            hover_color=("#E5E7EB", "#27272A"),
            command=self.destroy
        )
        cancel_btn.pack(side="right")
        
    def _save(self):
        answer = self.answer_box.get("1.0", "end-1c").strip()
        if not answer:
            messagebox.showwarning("Validation Error", "Please provide a valid answer!")
            return
            
        self.processing_win = ProcessingWindow(
            self, 
            title="Saving Answer", 
            message="Generating embedding & learning..."
        )
        
        def task():
            from rag import submit_admin_answer
            submit_admin_answer(self.question_id, answer)
            self.after(0, self._on_save_complete)
            
        threading.Thread(target=task, daemon=True).start()
        
    def _on_save_complete(self):
        if hasattr(self, 'processing_win') and self.processing_win:
            self.processing_win.finish()
            self.processing_win = None
            
        if self.on_save:
            self.on_save()
            
        messagebox.showinfo("Success", "Answer saved successfully! The AI has learned this response.")
        self.destroy()


class UnansweredQuestionsWindow(ctk.CTkToplevel):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.title("Questions Management & Learning Console")
        self.geometry("900x650")
        self.grab_set()
        self.parent = parent
        self.controller = controller
        
        # Center the window
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (900 // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (650 // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass
            
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(20, 10))
        
        title_label = ctk.CTkLabel(header, text="❓ Questions Management Console", font=ctk.CTkFont(size=22, weight="bold"), text_color="#FF8A65")
        title_label.pack(side="left")
        
        # Search & Filter Toolbar
        toolbar = ctk.CTkFrame(self, fg_color=("gray90", "gray15"), corner_radius=10)
        toolbar.pack(fill="x", padx=25, pady=(5, 15))
        
        ctk.CTkLabel(toolbar, text="🔍 Search:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(15, 5), pady=10)
        self.search_entry = ctk.CTkEntry(toolbar, placeholder_text="Type to search questions...", width=280, height=32)
        self.search_entry.pack(side="left", padx=(0, 20), pady=10)
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh())
        
        ctk.CTkLabel(toolbar, text="🎯 Status:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 5), pady=10)
        self.filter_menu = ctk.CTkOptionMenu(
            toolbar, 
            values=["All", "Unanswered", "Answered"], 
            command=lambda v: self._refresh(),
            width=140,
            height=32,
            fg_color=("#374151", "#27272A"),
            button_color=("#4B5563", "#1E1E24")
        )
        self.filter_menu.pack(side="left", pady=10)
        self.filter_menu.set("All")
        
        # Scrollable area
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=25, pady=(0, 20))
        setup_smooth_scroll(self.scroll, hover_widgets=(header,))
        
        self._refresh()

    def _refresh(self):
        for w in self.scroll.winfo_children(): w.destroy()
        from rag import get_unanswered_questions, delete_unanswered_question
        questions = get_unanswered_questions()
        
        # Filter logic
        search_query = self.search_entry.get().strip().lower()
        filter_status = self.filter_menu.get()
        
        filtered = []
        for q in questions:
            q_status = q.get("status", "unanswered")
            # Apply status filter
            if filter_status == "Unanswered" and q_status != "unanswered":
                continue
            if filter_status == "Answered" and q_status != "answered":
                continue
                
            # Apply search filter
            q_text = q["question"].lower()
            q_user = q.get("username", "anonymous").lower()
            q_ans = (q.get("answer") or "").lower()
            if search_query and (search_query not in q_text and search_query not in q_user and search_query not in q_ans):
                continue
                
            filtered.append(q)
            
        if not filtered:
            ctk.CTkLabel(self.scroll, text="No matching questions found.", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=50)
            return
            
        # Refresh parent AdminFrame view counters
        if hasattr(self.parent, "_refresh_entries"):
            self.parent._refresh_entries()
        if hasattr(self.parent, "insights_view") and self.parent.insights_view:
            self.parent.insights_view._refresh()

        def delete_and_refresh(q_id):
            if messagebox.askyesno("Delete", "Are you sure you want to dismiss/delete this question completely?"):
                delete_unanswered_question(q_id)
                self._refresh()

        def open_answer_dialog(q):
            AnswerQuestionDialog(
                self, 
                question_id=q["id"], 
                question_text=q["question"], 
                current_answer=q.get("answer") or "", 
                on_save=self._refresh
            )

        for q in filtered:
            is_answered = q.get("status") == "answered"
            
            row = ctk.CTkFrame(self.scroll, corner_radius=12, fg_color=("gray95", "gray12"), border_width=1, border_color=("gray85", "gray20"))
            row.pack(fill="x", pady=6, padx=2)
            
            # Left container: Meta, User, Question, and Answer (if available)
            left_col = ctk.CTkFrame(row, fg_color="transparent")
            left_col.pack(side="left", fill="both", expand=True, padx=15, pady=12)
            
            meta_row = ctk.CTkFrame(left_col, fg_color="transparent")
            meta_row.pack(fill="x", pady=(0, 6))
            
            # Status Badge
            status_text = "ANSWERED" if is_answered else "UNANSWERED"
            status_bg = ("#E8F5E9", "#2E7D32") if is_answered else ("#FBE9E7", "#D84315")
            status_fg = ("#2E7D32", "#A5D6A7") if is_answered else ("#D84315", "#FFAB91")
            
            badge_f = ctk.CTkFrame(meta_row, corner_radius=4, fg_color=status_bg)
            badge_f.pack(side="left")
            ctk.CTkLabel(badge_f, text=status_text, font=ctk.CTkFont(size=9, weight="bold"), text_color=status_fg).pack(padx=8, pady=2)
            
            # User Badge
            user_lbl = ctk.CTkLabel(meta_row, text=f"👤 Asked by: {q.get('username', 'Anonymous')}", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray")
            user_lbl.pack(side="left", padx=15)
            
            # Date
            date_lbl = ctk.CTkLabel(meta_row, text=q.get("date", ""), font=ctk.CTkFont(size=11), text_color="gray")
            date_lbl.pack(side="left")
            
            # Question Text
            q_lbl = ctk.CTkLabel(left_col, text=q["question"], font=ctk.CTkFont(size=14, weight="bold"), wraplength=600, justify="left")
            q_lbl.pack(anchor="w", pady=(2, 6))
            
            # Answer Display (if answered)
            if is_answered and q.get("answer"):
                ans_box = ctk.CTkFrame(left_col, fg_color=("gray90", "gray15"), corner_radius=8, border_width=1, border_color=("gray85", "gray20"))
                ans_box.pack(fill="x", pady=(4, 0))
                ctk.CTkLabel(ans_box, text="💡 Admin Answer:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#A5D6A7").pack(anchor="w", padx=10, pady=(6, 2))
                ctk.CTkLabel(ans_box, text=q["answer"], font=ctk.CTkFont(size=13), wraplength=580, justify="left").pack(anchor="w", padx=10, pady=(0, 8))
            
            # Right container: Actions
            right_col = ctk.CTkFrame(row, fg_color="transparent")
            right_col.pack(side="right", fill="y", padx=15, pady=12)
            
            action_text = "✏️ Edit Answer" if is_answered else "📝 Answer"
            action_btn = ctk.CTkButton(
                right_col,
                text=action_text,
                width=110,
                height=32,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=("#8E24AA", "#6A1B9A") if is_answered else ("#F57C00", "#E65100"),
                hover_color=("#7B1FA2", "#4A148C") if is_answered else ("#EF6C00", "#BF360C"),
                command=lambda question_item=q: open_answer_dialog(question_item)
            )
            action_btn.pack(side="left", padx=5)
            
            delete_btn = ctk.CTkButton(
                right_col, 
                text="🗑", 
                width=32, 
                height=32, 
                corner_radius=16, 
                fg_color="transparent", 
                hover_color=("#FFEBEE", "#3C1F22"), 
                text_color=("#D32F2F", "#EF5350"), 
                font=ctk.CTkFont(size=15), 
                command=lambda q_id=q["id"]: delete_and_refresh(q_id)
            )
            delete_btn.pack(side="right", padx=15, pady=10)
