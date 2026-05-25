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
        self.title("Topic Profile Builder")
        self.geometry("750x650")
        self.grab_set()
        
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (750 // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (650 // 2)
            self.geometry(f"+{x}+{y}")
        except:
            pass
            
        title_label = ctk.CTkLabel(self, text="✨ Topic Profile Builder", font=ctk.CTkFont(size=24, weight="bold"), text_color="#E040FB")
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
        
        cancel_btn = ctk.CTkButton(self.btn_frame, text="Cancel", height=40, width=100, fg_color="transparent", border_width=1, border_color=("#B0B0B0", "#52525B"), text_color=("#1A1A1E", "#E4E4E7"), hover_color=("#E5E7EB", "#27272A"), command=self.destroy)
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
        self.status_label.configure(text="Select the subtopics to save:", text_color=("gray20", "white"))
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
            
        actions_frame = ctk.CTkFrame(edit_win, fg_color="transparent")
        actions_frame.pack(side="bottom", fill="x", padx=20, pady=(10, 20))
        
        scroll = ctk.CTkScrollableFrame(edit_win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(20, 0))
        
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

        # Add Sub-Topic Button
        add_btn = ctk.CTkButton(actions_frame, text="➕ Add Sub-Topic", font=ctk.CTkFont(weight="bold"), 
                               height=40, fg_color=("#8E24AA", "#6A1B9A"), hover_color=("#7B1FA2", "#4A148C"),
                               command=lambda: create_subtopic_card(animate=True))

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
            
        save_btn = ctk.CTkButton(actions_frame, text="Save All Changes", font=ctk.CTkFont(weight="bold"), height=40, fg_color=("#388E3C", "#2E7D32"), command=save_all)

        def adjust_buttons_layout(event=None):
            if event and event.widget != edit_win:
                return
            w = edit_win.winfo_width()
            if w <= 1:
                w = 700
            
            if w < 500:
                # Stack vertically for small screens
                add_btn.pack_forget()
                save_btn.pack_forget()
                add_btn.pack(side="top", fill="x", pady=(0, 10))
                save_btn.pack(side="top", fill="x")
            else:
                # Side-by-side horizontally for larger screens
                add_btn.pack_forget()
                save_btn.pack_forget()
                add_btn.pack(side="left", expand=True, fill="x", padx=(0, 10))
                save_btn.pack(side="left", expand=True, fill="x", padx=(10, 0))

        # Perform initial layout and bind configure event for responsiveness
        adjust_buttons_layout()
        edit_win.bind("<Configure>", adjust_buttons_layout)


# ─────────────────────────────────────────────
#  VIEW SOURCE WINDOW
# ─────────────────────────────────────────────
class ViewSourceWindow(ctk.CTkToplevel):
    def __init__(self, parent, source_name, content):
        super().__init__(parent)
        self.title(f"Viewing: {source_name}")
        self.geometry("800x600")
        self.grab_set()
#  UNANSWERED QUESTIONS WINDOW & SYSTEM
# ─────────────────────────────────────────────
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
        except:
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
            
        from rag import submit_admin_answer
        submit_admin_answer(self.question_id, answer)
        
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
        except:
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
#  EMBEDDED SUB-VIEWS
# ─────────────────────────────────────────────
class EmbeddedAIBuilderFrame(ctk.CTkFrame):
    def __init__(self, parent, admin_frame):
        super().__init__(parent, fg_color="transparent")
        self.admin_frame = admin_frame
        
        title_label = ctk.CTkLabel(self, text="✨ Topic Profile Builder", font=ctk.CTkFont(size=24, weight="bold"), text_color="#E040FB")
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
        
        cancel_btn = ctk.CTkButton(self.btn_frame, text="Cancel", height=40, width=100, fg_color="transparent", border_width=1, border_color=("#B0B0B0", "#52525B"), text_color=("#1A1A1E", "#E4E4E7"), hover_color=("#E5E7EB", "#27272A"), command=self._reset_view)
        cancel_btn.pack(side="right")
        
        self.checkbox_frame = None

    def _reset_view(self):
        self.topic_entry.delete(0, "end")
        self.content_box.delete("1.0", "end")
        self.content_box.insert("1.0", "e.g., The sub-topics should be Beverages, Main Course, and Desserts. Use this PDF text to base the answers on...")
        self.status_label.configure(text="", text_color="gray")
        self.publish_btn.configure(text="✨ Auto-Generate", state="normal", command=self._generate_subtopics)
        self.browse_btn.pack(side="right")
        self.content_box.pack(fill="x", pady=(0, 20))
        if self.checkbox_frame:
            self.checkbox_frame.pack_forget()
            self.checkbox_frame.destroy()
            self.checkbox_frame = None

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
                gen = get_response(prompt, "llama3", system_prompt="You only output raw JSON arrays.")
                ai_output = "".join(list(gen)).strip()
                
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
        self.status_label.configure(text="Select the subtopics to save:", text_color=("gray20", "white"))
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
        self._reset_view()
        self.admin_frame.show_view("Manage Topic")

    def _on_fail(self, error_msg):
        self.status_label.configure(text="AI generation failed. Try again.", text_color="#FF6B6B")
        self.publish_btn.configure(state="normal")
        print(f"Topic Builder Error: {error_msg}")


class EmbeddedManageTopicsFrame(ctk.CTkFrame):
    def __init__(self, parent, controller, admin_frame):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.admin_frame = admin_frame
        
        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.pack(fill="x", pady=(20, 10), padx=20)
        
        title_label = ctk.CTkLabel(header_row, text="📋 Manage Topics", font=ctk.CTkFont(size=24, weight="bold"), text_color="#F57C00")
        title_label.pack(side="left")
        
        add_topic_btn = ctk.CTkButton(
            header_row,
            text="➕ New Main Topic",
            font=ctk.CTkFont(weight="bold", size=12),
            height=32,
            fg_color=("#F57C00", "#E65100"),
            hover_color=("#EF6C00", "#BF360C"),
            command=self._add_new_topic_popup
        )
        add_topic_btn.pack(side="right", padx=(10, 0))
        
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._refresh())
        search_entry = ctk.CTkEntry(
            header_row,
            placeholder_text="Search topics...",
            textvariable=self.search_var,
            width=200,
            height=32
        )
        search_entry.pack(side="right")
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self._refresh()

    def _add_new_topic_popup(self):
        dialog = ctk.CTkInputDialog(text="Enter new Main Topic name:", title="Add Topic")
        name = dialog.get_input()
        if name and name.strip():
            save_topic(None, name.strip(), f"You selected {name.strip()}. Please choose a sub-topic:")
            self._refresh()

    def _refresh(self):
        for w in self.scroll.winfo_children(): w.destroy()
        topics = get_main_topics()
        
        search_query = self.search_var.get().strip().lower()
        if search_query:
            topics = [t for t in topics if search_query in t['topic_name'].lower()]
            
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
            
        actions_frame = ctk.CTkFrame(edit_win, fg_color="transparent")
        actions_frame.pack(side="bottom", fill="x", padx=20, pady=(10, 20))
        
        scroll = ctk.CTkScrollableFrame(edit_win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(20, 0))
        
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

        sub_topics = get_sub_topics(main_topic['id'])
        for st in sub_topics:
            create_subtopic_card(st_id=st['id'], name=st['topic_name'], reply=st['reply_message'], animate=False)

        add_btn = ctk.CTkButton(actions_frame, text="➕ Add Sub-Topic", font=ctk.CTkFont(weight="bold"), 
                               height=40, fg_color=("#8E24AA", "#6A1B9A"), hover_color=("#7B1FA2", "#4A148C"),
                               command=lambda: create_subtopic_card(animate=True))

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
            
            update_topic(main_topic['id'], mn, mr)
            
            for del_id in deleted_subtopic_ids:
                delete_topic(del_id)
                
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
            
        save_btn = ctk.CTkButton(actions_frame, text="Save All Changes", font=ctk.CTkFont(weight="bold"), height=40, fg_color=("#388E3C", "#2E7D32"), command=save_all)

        def adjust_buttons_layout(event=None):
            if event and event.widget != edit_win:
                return
            w = edit_win.winfo_width()
            if w <= 1:
                w = 700
            
            if w < 500:
                add_btn.pack_forget()
                save_btn.pack_forget()
                add_btn.pack(side="top", fill="x", pady=(0, 10))
                save_btn.pack(side="top", fill="x")
            else:
                add_btn.pack_forget()
                save_btn.pack_forget()
                add_btn.pack(side="left", expand=True, fill="x", padx=(0, 10))
                save_btn.pack(side="left", expand=True, fill="x", padx=(10, 0))

        adjust_buttons_layout()
        edit_win.bind("<Configure>", adjust_buttons_layout)


