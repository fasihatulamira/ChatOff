"""Embedded admin sub-views: Topic Builder and Manage Topics."""
import os
import threading
import time
import customtkinter as ctk
from tkinter import messagebox

from auth import save_topic, get_main_topics, get_sub_topics, delete_topic, update_topic, get_topic_by_id
from chatbot import get_response
from json_utils import parse_json_array
from pdf_utils import extract_pdf_text
from rag import get_all_sources, get_source_content, build_topic_builder_excerpt
from gui.processing import ProcessingWindow
from gui.scroll_utils import setup_smooth_scroll

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
        
        self.kb_dropdown = ctk.CTkOptionMenu(
            header_frame,
            values=["Select Uploaded PDF..."],
            command=self._on_kb_select,
            width=200,
            height=28,
            fg_color=("#1976D2", "#0D47A1"),
            button_color=("#1565C0", "#002171")
        )
        self.kb_dropdown.pack(side="right", padx=(0, 10))
        
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
        self._refresh_kb_dropdown()

    def _reset_view(self):
        self.topic_entry.delete(0, "end")
        self.content_box.delete("1.0", "end")
        self.content_box.insert("1.0", "e.g., The sub-topics should be Beverages, Main Course, and Desserts. Use this PDF text to base the answers on...")
        self.status_label.configure(text="", text_color="gray")
        self.publish_btn.configure(text="✨ Auto-Generate", state="normal", command=self._generate_subtopics)
        self.browse_btn.pack(side="right")
        self.kb_dropdown.pack(side="right", padx=(0, 10))
        self.content_box.pack(fill="x", pady=(0, 20))
        if self.checkbox_frame:
            self.checkbox_frame.pack_forget()
            self.checkbox_frame.destroy()
            self.checkbox_frame = None
        self._refresh_kb_dropdown()

    def _load_pdf(self):
        file_path = ctk.filedialog.askopenfilename(parent=self, filetypes=[("PDF Files", "*.pdf")])
        if not file_path:
            return
        try:
            text, method = extract_pdf_text(file_path)
            if not text.strip():
                messagebox.showwarning(
                    "Warning",
                    "No text could be extracted from this PDF.\n"
                    "For scanned documents, set RAG_OCR_ENABLED=true in .env and install Tesseract OCR.",
                )
                return

            max_chars = int(os.getenv("TOPIC_BUILDER_MAX_CHARS", "12000"))
            truncated = len(text) > max_chars
            if truncated:
                text = text[:max_chars]

            self.content_box.delete("1.0", "end")
            self.content_box.insert("end", text)

            note = f"Loaded via {method}."
            if truncated:
                note += f" Trimmed to {max_chars:,} characters."
            self.status_label.configure(text=note, text_color="#4CAF50")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read PDF: {e}")
            
    def _on_kb_select(self, choice):
        if choice in ("Select Uploaded PDF...", "No Uploaded PDFs"):
            return
        
        self.status_label.configure(text="Retrieving text from Knowledge Base...", text_color="gray")
        self.update_idletasks()
        
        try:
            max_chars = int(os.getenv("TOPIC_BUILDER_MAX_CHARS", "12000"))
            text, truncated, full_len = build_topic_builder_excerpt(choice, max_chars)
            if text:
                self.content_box.delete("1.0", "end")
                self.content_box.insert("end", text)
                if truncated:
                    self.status_label.configure(
                        text=(
                            f"Loaded {len(text):,} chars from {choice} "
                            f"(PDF has {full_len:,}; sampled across sections)"
                        ),
                        text_color="#FF9800",
                    )
                    messagebox.showinfo(
                        "PDF excerpt loaded",
                        f"'{choice}' has {full_len:,} characters in total.\n\n"
                        f"Topic Builder loaded a {len(text):,}-character sample from multiple "
                        f"sections (not only the first pages), so Auto-Generate still works well.\n\n"
                        f"To load more text, increase TOPIC_BUILDER_MAX_CHARS in .env "
                        f"(current limit: {max_chars:,}).",
                    )
                else:
                    self.status_label.configure(
                        text=f"Loaded full content from {choice} ({full_len:,} chars)",
                        text_color="#4CAF50",
                    )
            else:
                self.status_label.configure(text="No content found in Knowledge Base.", text_color="#FF6B6B")
        except Exception as e:
            self.status_label.configure(text=f"Error loading: {str(e)}", text_color="#FF6B6B")
            
        self.kb_dropdown.set("Select Uploaded PDF...")
        
    def _refresh_kb_dropdown(self):
        try:
            sources = get_all_sources()
            pdf_sources = [src for src, meta in sources if not src.startswith("Manual:")]
            if pdf_sources:
                values = ["Select Uploaded PDF..."] + sorted(pdf_sources)
            else:
                values = ["No Uploaded PDFs"]
            self.kb_dropdown.configure(values=values)
            self.kb_dropdown.set(values[0])
        except Exception as e:
            print(f"Error refreshing KB dropdown: {e}")
        
    def _clear_placeholder(self, event):
        if "The sub-topics should be" in self.content_box.get("1.0", "end-1c"):
            self.content_box.delete("1.0", "end")
            
    def _generate_subtopics(self):
        topic_name = self.topic_entry.get().strip()
        content = self.content_box.get("1.0", "end-1c").strip()
        
        if not topic_name or not content or "The sub-topics should be" in content:
            self.status_label.configure(text="Please fill in both fields.", text_color="#FF6B6B")
            return

        max_chars = int(os.getenv("TOPIC_BUILDER_MAX_CHARS", "12000"))
        if len(content) > max_chars:
            content = content[:max_chars]
            messagebox.showinfo(
                "Content Trimmed",
                f"Your text was trimmed to {max_chars:,} characters before sending to the AI.\n"
                f"Increase TOPIC_BUILDER_MAX_CHARS in .env to allow more.",
            )
            
        self.status_label.configure(text="AI is analyzing and building...", text_color="#E040FB")
        self.publish_btn.configure(state="disabled")

        self._gen_cancel_event = threading.Event()

        def on_cancel():
            self._gen_cancel_event.set()
            self.status_label.configure(text="Generation cancelled.", text_color="orange")
            self.publish_btn.configure(state="normal")
            self.processing_win = None

        self.processing_win = ProcessingWindow(
            self,
            title="AI Topic Builder",
            message="AI is analyzing content & building sub-topics...",
            on_cancel=on_cancel,
        )
        current_win = self.processing_win

        def task():
            prompt = (
                f"You are an AI that structures conversation topics.\n"
                f"The user is creating a main topic called '{topic_name}'.\n"
                f"Based on the following content, extract the logical sub-topics.\n"
                f"For each sub-topic, write a detailed reply message (3–6 sentences) that fully explains the topic, "
                f"highlights key points from the content, and guides the user on what they can ask next.\n"
                f"Respond ONLY with a valid JSON array like [{{\"topic_name\": \"...\", \"reply_message\": \"...\"}}]. "
                f"Do not write any markdown code blocks or extra text.\n\n"
                f"Content: {content}"
            )

            try:
                if self._gen_cancel_event.is_set() or current_win is None or current_win.is_cancelled:
                    return

                model_name = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
                last_error = None
                subtopics = None
                for attempt in range(2):
                    if self._gen_cancel_event.is_set() or current_win is None or current_win.is_cancelled:
                        return
                    try:
                        gen = get_response(
                            prompt,
                            model_name,
                            system_prompt="You only output raw JSON arrays.",
                            json_mode=True,
                            cancel_event=self._gen_cancel_event,
                        )
                        ai_output = "".join(list(gen)).strip()
                        if self._gen_cancel_event.is_set() or current_win is None or current_win.is_cancelled:
                            return
                        subtopics = parse_json_array(ai_output)
                        break
                    except Exception as e:
                        last_error = e
                        if self._gen_cancel_event.is_set() or current_win is None or current_win.is_cancelled:
                            return
                        if attempt == 0:
                            time.sleep(2)
                            continue
                        raise

                if self._gen_cancel_event.is_set() or current_win is None or current_win.is_cancelled:
                    return

                if not subtopics:
                    raise last_error or ValueError("Failed to generate sub-topics.")

                self.generated_subtopics = subtopics
                self.main_topic_name = topic_name
                self.after(0, self._on_success)

            except Exception as e:
                if self._gen_cancel_event.is_set() or current_win is None or current_win.is_cancelled:
                    return
                self.after(0, lambda e=e: self._on_fail(str(e)))

        threading.Thread(target=task, daemon=True).start()
        
    def _on_success(self):
        if hasattr(self, 'processing_win') and self.processing_win:
            self.processing_win.finish()
            self.processing_win = None
        self._show_checkboxes()
        
    def _show_checkboxes(self):
        self.status_label.configure(text="Select the subtopics to save:", text_color=("gray20", "white"))
        self.content_box.pack_forget()
        self.browse_btn.pack_forget()
        self.kb_dropdown.pack_forget()
        
        self.checkbox_frame = ctk.CTkScrollableFrame(self.main_frame, height=200, fg_color=("gray95", "gray15"))
        self.checkbox_frame.pack(fill="x", pady=(0, 20), before=self.btn_frame)
        setup_smooth_scroll(self.checkbox_frame, hover_widgets=(self.main_frame,))
        
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
        if hasattr(self, 'processing_win') and self.processing_win:
            self.processing_win.finish()
            self.processing_win = None
        self.status_label.configure(text="AI generation failed. Try again.", text_color="#FF6B6B")
        self.publish_btn.configure(state="normal")
        messagebox.showerror("AI Error", f"Failed to auto-generate subtopics:\n{error_msg}")
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
        setup_smooth_scroll(self.scroll)
        
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
        except Exception:
            pass
            
        actions_frame = ctk.CTkFrame(edit_win, fg_color="transparent")
        actions_frame.pack(side="bottom", fill="x", padx=20, pady=(10, 20))
        
        scroll = ctk.CTkScrollableFrame(edit_win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(20, 0))
        setup_smooth_scroll(scroll, hover_widgets=(edit_win, actions_frame))
        
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
        
        ctk.CTkLabel(main_frame, text="Strict PDF Lock:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        from rag import get_all_sources
        all_pdfs = [src for src, meta in get_all_sources()]
        pdf_options = ["None (Search All PDFs)"] + all_pdfs
        pdf_menu = ctk.CTkOptionMenu(main_frame, values=pdf_options, width=250)
        pdf_menu.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        
        current_filter = main_topic.get("pdf_source")
        if current_filter and current_filter in all_pdfs:
            pdf_menu.set(current_filter)
        else:
            pdf_menu.set("None (Search All PDFs)")
        
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
            
            selected_pdf = pdf_menu.get()
            pdf_source_value = selected_pdf if selected_pdf != "None (Search All PDFs)" else None
            update_topic(main_topic['id'], mn, mr, pdf_source=pdf_source_value)
            
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

