# ===== MAIN CHATBOT WINDOW =====
# Loads chat history from MySQL on startup, saves every message,
# supports Knowledge Base management, and injects KB context into the AI.

import customtkinter as ctk
import threading
from tkinter import messagebox
from chatbot import get_response
from auth import (
    save_message, load_history, clear_history,
    add_knowledge, get_all_knowledge, delete_knowledge,
    build_system_prompt
)

# Set UI theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# ─────────────────────────────────────────────
#  KNOWLEDGE BASE MODAL WINDOW
# ─────────────────────────────────────────────
class KnowledgeBaseWindow(ctk.CTkToplevel):
    """
    Modal window to manage the knowledge base (option table).
    Users can add, view, and delete entries that are injected
    as system context into every AI response.
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.title("📚 Knowledge Base")
        self.geometry("620x580")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        # ── Header ──────────────────────────────
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("#0097A7", "#006064"))
        header.pack(fill="x")

        ctk.CTkLabel(
            header, text="📚  Knowledge Base",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white"
        ).pack(pady=(18, 4))
        ctk.CTkLabel(
            header,
            text="Entries are injected as context into every AI response",
            font=ctk.CTkFont(size=12),
            text_color="#B2EBF2"
        ).pack(pady=(0, 16))

        # ── Add entry form ───────────────────────
        form = ctk.CTkFrame(self, corner_radius=12)
        form.pack(fill="x", padx=20, pady=(16, 8))

        ctk.CTkLabel(form, text="Title", font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").pack(fill="x", padx=16, pady=(12, 2))
        self.title_entry = ctk.CTkEntry(form, placeholder_text="e.g. Company Name", height=38,
                                        corner_radius=8)
        self.title_entry.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(form, text="Content", font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").pack(fill="x", padx=16, pady=(0, 2))
        self.content_box = ctk.CTkTextbox(form, height=80, corner_radius=8,
                                          font=ctk.CTkFont(size=13))
        self.content_box.pack(fill="x", padx=16, pady=(0, 8))

        self.form_error = ctk.CTkLabel(form, text="", text_color="#FF6B6B",
                                       font=ctk.CTkFont(size=12))
        self.form_error.pack()

        ctk.CTkButton(form, text="➕  Add to Knowledge Base",
                      height=40, corner_radius=8,
                      fg_color=("#0097A7", "#006064"),
                      hover_color=("#00838F", "#004D40"),
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=self._add_entry).pack(fill="x", padx=16, pady=(4, 14))

        # ── Existing entries list ────────────────
        list_header = ctk.CTkFrame(self, fg_color="transparent")
        list_header.pack(fill="x", padx=20, pady=(4, 0))

        ctk.CTkLabel(list_header, text="Saved Entries",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")

        ctk.CTkButton(list_header, text="Clear All",
                      width=80, height=28, corner_radius=6,
                      fg_color="transparent", border_width=1,
                      text_color=("#CC0000", "#FF6B6B"),
                      border_color=("#CC0000", "#FF6B6B"),
                      hover_color=("#FFE0E0", "#3A1010"),
                      font=ctk.CTkFont(size=12),
                      command=self._clear_all).pack(side="right")

        # Scrollable frame for entries
        self.entries_frame = ctk.CTkScrollableFrame(self, corner_radius=10, height=160)
        self.entries_frame.pack(fill="both", expand=True, padx=20, pady=(6, 16))

        self._refresh_entries()

    # ── Add entry ──────────────────────────────
    def _add_entry(self):
        title   = self.title_entry.get().strip()
        content = self.content_box.get("1.0", "end").strip()

        ok, msg = add_knowledge(title, content)
        if ok:
            self.title_entry.delete(0, "end")
            self.content_box.delete("1.0", "end")
            self.form_error.configure(text="")
            self._refresh_entries()
        else:
            self.form_error.configure(text=f"⚠  {msg}")

    # ── Refresh entry list ─────────────────────
    def _refresh_entries(self):
        for widget in self.entries_frame.winfo_children():
            widget.destroy()

        entries = get_all_knowledge()

        if not entries:
            ctk.CTkLabel(self.entries_frame, text="No entries yet. Add one above.",
                         text_color="gray", font=ctk.CTkFont(size=13)).pack(pady=20)
            return

        for entry in entries:
            row = ctk.CTkFrame(self.entries_frame, corner_radius=8)
            row.pack(fill="x", pady=4)

            # Title + content preview
            text_frame = ctk.CTkFrame(row, fg_color="transparent")
            text_frame.pack(side="left", fill="both", expand=True, padx=(12, 4), pady=8)

            ctk.CTkLabel(
                text_frame,
                text=entry["title"],
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w"
            ).pack(fill="x")

            preview = entry["content"][:80] + ("…" if len(entry["content"]) > 80 else "")
            ctk.CTkLabel(
                text_frame,
                text=preview,
                font=ctk.CTkFont(size=11),
                text_color="gray",
                anchor="w",
                wraplength=380
            ).pack(fill="x")

            # Delete button
            eid = entry["id"]
            ctk.CTkButton(
                row, text="🗑", width=36, height=36,
                corner_radius=6,
                fg_color="transparent",
                text_color=("#CC0000", "#FF6B6B"),
                hover_color=("#FFE0E0", "#3A1010"),
                font=ctk.CTkFont(size=16),
                command=lambda i=eid: self._delete_entry(i)
            ).pack(side="right", padx=8, pady=8)

    # ── Delete single entry ────────────────────
    def _delete_entry(self, entry_id: int):
        delete_knowledge(entry_id)
        self._refresh_entries()

    # ── Clear all entries ──────────────────────
    def _clear_all(self):
        if messagebox.askyesno(
            "Clear Knowledge Base",
            "Delete ALL knowledge base entries? This cannot be undone.",
            parent=self
        ):
            from auth import clear_knowledge
            clear_knowledge()
            self._refresh_entries()


# ─────────────────────────────────────────────
#  MAIN CHATBOT WINDOW
# ─────────────────────────────────────────────
class OfflineChatbot(ctk.CTk):
    def __init__(self, user_name: str = "User", username: str = ""):
        super().__init__()

        self.user_name = user_name
        self.username  = username or user_name.lower().replace(" ", "")

        self.title("ChatOff AI 🤖")

        # Auto fullscreen: detect screen resolution and fill it
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.geometry(f"{screen_w}x{screen_h}+0+0")
        self.state("zoomed")  # also maximise for taskbar-aware platforms

        # Grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ===== SIDEBAR =====
        self.sidebar_frame = ctk.CTkFrame(self, width=210, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            self.sidebar_frame, text="💬 ChatOff AI",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(20, 4))

        ctk.CTkLabel(
            self.sidebar_frame,
            text=f"👤 {self.user_name}",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).grid(row=1, column=0, padx=20, pady=(0, 10))

        # Model selector
        ctk.CTkLabel(self.sidebar_frame, text="Select Model:", anchor="w"
                     ).grid(row=2, column=0, padx=20, pady=(10, 0))

        self.model_optionemenu = ctk.CTkOptionMenu(
            self.sidebar_frame, values=["llama3", "mistral", "phi3"]
        )
        self.model_optionemenu.grid(row=3, column=0, padx=20, pady=(6, 10))
        self.model_optionemenu.set("llama3")

        # Appearance selector
        ctk.CTkLabel(self.sidebar_frame, text="Appearance:", anchor="w"
                     ).grid(row=5, column=0, padx=20, pady=(10, 0))

        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["Dark", "Light", "System"],
            command=self.change_appearance_mode_event
        )
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(6, 14))

        # ── Knowledge Base button ─────────────────
        ctk.CTkButton(
            self.sidebar_frame,
            text="📚  Knowledge Base",
            height=38, corner_radius=8,
            fg_color=("#0097A7", "#006064"),
            hover_color=("#00838F", "#004D40"),
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._open_knowledge_base
        ).grid(row=7, column=0, padx=20, pady=(0, 6))

        # ── Clear History button ──────────────────
        ctk.CTkButton(
            self.sidebar_frame,
            text="🗑  Clear History",
            height=36, corner_radius=8,
            fg_color="transparent", border_width=1,
            text_color=("gray40", "gray60"),
            border_color=("gray50", "gray40"),
            hover_color=("gray85", "gray25"),
            font=ctk.CTkFont(size=13),
            command=self._clear_history
        ).grid(row=8, column=0, padx=20, pady=(0, 6))

        # ── Logout button ─────────────────────────
        ctk.CTkButton(
            self.sidebar_frame,
            text="⇠ Logout",
            height=36, corner_radius=8,
            fg_color="transparent", border_width=1,
            text_color=("#CC0000", "#FF6B6B"),
            border_color=("#CC0000", "#FF6B6B"),
            hover_color=("#FFE0E0", "#3A1010"),
            font=ctk.CTkFont(size=13),
            command=self._logout
        ).grid(row=9, column=0, padx=20, pady=(0, 20))

        # ===== MAIN CHAT AREA =====
        self.chat_area = ctk.CTkTextbox(self, font=ctk.CTkFont(size=14))
        self.chat_area.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="nsew")
        self.chat_area.configure(state="disabled")

        # ===== INPUT AREA =====
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=1, column=1, padx=20, pady=16, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Type your message here…",
            height=42
        )
        self.entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.entry.bind("<Return>", lambda e: self.send_message())

        self.send_button = ctk.CTkButton(
            self.input_frame, text="Send",
            width=100, height=42,
            font=ctk.CTkFont(weight="bold"),
            command=self.send_message
        )
        self.send_button.grid(row=0, column=1)

        # ── Load previous chat history ────────────
        self._load_previous_history()


    # ===== APPEARANCE =====
    def change_appearance_mode_event(self, new_mode: str):
        ctk.set_appearance_mode(new_mode)

    # ===== KNOWLEDGE BASE =====
    def _open_knowledge_base(self):
        KnowledgeBaseWindow(self)

    # ===== LOGOUT =====
    def _logout(self):
        from login import LoginWindow
        self.destroy()
        login = LoginWindow()
        login.mainloop()

    # ===== CLEAR HISTORY =====
    def _clear_history(self):
        if messagebox.askyesno(
            "Clear History",
            "Delete all your chat history? This cannot be undone.",
            parent=self
        ):
            clear_history(self.username)
            self.chat_area.configure(state="normal")
            self.chat_area.delete("1.0", "end")
            self.chat_area.configure(state="disabled")

    # ===== LOAD HISTORY =====
    def _load_previous_history(self):
        """Populate chat area with the last 100 stored messages."""
        rows = load_history(self.username, limit=100)
        if not rows:
            return

        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", "── Previous conversation ──\n\n", "gray")

        for row in rows:
            sender_label = "You" if row["sender"] == "user" else "Bot"
            self.chat_area.insert("end", f"{sender_label}: ", "bold")
            self.chat_area.insert("end", f"{row['message']}\n\n")

        self.chat_area.insert("end", "── New session ──\n\n", "gray")
        self.chat_area.configure(state="disabled")
        self.chat_area.see("end")

    # ===== DISPLAY IN CHAT =====
    def append_chat(self, sender, message):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", f"\n{sender}: ", "bold")
        self.chat_area.insert("end", f"{message}\n")
        self.chat_area.configure(state="disabled")
        self.chat_area.see("end")

    # ===== SEND MESSAGE =====
    def send_message(self):
        user_msg = self.entry.get()
        if not user_msg.strip():
            return

        self.entry.delete(0, "end")
        self.append_chat("You", user_msg)

        save_message(self.username, "user", user_msg, self.model_optionemenu.get())

        self.send_button.configure(state="disabled")
        threading.Thread(
            target=self.process_ai_response,
            args=(user_msg,),
            daemon=True
        ).start()

    # ===== AI RESPONSE =====
    def process_ai_response(self, prompt):
        model      = self.model_optionemenu.get()
        sys_prompt = build_system_prompt()   # fetch KB context from MySQL
        collected  = []

        try:
            self.after(0, lambda: self.chat_area.configure(state="normal"))
            self.after(0, lambda: self.chat_area.insert("end", "\nBot: ", "bold"))

            for chunk in get_response(prompt, model, system_prompt=sys_prompt):
                collected.append(chunk)
                self.after(0, lambda c=chunk: self.update_streaming_chat(c))

            self.after(0, lambda: self.chat_area.insert("end", "\n"))
            self.after(0, lambda: self.chat_area.configure(state="disabled"))
            self.after(0, lambda: self.chat_area.see("end"))

            full_reply = "".join(collected)
            save_message(self.username, "bot", full_reply, model)

        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.after(0, lambda: self.append_chat("System", f"Error: {error_msg}"))

        finally:
            self.after(0, lambda: self.send_button.configure(state="normal"))

    # ===== STREAMING UPDATE =====
    def update_streaming_chat(self, content):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", content)
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")
