
# ===== LOGIN & SIGN-UP WINDOWS =====
# Provides a styled Login screen and a Sign-Up screen using CustomTkinter.
# On successful login, the main OfflineChatbot window is launched.

import customtkinter as ctk
from tkinter import messagebox
from auth import login_user, register_user


# ─────────────────────────────────────────────
#  Helper: re-usable labelled entry widget
# ─────────────────────────────────────────────
def _make_field(parent, label_text: str, placeholder: str, show: str = "") -> ctk.CTkEntry:
    """Create a label + entry pair and return the CTkEntry widget."""
    ctk.CTkLabel(parent, text=label_text, anchor="w",
                 font=ctk.CTkFont(size=13)).pack(fill="x", padx=40, pady=(10, 2))
    entry = ctk.CTkEntry(parent, placeholder_text=placeholder,
                         height=42, show=show,
                         font=ctk.CTkFont(size=13),
                         corner_radius=10)
    entry.pack(fill="x", padx=40)
    return entry


# ─────────────────────────────────────────────
#  SIGN-UP FRAME
# ─────────────────────────────────────────────
class SignUpFrame(ctk.CTkFrame):
    """
    Frame that collects new-user details:
      full name · username · email · password · confirm password
    """

    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

        # ── Header ──────────────────────────────
        ctk.CTkLabel(self, text="🚀  Create Account",
                     font=ctk.CTkFont(size=26, weight="bold")).pack(pady=(20, 2))
        ctk.CTkLabel(self, text="Join ChatOff and start chatting offline",
                     font=ctk.CTkFont(size=13),
                     text_color="gray").pack(pady=(0, 6))

        # ── Form fields ─────────────────────────
        self.full_name_entry  = _make_field(self, "Full Name",        "e.g. Alice Smith")
        self.username_entry   = _make_field(self, "Username",         "e.g. alice123")
        self.email_entry      = _make_field(self, "Email Address",    "e.g. alice@example.com")
        self.password_entry   = _make_field(self, "Password",         "Min. 6 characters", show="•")
        self.confirm_entry    = _make_field(self, "Confirm Password", "Re-enter password",  show="•")

        # Allow Enter key to submit
        self.confirm_entry.bind("<Return>", lambda e: self._submit())

        # ── Error label ─────────────────────────
        self.error_label = ctk.CTkLabel(self, text="", text_color="#FF6B6B",
                                        font=ctk.CTkFont(size=12), wraplength=380)
        self.error_label.pack(pady=(6, 0))

        # ── Buttons ─────────────────────────────
        ctk.CTkButton(self, text="Create Account",
                      height=44, corner_radius=10,
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._submit).pack(fill="x", padx=40, pady=(10, 4))

        # Divider or Link back
        ctk.CTkButton(self, text="Already have an account? Login",
                      height=36, corner_radius=10,
                      fg_color="transparent",
                      border_width=1,
                      font=ctk.CTkFont(size=13),
                      command=lambda: controller.show_frame(LoginFrame)).pack(fill="x", padx=40, pady=(0, 20))

    # ── Submit handler ──────────────────────────
    def _submit(self):
        full_name = self.full_name_entry.get().strip()
        username  = self.username_entry.get().strip()
        email     = self.email_entry.get().strip()
        password  = self.password_entry.get()
        confirm   = self.confirm_entry.get()

        # Client-side validation
        if not all([full_name, username, email, password, confirm]):
            self._show_error("⚠  Please fill in all fields.")
            return

        if password != confirm:
            self._show_error("⚠  Passwords do not match.")
            return

        # Attempt registration
        ok, msg = register_user(full_name, username, email, password)
        if ok:
            messagebox.showinfo("Account Created",
                                f"Welcome, {full_name}! 🎉\nYou can now log in.")
            self.controller.show_frame(LoginFrame)
        else:
            self._show_error(f"⚠  {msg}")

    def _show_error(self, text: str):
        self.error_label.configure(text=text)


