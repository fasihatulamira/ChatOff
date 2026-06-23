"""Main chat frame with RAG-backed AI responses."""
import os
import re
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
import customtkinter as ctk
from tkinter import messagebox

from auth import (
    save_message, get_main_topics, get_sub_topics, get_topic_by_id,
    load_session_messages, update_session_title,
)
from chatbot import get_response, format_ai_error, collapse_output_repetition, rag_num_predict, looks_like_gibberish, looks_truncated
from rag import query_rag, save_unanswered_question, precompute_prompt_embedding
from gui.sidebar import NavigationSidebar

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

        self.status_label = ctk.CTkLabel(
            self.input_frame, text="", text_color="gray",
            font=ctk.CTkFont(size=12), anchor="w",
        )
        self.status_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

        self.cancel_event = threading.Event()
        self._streaming = False
        self._generating = False
        self._generating_base_text = ""
        self._generating_dots = 0
        self._generating_anim_job = None

    def _populate_options(self, parent_id=None):
        self.current_parent_id = parent_id
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
        ok, db_err = save_message(self.controller.username, self.current_session_id, topic["topic_name"], topic["reply_message"])
        if not ok:
            self.controller.after(0, lambda err=db_err: self._notify_db_error(err))
        self.controller.after(0, lambda: self.sidebar.refresh_sessions())
        
        # Set active pdf_source filter for the current session (with parent inheritance)
        self.active_source_filter = topic.get("pdf_source")
        if not self.active_source_filter and topic.get("parent_id"):
            parent_topic = get_topic_by_id(topic["parent_id"])
            if parent_topic:
                self.active_source_filter = parent_topic.get("pdf_source")
        
        if is_first_msg:
            self._schedule_catchy_title(topic["topic_name"])
            
        # Check for sub-topics
        self._populate_options(parent_id=topic["id"])

    def start_new_chat(self):
        self.active_source_filter = None
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
        messages, db_err = load_session_messages(self.controller.username, session_id)
        if db_err:
            messagebox.showwarning("Database Error", f"Could not load chat history:\n{db_err}")
            return
        self.chat_area.configure(state="normal")
        self.chat_area.delete("1.0", "end")
        for m in messages:
            self.chat_area.insert("end", "You: ", "bold")
            self.chat_area.insert("end", f"{m['prompt_text']}\n\n")
            self.chat_area.insert("end", "Bot: ", "bold")
            self.chat_area.insert("end", f"{m['response_text']}\n\n")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    def _set_status(self, text: str):
        self.status_label.configure(text=text, text_color="gray")

    def _clear_status(self):
        self.status_label.configure(text="", text_color="gray")

    def _start_generating_indicator(self, base_text: str = "Generating answer"):
        self._generating = True
        self._generating_base_text = base_text
        self._generating_dots = 0
        if self._generating_anim_job is not None:
            self.after_cancel(self._generating_anim_job)
            self._generating_anim_job = None
        self._animate_generating_indicator()

    def _update_generating_indicator(self, base_text: str):
        self._generating_base_text = base_text

    def _animate_generating_indicator(self):
        if not self._generating:
            return
        self._generating_dots = (self._generating_dots + 1) % 4
        dots = "." * self._generating_dots
        self.status_label.configure(
            text=f"⏳ {self._generating_base_text}{dots}",
            text_color=("#0097A7", "#4DD0E1"),
        )
        self._generating_anim_job = self.after(400, self._animate_generating_indicator)

    def _stop_generating_indicator(self, final_text: str = ""):
        self._generating = False
        if self._generating_anim_job is not None:
            self.after_cancel(self._generating_anim_job)
            self._generating_anim_job = None
        if final_text:
            self.status_label.configure(text=final_text, text_color="gray")
        else:
            self._clear_status()

    def _notify_db_error(self, message: str):
        self._set_status("⚠ Chat was not saved to database.")
        messagebox.showwarning(
            "Database Error",
            f"Your message was shown but could not be saved to history.\n\n{message}",
        )

    def _stop_generation(self):
        self.cancel_event.set()

    def _send(self):
        msg = self.entry.get().strip()
        if not msg: return
        
        if not getattr(self, "in_others_state", False):
            self._show_others_state(parent_id=getattr(self, "current_parent_id", None))
        
        is_first_msg = (self.current_session_id is None)
        if is_first_msg: self.current_session_id = str(uuid.uuid4())
        
        self.entry.delete(0, "end")
        self._append_chat("You", msg)
        
        self.send_btn.configure(state="disabled")
        self.entry.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.cancel_event.clear()
        self._start_generating_indicator("Preparing response")
        threading.Thread(
            target=self._process_ai, args=(msg, is_first_msg), daemon=True,
        ).start()

    def _show_bot_message(self, text: str):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", "Bot: ", "bold")
        self.chat_area.insert("end", text + "\n\n")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    def _begin_bot_stream(self):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", "Bot: ", "bold")
        self._stream_start = self.chat_area.index("end-1c")
        self._streaming = True

    def _append_stream_chunk(self, chunk: str):
        if not self._streaming:
            return
        self.chat_area.insert("end", chunk)
        self.chat_area.see("end")

    def _finalize_bot_stream(self, clean_text: str, rag_sources=None):
        self.chat_area.configure(state="normal")
        if getattr(self, "_stream_start", None):
            self.chat_area.delete(self._stream_start, "end")
        self.chat_area.insert("end", clean_text)
        if rag_sources:
            parts = [f"{s['name']} ({s['score']:.0%})" for s in rag_sources]
            self.chat_area.insert("end", "\n📎 Sources: " + ", ".join(parts))
        self.chat_area.insert("end", "\n\n")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")
        self._streaming = False
        self._stream_start = None

    def _finish_bot_stream(self):
        self.chat_area.insert("end", "\n\n")
        self.chat_area.configure(state="disabled")
        self._streaming = False
        self._stream_start = None

    def _append_sources_footer(self, sources):
        if not sources:
            return
        parts = [f"{s['name']} ({s['score']:.0%})" for s in sources]
        footer = "\n📎 Sources: " + ", ".join(parts) + "\n"
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", footer)
        self.chat_area.configure(state="disabled")

    def _stream_ai_response(self, user_message, model, system_prompt, is_first_msg, rag_sources=None):
        """Stream Ollama output into the chat area; returns collected text."""
        self.controller.after(0, self._begin_bot_stream)
        collected = []
        pending = []
        last_flush = time.monotonic()
        try:
            flush_ms = int(os.getenv("STREAM_FLUSH_MS", "120"))
        except ValueError:
            flush_ms = 120
        flush_interval = max(0.03, flush_ms / 1000.0)

        num_predict = rag_num_predict(user_message) if system_prompt.strip() else None
        for chunk in get_response(
            user_message,
            model,
            system_prompt,
            cancel_event=self.cancel_event,
            num_predict_override=num_predict,
        ):
            if self.cancel_event.is_set():
                break
            collected.append(chunk)
            pending.append(chunk)
            now = time.monotonic()
            if now - last_flush >= flush_interval:
                batch = "".join(pending)
                pending = []
                last_flush = now
                self.controller.after(0, lambda b=batch: self._append_stream_chunk(b))

        if pending and not self.cancel_event.is_set():
            batch = "".join(pending)
            self.controller.after(0, lambda b=batch: self._append_stream_chunk(b))

        full = collapse_output_repetition("".join(collected))
        if full and looks_like_gibberish(full):
            full = (
                "Maaf, jawapan AI tidak stabil (konteks terlalu besar untuk model). "
                "Cuba tanya semula dengan soalan lebih spesifik, atau naikkan OLLAMA_RAG_NUM_CTX dalam .env."
            )
        elif full and looks_truncated(full):
            full = (
                full.rstrip()
                + "\n\n_(Jawapan mungkin terpotong. Untuk ringkasan penuh, tanya: "
                "'Senaraikan semua bahagian dalam PDF ini' atau naikkan OLLAMA_LIST_NUM_PREDICT dalam .env.)_"
            )
        if full:
            self.controller.after(0, lambda t=full, s=rag_sources: self._finalize_bot_stream(t, s))
            display_text = full
            if rag_sources:
                parts = [f"{s['name']} ({s['score']:.0%})" for s in rag_sources]
                display_text += "\n📎 Sources: " + ", ".join(parts)
            ok, db_err = save_message(
                self.controller.username, self.current_session_id, user_message, display_text,
            )
            if not ok:
                self.controller.after(0, lambda err=db_err: self._notify_db_error(err))
            self.controller.after(0, lambda: self.sidebar.refresh_sessions())
            if is_first_msg and not self.cancel_event.is_set():
                self._schedule_catchy_title(user_message)
        elif self.cancel_event.is_set():
            self.controller.after(0, lambda: self._show_bot_message("[Stopped]"))
        return full

    def _process_ai(self, user_message, is_first_msg):
        model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        try:
            prompt_emb_holder = [None]

            self.controller.after(0, lambda: self._update_generating_indicator("Preparing your question"))
            if precompute_prompt_embedding(
                user_message, prompt_emb_holder=prompt_emb_holder, cancel_event=self.cancel_event,
            ) is None:
                return

            if self.cancel_event.is_set():
                return

            self.controller.after(0, lambda: self._update_generating_indicator("Searching knowledge base"))

            from rag import find_answered_question_match
            source_filter = getattr(self, "active_source_filter", None)

            with ThreadPoolExecutor(max_workers=2) as pool:
                answered_future = pool.submit(
                    find_answered_question_match,
                    user_message,
                    prompt_emb_holder=prompt_emb_holder,
                    cancel_event=self.cancel_event,
                )
                rag_future = pool.submit(
                    query_rag,
                    user_message,
                    source_filter=source_filter,
                    prompt_emb_holder=prompt_emb_holder,
                    cancel_event=self.cancel_event,
                )
                answered_match = answered_future.result()
                rag_result = rag_future.result()

            if self.cancel_event.is_set():
                return
            if answered_match:
                self.controller.after(0, lambda: self._stop_generating_indicator())
                self.controller.after(0, lambda: self._show_bot_message(answered_match))
                ok, db_err = save_message(
                    self.controller.username, self.current_session_id, user_message, answered_match,
                )
                if not ok:
                    self.controller.after(0, lambda err=db_err: self._notify_db_error(err))
                self.controller.after(0, lambda: self.sidebar.refresh_sessions())
                if is_first_msg:
                    self._schedule_catchy_title(user_message)
                return

            if self.cancel_event.is_set():
                return

            rag_sources = None
            if rag_result is None:
                save_unanswered_question(user_message, self.controller.username)
                self.controller.after(
                    0,
                    lambda: self._update_generating_indicator("Generating answer (no document match)"),
                )
                sys = ""
            else:
                sys = rag_result["system_prompt"]
                rag_sources = rag_result.get("sources", [])
                best = rag_result.get("best_score", 0)
                self.controller.after(
                    0,
                    lambda: self._update_generating_indicator(
                        f"Generating answer from {len(rag_sources)} document(s) (match {best:.0%})"
                    ),
                )

            self._stream_ai_response(
                user_message, model, sys, is_first_msg, rag_sources=rag_sources,
            )

        except Exception as e:
            if not self.cancel_event.is_set():
                err_msg = str(e) if str(e) else format_ai_error(e)
                self.controller.after(0, lambda msg=err_msg: messagebox.showerror("AI Unavailable", msg))
        finally:
            if self.cancel_event.is_set():
                self.controller.after(0, lambda: self._stop_generating_indicator("Stopped."))
            else:
                self.controller.after(0, lambda: self._stop_generating_indicator())
            self.controller.after(0, lambda: self.send_btn.configure(state="normal"))
            self.controller.after(0, lambda: self.entry.configure(state="normal"))
            self.controller.after(0, lambda: self.stop_btn.configure(state="disabled"))

    def _schedule_catchy_title(self, prompt):
        """Wait before title generation so the main Ollama reply can finish first."""
        try:
            delay_ms = int(os.getenv("TITLE_GEN_DELAY_MS", "8000"))
        except ValueError:
            delay_ms = 3000
        self.controller.after(
            delay_ms,
            lambda: threading.Thread(target=self._generate_catchy_title, args=(prompt,), daemon=True).start(),
        )

    def _generate_catchy_title(self, prompt):
        """Asks the AI to create a short catchy title for the conversation."""
        title_prompt = f"Summarize the following topic into a catchy 3-word title for a sidebar. Reply ONLY with the title: {prompt}"
        try:
            # We use a short request to get just the title
            model_name = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
            try:
                title_predict = int(os.getenv("OLLAMA_TITLE_NUM_PREDICT", "32"))
            except ValueError:
                title_predict = 32
            gen = get_response(
                title_prompt,
                model_name,
                system_prompt="Reply with a short 3-word title only.",
                num_predict_override=title_predict,
            )
            title = "".join(list(gen)).strip()
            # Clean up quotes if AI adds them
            title = re.sub(r'["\']', '', title)
            # Cap it at 30 chars just in case
            title = title[:30]
            
            update_session_title(self.current_session_id, title)
            self.controller.after(0, lambda: self.sidebar.refresh_sessions())
        except Exception:
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
