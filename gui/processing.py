"""Reusable modal processing overlay."""
import customtkinter as ctk


class ProcessingWindow(ctk.CTkToplevel):
    def __init__(self, parent, title="Processing", message="Please wait...", show_progress=False, on_cancel=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("420x190")
        self.resizable(False, False)
        self.on_cancel = on_cancel
        self.is_cancelled = False

        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (420 // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (190 // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        if on_cancel:
            self.protocol("WM_DELETE_WINDOW", self.cancel)
        else:
            self.protocol("WM_DELETE_WINDOW", lambda: None)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=25, pady=20)

        ctk.CTkLabel(frame, text="⚙️", font=ctk.CTkFont(size=36)).pack(pady=(5, 5))
        self.msg_lbl = ctk.CTkLabel(frame, text=message, font=ctk.CTkFont(size=14, weight="bold"))
        self.msg_lbl.pack(pady=5)

        self.show_progress = show_progress
        if show_progress:
            self.progress_bar = ctk.CTkProgressBar(frame, width=320, height=8, progress_color=("#8E24AA", "#B388FF"))
            self.progress_bar.pack(pady=(10, 5))
            self.progress_bar.set(0.0)
        else:
            self.progress_bar = None

        self.detail_lbl = ctk.CTkLabel(frame, text="Working...", font=ctk.CTkFont(size=11), text_color="gray")
        self.detail_lbl.pack(pady=(5, 0))

        self.anim_dots = 0
        self.animate_loader()

    def animate_loader(self):
        if not self.winfo_exists():
            return
        self.anim_dots = (self.anim_dots + 1) % 4
        dots = "." * self.anim_dots
        if not self.show_progress:
            self.detail_lbl.configure(text=f"Please wait{dots}")
        self.after(500, self.animate_loader)

    def update_message(self, message):
        self.msg_lbl.configure(text=message)
        self.update()

    def update_progress(self, current, total):
        if self.progress_bar:
            self.progress_bar.set(current / total)
            self.detail_lbl.configure(text=f"Progress: {current} of {total} chunks...")
            self.update()

    def update_detail(self, text):
        self.detail_lbl.configure(text=text)
        self.update()

    def finish(self):
        self.grab_release()
        self.destroy()

    def cancel(self):
        self.is_cancelled = True
        if self.on_cancel:
            self.on_cancel()
        self.finish()