class EmbeddedInsightsFrame(ctk.CTkFrame):
    def __init__(self, parent, controller, admin_frame):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.admin_frame = admin_frame
        
        title_label = ctk.CTkLabel(self, text="📈 System Insights", font=ctk.CTkFont(size=24, weight="bold"), text_color="#4CAF50")
        title_label.pack(pady=(20, 10), padx=20, anchor="w")
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self._refresh()
        
    def _refresh(self):
        for w in self.scroll.winfo_children(): w.destroy()
        
        from rag import get_all_sources, get_unanswered_questions
        sources = get_all_sources()
        unanswered = get_unanswered_questions()
        topics = get_main_topics()
        
        subtopics_count = 0
        for t in topics:
            subtopics_count += len(get_sub_topics(t['id']))
            
        stats_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        stats_frame.pack(fill="x", pady=10)
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="equal")
        
        doc_card = ctk.CTkFrame(stats_frame, corner_radius=12, fg_color=("#E8F5E9", "#1B5E20"))
        doc_card.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(doc_card, text="📁", font=ctk.CTkFont(size=40)).pack(pady=(15, 5))
        ctk.CTkLabel(doc_card, text="Total Documents", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#2E7D32", "#A5D6A7")).pack()
        ctk.CTkLabel(doc_card, text=str(len(sources)), font=ctk.CTkFont(size=24, weight="bold"), text_color=("#1B5E20", "white")).pack(pady=(5, 15))
        
        topic_card = ctk.CTkFrame(stats_frame, corner_radius=12, fg_color=("#E3F2FD", "#0D47A1"))
        topic_card.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(topic_card, text="📋", font=ctk.CTkFont(size=40)).pack(pady=(15, 5))
        ctk.CTkLabel(topic_card, text="Topics (Sub-topics)", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#1565C0", "#90CAF9")).pack()
        ctk.CTkLabel(topic_card, text=f"{len(topics)} ({subtopics_count})", font=ctk.CTkFont(size=24, weight="bold"), text_color=("#0D47A1", "white")).pack(pady=(5, 15))
        
        unans_card = ctk.CTkFrame(stats_frame, corner_radius=12, fg_color=("#FBE9E7", "#BF360C"))
        unans_card.grid(row=0, column=2, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(unans_card, text="❓", font=ctk.CTkFont(size=40)).pack(pady=(15, 5))
        ctk.CTkLabel(unans_card, text="Unanswered Questions", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#D84315", "#FFAB91")).pack()
        ctk.CTkLabel(unans_card, text=str(len(unanswered)), font=ctk.CTkFont(size=24, weight="bold"), text_color=("#BF360C", "white")).pack(pady=(5, 15))
        
        detail_frame = ctk.CTkFrame(self.scroll, corner_radius=12, fg_color=("gray95", "gray15"))
        detail_frame.pack(fill="both", expand=True, pady=15, padx=10)
        
        ctk.CTkLabel(detail_frame, text="System Configuration & Info", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(15, 10))
        
        info_text = (
            f"• LLM Model Instance: llama3 (local deployment via Ollama)\n"
            f"• Embeddings Model: Nomic-Embed-Text / Vectorizer\n"
            f"• Database Status: Connected (MySQL Chat Logs, Local JSON Vector DB)\n"
            f"• Active Admin Role: {self.controller.user_name}\n"
            f"• Last System Synchronization: Just now"
        )
        ctk.CTkLabel(detail_frame, text=info_text, font=ctk.CTkFont(size=13), justify="left").pack(anchor="w", padx=30, pady=(0, 20))


class EmbeddedEnvironmentFrame(ctk.CTkFrame):
    def __init__(self, parent, controller, admin_frame):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.admin_frame = admin_frame
        
        title_label = ctk.CTkLabel(self, text="⚙️ Environment Configuration", font=ctk.CTkFont(size=24, weight="bold"), text_color="#29B6F6")
        title_label.pack(pady=(20, 10), padx=20, anchor="w")
        ctk.CTkLabel(self, text="Configure global app settings, Database credentials, and local LLM options stored in the .env file.", text_color="gray").pack(padx=20, anchor="w", pady=(0, 15))
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # --- DATABASE SETTINGS CARD ---
        db_card = ctk.CTkFrame(self.scroll, corner_radius=12, fg_color=("gray95", "gray12"), border_width=1, border_color=("gray85", "gray20"))
        db_card.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(db_card, text="🔌 MySQL Database Settings", font=ctk.CTkFont(size=15, weight="bold"), text_color="#29B6F6").pack(anchor="w", padx=20, pady=(15, 10))
        
        # DB Grid Frame
        db_grid = ctk.CTkFrame(db_card, fg_color="transparent")
        db_grid.pack(fill="x", padx=20, pady=(0, 15))
        db_grid.grid_columnconfigure(1, weight=1)
        
        # Host
        ctk.CTkLabel(db_grid, text="Database Host:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", pady=6, padx=(0, 10))
        self.db_host_entry = ctk.CTkEntry(db_grid, placeholder_text="e.g. localhost", height=36)
        self.db_host_entry.grid(row=0, column=1, sticky="ew", pady=6)
        
        # User
        ctk.CTkLabel(db_grid, text="Database User:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=1, column=0, sticky="w", pady=6, padx=(0, 10))
        self.db_user_entry = ctk.CTkEntry(db_grid, placeholder_text="e.g. root", height=36)
        self.db_user_entry.grid(row=1, column=1, sticky="ew", pady=6)
        
        # Password
        ctk.CTkLabel(db_grid, text="Database Password:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=2, column=0, sticky="w", pady=6, padx=(0, 10))
        
        pass_container = ctk.CTkFrame(db_grid, fg_color="transparent")
        pass_container.grid(row=2, column=1, sticky="ew", pady=6)
        pass_container.grid_columnconfigure(0, weight=1)
        
        self.db_pass_entry = ctk.CTkEntry(pass_container, placeholder_text="e.g. empty or password", height=36, show="•")
        self.db_pass_entry.grid(row=0, column=0, sticky="ew")
        
        self.pass_visible = False
        def toggle_pass():
            if self.pass_visible:
                self.db_pass_entry.configure(show="•")
                toggle_btn.configure(text="👁")
                self.pass_visible = False
            else:
                self.db_pass_entry.configure(show="")
                toggle_btn.configure(text="🔒")
                self.pass_visible = True
                
        toggle_btn = ctk.CTkButton(pass_container, text="👁", width=36, height=36, fg_color=("gray85", "gray20"), hover_color=("gray75", "gray30"), text_color=("gray20", "white"), command=toggle_pass)
        toggle_btn.grid(row=0, column=1, padx=(6, 0))
        
        # Database Name
        ctk.CTkLabel(db_grid, text="Database Name:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=3, column=0, sticky="w", pady=6, padx=(0, 10))
        self.db_name_entry = ctk.CTkEntry(db_grid, placeholder_text="e.g. chatdb", height=36)
        self.db_name_entry.grid(row=3, column=1, sticky="ew", pady=6)
        
        # --- OLLAMA AI SETTINGS CARD ---
        llm_card = ctk.CTkFrame(self.scroll, corner_radius=12, fg_color=("gray95", "gray12"), border_width=1, border_color=("gray85", "gray20"))
        llm_card.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(llm_card, text="🧠 Ollama AI Engine Settings", font=ctk.CTkFont(size=15, weight="bold"), text_color="#AB47BC").pack(anchor="w", padx=20, pady=(15, 10))
        
        llm_grid = ctk.CTkFrame(llm_card, fg_color="transparent")
        llm_grid.pack(fill="x", padx=20, pady=(0, 15))
        llm_grid.grid_columnconfigure(1, weight=1)
        
        # Ollama Model Name
        ctk.CTkLabel(llm_grid, text="Ollama Model Name:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", pady=6, padx=(0, 10))
        self.llm_model_entry = ctk.CTkEntry(llm_grid, placeholder_text="e.g. llama3, mistral, gemma", height=36)
        self.llm_model_entry.grid(row=0, column=1, sticky="ew", pady=6)
        
        # Ollama Base Host URL
        ctk.CTkLabel(llm_grid, text="Ollama Host URL:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=1, column=0, sticky="w", pady=6, padx=(0, 10))
        self.llm_host_entry = ctk.CTkEntry(llm_grid, placeholder_text="e.g. http://localhost:11434 (default)", height=36)
        self.llm_host_entry.grid(row=1, column=1, sticky="ew", pady=6)
        
        # --- ACTIONS PANEL ---
        actions_card = ctk.CTkFrame(self.scroll, fg_color="transparent")
        actions_card.pack(fill="x", pady=15, padx=5)
        
        self.status_lbl = ctk.CTkLabel(actions_card, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.status_lbl.pack(side="left")
        
        save_btn = ctk.CTkButton(actions_card, text="💾 Save Config", font=ctk.CTkFont(weight="bold"), height=40, width=140, fg_color=("#388E3C", "#2E7D32"), command=self._save_config)
        save_btn.pack(side="right", padx=(10, 0))
        
        test_btn = ctk.CTkButton(actions_card, text="🔌 Test Connection", font=ctk.CTkFont(weight="bold"), height=40, width=140, fg_color=("#0288D1", "#01579B"), command=self._test_connection)
        test_btn.pack(side="right")
        
        self._load_current_env()
        
    def _load_current_env(self):
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        self.db_host_entry.delete(0, "end")
        self.db_host_entry.insert(0, os.getenv("DB_HOST", "localhost"))
        
        self.db_user_entry.delete(0, "end")
        self.db_user_entry.insert(0, os.getenv("DB_USER", "root"))
        
        self.db_pass_entry.delete(0, "end")
        self.db_pass_entry.insert(0, os.getenv("DB_PASSWORD", ""))
        
        self.db_name_entry.delete(0, "end")
        self.db_name_entry.insert(0, os.getenv("DB_DATABASE", "chatdb"))
        
        self.llm_model_entry.delete(0, "end")
        self.llm_model_entry.insert(0, os.getenv("OLLAMA_MODEL", "llama3"))
        
        self.llm_host_entry.delete(0, "end")
        self.llm_host_entry.insert(0, os.getenv("OLLAMA_HOST", ""))
        
    def _test_connection(self):
        host = self.db_host_entry.get().strip()
        user = self.db_user_entry.get().strip()
        password = self.db_pass_entry.get()
        database = self.db_name_entry.get().strip()
        
        self.status_lbl.configure(text="Connecting to database...", text_color="gray")
        self.update_idletasks()
        
        from auth import test_db_connection
        
        def task():
            ok, msg = test_db_connection(host, user, password, database)
            if ok:
                self.after(0, lambda: self.status_lbl.configure(text="✓ Connection test successful!", text_color="#4CAF50"))
            else:
                self.after(0, lambda: self.status_lbl.configure(text=f"✗ Connection failed: {msg[:60]}", text_color="#FF6B6B"))
                
        threading.Thread(target=task, daemon=True).start()
        
    def _save_config(self):
        host = self.db_host_entry.get().strip()
        user = self.db_user_entry.get().strip()
        password = self.db_pass_entry.get()
        database = self.db_name_entry.get().strip()
        model = self.llm_model_entry.get().strip()
        ollama_host = self.llm_host_entry.get().strip()
        
        try:
            env_content = f"""# MySQL Database Settings
DB_HOST={host}
DB_USER={user}
DB_PASSWORD={password}
DB_DATABASE={database}

# Ollama Engine Settings
OLLAMA_MODEL={model}
OLLAMA_HOST={ollama_host}
"""
            with open(".env", "w", encoding="utf-8") as f:
                f.write(env_content)
                
            from dotenv import load_dotenv
            load_dotenv(override=True)
            
            self._show_success_toast()
            self.status_lbl.configure(text="✓ Configuration saved and hot-reloaded!", text_color="#4CAF50")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save .env file: {e}")
            
    def _show_success_toast(self):
        toast = ctk.CTkFrame(self, corner_radius=15, fg_color=("#388E3C", "#2E7D32"), border_width=1, border_color="#81C784")
        toast.place(relx=0.5, rely=1.1, anchor="center")
        
        ctk.CTkLabel(toast, text="✨ Configuration Saved Successfully!", font=ctk.CTkFont(weight="bold", size=13), text_color="white").pack(padx=25, pady=8)
        
        def slide_up(curr_rely=1.1):
            if curr_rely > 0.85:
                next_rely = curr_rely - 0.025
                toast.place(relx=0.5, rely=next_rely, anchor="center")
                self.after(10, lambda: slide_up(next_rely))
            else:
                toast.place(relx=0.5, rely=0.85, anchor="center")
                self.after(1200, slide_down)
                
        def slide_down(curr_rely=0.85):
            if curr_rely < 1.1:
                next_rely = curr_rely + 0.025
                toast.place(relx=0.5, rely=next_rely, anchor="center")
                self.after(10, lambda: slide_down(next_rely))
            else:
                toast.destroy()
                
        slide_up()


# ─────────────────────────────────────────────
#  ADMIN DASHBOARD FRAME
# ─────────────────────────────────────────────
class AdminFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

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

        btn_insights = create_menu_btn(sidebar_content, "📈", "Insights", is_active=False)
        btn_insights.pack(fill="x", pady=6)

        btn_env = create_menu_btn(sidebar_content, "🛠", "Environment", is_active=False)
        btn_env.pack(fill="x", pady=6)

        self.menu_buttons = {
            "Dashboard": btn_manage,
            "Topic Builder": btn_builder,
            "Manage Topic": btn_topic,
            "Library": btn_library,
            "Insights": btn_insights,
            "Environment": btn_env
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

        # Documents Table area inside self.main_container
        table_container = ctk.CTkFrame(self.main_container, corner_radius=15, fg_color=("gray95", "gray15"))
        table_container.pack(fill="both", expand=True, padx=40, pady=(0, 30))
        self.table_container = table_container
        
        table_header_top = ctk.CTkFrame(table_container, fg_color="transparent")
        table_header_top.pack(fill="x", padx=20, pady=(15, 10))
        
        self.doc_count_label = ctk.CTkLabel(table_header_top, text="Uploaded Documents (0)", font=ctk.CTkFont(size=18, weight="bold"), text_color=("gray20", "white"))
        self.doc_count_label.pack(side="left")
        
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
        if hasattr(self, 'insights_view'):
            self.insights_view.pack_forget()
        if hasattr(self, 'environment_view'):
            self.environment_view.pack_forget()
            
        # Route to active view
        if name == "Dashboard":
            self.title_frame.pack(fill="x", padx=40, pady=(25, 20))
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
            
        elif name == "Insights":
            if not hasattr(self, 'insights_view'):
                self.insights_view = EmbeddedInsightsFrame(self.main_container, self.controller, self)
            self.insights_view.pack(fill="both", expand=True, padx=40, pady=30)
            self.insights_view._refresh()
            
        elif name == "Environment":
            if not hasattr(self, 'environment_view'):
                self.environment_view = EmbeddedEnvironmentFrame(self.main_container, self.controller, self)
            self.environment_view.pack(fill="both", expand=True, padx=40, pady=30)
            self.environment_view._load_current_env()

    def _open_unanswered(self):
        UnansweredQuestionsWindow(self, self.controller)
        
    def _open_manual(self):
        ManualEntryWindow(self, self._refresh_entries)
        
    def _open_topic_builder(self):
        self.show_view("Topic Builder")

    def _open_manage_topics(self):
        self.show_view("Manage Topic")

    def _upload_pdf(self):
        file_path = ctk.filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not file_path: return
        
        if hasattr(self, 'upload_btn') and self.upload_btn:
            self.upload_btn.configure(state="disabled")
        self.status_label.configure(text=f"Reading & Embedding: {os.path.basename(file_path)}...")
        
        def task():
            def progress(current, total):
                self.controller.after(0, lambda: self.status_label.configure(text=f"Embedding chunk {current}/{total}..."))
                
            ok, msg = process_pdf(file_path, progress_callback=progress)
            self.controller.after(0, lambda: self._upload_complete(ok, msg))
            
        threading.Thread(target=task, daemon=True).start()
        
    def _upload_complete(self, ok, msg):
        if hasattr(self, 'upload_btn') and self.upload_btn:
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
        self.in_others_state = False
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
                            command=lambda: self._show_others_state(parent_id))
        others_btn.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="ew")
        self.options_frame.grid_columnconfigure(col_idx, weight=1)

    def _show_others_state(self, parent_id):
        self.in_others_state = True
        for w in self.options_frame.winfo_children(): w.destroy()
        self.options_frame.grid()
        self.options_frame.grid_columnconfigure(0, weight=1)
        self.options_frame.grid_columnconfigure(1, weight=0)
        
        btn = ctk.CTkButton(self.options_frame, text="⬅ Back", height=36, corner_radius=18,
                            fg_color="transparent", border_width=1, border_color="#D32F2F",
                            text_color=("#D32F2F", "#EF5350"), hover_color=("#FFEBEE", "#421010"),
                            command=lambda: self._populate_options(parent_id=parent_id))
        btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

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
        
        if not getattr(self, "in_others_state", False):
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
        
        # Check if there is a previously answered question matching this
        from rag import find_answered_question_match
        answered_match = find_answered_question_match(prompt)
        if answered_match:
            self.controller.after(0, lambda: (
                self.chat_area.configure(state="normal"),
                self.chat_area.insert("end", "Bot: ", "bold"),
                self.chat_area.insert("end", answered_match + "\n\n"),
                self.chat_area.see("end"),
                self.chat_area.configure(state="disabled"),
                self.send_btn.configure(state="normal"),
                self.stop_btn.configure(state="disabled")
            ))
            save_message(self.controller.username, self.current_session_id, prompt, answered_match)
            self.controller.after(0, lambda: self.sidebar.refresh_sessions())
            if is_first_msg:
                threading.Thread(target=self._generate_catchy_title, args=(prompt,), daemon=True).start()
            return

        sys = query_rag(prompt)
        
        if sys is None:
            # Fallback logic
            save_unanswered_question(prompt, self.controller.username)
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