# ─────────────────────────────────────────────
#  LOGIN FRAME
# ─────────────────────────────────────────────
class LoginFrame(ctk.CTkFrame):
    """
    Frame for user login.
    """

    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

        ctk.CTkLabel(self, text="Welcome back 👋",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(24, 4))
        ctk.CTkLabel(self, text="Log in to continue",
                     font=ctk.CTkFont(size=13), text_color="gray").pack(pady=(0, 10))

        self.username_entry = _make_field(self, "Username", "Enter your username")
        self.password_entry = _make_field(self, "Password", "Enter your password", show="•")

        # Allow Enter key to submit
        self.password_entry.bind("<Return>", lambda e: self._login())

        # ── Error label ─────────────────────────
        self.error_label = ctk.CTkLabel(self, text="", text_color="#FF6B6B",
                                        font=ctk.CTkFont(size=12), wraplength=340)
        self.error_label.pack(pady=(6, 0))

        # ── Login button ─────────────────────────
        ctk.CTkButton(self, text="Login",
                      height=44, corner_radius=10,
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._login).pack(fill="x", padx=40, pady=(14, 6))

        # ── Divider ───────────────────────────────────
        ctk.CTkLabel(self, text="─────  or  ─────",
                     font=ctk.CTkFont(size=12), text_color="gray").pack(pady=4)

        # ── Sign-up button ────────────────────────
        ctk.CTkButton(self, text="✨  Don't have an account? Sign Up",
                      height=44, corner_radius=10,
                      fg_color=("#0097A7", "#006064"),
                      hover_color=("#00838F", "#004D40"),
                      text_color="white",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=lambda: controller.show_frame(SignUpFrame)).pack(fill="x", padx=40, pady=(0, 20))

    # ── Login handler ────────────────────────────
    def _login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        ok, result = login_user(username, password)
        if ok:
            self.controller.logged_in_user     = result    # result is full_name on success
            self.controller.logged_in_username = username  # keep the login handle for DB lookups
            self.controller._launch_chatbot()
        else:
            self._show_error(f"⚠  {result}")

    def _show_error(self, text: str):
        self.error_label.configure(text=text)


# ─────────────────────────────────────────────
#  LOGIN WINDOW (Main Container)
# ─────────────────────────────────────────────
class LoginWindow(ctk.CTk):
    """
    Main entry-point window that swaps between Login and Sign Up frames.
    """

    def __init__(self):
        super().__init__()

        self.title("ChatOff — Login")
        self.resizable(True, True)

        # Auto-size and center on screen
        win_w, win_h = 480, 680
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - win_w) // 2
        y  = (sh - win_h) // 2
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.minsize(420, 620)
        self.after(10, lambda: self.state("zoomed"))  # Maximize after window draws

        self.logged_in_user: str = ""
        self.logged_in_username: str = ""

        # ── Hero / branding section (persistent) ──────────────
        hero = ctk.CTkFrame(self, corner_radius=0, fg_color=("#1565C0", "#0D1B2A"))
        hero.pack(fill="x")

        ctk.CTkLabel(hero, text="💬  ChatOff",
                     font=ctk.CTkFont(size=34, weight="bold"),
                     text_color="white").pack(pady=(18, 2))
        ctk.CTkLabel(hero, text="Your offline AI companion",
                     font=ctk.CTkFont(size=14),
                     text_color="#90CAF9").pack(pady=(0, 16))

        # ── Frame Container ────────────────────────────
        self.container = ctk.CTkFrame(self, corner_radius=16)
        self.container.pack(fill="both", expand=True, padx=24, pady=16)

        # Initialize frames
        self.frames = {}
        for F in (LoginFrame, SignUpFrame):
            frame = F(self.container, self)
            self.frames[F] = frame

        self.show_frame(LoginFrame)

    def show_frame(self, frame_class):
        """Show a frame for the given class."""
        # Hide all frames
        for frame in self.frames.values():
            frame.pack_forget()
        
        # Show the requested frame
        frame = self.frames[frame_class]
        frame.pack(fill="both", expand=True)

    def _launch_chatbot(self):
        """Destroy the login window and open the main chatbot window."""
        from GUI import OfflineChatbot
        self.destroy()
        app = OfflineChatbot(
            user_name=self.logged_in_user,
            username=self.logged_in_username
        )
        app.mainloop()
