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
    update_session_title, save_topic, get_main_topics, get_sub_topics,
    get_all_topics, delete_topic, update_topic, get_topic_by_id
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
#  AI TOPIC BUILDER WINDOW
# ─────────────────────────────────────────────
import json
import PyPDF2
class TopicBuilderWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("AI Topic Profile Builder")
        self.geometry("750x650")
        self.grab_set()
        
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (750 // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (650 // 2)
            self.geometry(f"+{x}+{y}")
        except:
            pass
            
        title_label = ctk.CTkLabel(self, text="✨ AI Topic Profile Builder", font=ctk.CTkFont(size=24, weight="bold"), text_color="#E040FB")
        title_label.pack(pady=(30, 10), padx=40, anchor="w")
        ctk.CTkLabel(self, text="Tell the AI what the topic is about, or load a PDF, and select the sub-topics to save.", text_color="gray").pack(padx=40, anchor="w", pady=(0,20))
        
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=40, pady=(0, 20))
        
        ctk.CTkLabel(self.main_frame, text="MAIN TOPIC NAME", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(anchor="w", pady=(0, 5))
        self.topic_entry = ctk.CTkEntry(self.main_frame, placeholder_text="e.g., Food", height=40)
        self.topic_entry.pack(fill="x", pady=(0, 20))
        
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(header_frame, text="KNOWLEDGE CONTEXT (Paste text or load PDF)", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(side="left")
        
        self.browse_btn = ctk.CTkButton(header_frame, text="Browse PDF", width=100, height=28, command=self._load_pdf, fg_color=("#0097A7", "#006064"))
        self.browse_btn.pack(side="right")
        
        self.content_box = ctk.CTkTextbox(self.main_frame, height=200, font=ctk.CTkFont(size=14))
        self.content_box.pack(fill="x", pady=(0, 20))
        self.content_box.insert("1.0", "e.g., The sub-topics should be Beverages, Main Course, and Desserts. Use this PDF text to base the answers on...")
        self.content_box.bind("<FocusIn>", self._clear_placeholder)
        
        self.btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.btn_frame.pack(fill="x", pady=(10, 0))
        
        self.status_label = ctk.CTkLabel(self.btn_frame, text="", text_color="gray")
        self.status_label.pack(side="left")
        
        self.publish_btn = ctk.CTkButton(self.btn_frame, text="✨ Auto-Generate", height=40, width=150, font=ctk.CTkFont(weight="bold"), fg_color=("#8E24AA", "#6A1B9A"), hover_color=("#7B1FA2", "#4A148C"), command=self._generate_subtopics)
        self.publish_btn.pack(side="right", padx=(10, 0))
        
        cancel_btn = ctk.CTkButton(self.btn_frame, text="Cancel", height=40, width=100, fg_color="transparent", border_width=1, command=self.destroy)
        cancel_btn.pack(side="right")

    def _load_pdf(self):
        file_path = ctk.filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not file_path: return
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted: text += extracted + "\n"
            self.content_box.delete("1.0", "end")
            self.content_box.insert("end", text)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read PDF: {e}")
        
    def _clear_placeholder(self, event):
        if "The sub-topics should be" in self.content_box.get("1.0", "end-1c"):
            self.content_box.delete("1.0", "end")
            
    def _generate_subtopics(self):
        topic_name = self.topic_entry.get().strip()
        content = self.content_box.get("1.0", "end-1c").strip()
        
        if not topic_name or not content or "The sub-topics should be" in content:
            self.status_label.configure(text="Please fill in both fields.", text_color="#FF6B6B")
            return
            
        self.status_label.configure(text="AI is analyzing and building...", text_color="#E040FB")
        self.publish_btn.configure(state="disabled")
        self.update_idletasks()
        
        def task():
            prompt = (
                f"You are an AI that structures conversation topics.\n"
                f"The user is creating a main topic called '{topic_name}'.\n"
                f"Based on the following content, extract the logical sub-topics.\n"
                f"For each sub-topic, write a helpful reply message that the bot should say when the user clicks it.\n"
                f"Respond ONLY with a valid JSON array like [{{\"topic_name\": \"...\", \"reply_message\": \"...\"}}]. Do not write any markdown code blocks or extra text.\n\n"
                f"Content: {content}"
            )
            
            try:
                # get_response from chatbot.py yields text
                gen = get_response(prompt, "llama3", system_prompt="You only output raw JSON arrays.")
                ai_output = "".join(list(gen)).strip()
                
                # Clean up if AI hallucinates markdown
                if ai_output.startswith("```json"): ai_output = ai_output[7:]
                if ai_output.startswith("```"): ai_output = ai_output[3:]
                if ai_output.endswith("```"): ai_output = ai_output[:-3]
                    
                subtopics = json.loads(ai_output)
                if not isinstance(subtopics, list): raise ValueError("AI did not return a list.")
                
                self.generated_subtopics = subtopics
                self.main_topic_name = topic_name
                self.after(0, lambda: self._show_checkboxes())
                
            except Exception as e:
                self.after(0, lambda e=e: self._on_fail(str(e)))
                
        threading.Thread(target=task, daemon=True).start()
        
    def _show_checkboxes(self):
        self.status_label.configure(text="Select the subtopics to save:", text_color="white")
        self.content_box.pack_forget()
        self.browse_btn.pack_forget()
        
        self.checkbox_frame = ctk.CTkScrollableFrame(self.main_frame, height=200, fg_color=("gray95", "gray15"))
        self.checkbox_frame.pack(fill="x", pady=(0, 20), before=self.btn_frame)
        
        self.checkbox_vars = []
        for st in self.generated_subtopics:
            var = ctk.StringVar(value="on")
            short_reply = st.get('reply_message', '')[:60] + "..." if len(st.get('reply_message', '')) > 60 else st.get('reply_message', '')
            cb_text = f"✅ {st.get('topic_name')}  (Reply: {short_reply})"
            cb = ctk.CTkCheckBox(self.checkbox_frame, text=cb_text, variable=var, onvalue="on", offvalue="off", font=ctk.CTkFont(size=12))
            cb.pack(anchor="w", pady=8, padx=10)
            self.checkbox_vars.append((var, st))
            
        self.publish_btn.configure(text="Save Selected", state="normal", command=self._final_save)

    def _final_save(self):
        selected_subtopics = [st for var, st in self.checkbox_vars if var.get() == "on"]
        if not selected_subtopics:
            self.status_label.configure(text="No subtopics selected.", text_color="#FF6B6B")
            return
            
        # Save Main Topic
        parent_id = save_topic(None, self.main_topic_name, f"You selected {self.main_topic_name}. Please choose a sub-topic:")
        if parent_id == -1:
            self._on_fail("Failed to save to database.")
            return
            
        # Save Selected Sub-topics
        for st in selected_subtopics:
            save_topic(parent_id, st.get("topic_name", "Unknown"), st.get("reply_message", ""))
            
        messagebox.showinfo("Success", "Topic and Selected Sub-topics created successfully!")
        self.destroy()

    def _on_fail(self, error_msg):
        self.status_label.configure(text="AI generation failed. Try again.", text_color="#FF6B6B")
        self.publish_btn.configure(state="normal")
        print(f"Topic Builder Error: {error_msg}")




# ─────────────────────────────────────────────
#  MANAGE TOPICS WINDOW
# ─────────────────────────────────────────────
class ManageTopicsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Manage Topics")
        self.geometry("800x600")
        self.grab_set()
        
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (800 // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (600 // 2)
            self.geometry(f"+{x}+{y}")
        except:
            pass
            
        title_label = ctk.CTkLabel(self, text="📋 Manage Topics", font=ctk.CTkFont(size=24, weight="bold"), text_color="#F57C00")
        title_label.pack(pady=(20, 10), padx=20, anchor="w")
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self._refresh()

    def _refresh(self):
        for w in self.scroll.winfo_children(): w.destroy()
        topics = get_main_topics()
        
        if not topics:
            ctk.CTkLabel(self.scroll, text="No topics found.", text_color="gray").pack(pady=40)
            return
            
        for t in topics:
            row = ctk.CTkFrame(self.scroll, corner_radius=8, fg_color=("gray85", "gray15"))
            row.pack(fill="x", pady=5)
            
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=15, pady=10)
            
            ctk.CTkLabel(info_frame, text=f"{t['topic_name']}", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(info_frame, text=f"Type: Main Topic | Reply: {t['reply_message'][:50]}...", font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w")
            
            def edit_cmd(topic=t):
                self._open_edit_group(topic)
                
            def delete_cmd(topic_id=t['id'], name=t['topic_name']):
                if messagebox.askyesno("Delete", f"Are you sure you want to delete '{name}' and all its subtopics?"):
                    delete_topic(topic_id)
                    self._refresh()
                    
            ctk.CTkButton(row, text="Edit Group", width=80, fg_color=("#1976D2", "#0D47A1"), command=edit_cmd).pack(side="right", padx=10)
            ctk.CTkButton(row, text="Delete", width=60, fg_color="#D32F2F", hover_color="#B71C1C", command=delete_cmd).pack(side="right", padx=(0, 10))

    def _open_edit_group(self, main_topic):
        edit_win = ctk.CTkToplevel(self)
        edit_win.title(f"Editing Topic Group: {main_topic['topic_name']}")
        edit_win.geometry("700x700")
        edit_win.grab_set()
        
        try:
            x = self.winfo_x() + (self.winfo_width() // 2) - (700 // 2)
            y = self.winfo_y() + (self.winfo_height() // 2) - (700 // 2)
            edit_win.geometry(f"+{x}+{y}")
        except:
            pass
            
        # Create responsive action button row at the bottom of the window
        btn_panel = ctk.CTkFrame(edit_win, fg_color="transparent")
        btn_panel.pack(fill="x", side="bottom", padx=20, pady=(10, 20))
        
        scroll = ctk.CTkScrollableFrame(edit_win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(20, 10))
        
        ctk.CTkLabel(scroll, text="Main Topic", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0,5))
        main_frame = ctk.CTkFrame(scroll, fg_color=("gray90", "gray10"))
        main_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(main_frame, text="Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        main_name_entry = ctk.CTkEntry(main_frame, width=200)
        main_name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        main_name_entry.insert(0, main_topic['topic_name'])
        
        ctk.CTkLabel(main_frame, text="Reply:").grid(row=1, column=0, padx=10, pady=10, sticky="nw")
        main_reply_box = ctk.CTkTextbox(main_frame, height=60, width=400)
        main_reply_box.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        main_reply_box.insert("1.0", main_topic['reply_message'])
        
        ctk.CTkLabel(scroll, text="Sub-Topics", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0,5))
        
        subtopics_container = ctk.CTkFrame(scroll, fg_color="transparent")
        subtopics_container.pack(fill="x", pady=(0, 10))
        
        sub_widgets = []
        deleted_subtopic_ids = set()
        
        def animate_expand(frame, current_height=0, target_height=150, step=15):
            if current_height < target_height:
                new_height = current_height + step
                if new_height > target_height:
                    new_height = target_height
                frame.configure(height=new_height)
                edit_win.after(10, lambda: animate_expand(frame, new_height, target_height, step))
            else:
                frame.configure(height="")
                frame.pack_propagate(True)

        def animate_collapse(frame, current_height, step=15, on_complete=None):
            if current_height > 0:
                new_height = current_height - step
                if new_height < 0:
                    new_height = 0
                frame.configure(height=new_height)
                edit_win.after(10, lambda: animate_collapse(frame, new_height, step, on_complete))
            else:
                frame.pack_forget()
                frame.destroy()
                if on_complete:
                    on_complete()
                    
        def update_reorder_buttons():
            for idx, sw in enumerate(sub_widgets):
                if idx == 0:
                    sw["up_btn"].configure(state="disabled", text_color="gray50")
                else:
                    sw["up_btn"].configure(state="normal", text_color=("gray30", "#A1A1AA"))
                if idx == len(sub_widgets) - 1:
                    sw["down_btn"].configure(state="disabled", text_color="gray50")
                else:
                    sw["down_btn"].configure(state="normal", text_color=("gray30", "#A1A1AA"))

        def move_card(card_data, direction):
            idx = sub_widgets.index(card_data)
            target_idx = idx + direction
            if 0 <= target_idx < len(sub_widgets):
                sub_widgets[idx], sub_widgets[target_idx] = sub_widgets[target_idx], sub_widgets[idx]
                for sw in sub_widgets:
                    sw["frame"].pack_forget()
                for sw in sub_widgets:
                    sw["frame"].pack(fill="x", pady=(0, 10))
                update_reorder_buttons()

        def remove_card(card_data):
            if messagebox.askyesno("Delete Sub-Topic", "Are you sure you want to remove this sub-topic? This will not be saved until you click 'Save All Changes'."):
                sf = card_data["frame"]
                sf.update_idletasks()
                current_h = sf.winfo_height()
                sf.pack_propagate(False)
                
                def on_complete():
                    sub_widgets.remove(card_data)
                    if card_data["id"] is not None:
                        deleted_subtopic_ids.add(card_data["id"])
                    update_reorder_buttons()
                    
                animate_collapse(sf, current_h, step=max(1, current_h // 10), on_complete=on_complete)

        def create_subtopic_card(st_id=None, name="", reply="", animate=False):
            sf = ctk.CTkFrame(subtopics_container, fg_color=("gray90", "gray10"))
            sf.columnconfigure(1, weight=1)
            
            if animate:
                sf.pack_propagate(False)
                sf.configure(height=0)
                sf.pack(fill="x", pady=(0, 10))
            else:
                sf.pack(fill="x", pady=(0, 10))
                
            ctk.CTkLabel(sf, text="Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
            sne = ctk.CTkEntry(sf, width=200)
            sne.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
            sne.insert(0, name)
            
            # Controls Frame (Reorder + Delete)
            cf = ctk.CTkFrame(sf, fg_color="transparent")
            cf.grid(row=0, column=2, padx=10, pady=10, sticky="e")
            
            up_btn = ctk.CTkButton(cf, text="▲", width=24, height=28, fg_color="transparent", hover_color=("gray85", "#27272A"), text_color=("gray30", "#A1A1AA"), font=ctk.CTkFont(size=12, weight="bold"))
            down_btn = ctk.CTkButton(cf, text="▼", width=24, height=28, fg_color="transparent", hover_color=("gray85", "#27272A"), text_color=("gray30", "#A1A1AA"), font=ctk.CTkFont(size=12, weight="bold"))
            del_btn = ctk.CTkButton(cf, text="🗑", width=28, height=28, corner_radius=14, fg_color="transparent", hover_color=("#FFEBEE", "#3C1F22"), text_color=("#D32F2F", "#EF5350"), font=ctk.CTkFont(size=13))
            
            up_btn.pack(side="left", padx=2)
            down_btn.pack(side="left", padx=2)
            del_btn.pack(side="left", padx=2)
            
            ctk.CTkLabel(sf, text="Reply:").grid(row=1, column=0, padx=10, pady=10, sticky="nw")
            srb = ctk.CTkTextbox(sf, height=60, width=400)
            srb.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
            srb.insert("1.0", reply)
            
            card_data = {
                "id": st_id,
                "frame": sf,
                "name_entry": sne,
                "reply_box": srb,
                "up_btn": up_btn,
                "down_btn": down_btn,
                "is_new": (st_id is None)
            }
            
            up_btn.configure(command=lambda: move_card(card_data, -1))
            down_btn.configure(command=lambda: move_card(card_data, 1))
            del_btn.configure(command=lambda: remove_card(card_data))
            
            sub_widgets.append(card_data)
            update_reorder_buttons()
            
            if animate:
                animate_expand(sf)

        # Load existing sub-topics
        sub_topics = get_sub_topics(main_topic['id'])
        for st in sub_topics:
            create_subtopic_card(st_id=st['id'], name=st['topic_name'], reply=st['reply_message'], animate=False)

        def show_success_toast(callback):
            toast = ctk.CTkFrame(edit_win, corner_radius=15, fg_color=("#388E3C", "#2E7D32"), border_width=1, border_color="#81C784")
            toast.place(relx=0.5, rely=1.1, anchor="center")
            
            ctk.CTkLabel(toast, text="✨ Changes Saved Successfully!", font=ctk.CTkFont(weight="bold", size=13), text_color="white").pack(padx=25, pady=8)
            
            def slide_up(curr_rely=1.1):
                if curr_rely > 0.85:
                    next_rely = curr_rely - 0.025
                    toast.place(relx=0.5, rely=next_rely, anchor="center")
                    edit_win.after(10, lambda: slide_up(next_rely))
                else:
                    toast.place(relx=0.5, rely=0.85, anchor="center")
                    edit_win.after(1200, slide_down)
                    
            def slide_down(curr_rely=0.85):
                if curr_rely < 1.1:
                    next_rely = curr_rely + 0.025
                    toast.place(relx=0.5, rely=next_rely, anchor="center")
                    edit_win.after(10, lambda: slide_down(next_rely))
                else:
                    toast.destroy()
                    callback()
                    
            slide_up()

        def save_all():
            mn = main_name_entry.get().strip()
            mr = main_reply_box.get("1.0", "end-1c").strip()
            
            # Validation
            if not mn:
                messagebox.showwarning("Validation Error", "Main Topic Name cannot be empty!")
                main_name_entry.focus()
                return
            if not mr:
                messagebox.showwarning("Validation Error", "Main Topic Reply cannot be empty!")
                main_reply_box.focus()
                return
                
            for idx, sw in enumerate(sub_widgets):
                sn = sw["name_entry"].get().strip()
                sr = sw["reply_box"].get("1.0", "end-1c").strip()
                if not sn:
                    messagebox.showwarning("Validation Error", f"Sub-topic #{idx+1} Name cannot be empty!")
                    sw["name_entry"].focus()
                    return
                if not sr:
                    messagebox.showwarning("Validation Error", f"Sub-topic #{idx+1} Reply cannot be empty!")
                    sw["reply_box"].focus()
                    return
            
            # Save Main Topic
            update_topic(main_topic['id'], mn, mr)
            
            # Delete Staged Sub-topics
            for del_id in deleted_subtopic_ids:
                delete_topic(del_id)
                
            # Save Active Sub-topics
            for sw in sub_widgets:
                sn = sw["name_entry"].get().strip()
                sr = sw["reply_box"].get("1.0", "end-1c").strip()
                if sw["is_new"]:
                    save_topic(parent_id=main_topic['id'], topic_name=sn, reply_message=sr)
                else:
                    update_topic(sw["id"], sn, sr)
                    
            def on_toast_complete():
                edit_win.destroy()
                self._refresh()
                
            show_success_toast(on_toast_complete)
            
        # Create action buttons inside responsive row panel
        add_btn = ctk.CTkButton(btn_panel, text="➕ Add Sub-Topic", font=ctk.CTkFont(weight="bold"), 
                               height=40, fg_color=("#8E24AA", "#6A1B9A"), hover_color=("#7B1FA2", "#4A148C"),
                               command=lambda: create_subtopic_card(animate=True))
                               
        save_btn = ctk.CTkButton(btn_panel, text="Save All Changes", font=ctk.CTkFont(weight="bold"), 
                                height=40, fg_color=("#388E3C", "#2E7D32"), command=save_all)
                                
        def on_resize(event):
            width = event.width
            add_btn.pack_forget()
            save_btn.pack_forget()
            if width < 450:
                add_btn.pack(side="top", fill="x", pady=(0, 10))
                save_btn.pack(side="top", fill="x")
            else:
                add_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))
                save_btn.pack(side="left", fill="x", expand=True, padx=(10, 0))
                
        btn_panel.bind("<Configure>", on_resize)


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
        self._nav_buttons = {}
        self._pages = {}

        # ── Left Sidebar ───────────────────────────
        self.admin_sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("#0F0F12", "#09090B"))
        self.admin_sidebar.pack(side="left", fill="y")
        self.admin_sidebar.pack_propagate(False)

        # Purple left accent strip
        ctk.CTkFrame(self.admin_sidebar, width=4, corner_radius=0, fg_color="#8E24AA").pack(side="left", fill="y")

        # Sidebar content frame
        sidebar_content = ctk.CTkFrame(self.admin_sidebar, fg_color="transparent")
        sidebar_content.pack(side="left", fill="both", expand=True, padx=15, pady=20)

        # Branding
        ctk.CTkLabel(sidebar_content, text="AI Command",
                     font=ctk.CTkFont(size=24, weight="bold"), text_color="#B388FF").pack(anchor="w", pady=(10, 0))
        ctk.CTkLabel(sidebar_content, text="Power User Console",
                     font=ctk.CTkFont(size=12, weight="bold"), text_color="#FF8A65").pack(anchor="w", pady=(0, 30))

        # Nav buttons
        def _make_nav_btn(icon, label, key):
            btn = ctk.CTkButton(
                sidebar_content,
                text=f"{icon}  {label}",
                font=ctk.CTkFont(size=14, weight="normal"),
                anchor="w", height=40, corner_radius=8,
                fg_color="transparent", border_width=0,
                text_color="#A1A1AA",
                hover_color=("#1E1E28", "#1E1E28"),
                command=lambda k=key: self._navigate(k)
            )
            btn.pack(fill="x", pady=6)
            self._nav_buttons[key] = btn

        _make_nav_btn("⚙️", "Manage",     "manage")
        _make_nav_btn("✨", "AI Builder", "builder")
        _make_nav_btn("🗂", "Topic",      "topic")
        _make_nav_btn("📂", "Library",    "library")

        # Bottom sidebar
        bottom = ctk.CTkFrame(sidebar_content, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", pady=(0, 10))

        ctk.CTkLabel(bottom, text="Appearance:",
                     font=ctk.CTkFont(size=11, weight="bold"), text_color="#71717A").pack(anchor="w", pady=(10, 2))
        self.appearance_menu = ctk.CTkOptionMenu(
            bottom, values=["Dark", "Light", "System"],
            command=ctk.set_appearance_mode, height=36,
            fg_color=("#374151", "#1E1E24"),
            button_color=("#4B5563", "#27272A"),
            button_hover_color=("#6B7280", "#3F3F46")
        )
        self.appearance_menu.pack(fill="x", pady=(0, 15))
        self.appearance_menu.set("Dark")

        ctk.CTkButton(
            bottom, text="⇠  Logout", height=38,
            font=ctk.CTkFont(weight="bold", size=13),
            fg_color=("#D32F2F", "#B71C1C"), hover_color=("#FF1744", "#C62828"),
            command=self.controller._logout
        ).pack(fill="x", pady=(0, 10))

        # ── Main content area ──────────────────────
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(side="right", fill="both", expand=True)

        # Build all pages
        self._build_manage_page()
        self._build_builder_page()
        self._build_topic_page()
        self._build_library_page()

        # Default page
        self._navigate("manage")

    # ── Navigation ────────────────────────────────
    def _navigate(self, page_key):
        for page in self._pages.values():
            page.pack_forget()
        for key, btn in self._nav_buttons.items():
            if key == page_key:
                btn.configure(
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="white",
                    border_width=1,
                    border_color="#B388FF",
                    fg_color="transparent"
                )
            else:
                btn.configure(
                    font=ctk.CTkFont(size=14, weight="normal"),
                    text_color="#A1A1AA",
                    border_width=0,
                    border_color=None,
                    fg_color="transparent"
                )
        self._pages[page_key].pack(fill="both", expand=True)
        if page_key in ("manage", "library"):
            self._refresh_entries()
        elif page_key == "topic":
            self._refresh_topics()

    # ══════════════════════════════════════════════
    #  PAGE: MANAGE – Knowledge Base Dashboard
    # ══════════════════════════════════════════════
    def _build_manage_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._pages["manage"] = page

        # Header
        hdr = ctk.CTkFrame(page, fg_color="transparent")
        hdr.pack(fill="x", padx=40, pady=(25, 20))
        ctr = ctk.CTkFrame(hdr, fg_color="transparent")
        ctr.pack(anchor="center")

        ctk.CTkLabel(ctr, text="Knowledge Base Management",
                     font=ctk.CTkFont(size=30, weight="bold"), text_color="white",
                     justify="center").pack(anchor="center")
        ctk.CTkLabel(ctr, text="Upload and manage PDF documents to power the AI responses.",
                     font=ctk.CTkFont(size=13), text_color="#A1A1AA",
                     justify="center").pack(anchor="center", pady=(4, 15))

        btn_row = ctk.CTkFrame(ctr, fg_color="transparent")
        btn_row.pack(anchor="center", pady=(0, 5))

        self.upload_btn = ctk.CTkButton(
            btn_row, text="📤 Upload PDF",
            font=ctk.CTkFont(weight="bold", size=13), height=38,
            fg_color=("#1565C0", "#0D47A1"), hover_color=("#1976D2", "#1565C0"),
            command=self._upload_pdf
        )
        self.upload_btn.pack(side="left", padx=8)

        ctk.CTkButton(
            btn_row, text="✏️ Manual Entry",
            font=ctk.CTkFont(weight="bold", size=13), height=38,
            fg_color=("#00796B", "#004D40"), hover_color=("#00897B", "#00695C"),
            command=self._open_manual
        ).pack(side="left", padx=8)

        self.status_label = ctk.CTkLabel(page, text="", text_color="gray", font=ctk.CTkFont(size=12))

        # Table
        table_container = ctk.CTkFrame(page, corner_radius=15, fg_color=("gray95", "gray15"))
        table_container.pack(fill="both", expand=True, padx=40, pady=(0, 30))

        tbl_hdr = ctk.CTkFrame(table_container, fg_color="transparent")
        tbl_hdr.pack(fill="x", padx=20, pady=(15, 10))

        self.doc_count_label = ctk.CTkLabel(tbl_hdr, text="Uploaded Documents (0)",
                                            font=ctk.CTkFont(size=18, weight="bold"), text_color="white")
        self.doc_count_label.pack(side="left")

        ctk.CTkButton(
            tbl_hdr, text="🗑 Clear All", width=90, height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#374151", "#27272A"), hover_color=("#4B5563", "#3F3F46"),
            text_color="#D1D5DB", command=self._clear_all
        ).pack(side="right")

        ctk.CTkButton(
            tbl_hdr, text="⚠ Unanswered Questions", width=170, height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#FFCCBC", "#FF8A65"), hover_color=("#FFAB91", "#FF7043"),
            text_color="#1E1E1E", command=self._open_unanswered
        ).pack(side="right", padx=(0, 10))

        self.col_frame = ctk.CTkFrame(table_container, fg_color=("gray85", "gray20"), corner_radius=8)
        self.col_frame.pack(fill="x", padx=(15, 37), pady=(0, 10))
        self.col_frame.grid_columnconfigure(0, weight=1)
        self.col_frame.grid_columnconfigure(1, minsize=200, weight=0)
        self.col_frame.grid_columnconfigure(2, minsize=200, weight=0)
        self.col_frame.grid_columnconfigure(3, minsize=120, weight=0)
        ctk.CTkLabel(self.col_frame, text="🖧 FILE NAME", font=ctk.CTkFont(size=10, weight="bold"), text_color="#A1A1AA").grid(row=0, column=0, sticky="w", padx=15, pady=6)
        ctk.CTkLabel(self.col_frame, text="SIZE",        font=ctk.CTkFont(size=10, weight="bold"), text_color="#A1A1AA").grid(row=0, column=1, sticky="w", padx=10, pady=6)
        ctk.CTkLabel(self.col_frame, text="UPLOAD DATE", font=ctk.CTkFont(size=10, weight="bold"), text_color="#A1A1AA").grid(row=0, column=2, sticky="w", padx=10, pady=6)
        ctk.CTkLabel(self.col_frame, text="ACTIONS",     font=ctk.CTkFont(size=10, weight="bold"), text_color="#A1A1AA").grid(row=0, column=3, sticky="e", padx=15, pady=6)

        self.entries_frame = ctk.CTkScrollableFrame(table_container, fg_color="transparent")
        self.entries_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.entries_frame.bind("<Configure>", lambda event: self._align_header_action())

    # ══════════════════════════════════════════════
    #  PAGE: AI BUILDER – inline topic builder
    # ══════════════════════════════════════════════
    def _build_builder_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._pages["builder"] = page

        ctk.CTkLabel(page, text="✨ AI Topic Profile Builder",
                     font=ctk.CTkFont(size=30, weight="bold"), text_color="#E040FB"
                     ).pack(pady=(30, 5), padx=40, anchor="w")
        ctk.CTkLabel(page, text="Tell the AI what the topic is about, or load a PDF, and select the sub-topics to save.",
                     font=ctk.CTkFont(size=13), text_color="#A1A1AA"
                     ).pack(padx=40, anchor="w", pady=(0, 25))

        mf = ctk.CTkFrame(page, fg_color="transparent")
        mf.pack(fill="both", expand=True, padx=40, pady=(0, 30))

        ctk.CTkLabel(mf, text="MAIN TOPIC NAME", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(anchor="w", pady=(0, 5))
        self.builder_topic_entry = ctk.CTkEntry(mf, placeholder_text="e.g., Food", height=40)
        self.builder_topic_entry.pack(fill="x", pady=(0, 20))

        ctx_hdr = ctk.CTkFrame(mf, fg_color="transparent")
        ctx_hdr.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(ctx_hdr, text="KNOWLEDGE CONTEXT (Paste text or load PDF)",
                     font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(side="left")
        self.builder_browse_btn = ctk.CTkButton(
            ctx_hdr, text="Browse PDF", width=100, height=28,
            command=self._builder_load_pdf, fg_color=("#0097A7", "#006064")
        )
        self.builder_browse_btn.pack(side="right")

        self.builder_content_box = ctk.CTkTextbox(mf, height=220, font=ctk.CTkFont(size=14))
        self.builder_content_box.pack(fill="x", pady=(0, 20))
        self.builder_content_box.insert("1.0", "e.g., The sub-topics should be Beverages, Main Course, and Desserts. Use this PDF text to base the answers on...")
        self.builder_content_box.bind("<FocusIn>", self._builder_clear_placeholder)

        self.builder_btn_frame = ctk.CTkFrame(mf, fg_color="transparent")
        self.builder_btn_frame.pack(fill="x", pady=(10, 0))

        self.builder_status_label = ctk.CTkLabel(self.builder_btn_frame, text="", text_color="gray")
        self.builder_status_label.pack(side="left")

        self.builder_generate_btn = ctk.CTkButton(
            self.builder_btn_frame, text="✨ Auto-Generate",
            height=42, width=160, font=ctk.CTkFont(weight="bold"),
            fg_color=("#8E24AA", "#6A1B9A"), hover_color=("#7B1FA2", "#4A148C"),
            command=self._builder_generate
        )
        self.builder_generate_btn.pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            self.builder_btn_frame, text="🔄 Reset",
            height=42, width=100, fg_color="transparent", border_width=1,
            command=self._builder_reset
        ).pack(side="right")

        # Hidden checkbox container (shown after AI generates)
        self.builder_checkbox_container = ctk.CTkFrame(mf, fg_color="transparent")
        self.builder_checkbox_frame = None
        self.builder_generated_subtopics = []
        self.builder_checkbox_vars = []
        self.builder_main_topic_name = ""

    def _builder_load_pdf(self):
        fp = ctk.filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not fp: return
        try:
            with open(fp, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = "".join(p.extract_text() or "" for p in reader.pages)
            self.builder_content_box.delete("1.0", "end")
            self.builder_content_box.insert("end", text)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read PDF: {e}")

    def _builder_clear_placeholder(self, event):
        if "The sub-topics should be" in self.builder_content_box.get("1.0", "end-1c"):
            self.builder_content_box.delete("1.0", "end")

    def _builder_generate(self):
        topic_name = self.builder_topic_entry.get().strip()
        content = self.builder_content_box.get("1.0", "end-1c").strip()
        if not topic_name or not content or "The sub-topics should be" in content:
            self.builder_status_label.configure(text="Please fill in both fields.", text_color="#FF6B6B")
            return
        self.builder_status_label.configure(text="AI is analyzing and building...", text_color="#E040FB")
        self.builder_generate_btn.configure(state="disabled")
        self.update_idletasks()

        def task():
            prompt = (
                f"You are an AI that structures conversation topics.\n"
                f"The user is creating a main topic called '{topic_name}'.\n"
                f"Based on the following content, extract the logical sub-topics.\n"
                f"For each sub-topic, write a helpful reply message that the bot should say when the user clicks it.\n"
                f"Respond ONLY with a valid JSON array like [{{\"topic_name\": \"...\", \"reply_message\": \"...\"}}]. No markdown.\n\n"
                f"Content: {content}"
            )
            try:
                gen = get_response(prompt, "llama3", system_prompt="You only output raw JSON arrays.")
                ai_output = "".join(list(gen)).strip()
                for strip in ("```json", "```"):
                    if ai_output.startswith(strip): ai_output = ai_output[len(strip):]
                if ai_output.endswith("```"): ai_output = ai_output[:-3]
                subtopics = json.loads(ai_output)
                if not isinstance(subtopics, list): raise ValueError("Not a list")
                self.builder_generated_subtopics = subtopics
                self.builder_main_topic_name = topic_name
                self.after(0, self._builder_show_checkboxes)
            except Exception as e:
                self.after(0, lambda e=e: self._builder_on_fail(str(e)))

        threading.Thread(target=task, daemon=True).start()

    def _builder_show_checkboxes(self):
        self.builder_status_label.configure(text="Select the subtopics to save:", text_color="white")
        self.builder_content_box.pack_forget()
        self.builder_browse_btn.pack_forget()
        if self.builder_checkbox_frame:
            self.builder_checkbox_frame.destroy()
        self.builder_checkbox_frame = ctk.CTkScrollableFrame(
            self.builder_checkbox_container, height=200, fg_color=("gray95", "gray15")
        )
        self.builder_checkbox_frame.pack(fill="x", pady=(0, 20))
        self.builder_checkbox_container.pack(fill="x", before=self.builder_btn_frame)
        self.builder_checkbox_vars = []
        for st in self.builder_generated_subtopics:
            var = ctk.StringVar(value="on")
            short = st.get('reply_message', '')[:60] + ("..." if len(st.get('reply_message', '')) > 60 else "")
            ctk.CTkCheckBox(
                self.builder_checkbox_frame,
                text=f"✅ {st.get('topic_name')}  (Reply: {short})",
                variable=var, onvalue="on", offvalue="off",
                font=ctk.CTkFont(size=12)
            ).pack(anchor="w", pady=8, padx=10)
            self.builder_checkbox_vars.append((var, st))
        self.builder_generate_btn.configure(text="Save Selected", state="normal", command=self._builder_final_save)

    def _builder_final_save(self):
        selected = [st for var, st in self.builder_checkbox_vars if var.get() == "on"]
        if not selected:
            self.builder_status_label.configure(text="No subtopics selected.", text_color="#FF6B6B")
            return
        pid = save_topic(None, self.builder_main_topic_name, f"You selected {self.builder_main_topic_name}. Please choose a sub-topic:")
        if pid == -1:
            self._builder_on_fail("Failed to save to database."); return
        for st in selected:
            save_topic(pid, st.get("topic_name", "Unknown"), st.get("reply_message", ""))
        messagebox.showinfo("Success", "Topic and sub-topics created successfully!")
        self._builder_reset()

    def _builder_on_fail(self, msg):
        self.builder_status_label.configure(text="AI generation failed. Try again.", text_color="#FF6B6B")
        self.builder_generate_btn.configure(state="normal")
        print(f"Topic Builder Error: {msg}")

    def _builder_reset(self):
        if self.builder_checkbox_frame:
            self.builder_checkbox_frame.destroy()
            self.builder_checkbox_frame = None
        self.builder_checkbox_container.pack_forget()
        self.builder_content_box.pack(fill="x", pady=(0, 20), before=self.builder_btn_frame)
        self.builder_browse_btn.pack(side="right")
        self.builder_topic_entry.delete(0, "end")
        self.builder_content_box.delete("1.0", "end")
        self.builder_content_box.insert("1.0", "e.g., The sub-topics should be Beverages, Main Course, and Desserts. Use this PDF text to base the answers on...")
        self.builder_generate_btn.configure(text="✨ Auto-Generate", state="normal", command=self._builder_generate)
        self.builder_status_label.configure(text="")

    # ══════════════════════════════════════════════
    #  PAGE: TOPIC – Manage Topics inline
    # ══════════════════════════════════════════════
    def _build_topic_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._pages["topic"] = page

        hdr = ctk.CTkFrame(page, fg_color="transparent")
        hdr.pack(fill="x", padx=40, pady=(25, 10))
        ctk.CTkLabel(hdr, text="📋 Manage Topics",
                     font=ctk.CTkFont(size=30, weight="bold"), text_color="#F57C00").pack(side="left")
        ctk.CTkButton(
            hdr, text="🔄 Refresh", width=90, height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#374151", "#27272A"), hover_color=("#4B5563", "#3F3F46"),
            text_color="#D1D5DB", command=self._refresh_topics
        ).pack(side="right")

        ctk.CTkLabel(page, text="View, edit and delete main topic groups and their sub-topics.",
                     font=ctk.CTkFont(size=13), text_color="#A1A1AA").pack(padx=40, anchor="w", pady=(0, 20))

        self.topic_scroll = ctk.CTkScrollableFrame(page, fg_color="transparent")
        self.topic_scroll.pack(fill="both", expand=True, padx=40, pady=(0, 30))

    def _refresh_topics(self):
        for w in self.topic_scroll.winfo_children(): w.destroy()
        topics = get_main_topics()
        if not topics:
            ctk.CTkLabel(self.topic_scroll, text="No topics found. Use AI Builder to create topics.",
                         text_color="gray").pack(pady=40)
            return
        for t in topics:
            row = ctk.CTkFrame(self.topic_scroll, corner_radius=10,
                               fg_color=("gray85", "gray15"),
                               border_width=1, border_color=("gray80", "#232329"))
            row.pack(fill="x", pady=6)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=15, pady=12)

            name_row = ctk.CTkFrame(info, fg_color="transparent")
            name_row.pack(anchor="w")
            ctk.CTkLabel(name_row, text="🗂", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(name_row, text=t['topic_name'],
                         font=ctk.CTkFont(size=15, weight="bold"), text_color="white").pack(side="left")

            preview = t['reply_message'][:70] + ("..." if len(t['reply_message']) > 70 else "")
            ctk.CTkLabel(info, text=f"Reply: {preview}",
                         font=ctk.CTkFont(size=11), text_color="#71717A").pack(anchor="w", pady=(3, 0))

            btns = ctk.CTkFrame(row, fg_color="transparent")
            btns.pack(side="right", padx=12)

            def edit_cmd(topic=t): self._open_edit_group(topic)
            def del_cmd(tid=t['id'], nm=t['topic_name']):
                if messagebox.askyesno("Delete", f"Delete '{nm}' and all its subtopics?"):
                    delete_topic(tid); self._refresh_topics()

            ctk.CTkButton(
                btns, text="Edit Group", width=90, height=34,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=("#1976D2", "#0D47A1"), hover_color=("#1565C0", "#0A3880"),
                command=edit_cmd
            ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                btns, text="🗑 Delete", width=80, height=34,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="transparent", border_width=1, border_color="#D32F2F",
                text_color=("#D32F2F", "#EF5350"), hover_color=("#FFEBEE", "#3C1F22"),
                command=del_cmd
            ).pack(side="left")

    def _open_edit_group(self, main_topic):
        """Opens the Edit Topic Group as a Toplevel popup."""
        edit_win = ctk.CTkToplevel(self)
        edit_win.title(f"Editing Topic Group: {main_topic['topic_name']}")
        edit_win.geometry("700x700")
        edit_win.grab_set()
        try:
            x = self.winfo_x() + (self.winfo_width() // 2) - 350
            y = self.winfo_y() + (self.winfo_height() // 2) - 350
            edit_win.geometry(f"+{x}+{y}")
        except: pass

        btn_panel = ctk.CTkFrame(edit_win, fg_color="transparent")
        btn_panel.pack(fill="x", side="bottom", padx=20, pady=(10, 20))

        scroll = ctk.CTkScrollableFrame(edit_win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        ctk.CTkLabel(scroll, text="Main Topic", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 5))
        mf = ctk.CTkFrame(scroll, fg_color=("gray90", "gray10"))
        mf.pack(fill="x", pady=(0, 20))
        mf.columnconfigure(1, weight=1)

        ctk.CTkLabel(mf, text="Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        main_name_entry = ctk.CTkEntry(mf, width=200)
        main_name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        main_name_entry.insert(0, main_topic['topic_name'])

        ctk.CTkLabel(mf, text="Reply:").grid(row=1, column=0, padx=10, pady=10, sticky="nw")
        main_reply_box = ctk.CTkTextbox(mf, height=60, width=400)
        main_reply_box.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        main_reply_box.insert("1.0", main_topic['reply_message'])

        ctk.CTkLabel(scroll, text="Sub-Topics", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 5))
        subtopics_container = ctk.CTkFrame(scroll, fg_color="transparent")
        subtopics_container.pack(fill="x", pady=(0, 10))

        sub_widgets = []
        deleted_subtopic_ids = set()

        def animate_expand(frame, cur=0, target=150, step=15):
            if cur < target:
                nxt = min(cur + step, target)
                frame.configure(height=nxt)
                edit_win.after(10, lambda: animate_expand(frame, nxt, target, step))
            else:
                frame.configure(height="")
                frame.pack_propagate(True)

        def animate_collapse(frame, cur, step=15, on_complete=None):
            if cur > 0:
                nxt = max(cur - step, 0)
                frame.configure(height=nxt)
                edit_win.after(10, lambda: animate_collapse(frame, nxt, step, on_complete))
            else:
                frame.pack_forget(); frame.destroy()
                if on_complete: on_complete()

        def update_reorder_buttons():
            for idx, sw in enumerate(sub_widgets):
                sw["up_btn"].configure(
                    state="disabled" if idx == 0 else "normal",
                    text_color="gray50" if idx == 0 else ("gray30", "#A1A1AA")
                )
                sw["down_btn"].configure(
                    state="disabled" if idx == len(sub_widgets) - 1 else "normal",
                    text_color="gray50" if idx == len(sub_widgets) - 1 else ("gray30", "#A1A1AA")
                )

        def move_card(cd, direction):
            idx = sub_widgets.index(cd)
            ti = idx + direction
            if 0 <= ti < len(sub_widgets):
                sub_widgets[idx], sub_widgets[ti] = sub_widgets[ti], sub_widgets[idx]
                for sw in sub_widgets: sw["frame"].pack_forget()
                for sw in sub_widgets: sw["frame"].pack(fill="x", pady=(0, 10))
                update_reorder_buttons()

        def remove_card(cd):
            if messagebox.askyesno("Delete Sub-Topic", "Remove this sub-topic? Changes apply on Save."):
                sf = cd["frame"]
                sf.update_idletasks(); h = sf.winfo_height()
                sf.pack_propagate(False)
                def done():
                    sub_widgets.remove(cd)
                    if cd["id"] is not None: deleted_subtopic_ids.add(cd["id"])
                    update_reorder_buttons()
                animate_collapse(sf, h, step=max(1, h // 10), on_complete=done)

        def create_subtopic_card(st_id=None, name="", reply="", animate=False):
            sf = ctk.CTkFrame(subtopics_container, fg_color=("gray90", "gray10"))
            sf.columnconfigure(1, weight=1)
            if animate:
                sf.pack_propagate(False); sf.configure(height=0)
                sf.pack(fill="x", pady=(0, 10))
            else:
                sf.pack(fill="x", pady=(0, 10))

            ctk.CTkLabel(sf, text="Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
            sne = ctk.CTkEntry(sf, width=200)
            sne.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
            sne.insert(0, name)

            cf = ctk.CTkFrame(sf, fg_color="transparent")
            cf.grid(row=0, column=2, padx=10, pady=10, sticky="e")
            up_btn  = ctk.CTkButton(cf, text="▲", width=24, height=28, fg_color="transparent", hover_color=("gray85", "#27272A"), text_color=("gray30", "#A1A1AA"), font=ctk.CTkFont(size=12, weight="bold"))
            down_btn= ctk.CTkButton(cf, text="▼", width=24, height=28, fg_color="transparent", hover_color=("gray85", "#27272A"), text_color=("gray30", "#A1A1AA"), font=ctk.CTkFont(size=12, weight="bold"))
            del_btn = ctk.CTkButton(cf, text="🗑", width=28, height=28, corner_radius=14, fg_color="transparent", hover_color=("#FFEBEE", "#3C1F22"), text_color=("#D32F2F", "#EF5350"), font=ctk.CTkFont(size=13))
            up_btn.pack(side="left", padx=2)
            down_btn.pack(side="left", padx=2)
            del_btn.pack(side="left", padx=2)

            ctk.CTkLabel(sf, text="Reply:").grid(row=1, column=0, padx=10, pady=10, sticky="nw")
            srb = ctk.CTkTextbox(sf, height=60, width=400)
            srb.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
            srb.insert("1.0", reply)

            cd = {"id": st_id, "frame": sf, "name_entry": sne, "reply_box": srb,
                  "up_btn": up_btn, "down_btn": down_btn, "is_new": (st_id is None)}
            up_btn.configure(command=lambda: move_card(cd, -1))
            down_btn.configure(command=lambda: move_card(cd, 1))
            del_btn.configure(command=lambda: remove_card(cd))
            sub_widgets.append(cd)
            update_reorder_buttons()
            if animate: animate_expand(sf)

        for st in get_sub_topics(main_topic['id']):
            create_subtopic_card(st_id=st['id'], name=st['topic_name'], reply=st['reply_message'])

        def show_success_toast(callback):
            toast = ctk.CTkFrame(edit_win, corner_radius=15,
                                 fg_color=("#388E3C", "#2E7D32"),
                                 border_width=1, border_color="#81C784")
            toast.place(relx=0.5, rely=1.1, anchor="center")
            ctk.CTkLabel(toast, text="✨ Changes Saved Successfully!",
                         font=ctk.CTkFont(weight="bold", size=13), text_color="white").pack(padx=25, pady=8)
            def slide_up(r=1.1):
                if r > 0.85:
                    toast.place(relx=0.5, rely=r - 0.025, anchor="center")
                    edit_win.after(10, lambda: slide_up(r - 0.025))
                else:
                    edit_win.after(1200, slide_down)
            def slide_down(r=0.85):
                if r < 1.1:
                    toast.place(relx=0.5, rely=r + 0.025, anchor="center")
                    edit_win.after(10, lambda: slide_down(r + 0.025))
                else:
                    toast.destroy(); callback()
            slide_up()

        def save_all():
            mn = main_name_entry.get().strip()
            mr = main_reply_box.get("1.0", "end-1c").strip()
            if not mn:
                messagebox.showwarning("Validation", "Main Topic Name cannot be empty!"); main_name_entry.focus(); return
            if not mr:
                messagebox.showwarning("Validation", "Main Topic Reply cannot be empty!"); main_reply_box.focus(); return
            for idx, sw in enumerate(sub_widgets):
                sn = sw["name_entry"].get().strip()
                sr = sw["reply_box"].get("1.0", "end-1c").strip()
                if not sn:
                    messagebox.showwarning("Validation", f"Sub-topic #{idx+1} Name cannot be empty!"); sw["name_entry"].focus(); return
                if not sr:
                    messagebox.showwarning("Validation", f"Sub-topic #{idx+1} Reply cannot be empty!"); sw["reply_box"].focus(); return
            update_topic(main_topic['id'], mn, mr)
            for did in deleted_subtopic_ids: delete_topic(did)
            for sw in sub_widgets:
                sn = sw["name_entry"].get().strip()
                sr = sw["reply_box"].get("1.0", "end-1c").strip()
                if sw["is_new"]: save_topic(parent_id=main_topic['id'], topic_name=sn, reply_message=sr)
                else: update_topic(sw["id"], sn, sr)
            def after_toast(): edit_win.destroy(); self._refresh_topics()
            show_success_toast(after_toast)

        add_btn  = ctk.CTkButton(btn_panel, text="➕ Add Sub-Topic", font=ctk.CTkFont(weight="bold"),
                                 height=40, fg_color=("#8E24AA", "#6A1B9A"), hover_color=("#7B1FA2", "#4A148C"),
                                 command=lambda: create_subtopic_card(animate=True))
        save_btn = ctk.CTkButton(btn_panel, text="Save All Changes", font=ctk.CTkFont(weight="bold"),
                                 height=40, fg_color=("#388E3C", "#2E7D32"), command=save_all)

        def on_resize(event):
            w = event.width
            add_btn.pack_forget(); save_btn.pack_forget()
            if w < 450:
                add_btn.pack(side="top", fill="x", pady=(0, 10))
                save_btn.pack(side="top", fill="x")
            else:
                add_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))
                save_btn.pack(side="left", fill="x", expand=True, padx=(10, 0))
        btn_panel.bind("<Configure>", on_resize)

    # ══════════════════════════════════════════════
    #  PAGE: LIBRARY – Document list
    # ══════════════════════════════════════════════
    def _build_library_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._pages["library"] = page

        hdr = ctk.CTkFrame(page, fg_color="transparent")
        hdr.pack(fill="x", padx=40, pady=(25, 10))
        ctk.CTkLabel(hdr, text="📂 Document Library",
                     font=ctk.CTkFont(size=30, weight="bold"), text_color="white").pack(side="left")
        ctk.CTkButton(
            hdr, text="📤 Upload PDF",
            font=ctk.CTkFont(weight="bold", size=13), height=38,
            fg_color=("#1565C0", "#0D47A1"), hover_color=("#1976D2", "#1565C0"),
            command=self._upload_pdf
        ).pack(side="right", padx=(10, 0))
        ctk.CTkButton(
            hdr, text="✏️ Manual Entry",
            font=ctk.CTkFont(weight="bold", size=13), height=38,
            fg_color=("#00796B", "#004D40"), hover_color=("#00897B", "#00695C"),
            command=self._open_manual
        ).pack(side="right")

        ctk.CTkLabel(page,
                     text="All uploaded PDFs and manual knowledge entries stored in the AI knowledge base.",
                     font=ctk.CTkFont(size=13), text_color="#A1A1AA").pack(padx=40, anchor="w", pady=(0, 20))

        lib_tc = ctk.CTkFrame(page, corner_radius=15, fg_color=("gray95", "gray15"))
        lib_tc.pack(fill="both", expand=True, padx=40, pady=(0, 30))

        lib_hdr = ctk.CTkFrame(lib_tc, fg_color="transparent")
        lib_hdr.pack(fill="x", padx=20, pady=(15, 10))
        self.lib_doc_count_label = ctk.CTkLabel(lib_hdr, text="All Documents (0)",
                                                font=ctk.CTkFont(size=18, weight="bold"), text_color="white")
        self.lib_doc_count_label.pack(side="left")
        ctk.CTkButton(
            lib_hdr, text="🗑 Clear All", width=90, height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#374151", "#27272A"), hover_color=("#4B5563", "#3F3F46"),
            text_color="#D1D5DB", command=self._clear_all
        ).pack(side="right")
        ctk.CTkButton(
            lib_hdr, text="⚠ Unanswered", width=130, height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#FFCCBC", "#FF8A65"), hover_color=("#FFAB91", "#FF7043"),
            text_color="#1E1E1E", command=self._open_unanswered
        ).pack(side="right", padx=(0, 10))

        self.lib_col_frame = ctk.CTkFrame(lib_tc, fg_color=("gray85", "gray20"), corner_radius=8)
        self.lib_col_frame.pack(fill="x", padx=(15, 37), pady=(0, 10))
        self.lib_col_frame.grid_columnconfigure(0, weight=1)
        self.lib_col_frame.grid_columnconfigure(1, minsize=200, weight=0)
        self.lib_col_frame.grid_columnconfigure(2, minsize=200, weight=0)
        self.lib_col_frame.grid_columnconfigure(3, minsize=120, weight=0)
        ctk.CTkLabel(self.lib_col_frame, text="🖧 FILE NAME", font=ctk.CTkFont(size=10, weight="bold"), text_color="#A1A1AA").grid(row=0, column=0, sticky="w", padx=15, pady=6)
        ctk.CTkLabel(self.lib_col_frame, text="SIZE",        font=ctk.CTkFont(size=10, weight="bold"), text_color="#A1A1AA").grid(row=0, column=1, sticky="w", padx=10, pady=6)
        ctk.CTkLabel(self.lib_col_frame, text="UPLOAD DATE", font=ctk.CTkFont(size=10, weight="bold"), text_color="#A1A1AA").grid(row=0, column=2, sticky="w", padx=10, pady=6)
        ctk.CTkLabel(self.lib_col_frame, text="ACTIONS",     font=ctk.CTkFont(size=10, weight="bold"), text_color="#A1A1AA").grid(row=0, column=3, sticky="e", padx=15, pady=6)

        self.lib_entries_frame = ctk.CTkScrollableFrame(lib_tc, fg_color="transparent")
        self.lib_entries_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _populate_lib_rows(self, sources_info):
        for w in self.lib_entries_frame.winfo_children(): w.destroy()
        self.lib_doc_count_label.configure(text=f"All Documents ({len(sources_info)})")
        if not sources_info:
            ctk.CTkLabel(self.lib_entries_frame, text="No documents found.", text_color="gray").pack(pady=40)
            return
        for src, meta in sources_info:
            row = ctk.CTkFrame(self.lib_entries_frame, corner_radius=10,
                               border_width=1, border_color=("gray80", "#232329"),
                               fg_color=("gray95", "#16161a"))
            row.pack(fill="x", pady=6, padx=5)
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, minsize=200, weight=0)
            row.grid_columnconfigure(2, minsize=200, weight=0)
            row.grid_columnconfigure(3, minsize=120, weight=0)

            nm_f = ctk.CTkFrame(row, fg_color="transparent")
            nm_f.grid(row=0, column=0, sticky="w", padx=15, pady=10)
            is_manual = src.startswith("Manual:")
            if is_manual:
                ic = ctk.CTkFrame(nm_f, width=36, height=36, corner_radius=8, fg_color=("#E0F2F1", "#102624"))
                ic.pack_propagate(False); ic.pack(side="left", padx=(0, 12))
                ctk.CTkLabel(ic, text="📝", font=ctk.CTkFont(size=16)).pack(expand=True)
                badge = "MANUAL ENTRY"
            else:
                ic = ctk.CTkFrame(nm_f, width=36, height=36, corner_radius=8, fg_color=("#FFEBEE", "#2E1618"))
                ic.pack_propagate(False); ic.pack(side="left", padx=(0, 12))
                ctk.CTkLabel(ic, text="📄", font=ctk.CTkFont(size=16)).pack(expand=True)
                badge = "OCR ACTIVE" if "complex" in src.lower() else "VECTOR OPTIMIZED"

            tc = ctk.CTkFrame(nm_f, fg_color="transparent")
            tc.pack(side="left", fill="both")
            ctk.CTkLabel(tc, text=src, font=ctk.CTkFont(size=13, weight="bold"), text_color=("black", "white")).pack(anchor="w")
            bf = ctk.CTkFrame(tc, corner_radius=4, fg_color=("gray90", "#212124"), border_width=1, border_color=("gray80", "#2D2D30"))
            bf.pack(anchor="w", pady=(2, 0))
            ctk.CTkLabel(bf, text=badge, font=ctk.CTkFont(size=8, weight="bold"), text_color=("#555555", "#A1A1AA")).pack(padx=6, pady=1)

            ctk.CTkLabel(row, text="Manual Entry" if is_manual else meta.get("size", "Unknown"),
                         font=ctk.CTkFont(size=12, weight="bold"), text_color=("gray30", "#A1A1AA")).grid(row=0, column=1, sticky="w", padx=10)
            ctk.CTkLabel(row, text=meta.get("date", "Unknown"),
                         font=ctk.CTkFont(size=12), text_color=("gray40", "#71717A")).grid(row=0, column=2, sticky="w", padx=10)

            af = ctk.CTkFrame(row, fg_color="transparent")
            af.grid(row=0, column=3, sticky="e", padx=15)
            ctk.CTkButton(af, text="👁", width=32, height=32, corner_radius=16,
                          fg_color="transparent", hover_color=("gray85", "#27272A"),
                          text_color=("gray30", "#A1A1AA"), font=ctk.CTkFont(size=15),
                          command=lambda s=src: self._view_single(s)).pack(side="left", padx=(0, 6))
            ctk.CTkButton(af, text="🗑", width=32, height=32, corner_radius=16,
                          fg_color="transparent", hover_color=("#FFEBEE", "#3C1F22"),
                          text_color=("#D32F2F", "#EF5350"), font=ctk.CTkFont(size=15),
                          command=lambda s=src: self._delete_single(s)).pack(side="left")
        
    # ── Shared utility methods ──────────────────
    def _open_unanswered(self):
        UnansweredQuestionsWindow(self, self.controller)

    def _open_manual(self):
        ManualEntryWindow(self, self._refresh_entries)

    def _upload_pdf(self):
        file_path = ctk.filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not file_path: return
        if hasattr(self, 'upload_btn') and self.upload_btn:
            self.upload_btn.configure(state="disabled")
        if hasattr(self, 'status_label'):
            self.status_label.configure(text=f"Reading & Embedding: {os.path.basename(file_path)}...")
        def task():
            ok, msg = process_pdf(file_path)
            self.controller.after(0, lambda: self._upload_complete(ok, msg))
        threading.Thread(target=task, daemon=True).start()

    def _upload_complete(self, ok, msg):
        if hasattr(self, 'upload_btn') and self.upload_btn:
            self.upload_btn.configure(state="normal")
        if hasattr(self, 'status_label'):
            self.status_label.configure(text=msg, text_color="#4CAF50" if ok else "#FF6B6B")
        if ok:
            self._refresh_entries()

    def _refresh_entries(self):
        """Refresh both the Manage page table and the Library page table."""
        sources_info = get_all_sources()

        # -- Manage page --
        if hasattr(self, 'entries_frame'):
            for w in self.entries_frame.winfo_children(): w.destroy()
            self.doc_count_label.configure(text=f"Uploaded Documents ({len(sources_info)})")
            if not sources_info:
                ctk.CTkLabel(self.entries_frame, text="No documents found.", text_color="gray").pack(pady=40)
            else:
                for src, meta in sources_info:
                    self._make_doc_row(self.entries_frame, src, meta, on_delete=self._delete_single)
                self.after(50,  self._align_header_action)
                self.after(150, self._align_header_action)

        # -- Library page --
        if hasattr(self, 'lib_entries_frame'):
            self._populate_lib_rows(sources_info)

    def _populate_lib_rows(self, sources_info):
        for w in self.lib_entries_frame.winfo_children(): w.destroy()
        self.lib_doc_count_label.configure(text=f"All Documents ({len(sources_info)})")
        if not sources_info:
            ctk.CTkLabel(self.lib_entries_frame, text="No documents found.", text_color="gray").pack(pady=40)
            return
        for src, meta in sources_info:
            self._make_doc_row(self.lib_entries_frame, src, meta, on_delete=self._delete_single)

    def _make_doc_row(self, parent_frame, src, meta, on_delete):
        row = ctk.CTkFrame(parent_frame, corner_radius=10,
                           border_width=1, border_color=("gray80", "#232329"),
                           fg_color=("gray95", "#16161a"))
        row.pack(fill="x", pady=6, padx=5)
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, minsize=200, weight=0)
        row.grid_columnconfigure(2, minsize=200, weight=0)
        row.grid_columnconfigure(3, minsize=120, weight=0)

        nm_f = ctk.CTkFrame(row, fg_color="transparent")
        nm_f.grid(row=0, column=0, sticky="w", padx=15, pady=10)
        is_manual = src.startswith("Manual:")
        if is_manual:
            ic = ctk.CTkFrame(nm_f, width=36, height=36, corner_radius=8, fg_color=("#E0F2F1", "#102624"))
            ic.pack_propagate(False); ic.pack(side="left", padx=(0, 12))
            ctk.CTkLabel(ic, text="📝", font=ctk.CTkFont(size=16)).pack(expand=True)
            badge = "MANUAL ENTRY"
        else:
            ic = ctk.CTkFrame(nm_f, width=36, height=36, corner_radius=8, fg_color=("#FFEBEE", "#2E1618"))
            ic.pack_propagate(False); ic.pack(side="left", padx=(0, 12))
            ctk.CTkLabel(ic, text="📄", font=ctk.CTkFont(size=16)).pack(expand=True)
            badge = "OCR ACTIVE" if "complex" in src.lower() else "VECTOR OPTIMIZED"

        tc = ctk.CTkFrame(nm_f, fg_color="transparent")
        tc.pack(side="left", fill="both")
        ctk.CTkLabel(tc, text=src, font=ctk.CTkFont(size=13, weight="bold"), text_color=("black", "white")).pack(anchor="w")
        bf = ctk.CTkFrame(tc, corner_radius=4, fg_color=("gray90", "#212124"), border_width=1, border_color=("gray80", "#2D2D30"))
        bf.pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(bf, text=badge, font=ctk.CTkFont(size=8, weight="bold"), text_color=("#555555", "#A1A1AA")).pack(padx=6, pady=1)

        ctk.CTkLabel(row, text="Manual Entry" if is_manual else meta.get("size", "Unknown"),
                     font=ctk.CTkFont(size=12, weight="bold"), text_color=("gray30", "#A1A1AA")).grid(row=0, column=1, sticky="w", padx=10)
        ctk.CTkLabel(row, text=meta.get("date", "Unknown"),
                     font=ctk.CTkFont(size=12), text_color=("gray40", "#71717A")).grid(row=0, column=2, sticky="w", padx=10)

        af = ctk.CTkFrame(row, fg_color="transparent")
        af.grid(row=0, column=3, sticky="e", padx=15)
        ctk.CTkButton(af, text="👁", width=32, height=32, corner_radius=16,
                      fg_color="transparent", hover_color=("gray85", "#27272A"),
                      text_color=("gray30", "#A1A1AA"), font=ctk.CTkFont(size=15),
                      command=lambda s=src: self._view_single(s)).pack(side="left", padx=(0, 6))
        ctk.CTkButton(af, text="🗑", width=32, height=32, corner_radius=16,
                      fg_color="transparent", hover_color=("#FFEBEE", "#3C1F22"),
                      text_color=("#D32F2F", "#EF5350"), font=ctk.CTkFont(size=15),
                      command=lambda s=src: on_delete(s)).pack(side="left")

    def _view_single(self, src):
        content = get_source_content(src)
        ViewSourceWindow(self, src, content or "No content found for this entry.")

    def _delete_single(self, src):
        if messagebox.askyesno("Delete", f"Are you sure you want to delete '{src}'?"):
            delete_source(src)
            self._refresh_entries()

    def _clear_all(self):
        if messagebox.askyesno("Clear", "Delete ALL uploaded documents?"):
            clear_rag()
            self._refresh_entries()

    def _align_header_action(self, event=None):
        if not hasattr(self, 'entries_frame'): return
        for child in self.entries_frame.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                self._align_header(child); break

    def _align_header(self, row):
        row.update_idletasks()
        row_width = row.winfo_width()
        table_container = self.entries_frame.master
        container_width = table_container.winfo_width()
        if row_width > 1 and container_width > 1:
            scale = self.col_frame._scaling_coefficient
            right_pad_physical = container_width - (15 * scale) - row_width
            right_pad_virtual = int(right_pad_physical / scale)
            if 10 <= right_pad_virtual <= 100:
                current_padx = self.col_frame.pack_info().get("padx", (15, 37))
                current_right = int(current_padx[1] if isinstance(current_padx, (tuple, list)) else current_padx)
                if current_right != right_pad_virtual:
                    self.col_frame.pack_configure(padx=(15, right_pad_virtual))


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

    def _populate_options(self, parent_id=None):
        for w in self.options_frame.winfo_children(): w.destroy()
        
        if parent_id is None:
            topics = get_main_topics()
            parent_topic = None
        else:
            topics = get_sub_topics(parent_id)
            parent_topic = get_topic_by_id(parent_id)
            
        if not topics and parent_id is None:
            self.options_frame.grid_remove()
            return
            
        self.options_frame.grid()
        row_idx, col_idx, max_cols = 0, 0, 2
        
        # Add 'Back' button if we are in a sub-topic menu
        if parent_id is not None and parent_topic:
            btn = ctk.CTkButton(self.options_frame, text="⬅ Back", height=36, corner_radius=18,
                                fg_color="transparent", border_width=1, border_color="#D32F2F",
                                text_color=("#D32F2F", "#EF5350"), hover_color=("#FFEBEE", "#421010"),
                                command=lambda pid=parent_topic['parent_id']: self._populate_options(parent_id=pid))
            btn.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="ew")
            self.options_frame.grid_columnconfigure(col_idx, weight=1)
            
            col_idx += 1
            if col_idx >= max_cols:
                col_idx = 0
                row_idx += 1
                
        for t in topics:
            btn = ctk.CTkButton(self.options_frame, text=t["topic_name"], height=36, corner_radius=18,
                                fg_color="transparent", border_width=1, border_color="#0097A7",
                                text_color=("#0097A7", "#4DD0E1"), hover_color=("#E0F7FA", "#004D40"),
                                command=lambda topic=t: self._handle_topic_click(topic))
            btn.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="ew")
            self.options_frame.grid_columnconfigure(col_idx, weight=1)
            
            col_idx += 1
            if col_idx >= max_cols:
                col_idx = 0
                row_idx += 1
                
        # Add 'Others' button
        others_btn = ctk.CTkButton(self.options_frame, text="Others", height=36, corner_radius=18,
                            fg_color="transparent", border_width=1, border_color="#9E9E9E",
                            text_color=("#9E9E9E", "#BDBDBD"), hover_color=("#F5F5F5", "#424242"),
                            command=self.options_frame.grid_remove)
        others_btn.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="ew")
        self.options_frame.grid_columnconfigure(col_idx, weight=1)

    def _handle_topic_click(self, topic):
        is_first_msg = (self.current_session_id is None)
        if is_first_msg: self.current_session_id = str(uuid.uuid4())
        
        self._append_chat("You", topic["topic_name"])
        self._append_chat("Bot", topic["reply_message"])
        
        # Save to chat history database
        save_message(self.controller.username, self.current_session_id, topic["topic_name"], topic["reply_message"])
        self.controller.after(0, lambda: self.sidebar.refresh_sessions())
        
        # Generate catchy title if first message
        if is_first_msg:
            threading.Thread(target=self._generate_catchy_title, args=(topic["topic_name"],), daemon=True).start()
            
        # Check for sub-topics
        self._populate_options(parent_id=topic["id"])

    def start_new_chat(self):
        self.current_session_id = str(uuid.uuid4())
        self.chat_area.configure(state="normal")
        self.chat_area.delete("1.0", "end")
        self.chat_area.insert("end", "✨ New chat session started.\n\n", "italic")
        self.chat_area.insert("end", "Bot: ", "bold")
        self.chat_area.insert("end", "Hi, may I help you? You can choose an option below or type your question.\n\n")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")
        self._populate_options()
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
